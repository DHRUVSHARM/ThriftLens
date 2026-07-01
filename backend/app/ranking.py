from app.workflow_contracts import ProductReference, RankedProduct, SourceProduct


def deterministic_rank(product_reference: ProductReference, products: list[SourceProduct]) -> list[RankedProduct]:
    reference_terms = set(product_reference.title.lower().split())
    ranked: list[RankedProduct] = []
    known_prices = [product.price for product in products if product.price is not None]
    median_price = sorted(known_prices)[len(known_prices) // 2] if known_prices else None

    for product in products:
        title_terms = set(product.title.lower().split())
        overlap = len(reference_terms & title_terms)
        score = min(1.0, 0.35 + (overlap / max(len(reference_terms), 1)) * 0.65)
        group = "possible"
        if score >= 0.74:
            group = "closest"
        elif median_price is not None and product.price is not None and product.price < median_price:
            group = "cheaper"
        elif median_price is not None and product.price is not None and product.price > median_price:
            group = "premium"
        elif score >= 0.55:
            group = "similar"

        confidence = "high" if score >= 0.8 else "medium" if score >= 0.6 else "low"
        ranked.append(
            RankedProduct(
                product=product,
                score=round(score, 2),
                group=group,
                confidence=confidence,
                reason=f"Matched {overlap} reference terms with source-backed product data.",
            )
        )

    return sorted(ranked, key=lambda item: item.score, reverse=True)
