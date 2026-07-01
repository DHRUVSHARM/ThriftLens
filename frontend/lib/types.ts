export type InputMode = "image" | "text";

export type JobStatus =
  | "queued"
  | "extracting_reference"
  | "needs_refinement"
  | "researching_sources"
  | "ranking_results"
  | "complete"
  | "partial"
  | "failed"
  | "expired";

export type ProductReference = {
  productType: string;
  title: string;
  brand?: string | null;
  color?: string | null;
  materials?: string[];
  keyFeatures?: string[];
  searchQueries?: string[];
  confidence?: number;
  assumptions?: string[];
};

export type SourceProduct = {
  source: string;
  title: string;
  retailer?: string | null;
  url?: string | null;
  price?: number | null;
  currency?: string;
  imageUrl?: string | null;
  availability?: string | null;
  freshness?: string | null;
};

export type RankedProduct = {
  product: SourceProduct;
  score: number;
  group: "closest" | "cheaper" | "similar" | "premium" | "possible";
  confidence: "high" | "medium" | "low";
  reason: string;
};

export type ProductResearchBrief = {
  mode: string;
  label: string;
  productReference: ProductReference;
  trustSummary: string;
  sourceCount: number;
  freshnessNote: string;
  uncertaintyNotes: string[];
  rankedProducts: RankedProduct[];
  userActions: string[];
  statusReason?: string | null;
};

export type SafeError = {
  code: string;
  message: string;
  retryable: boolean;
};

export type ResearchJob = {
  jobId: string;
  status: JobStatus;
  progressMessage: string;
  retryable: boolean;
  providerMode: string;
  safeError?: SafeError | null;
  partialBrief?: ProductResearchBrief | null;
  finalBrief?: ProductResearchBrief | null;
};

export type ResearchPreferences = {
  rankingPreference: "closest" | "grouped";
  budgetMin?: number;
  budgetMax?: number;
};

export type CreateJobInput =
  | {
      inputType: "text";
      textDescription: string;
      researchPreferences: ResearchPreferences;
    }
  | {
      inputType: "image";
      image: File;
      researchPreferences: ResearchPreferences;
    };
