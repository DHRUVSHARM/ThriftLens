import type { ProductResearchBrief, RankedProduct, ResearchJob } from "./types";

export type RankedProductGroups = {
  closest: RankedProduct[];
  cheaper: RankedProduct[];
  similar: RankedProduct[];
  premium: RankedProduct[];
  possible: RankedProduct[];
};

export function priceLabel(item: RankedProduct): string {
  const price = item.product.price;
  if (typeof price !== "number") return "Unknown price";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: item.product.currency || "USD",
  }).format(price);
}

export function currentBrief(job: ResearchJob | null): ProductResearchBrief | null {
  return job?.finalBrief || job?.partialBrief || null;
}

export function priceContext(brief: ProductResearchBrief | null): string {
  const prices = brief?.rankedProducts
    .map((item) => item.product.price)
    .filter((price): price is number => typeof price === "number")
    .sort((a, b) => a - b);
  if (!prices || prices.length === 0) return "No source-backed prices yet.";

  const formatter = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" });
  const low = formatter.format(prices[0]);
  const high = formatter.format(prices[prices.length - 1]);
  return prices.length === 1 ? `Observed price: ${low}` : `Observed range: ${low} to ${high}`;
}

export function groupRankedProducts(products: RankedProduct[]): RankedProductGroups {
  return {
    closest: products.filter((item) => item.group === "closest"),
    cheaper: products.filter((item) => item.group === "cheaper"),
    similar: products.filter((item) => item.group === "similar"),
    premium: products.filter((item) => item.group === "premium"),
    possible: products.filter((item) => item.group === "possible"),
  };
}

export function buildSummary(brief: ProductResearchBrief): string {
  const lines = [
    `ThriftLens research brief (${brief.label})`,
    `Reference: ${brief.productReference.title}`,
    `Trust: ${brief.trustSummary}`,
    `Freshness: ${brief.freshnessNote}`,
    "",
    "Products:",
    ...brief.rankedProducts.map((item, index) => {
      const url = item.product.url ? ` ${item.product.url}` : "";
      return `${index + 1}. ${item.product.title} - ${priceLabel(item)} - ${item.reason}${url}`;
    }),
  ];
  return lines.join("\n");
}
