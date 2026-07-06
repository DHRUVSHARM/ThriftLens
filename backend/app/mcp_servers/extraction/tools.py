from __future__ import annotations

import re
from typing import Any, Protocol

from app.config import get_settings
from app.gemini_provider import GeminiExtractionProvider
from app.product_safety import (
    DISALLOWED_IMAGE_UNSAFE_REASONS,
    INSUFFICIENT_PRODUCT_DETAIL_MESSAGE,
    MALFORMED_TEXT_MESSAGE,
    MISSING_PRODUCT_DESCRIPTION_MESSAGE,
    NON_PRODUCT_REQUEST_MESSAGE,
    KNOWN_PRODUCT_HINT_TERMS,
    PROMPT_INJECTION_MESSAGE,
    TEXT_COMMAND_PATTERNS,
    TEXT_INJECTION_PATTERNS,
    TEXT_STOPWORDS,
    has_known_product_hint_text,
    matched_text_unsafe_rules,
    text_safety_message_for_reason,
)
from app.sample_providers import SampleExtractionProvider
from app.tool_policy import ToolExecutionPolicy
from app.workflow_contracts import (
    DetectedProduct,
    ImageGateResult,
    ImageSafetyResult,
    ProductReference,
    TargetProductSelection,
    TextSafetyResult,
    model_dump_alias,
)


class ExtractionProviderProtocol(Protocol):
    async def screen_image_safety(
        self,
        *,
        request_payload: dict[str, Any],
        image_metadata: list[dict[str, Any]],
    ) -> dict[str, Any]:
        ...

    async def screen_text_safety(self, *, request_payload: dict[str, Any]) -> dict[str, Any]:
        ...

    async def gate_image(self, *, request_payload: dict[str, Any], image_metadata: list[dict[str, Any]]) -> dict[str, Any]:
        ...

    async def extract(
        self,
        *,
        input_type: str,
        request_payload: dict[str, Any],
        image_metadata: list[dict[str, Any]],
    ) -> dict[str, Any]:
        ...

    async def repair(self, raw_output: dict[str, Any]) -> dict[str, Any]:
        ...


def build_extraction_provider(policy: ToolExecutionPolicy | None = None) -> ExtractionProviderProtocol:
    settings = get_settings()
    if settings.provider_mode == "REAL_MODE":
        return GeminiExtractionProvider(policy=policy)
    return SampleExtractionProvider()


async def screen_image_safety_tool(
    *,
    request_payload: dict[str, Any],
    image_metadata: list[dict[str, Any]],
    extraction_provider: ExtractionProviderProtocol | None = None,
) -> dict[str, Any]:
    provider = extraction_provider or build_extraction_provider()
    safety = ImageSafetyResult.model_validate(
        await provider.screen_image_safety(request_payload=request_payload, image_metadata=image_metadata)
    )
    return model_dump_alias(_with_default_safety_message(safety))


async def screen_text_safety_tool(
    *,
    request_payload: dict[str, Any],
    extraction_provider: ExtractionProviderProtocol | None = None,
) -> dict[str, Any]:
    safety = await _screen_text_safety(request_payload, extraction_provider=extraction_provider)
    return model_dump_alias(safety)


async def image_product_gate_tool(
    *,
    request_payload: dict[str, Any],
    image_metadata: list[dict[str, Any]],
    extraction_provider: ExtractionProviderProtocol | None = None,
) -> dict[str, Any]:
    gate = await _load_image_gate(
        request_payload=request_payload,
        image_metadata=image_metadata,
        extraction_provider=extraction_provider,
    )
    return model_dump_alias(gate)


async def extract_product_reference_tool(
    *,
    input_type: str,
    request_payload: dict[str, Any],
    image_metadata: list[dict[str, Any]],
    extraction_provider: ExtractionProviderProtocol | None = None,
) -> dict[str, Any]:
    provider = extraction_provider or build_extraction_provider()
    reference = ProductReference.model_validate(
        await provider.extract(input_type=input_type, request_payload=request_payload, image_metadata=image_metadata)
    )
    return model_dump_alias(reference)


async def repair_product_reference_tool(
    *,
    raw_output: dict[str, Any],
    extraction_provider: ExtractionProviderProtocol | None = None,
) -> dict[str, Any]:
    provider = extraction_provider or build_extraction_provider()
    reference = ProductReference.model_validate(await provider.repair(raw_output))
    return model_dump_alias(reference)


async def disambiguate_target_product_tool(
    *,
    detected_products: list[dict[str, Any]],
    target_description: str | None = None,
) -> dict[str, Any]:
    products = [DetectedProduct.model_validate(product) for product in detected_products]
    target_terms = _terms(target_description or "")

    if not products:
        selection = TargetProductSelection(
            decision="needs_refinement",
            selectedProduct=None,
            reason="No product candidates were detected in the image.",
            clarificationPrompt="Add a short product description or upload a clearer product image.",
        )
        return model_dump_alias(selection)

    if len(products) == 1 and not target_terms:
        selection = TargetProductSelection(
            decision="selected",
            selectedProduct=products[0],
            reason="Only one product candidate was detected.",
            clarificationPrompt=None,
        )
        return model_dump_alias(selection)

    scored = sorted(
        ((_target_overlap(product, target_terms), product.confidence, product) for product in products),
        key=lambda item: (item[0], item[1]),
        reverse=True,
    )
    best_overlap, _, best_product = scored[0]
    runner_up_overlap = scored[1][0] if len(scored) > 1 else 0

    if target_terms and best_overlap > 0 and best_overlap > runner_up_overlap:
        selection = TargetProductSelection(
            decision="selected",
            selectedProduct=best_product,
            reason="The target description best matches one detected product.",
            clarificationPrompt=None,
        )
        return model_dump_alias(selection)

    selection = TargetProductSelection(
        decision="needs_refinement",
        selectedProduct=None,
        reason="Multiple product candidates are plausible.",
        clarificationPrompt=(
            "Multiple products or objects were detected. Add a short focus note, such as the item type, color, or location, "
            "or crop the image to one product."
        ),
    )
    return model_dump_alias(selection)


def _target_overlap(product: DetectedProduct, target_terms: set[str]) -> int:
    candidate_terms = _terms(" ".join(part for part in [product.label, product.location_hint] if part))
    return len(candidate_terms & target_terms)


def _with_default_safety_message(safety: ImageSafetyResult) -> ImageSafetyResult:
    safety = _normalize_safety_result(safety)
    if safety.safety_status == "safe" or safety.user_safe_message:
        return safety
    if safety.safety_status == "unclear":
        return safety.model_copy(
            update={
                "user_safe_message": "We could not verify this image is safe for product research. Please upload a clearer product-only image.",
            }
        )
    return safety.model_copy(
        update={
            "user_safe_message": "This image cannot be processed for product research. Please upload a clear product-only image without explicit, graphic, or sensitive content.",
        }
    )


def _normalize_safety_result(safety: ImageSafetyResult) -> ImageSafetyResult:
    if safety.safety_status != "unsafe":
        return safety

    normalized_reasons = {reason.strip().lower() for reason in safety.unsafe_reasons if reason.strip()}
    if normalized_reasons & DISALLOWED_IMAGE_UNSAFE_REASONS:
        return safety

    return safety.model_copy(
        update={
            "safety_status": "unclear",
            "unsafe_reasons": [],
            "user_safe_message": safety.user_safe_message
            or "Please provide an image that clearly shows the product you would like to research.",
        }
    )


async def _load_image_gate(
    *,
    request_payload: dict[str, Any],
    image_metadata: list[dict[str, Any]],
    extraction_provider: ExtractionProviderProtocol | None,
) -> ImageGateResult:
    provider = extraction_provider or build_extraction_provider()
    return ImageGateResult.model_validate(
        await provider.gate_image(request_payload=request_payload, image_metadata=image_metadata)
    )


def _terms(value: str) -> set[str]:
    return {term for term in re.findall(r"[a-z0-9]+", value.lower()) if len(term) > 2}


async def _screen_text_safety(
    request_payload: dict[str, Any],
    *,
    extraction_provider: ExtractionProviderProtocol | None = None,
) -> TextSafetyResult:
    deterministic = _deterministic_text_safety(request_payload)

    settings = get_settings()
    if settings.provider_mode != "REAL_MODE" or not settings.text_safety_model_enabled:
        return deterministic

    if deterministic.safety_status != "safe" and not _should_defer_text_safety_to_model(deterministic):
        return deterministic

    provider = extraction_provider or build_extraction_provider()
    try:
        model_safety = TextSafetyResult.model_validate(await provider.screen_text_safety(request_payload=request_payload))
    except Exception:
        return deterministic
    return _normalize_model_text_safety(model_safety, fallback=deterministic)


def _deterministic_text_safety(request_payload: dict[str, Any]) -> TextSafetyResult:
    text = _combined_user_text(request_payload)
    normalized = " ".join(text.split())
    if not normalized:
        return TextSafetyResult(
            safetyStatus="unclear",
            reason="missing_product_description",
            confidence=0.93,
            detectedPatterns=[],
            userSafeMessage=MISSING_PRODUCT_DESCRIPTION_MESSAGE,
        )

    unsafe_rules = matched_text_unsafe_rules(normalized)
    if unsafe_rules:
        reasons = {rule.reason for rule in unsafe_rules}
        selected_reason = "regulated_product" if "regulated_product" in reasons else "unsafe_text"
        selected_message = next(
            (rule.user_safe_message for rule in unsafe_rules if rule.reason == selected_reason),
            unsafe_rules[0].user_safe_message,
        )
        return TextSafetyResult(
            safetyStatus="unsafe",
            reason=selected_reason,
            confidence=0.9,
            detectedPatterns=[rule.name for rule in unsafe_rules],
            userSafeMessage=selected_message,
        )

    injection_patterns = _matched_patterns(TEXT_INJECTION_PATTERNS, normalized)
    if injection_patterns:
        return TextSafetyResult(
            safetyStatus="unclear",
            reason="prompt_injection",
            confidence=0.9,
            detectedPatterns=injection_patterns,
            userSafeMessage=PROMPT_INJECTION_MESSAGE,
        )

    if _looks_malformed_text(normalized):
        return TextSafetyResult(
            safetyStatus="unclear",
            reason="malformed_text",
            confidence=0.86,
            detectedPatterns=["low_signal_text"],
            userSafeMessage=MALFORMED_TEXT_MESSAGE,
        )

    command_patterns = _matched_patterns(TEXT_COMMAND_PATTERNS, normalized)
    if command_patterns:
        return TextSafetyResult(
            safetyStatus="unclear",
            reason="non_product_request",
            confidence=0.84,
            detectedPatterns=command_patterns,
            userSafeMessage=NON_PRODUCT_REQUEST_MESSAGE,
        )

    if not _has_product_signal(normalized):
        return TextSafetyResult(
            safetyStatus="unclear",
            reason="insufficient_product_detail",
            confidence=0.75,
            detectedPatterns=["insufficient_product_signal"],
            userSafeMessage=INSUFFICIENT_PRODUCT_DETAIL_MESSAGE,
        )

    return TextSafetyResult(
        safetyStatus="safe",
        reason="product_description",
        confidence=0.88,
        detectedPatterns=[],
        userSafeMessage=None,
    )


def _normalize_model_text_safety(model_safety: TextSafetyResult, *, fallback: TextSafetyResult) -> TextSafetyResult:
    settings = get_settings()
    reason = _normalize_model_text_reason(model_safety.reason)
    if model_safety.safety_status == "unsafe":
        if reason not in {"regulated_product", "unsafe_text"}:
            return _model_unclear_text_safety(reason=reason, confidence=model_safety.confidence, detected_patterns=model_safety.detected_patterns)
        if model_safety.confidence >= settings.text_safety_model_unsafe_threshold:
            return model_safety.model_copy(
                update={
                    "reason": reason,
                    "user_safe_message": model_safety.user_safe_message or text_safety_message_for_reason(reason),
                }
            )
        return _model_unclear_text_safety(
            reason="safety_unclear",
            confidence=model_safety.confidence,
            detected_patterns=model_safety.detected_patterns,
        )

    if model_safety.safety_status == "unclear":
        return model_safety.model_copy(
            update={
                "reason": reason,
                "user_safe_message": model_safety.user_safe_message or text_safety_message_for_reason(reason),
            }
        )

    if reason != "product_description":
        return _model_unclear_text_safety(
            reason=reason,
            confidence=model_safety.confidence,
            detected_patterns=model_safety.detected_patterns,
        )
    if model_safety.confidence < settings.text_safety_model_safe_threshold:
        return _model_unclear_text_safety(
            reason="safety_unclear",
            confidence=model_safety.confidence,
            detected_patterns=model_safety.detected_patterns,
        )
    if fallback.safety_status != "safe":
        return model_safety.model_copy(
            update={
                "reason": "product_description",
                "user_safe_message": None,
            }
        )
    return fallback.model_copy(update={"confidence": max(fallback.confidence, model_safety.confidence)})


def _normalize_model_text_reason(reason: str) -> str:
    allowed = {
        "product_description",
        "regulated_product",
        "unsafe_text",
        "prompt_injection",
        "non_product_request",
        "malformed_text",
        "insufficient_product_detail",
        "safety_unclear",
    }
    normalized = reason.strip().lower()
    return normalized if normalized in allowed else "safety_unclear"


def _model_unclear_text_safety(
    *,
    reason: str,
    confidence: float,
    detected_patterns: list[str],
) -> TextSafetyResult:
    return TextSafetyResult(
        safetyStatus="unclear",
        reason=reason,
        confidence=max(0, min(confidence, 1)),
        detectedPatterns=detected_patterns or ["model_safety_unclear"],
        userSafeMessage=text_safety_message_for_reason(reason),
    )


def _should_defer_text_safety_to_model(safety: TextSafetyResult) -> bool:
    return safety.safety_status == "unclear" and safety.reason == "insufficient_product_detail"


def _combined_user_text(request_payload: dict[str, Any]) -> str:
    parts = [
        request_payload.get("textDescription"),
        request_payload.get("targetDescription"),
    ]
    return " ".join(str(part) for part in parts if isinstance(part, str) and part.strip())


def _matched_patterns(patterns: dict[str, re.Pattern[str]], text: str) -> list[str]:
    return [name for name, pattern in patterns.items() if pattern.search(text)]


def _looks_malformed_text(text: str) -> bool:
    compact = re.sub(r"\s+", "", text.lower())
    if len(re.sub(r"[^a-z0-9]", "", compact)) < 3:
        return True
    alpha = re.sub(r"[^a-z]", "", compact)
    if len(alpha) >= 6 and not re.search(r"[aeiouy]", alpha):
        return True
    if len(alpha) >= 6 and max(alpha.count(character) for character in set(alpha)) / len(alpha) >= 0.72:
        return True
    tokens = _text_tokens(text)
    return len(tokens) == 1 and not _has_product_signal(text) and len(tokens[0]) > 5


def _has_product_signal(text: str) -> bool:
    if has_known_product_hint_text(text):
        return True
    tokens = [token for token in _text_tokens(text) if token not in TEXT_STOPWORDS]
    return any(token in KNOWN_PRODUCT_HINT_TERMS for token in tokens)


def _text_tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9][a-z0-9-]*", text.lower())
