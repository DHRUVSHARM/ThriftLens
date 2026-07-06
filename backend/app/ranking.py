from __future__ import annotations

import re
from statistics import median
from typing import Any, Iterable, Literal

from app.workflow_contracts import (
    CandidateMismatch,
    ProductDiscoveryProfile,
    ProductReference,
    ProductSearchContext,
    RankedProduct,
    RankingScoreBreakdown,
    SourceProduct,
)


STOP_WORDS = {
    "a",
    "an",
    "and",
    "by",
    "for",
    "from",
    "in",
    "of",
    "on",
    "or",
    "the",
    "to",
    "with",
}


def deterministic_rank(product_reference: ProductReference, products: list[SourceProduct]) -> list[RankedProduct]:
    scored = score_products(
        product_reference=product_reference,
        product_profile=None,
        search_context=None,
        products=products,
        preferences={},
    )
    with_mismatches = detect_ranked_mismatches(
        product_reference=product_reference,
        product_profile=None,
        search_context=None,
        ranked_products=scored,
    )
    return group_ranked_products(ranked_products=with_mismatches, preferences={})


def score_products(
    *,
    product_reference: ProductReference,
    product_profile: ProductDiscoveryProfile | None,
    search_context: ProductSearchContext | None,
    products: list[SourceProduct],
    preferences: dict[str, Any],
) -> list[RankedProduct]:
    return [
        _score_single_product(
            product_reference=product_reference,
            product_profile=product_profile,
            search_context=search_context,
            product=product,
            preferences=preferences,
        )
        for product in products
    ]


def detect_ranked_mismatches(
    *,
    product_reference: ProductReference,
    product_profile: ProductDiscoveryProfile | None,
    search_context: ProductSearchContext | None,
    ranked_products: list[RankedProduct],
) -> list[RankedProduct]:
    adjusted: list[RankedProduct] = []
    for item in ranked_products:
        mismatches = _candidate_mismatches(
            product_reference=product_reference,
            product_profile=product_profile,
            search_context=search_context,
            product=item.product,
        )
        if not mismatches:
            adjusted.append(item)
            continue

        penalty = min(0.45, sum(_mismatch_weight(mismatch) for mismatch in mismatches))
        breakdown = item.score_breakdown or RankingScoreBreakdown(finalScore=item.score)
        updated_breakdown = breakdown.model_copy(
            update={
                "mismatch_penalty": max(breakdown.mismatch_penalty, penalty),
                "final_score": _clamp(item.score - penalty),
            }
        )
        updated_score = round(updated_breakdown.final_score, 2)
        adjusted.append(
            item.model_copy(
                update={
                    "score": updated_score,
                    "confidence": _confidence(updated_score),
                    "score_breakdown": updated_breakdown,
                    "mismatches": mismatches,
                    "reason": _reason(product_reference, item.product, updated_breakdown, mismatches),
                }
            )
        )
    return adjusted


def group_ranked_products(*, ranked_products: list[RankedProduct], preferences: dict[str, Any]) -> list[RankedProduct]:
    if not ranked_products:
        return []

    known_prices = [item.product.price for item in ranked_products if item.product.price is not None]
    median_price = median(known_prices) if known_prices else None
    grouped: list[RankedProduct] = []
    for item in ranked_products:
        group = _group_for_ranked_product(item, median_price=median_price)
        grouped.append(item.model_copy(update={"group": group}))

    return sorted(grouped, key=_group_sort_key)


def explain_ranked_products(
    *,
    product_reference: ProductReference,
    product_profile: ProductDiscoveryProfile | None,
    search_context: ProductSearchContext | None,
    ranked_products: list[RankedProduct],
) -> dict[str, str]:
    if not ranked_products:
        return {
            "summary": "No source-backed candidates were available to rank.",
            "method": "Ranking did not run because discovery returned no source products.",
        }

    top = ranked_products[0]
    profile_label = product_profile.refined_product_type if product_profile else product_reference.product_type
    signals = _top_signals(top)
    priorities = _display_terms(product_profile.ranking_priorities if product_profile else [], limit=4)
    must_have = _display_terms(search_context.must_have_details if search_context else [], limit=4)
    strategy_parts = []
    if product_profile:
        strategy_parts.append(f"classified as {product_profile.product_family.replace('_', ' ')}")
    if must_have:
        strategy_parts.append(f"checked required details: {', '.join(must_have)}")
    if priorities:
        strategy_parts.append(f"weighted shopper priorities: {', '.join(priorities)}")
    strategy = "; ".join(strategy_parts) if strategy_parts else "used extracted product details and source-backed metadata"
    mismatch_count = sum(len(item.mismatches) for item in ranked_products)
    candidate_word = "candidate" if len(ranked_products) == 1 else "candidates"
    return {
        "summary": (
            f"Compared {len(ranked_products)} source-backed {candidate_word} for the extracted "
            f"{profile_label}; {strategy}."
        ),
        "topMatch": (
            f"Top candidate: {top.product.title} from {top.product.retailer or top.product.source} "
            f"with {top.confidence} confidence."
        ),
        "signals": ", ".join(signals) if signals else "No strong positive signal dominated the result.",
        "caveats": (
            f"{mismatch_count} caveat(s) were detected across the result set."
            if mismatch_count
            else "No major mismatch caveats were detected from the available source data."
        ),
        "method": "Hybrid deterministic ranking with optional model overlay at the Ranking MCP boundary.",
    }


def _score_single_product(
    *,
    product_reference: ProductReference,
    product_profile: ProductDiscoveryProfile | None,
    search_context: ProductSearchContext | None,
    product: SourceProduct,
    preferences: dict[str, Any],
) -> RankedProduct:
    product_text = _join_text(
        [
            product.title,
            product.retailer,
            product.source,
            product.availability,
            product.freshness,
        ]
    )
    product_terms = _terms(product_text)

    type_terms = _terms(_join_text([product_reference.product_type, product_profile.refined_product_type if product_profile else ""]))
    title_terms = _terms(product_reference.title)
    feature_terms = _terms(product_reference.key_features)
    material_terms = _terms(product_reference.materials)
    color_terms = _terms([product_reference.color] if product_reference.color else [])
    style_terms = _terms(search_context.style_terms if search_context else [])
    must_have_terms = _terms(search_context.must_have_details if search_context else [product_reference.product_type])

    product_type_match = _overlap_score(type_terms | title_terms, product_terms, required=type_terms)
    brand_model_match = _brand_model_score(product_reference, product_terms)
    visual_attribute_match = _overlap_score(color_terms | feature_terms, product_terms)
    feature_match = _overlap_score(feature_terms | must_have_terms, product_terms)
    material_color_style_match = _overlap_score(material_terms | color_terms | style_terms, product_terms)
    price_preference_fit = _price_preference_fit(product.price, preferences)
    source_confidence = _source_confidence(product)
    availability_confidence = _availability_confidence(product.availability)

    breakdown = RankingScoreBreakdown(
        productTypeMatch=product_type_match,
        brandModelMatch=brand_model_match,
        visualAttributeMatch=visual_attribute_match,
        featureMatch=feature_match,
        materialColorStyleMatch=material_color_style_match,
        pricePreferenceFit=price_preference_fit,
        sourceConfidence=source_confidence,
        availabilityConfidence=availability_confidence,
        mismatchPenalty=0,
        finalScore=0,
    )
    preliminary = _weighted_score(breakdown, product_profile)
    breakdown = breakdown.model_copy(update={"final_score": preliminary})
    score = round(preliminary, 2)

    return RankedProduct(
        product=product,
        score=score,
        group="possible",
        confidence=_confidence(score),
        reason=_reason(product_reference, product, breakdown, []),
        scoreBreakdown=breakdown,
        mismatches=[],
    )


def _weighted_score(breakdown: RankingScoreBreakdown, profile: ProductDiscoveryProfile | None) -> float:
    family = profile.product_family if profile else "general"
    weights = {
        "product_type_match": 0.20,
        "brand_model_match": 0.10,
        "visual_attribute_match": 0.14,
        "feature_match": 0.16,
        "material_color_style_match": 0.15,
        "price_preference_fit": 0.08,
        "source_confidence": 0.10,
        "availability_confidence": 0.07,
    }
    if family == "electronics":
        weights.update({"brand_model_match": 0.20, "feature_match": 0.20, "material_color_style_match": 0.08})
    elif family in {"apparel", "furniture", "home_goods"}:
        weights.update({"visual_attribute_match": 0.17, "material_color_style_match": 0.18, "brand_model_match": 0.07})
    elif family == "home_improvement":
        weights.update({"feature_match": 0.20, "product_type_match": 0.23, "brand_model_match": 0.08})

    total = sum(
        getattr(breakdown, key) * weight
        for key, weight in weights.items()
    )
    return _clamp(total - breakdown.mismatch_penalty)


def _candidate_mismatches(
    *,
    product_reference: ProductReference,
    product_profile: ProductDiscoveryProfile | None,
    search_context: ProductSearchContext | None,
    product: SourceProduct,
) -> list[CandidateMismatch]:
    text = _join_text([product.title, product.retailer, product.source, product.availability]).lower()
    product_terms = _terms(text)
    mismatches: list[CandidateMismatch] = []

    type_terms = _terms([product_reference.product_type, product_profile.refined_product_type if product_profile else ""])
    if type_terms and not (type_terms & product_terms):
        mismatches.append(
            CandidateMismatch(
                code="wrong_category",
                severity="medium",
                message="The source title does not clearly share the extracted product category.",
                evidence=[product.title],
            )
        )

    if product_reference.brand:
        brand_terms = _terms(product_reference.brand)
        if brand_terms and not (brand_terms & product_terms):
            mismatches.append(
                CandidateMismatch(
                    code="brand_conflict",
                    severity="low",
                    message="The extracted brand was not visible in the source product title.",
                    evidence=[product_reference.brand, product.title],
                )
            )

    material_terms = _terms(product_reference.materials)
    if material_terms and not (material_terms & product_terms):
        mismatches.append(
            CandidateMismatch(
                code="material_conflict",
                severity="low",
                message="The extracted material was not confirmed by the source title.",
                evidence=[", ".join(product_reference.materials), product.title],
            )
        )

    must_have_terms = _terms(search_context.must_have_details if search_context else product_reference.key_features)
    missing_required = sorted(term for term in must_have_terms if term not in product_terms)
    if len(missing_required) >= max(1, min(3, len(must_have_terms))):
        mismatches.append(
            CandidateMismatch(
                code="missing_required_feature",
                severity="medium",
                message="Several required product details were not visible in the source title.",
                evidence=missing_required[:5],
            )
        )

    if not product.url or product.price is None:
        missing = []
        if not product.url:
            missing.append("source URL")
        if product.price is None:
            missing.append("source price")
        mismatches.append(
            CandidateMismatch(
                code="weak_source_evidence",
                severity="medium" if not product.url else "low",
                message=f"Missing {' and '.join(missing)} from the source result.",
                evidence=[product.source],
            )
        )

    return mismatches


def _group_for_ranked_product(item: RankedProduct, *, median_price: float | None) -> Literal["closest", "cheaper", "similar", "premium", "possible"]:
    price = item.product.price
    has_high_mismatch = any(mismatch.severity == "high" for mismatch in item.mismatches)
    if item.score >= 0.72 and not has_high_mismatch:
        return "closest"
    if median_price is not None and price is not None and price < median_price:
        return "cheaper"
    if median_price is not None and price is not None and price > median_price:
        return "premium"
    if item.score >= 0.52:
        return "similar"
    return "possible"


def _group_sort_key(item: RankedProduct) -> tuple[int, float, float, str]:
    order = {"closest": 0, "cheaper": 1, "similar": 2, "premium": 3, "possible": 4}
    price = item.product.price
    price_sort = 0.0
    if item.group == "cheaper":
        price_sort = price if price is not None else float("inf")
    elif item.group == "premium":
        price_sort = -(price if price is not None else -1)
    return (order[item.group], price_sort, -item.score, item.product.title.lower())


def _reason(
    product_reference: ProductReference,
    product: SourceProduct,
    breakdown: RankingScoreBreakdown,
    mismatches: list[CandidateMismatch],
) -> str:
    signals = _top_breakdown_labels(breakdown)
    matched_terms = _matched_reference_terms(product_reference, product)
    caveat = ""
    if mismatches:
        caveat = f" Caveat: {mismatches[0].message}"
    match_sentence = (
        f"Matched: {', '.join(matched_terms)}."
        if matched_terms
        else "Few extracted details were confirmed in the source title."
    )
    return (
        f"{match_sentence} Ranked on {', '.join(signals) if signals else 'source evidence'}.{caveat}"
    )


def _top_signals(item: RankedProduct) -> list[str]:
    if item.score_breakdown is None:
        return []
    return _top_breakdown_labels(item.score_breakdown)


def _top_breakdown_labels(breakdown: RankingScoreBreakdown) -> list[str]:
    values = {
        "product type": breakdown.product_type_match,
        "brand/model": breakdown.brand_model_match,
        "visual attributes": breakdown.visual_attribute_match,
        "features": breakdown.feature_match,
        "material/color/style": breakdown.material_color_style_match,
        "price fit": breakdown.price_preference_fit,
        "source confidence": breakdown.source_confidence,
        "availability": breakdown.availability_confidence,
    }
    return [label for label, score in sorted(values.items(), key=lambda item: item[1], reverse=True)[:3] if score >= 0.45]


def _matched_reference_terms(product_reference: ProductReference, product: SourceProduct) -> list[str]:
    product_terms = _terms(_join_text([product.title, product.retailer]))
    candidates = [
        product_reference.product_type,
        product_reference.brand,
        product_reference.color,
        *product_reference.materials,
        *product_reference.key_features,
    ]
    matched: list[str] = []
    for candidate in candidates:
        if not candidate:
            continue
        terms = _terms(candidate)
        if terms and terms <= product_terms:
            matched.append(str(candidate))
    return _display_terms(matched, limit=5)


def _display_terms(values: Iterable[str], *, limit: int) -> list[str]:
    seen: set[str] = set()
    terms: list[str] = []
    for value in values:
        normalized = str(value).strip()
        key = normalized.lower()
        if not normalized or key in seen:
            continue
        seen.add(key)
        terms.append(normalized)
        if len(terms) >= limit:
            break
    return terms


def _overlap_score(reference_terms: set[str], product_terms: set[str], *, required: set[str] | None = None) -> float:
    if not reference_terms:
        return 0.5
    overlap = len(reference_terms & product_terms) / max(len(reference_terms), 1)
    if required:
        required_overlap = len(required & product_terms) / max(len(required), 1)
        overlap = (overlap * 0.55) + (required_overlap * 0.45)
    return round(_clamp(overlap), 3)


def _brand_model_score(reference: ProductReference, product_terms: set[str]) -> float:
    if not reference.brand:
        return 0.55
    brand_terms = _terms(reference.brand)
    if not brand_terms:
        return 0.55
    return 1.0 if brand_terms & product_terms else 0.15


def _price_preference_fit(price: float | None, preferences: dict[str, Any]) -> float:
    min_price = _float_preference(preferences, "budgetMin", "budget_min", "minPrice", "priceMin")
    max_price = _float_preference(preferences, "budgetMax", "budget_max", "maxPrice", "priceMax")
    if price is None:
        return 0.35 if (min_price is not None or max_price is not None) else 0.55
    if min_price is None and max_price is None:
        return 0.72
    if min_price is not None and price < min_price:
        return 0.65
    if max_price is not None and price > max_price:
        overage = (price - max_price) / max(max_price, 1)
        return _clamp(0.55 - min(overage, 0.45))
    return 1.0


def _source_confidence(product: SourceProduct) -> float:
    score = 0.25
    if product.url:
        score += 0.3
    if product.retailer:
        score += 0.15
    if product.price is not None:
        score += 0.2
    if product.freshness:
        score += 0.1
    return _clamp(score)


def _availability_confidence(availability: str | None) -> float:
    if not availability:
        return 0.5
    text = availability.lower()
    if any(term in text for term in ["out of stock", "sold out", "unavailable"]):
        return 0.1
    if any(term in text for term in ["limited", "low stock"]):
        return 0.65
    if any(term in text for term in ["in stock", "available"]):
        return 1.0
    return 0.55


def _mismatch_weight(mismatch: CandidateMismatch) -> float:
    return {"low": 0.04, "medium": 0.10, "high": 0.18}[mismatch.severity]


def _confidence(score: float) -> Literal["high", "medium", "low"]:
    if score >= 0.78:
        return "high"
    if score >= 0.56:
        return "medium"
    return "low"


def _terms(value: str | Iterable[str]) -> set[str]:
    if isinstance(value, str):
        text = value
    else:
        text = " ".join(str(item) for item in value if item)
    return {
        term
        for term in re.findall(r"[a-z0-9]+", text.lower())
        if term and term not in STOP_WORDS and len(term) > 1
    }


def _join_text(values: Iterable[Any]) -> str:
    return " ".join(str(value) for value in values if value)


def _float_preference(preferences: dict[str, Any], *keys: str) -> float | None:
    for key in keys:
        value = preferences.get(key)
        if value in (None, ""):
            continue
        try:
            return float(value)
        except (TypeError, ValueError):
            continue
    return None


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))
