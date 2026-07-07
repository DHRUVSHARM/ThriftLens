from __future__ import annotations

import asyncio
import json
import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.config import Settings, get_settings
from app.gemini_provider import SYSTEM_BOUNDARY
from app.ranking import (
    detect_ranked_mismatches,
    explain_ranked_products,
    group_ranked_products,
    score_products,
)
from app.tool_policy import ToolExecutionPolicy
from app.workflow_contracts import (
    CandidateMismatch,
    ProductDiscoveryProfile,
    ProductReference,
    ProductSearchContext,
    RankedProduct,
    SourceProduct,
    WorkflowProviderError,
    model_dump_alias,
)


class RankingModelCandidateAssessment(BaseModel):
    candidate_index: int = Field(alias="candidateIndex", ge=0)
    semantic_score: float = Field(alias="semanticScore", ge=0, le=1)
    reason: str
    mismatch_codes: list[str] = Field(default_factory=list, alias="mismatchCodes")

    model_config = ConfigDict(populate_by_name=True)


class RankingModelAssessment(BaseModel):
    candidates: list[RankingModelCandidateAssessment] = Field(default_factory=list)
    summary: str = ""


async def score_candidates_tool(
    *,
    product_reference: dict[str, Any],
    product_profile: dict[str, Any] | None,
    search_context: dict[str, Any] | None,
    source_products: list[dict[str, Any]],
    preferences: dict[str, Any] | None = None,
    settings: Settings | None = None,
    policy: ToolExecutionPolicy | None = None,
) -> list[dict[str, Any]]:
    active_settings = settings or get_settings()
    reference = ProductReference.model_validate(product_reference)
    profile = ProductDiscoveryProfile.model_validate(product_profile) if product_profile else None
    context = ProductSearchContext.model_validate(search_context) if search_context else None
    products = [SourceProduct.model_validate(product) for product in source_products]
    ranked = score_products(
        product_reference=reference,
        product_profile=profile,
        search_context=context,
        products=products,
        preferences=preferences or {},
    )

    if _ranking_model_enabled(active_settings) and ranked:
        try:
            assessment = await _model_score_candidates(
                product_reference=reference,
                product_profile=profile,
                search_context=context,
                ranked_products=ranked,
                settings=active_settings,
                policy=policy,
            )
            ranked = _merge_model_assessment(ranked, assessment)
        except WorkflowProviderError:
            pass
        except Exception:
            pass

    return [model_dump_alias(product) for product in ranked]


async def detect_mismatches_tool(
    *,
    product_reference: dict[str, Any],
    product_profile: dict[str, Any] | None,
    search_context: dict[str, Any] | None,
    ranked_products: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    reference = ProductReference.model_validate(product_reference)
    profile = ProductDiscoveryProfile.model_validate(product_profile) if product_profile else None
    context = ProductSearchContext.model_validate(search_context) if search_context else None
    ranked = [RankedProduct.model_validate(product) for product in ranked_products]
    return [
        model_dump_alias(product)
        for product in detect_ranked_mismatches(
            product_reference=reference,
            product_profile=profile,
            search_context=context,
            ranked_products=ranked,
        )
    ]


async def group_candidates_tool(
    *,
    ranked_products: list[dict[str, Any]],
    preferences: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    ranked = [RankedProduct.model_validate(product) for product in ranked_products]
    grouped = group_ranked_products(ranked_products=ranked, preferences=preferences or {})
    return [model_dump_alias(product) for product in grouped]


async def explain_match_tool(
    *,
    product_reference: dict[str, Any],
    product_profile: dict[str, Any] | None,
    search_context: dict[str, Any] | None,
    ranked_products: list[dict[str, Any]],
    settings: Settings | None = None,
    policy: ToolExecutionPolicy | None = None,
) -> dict[str, str]:
    active_settings = settings or get_settings()
    reference = ProductReference.model_validate(product_reference)
    profile = ProductDiscoveryProfile.model_validate(product_profile) if product_profile else None
    context = ProductSearchContext.model_validate(search_context) if search_context else None
    ranked = [RankedProduct.model_validate(product) for product in ranked_products]
    explanation = explain_ranked_products(
        product_reference=reference,
        product_profile=profile,
        search_context=context,
        ranked_products=ranked,
    )
    if _ranking_model_enabled(active_settings) and ranked:
        try:
            model_summary = await _model_explain_ranking(
                product_reference=reference,
                product_profile=profile,
                search_context=context,
                ranked_products=ranked,
                settings=active_settings,
                policy=policy,
            )
            if model_summary:
                explanation["modelSummary"] = model_summary
        except WorkflowProviderError:
            explanation["modelSummary"] = "Ranking model explanation was unavailable; deterministic explanation was used."
        except Exception:
            explanation["modelSummary"] = "Ranking model explanation was unavailable; deterministic explanation was used."
    return explanation


def _ranking_model_enabled(settings: Settings) -> bool:
    return settings.provider_mode == "REAL_MODE" and settings.gemini_ranking_enabled and bool(settings.gemini_provider_api_key())


async def _model_score_candidates(
    *,
    product_reference: ProductReference,
    product_profile: ProductDiscoveryProfile | None,
    search_context: ProductSearchContext | None,
    ranked_products: list[RankedProduct],
    settings: Settings,
    policy: ToolExecutionPolicy | None,
) -> RankingModelAssessment:
    async def call() -> RankingModelAssessment:
        from google import genai
        from google.genai import types

        candidate_payload = [
            {
                "candidateIndex": index,
                "sourceProduct": model_dump_alias(item.product),
                "deterministicScore": item.score,
                "scoreBreakdown": model_dump_alias(item.score_breakdown) if item.score_breakdown else None,
            }
            for index, item in enumerate(ranked_products[:20])
        ]
        client = genai.Client(api_key=settings.gemini_provider_api_key())
        prompt = (
            f"{SYSTEM_BOUNDARY}\n\n"
            "You are ranking source-backed product candidates. Use only the provided ProductReference, "
            "ProductDiscoveryProfile, ProductSearchContext, and SourceProduct fields. Do not invent facts, "
            "prices, retailers, URLs, materials, availability, or brands. Score semantic closeness from 0 to 1 "
            "and call out mismatches using these codes only: wrong_category, brand_conflict, model_conflict, "
            "material_conflict, style_conflict, missing_required_feature, price_out_of_range, weak_source_evidence.\n"
            f"ProductReference: {model_dump_alias(product_reference)}\n"
            f"ProductDiscoveryProfile: {model_dump_alias(product_profile) if product_profile else {}}\n"
            f"ProductSearchContext: {model_dump_alias(search_context) if search_context else {}}\n"
            f"Candidates: {candidate_payload}"
        )
        response = await asyncio.to_thread(
            client.models.generate_content,
            model=settings.gemini_ranking_model_name(),
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=RankingModelAssessment,
            ),
        )
        if not response.text:
            raise WorkflowProviderError("ranking_model_empty_response", "Ranking model returned no response.", retryable=True)
        return RankingModelAssessment.model_validate(json.loads(response.text))

    return await (policy or ToolExecutionPolicy()).run(dependency="gemini", operation="gemini_ranking_score", call=call)


async def _model_explain_ranking(
    *,
    product_reference: ProductReference,
    product_profile: ProductDiscoveryProfile | None,
    search_context: ProductSearchContext | None,
    ranked_products: list[RankedProduct],
    settings: Settings,
    policy: ToolExecutionPolicy | None,
) -> str:
    async def call() -> str:
        from google import genai

        client = genai.Client(api_key=settings.gemini_provider_api_key())
        payload = [model_dump_alias(item) for item in ranked_products[:5]]
        prompt = (
            f"{SYSTEM_BOUNDARY}\n\n"
            "Write one concise, user-safe ranking summary using only the provided ranking payload. "
            "Mention the strongest matching signals and any caveat. Do not invent facts.\n"
            f"ProductReference: {model_dump_alias(product_reference)}\n"
            f"ProductDiscoveryProfile: {model_dump_alias(product_profile) if product_profile else {}}\n"
            f"ProductSearchContext: {model_dump_alias(search_context) if search_context else {}}\n"
            f"RankedProducts: {payload}"
        )
        response = await asyncio.to_thread(
            client.models.generate_content,
            model=settings.gemini_ranking_model_name(),
            contents=prompt,
        )
        return _plain_model_summary(response.text or "")

    return await (policy or ToolExecutionPolicy()).run(dependency="gemini", operation="gemini_ranking_explain", call=call)


def _merge_model_assessment(
    ranked_products: list[RankedProduct],
    assessment: RankingModelAssessment,
) -> list[RankedProduct]:
    by_index = {item.candidate_index: item for item in assessment.candidates}
    merged: list[RankedProduct] = []
    for index, ranked in enumerate(ranked_products):
        model_item = by_index.get(index)
        if model_item is None:
            merged.append(ranked)
            continue
        score = round(max(0, min(1, (ranked.score * 0.65) + (model_item.semantic_score * 0.35))), 2)
        breakdown = ranked.score_breakdown
        if breakdown is not None:
            breakdown = breakdown.model_copy(update={"final_score": score})
        mismatches = list(ranked.mismatches)
        mismatches.extend(_model_mismatches(model_item))
        merged.append(
            ranked.model_copy(
                update={
                    "score": score,
                    "confidence": "high" if score >= 0.78 else "medium" if score >= 0.56 else "low",
                    "reason": model_item.reason[:360] or ranked.reason,
                    "score_breakdown": breakdown,
                    "mismatches": mismatches,
                }
            )
        )
    return merged


def _model_mismatches(model_item: RankingModelCandidateAssessment) -> list[CandidateMismatch]:
    allowed = {
        "wrong_category",
        "brand_conflict",
        "model_conflict",
        "material_conflict",
        "style_conflict",
        "missing_required_feature",
        "price_out_of_range",
        "weak_source_evidence",
    }
    return [
        CandidateMismatch(
            code=code,  # type: ignore[arg-type]
            severity="medium",
            message=_model_mismatch_message(code, model_item.reason),
            evidence=[model_item.reason[:180]] if model_item.reason else [],
        )
        for code in model_item.mismatch_codes
        if code in allowed
    ]


def _model_mismatch_message(code: str, reason: str) -> str:
    label = code.replace("_", " ")
    if reason:
        return f"{label}: {reason[:180]}"
    return f"Ranking model flagged {label}."


def _plain_model_summary(value: str) -> str:
    text = value.strip()
    if not text:
        return ""
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.DOTALL)
    if fenced:
        text = fenced.group(1).strip()
    if text.startswith("{") and text.endswith("}"):
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            return value.strip()
        if isinstance(parsed, dict):
            for key in ("summary", "modelSummary", "explanation", "text"):
                candidate = parsed.get(key)
                if isinstance(candidate, str) and candidate.strip():
                    return candidate.strip()
            return ""
    return value.strip()
