import type { JobStatus, ProductResearchBrief, RankedProduct, ResearchJob } from "./types";

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

export function formatMoney(value: number, currency = "USD"): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
  }).format(value);
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

export function priceStats(brief: ProductResearchBrief | null): { low: number; high: number; count: number; currency: string } | null {
  const priced = brief?.rankedProducts
    .map((item) => ({ price: item.product.price, currency: item.product.currency || "USD" }))
    .filter((item): item is { price: number; currency: string } => typeof item.price === "number")
    .sort((a, b) => a.price - b.price);
  if (!priced || priced.length === 0) return null;
  return {
    low: priced[0].price,
    high: priced[priced.length - 1].price,
    count: priced.length,
    currency: priced[0].currency,
  };
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

export function statusLabel(status: JobStatus): string {
  const labels: Record<JobStatus, string> = {
    queued: "Preparing research",
    extracting_reference: "Interpreting evidence",
    needs_refinement: "Needs focus",
    researching_sources: "Searching sources",
    ranking_results: "Comparing candidates",
    complete: "Brief ready",
    partial: "Partial brief",
    failed: "Stopped",
    expired: "Expired",
  };
  return labels[status];
}

export type ResearchStage = {
  id: "capture" | "interpret" | "research" | "compare" | "brief";
  label: string;
  description: string;
};

export type StageState = "waiting" | "active" | "complete" | "failed" | "skipped";
export type ResearchSubstep = {
  label: string;
  state: StageState;
};

export const RESEARCH_STAGES: ResearchStage[] = [
  { id: "capture", label: "Capture", description: "Product evidence" },
  { id: "interpret", label: "Interpret", description: "Reference extraction" },
  { id: "research", label: "Research", description: "Source search" },
  { id: "compare", label: "Compare", description: "Candidate ranking" },
  { id: "brief", label: "Brief", description: "Research summary" },
];

const RESEARCH_SUBSTEPS: Record<ResearchStage["id"], string[]> = {
  capture: ["Evidence received", "Job queued", "Worker pickup"],
  interpret: ["Safety screen", "Product clarity", "Reference extraction", "Reference saved"],
  research: ["Product profile", "Search context", "Source plan", "Live source search", "Normalize results"],
  compare: ["Candidate scores", "Mismatch checks", "Alternative groups", "Ranking explanation"],
  brief: ["Build summary", "Ready for review"],
};

export function stageState(stageId: ResearchStage["id"], status?: JobStatus): StageState {
  if (!status) return "waiting";
  if (status === "failed" || status === "expired") {
    if (stageId === "brief") return "failed";
  }
  if (status === "needs_refinement") {
    if (stageId === "capture" || stageId === "interpret") return "complete";
    return stageId === "brief" ? "failed" : "skipped";
  }
  const activeByStatus: Partial<Record<JobStatus, ResearchStage["id"]>> = {
    queued: "capture",
    extracting_reference: "interpret",
    researching_sources: "research",
    ranking_results: "compare",
    complete: "brief",
    partial: "brief",
  };
  const active = activeByStatus[status];
  const order = RESEARCH_STAGES.findIndex((stage) => stage.id === stageId);
  const activeIndex = RESEARCH_STAGES.findIndex((stage) => stage.id === active);
  if (status === "complete" || status === "partial") return "complete";
  if (stageId === active) return "active";
  if (activeIndex >= 0 && order < activeIndex) return "complete";
  return "waiting";
}

export function stageSubsteps(stageId: ResearchStage["id"], job?: ResearchJob | null): ResearchSubstep[] {
  const labels = RESEARCH_SUBSTEPS[stageId];
  const state = stageState(stageId, job?.status);
  if (!job || state !== "active") return [];
  const dynamicLabel = dynamicSubstepLabel(stageId, job);
  if (dynamicLabel) return [{ label: dynamicLabel, state: "active" }];
  const activeIndex = activeSubstepIndex(stageId, job);
  return [{ label: labels[activeIndex], state: "active" }];
}

function dynamicSubstepLabel(stageId: ResearchStage["id"], job: ResearchJob): string | null {
  if (stageId !== "research") return null;
  const message = job.progressMessage.trim();
  if (/^Searching .+\.$/.test(message)) return message.replace(/\.$/, "");
  return null;
}

function activeSubstepIndex(stageId: ResearchStage["id"], job: ResearchJob): number {
  const message = job.progressMessage.toLowerCase();
  if (stageId === "capture") {
    if (message.includes("queued")) return 1;
    return 0;
  }
  if (stageId === "interpret") {
    if (message.includes("screening")) return 0;
    if (message.includes("clarity")) return 1;
    if (message.includes("reference extracted") || message.includes("product reference extracted")) return 3;
    if (message.includes("extracting")) return 2;
    return 2;
  }
  if (stageId === "research") {
    if (message.includes("strategy")) return 0;
    if (message.includes("context")) return 1;
    if (message.includes("planning")) return 2;
    if (message.includes("searching")) return 3;
    if (message.includes("normalizing")) return 4;
    return 3;
  }
  if (stageId === "compare") {
    if (message.includes("scoring")) return 0;
    if (message.includes("mismatch")) return 1;
    if (message.includes("grouping")) return 2;
    if (message.includes("explanation")) return 3;
    return 0;
  }
  if (stageId === "brief") {
    return job.status === "complete" || job.status === "partial" ? 1 : 0;
  }
  return 0;
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
