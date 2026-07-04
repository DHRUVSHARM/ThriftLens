from typing import Any

from app.workflow_contracts import ProductReference, SourceProduct, WorkflowProviderError

# data with examples for running app in sample mode 
class SampleExtractionProvider:
    async def gate_image(self, *, request_payload: dict[str, Any], image_metadata: list[dict[str, Any]]) -> dict[str, Any]:
        target = request_payload.get("targetDescription")
        return {
            "safetyStatus": "safe",
            "productSuitability": "single_product",
            "productLikenessConfidence": 0.9,
            "detectedProducts": [
                {
                    "label": target or "stainless steel insulated water bottle",
                    "locationHint": "center of image",
                    "confidence": 0.9,
                }
            ],
            "needsClarification": False,
            "clarificationPrompt": None,
            "injectionRisk": "low",
            "instructionLikeText": [],
            "decision": "proceed",
            "reason": "Sample image gate treats fixture image as a clear product.",
        }

    async def extract(self, *, input_type: str, request_payload: dict[str, Any], image_metadata: list[dict[str, Any]]) -> dict[str, Any]:
        if input_type == "image":
            return {
                "productType": "water bottle",
                "title": "stainless steel insulated water bottle",
                "brand": None,
                "color": "silver",
                "materials": ["stainless steel"],
                "keyFeatures": ["insulated", "reusable", "screw cap"],
                "searchQueries": [
                    "stainless steel insulated water bottle",
                    "silver insulated water bottle",
                ],
                "confidence": 0.82,
                "assumptions": ["Sample image flow uses deterministic fixture metadata."],
            }

        text = request_payload.get("textDescription") or "minimal black desk lamp with wireless charging"
        return {
            "productType": "desk lamp",
            "title": text,
            "brand": None,
            "color": "black" if "black" in text.lower() else None,
            "materials": [],
            "keyFeatures": ["wireless charging"] if "wireless" in text.lower() else ["compact"],
            "searchQueries": [text, f"{text} price"],
            "confidence": 0.78,
            "assumptions": ["Sample text flow uses deterministic fixture extraction."],
        }

    async def repair(self, raw_output: dict[str, Any]) -> dict[str, Any]:
        repaired = dict(raw_output)
        repaired.setdefault("productType", repaired.get("title", "unknown product"))
        repaired.setdefault("title", repaired["productType"])
        repaired.setdefault("materials", [])
        repaired.setdefault("keyFeatures", [])
        repaired.setdefault("searchQueries", [repaired["title"]])
        repaired.setdefault("confidence", 0.5)
        repaired.setdefault("assumptions", ["Reference was repaired from incomplete structured output."])
        return repaired


class InvalidThenRepairExtractionProvider(SampleExtractionProvider):
    async def extract(self, *, input_type: str, request_payload: dict[str, Any], image_metadata: list[dict[str, Any]]) -> dict[str, Any]:
        return {"title": request_payload.get("textDescription") or "repairable product"}


class InvalidAlwaysExtractionProvider(SampleExtractionProvider):
    async def extract(self, *, input_type: str, request_payload: dict[str, Any], image_metadata: list[dict[str, Any]]) -> dict[str, Any]:
        return {"confidence": 2}

    async def repair(self, raw_output: dict[str, Any]) -> dict[str, Any]:
        return {"confidence": 2}


class SampleResearchProvider:
    async def research(self, product_reference: ProductReference, preferences: dict[str, Any]) -> list[dict[str, Any]]:
        title = product_reference.title.lower()
        if "no verified" in title:
            return [
                {
                    "source": "sample-google-shopping",
                    "title": "adjustable black desk lamp",
                    "retailer": "Sample Retailer",
                    "url": "https://example.com/sample-adjustable-lamp",
                    "price": 39.99,
                    "currency": "USD",
                    "availability": "in stock",
                    "freshness": "sample/static",
                }
            ]

        return [
            {
                "source": "sample-google-shopping",
                "title": product_reference.title,
                "retailer": "Sample Retailer",
                "url": "https://example.com/sample-closest",
                "price": 49.99,
                "currency": "USD",
                "availability": "in stock",
                "freshness": "sample/static",
            },
            {
                "source": "sample-google-shopping",
                "title": f"budget {product_reference.product_type}",
                "retailer": "Sample Outlet",
                "url": "https://example.com/sample-budget",
                "price": 29.99,
                "currency": "USD",
                "availability": "in stock",
                "freshness": "sample/static",
            },
            {
                "source": "sample-google-shopping",
                "title": f"premium {product_reference.product_type}",
                "retailer": "Sample Premium",
                "url": "https://example.com/sample-premium",
                "price": 89.99,
                "currency": "USD",
                "availability": "limited",
                "freshness": "sample/static",
            },
        ]


class FailingResearchProvider(SampleResearchProvider):
    async def research(self, product_reference: ProductReference, preferences: dict[str, Any]) -> list[dict[str, Any]]:
        raise WorkflowProviderError(
            "research_unavailable",
            "Research sources are temporarily unavailable.",
            retryable=True,
        )


class FailingRankingExplainer:
    async def explain(self, product_reference: ProductReference, products: list[SourceProduct]) -> dict[str, str]:
        raise WorkflowProviderError("ranking_model_unavailable", "Ranking model unavailable.", retryable=True)
