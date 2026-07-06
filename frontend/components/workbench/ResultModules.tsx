"use client";

import { AlertCircle, BadgeCheck, ChevronLeft, ChevronRight, Clipboard, DollarSign, RefreshCw, Search } from "lucide-react";
import { useEffect, useMemo, useState, type ReactNode } from "react";

import { formatMoney, groupRankedProducts, priceStats } from "@/lib/presentation";
import type { ProductResearchBrief, RankedProduct, ResearchJob } from "@/lib/types";

import { ProductCard } from "./ProductCard";
import { Badge, Button, Panel } from "./ui";

type ProductGroupValue = "all" | RankedProduct["group"];

const PRODUCT_PAGE_SIZE = 8;

const groupOptions: Array<{
  value: ProductGroupValue;
  label: string;
  emptyLabel: string;
}> = [
  { value: "all", label: "All", emptyLabel: "No matches available." },
  { value: "closest", label: "Closest", emptyLabel: "No closest matches in this brief." },
  { value: "cheaper", label: "Lower priced", emptyLabel: "No lower-priced matches in this brief." },
  { value: "similar", label: "Similar price", emptyLabel: "No similar-price matches in this brief." },
  { value: "premium", label: "Higher-end", emptyLabel: "No higher-end matches in this brief." },
  { value: "possible", label: "Other matches", emptyLabel: "No other matches in this brief." },
];

export function ResultsWorkbench({
  job,
  brief,
  copied,
  onCopy,
  onRetry,
  onRefine,
}: {
  job: ResearchJob | null;
  brief: ProductResearchBrief | null;
  copied: boolean;
  onCopy: () => void;
  onRetry: () => void;
  onRefine: () => void;
}) {
  if (!job) return <EmptyWorkbench />;
  if (!brief && !isTerminal(job.status)) {
    return <GuidanceState icon={<Search size={22} aria-hidden="true" />} title="Research in motion" message={job.progressMessage} tone="accent" />;
  }
  if (!brief) {
    return <FailureGuidance job={job} onRetry={onRetry} onRefine={onRefine} />;
  }
  if (brief.statusReason === "research_unavailable") {
    return <ResearchUnavailable brief={brief} job={job} onRetry={onRetry} onRefine={onRefine} />;
  }

  const groups = groupRankedProducts(brief.rankedProducts);
  const bestCandidate = groups.closest[0] || brief.rankedProducts[0] || null;
  const isVerifiedBest = bestCandidate?.group === "closest" && bestCandidate.score >= 0.74;
  const browserProducts = bestCandidate ? brief.rankedProducts.filter((item) => item !== bestCandidate) : brief.rankedProducts;
  const sharedCaveats = commonCaveatMessages(brief.rankedProducts);
  const suppressedCaveats = new Set(sharedCaveats.map(normalizeCaveat));

  return (
    <div className="grid gap-4">
      <div className="grid gap-4 xl:grid-cols-[minmax(0,1.35fr)_minmax(280px,0.65fr)]">
        <Panel elevated className="p-4">
          <div className="mb-3 flex flex-wrap items-center gap-2">
            <BadgeCheck size={18} className="text-[var(--accent)]" aria-hidden="true" />
            <h2 className="text-base font-semibold text-[var(--text-primary)]">{isVerifiedBest ? "Best match" : "Best available match"}</h2>
            {!isVerifiedBest && bestCandidate ? <Badge tone="warning">Review caveats</Badge> : null}
          </div>
          {bestCandidate ? (
            <div className="grid gap-3">
              <ProductCard item={bestCandidate} featured lowConfidence={!isVerifiedBest} suppressedCaveats={suppressedCaveats} />
            </div>
          ) : (
            <p className="rounded-md border border-[var(--border)] bg-[var(--surface-raised)] p-4 text-sm text-[var(--text-secondary)]">No source-backed products were returned.</p>
          )}
        </Panel>
        <div className="grid gap-4">
          <PriceContext brief={brief} />
          <TrustEvidence brief={brief} />
          <div className="flex flex-wrap gap-2">
            <Button disabled={!brief} onClick={onCopy} type="button">
              <Clipboard size={16} aria-hidden="true" />
              {copied ? "Copied" : "Copy brief"}
            </Button>
            {job.retryable ? (
              <Button onClick={onRetry} type="button">
                <RefreshCw size={16} aria-hidden="true" />
                Retry
              </Button>
            ) : null}
          </div>
        </div>
      </div>
      <ProductBrowser products={browserProducts} sharedCaveats={sharedCaveats} suppressedCaveats={suppressedCaveats} />
      <ReferenceSignals brief={brief} />
    </div>
  );
}

function isTerminal(status: ResearchJob["status"]) {
  return ["complete", "partial", "failed", "expired", "needs_refinement"].includes(status);
}

function EmptyWorkbench() {
  return (
    <GuidanceState
      icon={<Search size={24} aria-hidden="true" />}
      title="Ready for product research"
      message="Add a product image, a description, or both. ThriftLens will turn it into a source-backed brief."
      tone="accent"
    />
  );
}

function FailureGuidance({ job, onRetry, onRefine }: { job: ResearchJob; onRetry: () => void; onRefine: () => void }) {
  const code = job.safeError?.code;
  const isRefinement = job.status === "needs_refinement";
  const title = isRefinement
    ? "More focus needed"
    : code === "unsafe_image"
      ? "Image cannot be processed"
      : code === "unsafe_text"
        ? "Description cannot be processed"
        : code === "regulated_product"
          ? "Product category unavailable"
          : "Research stopped";
  const message = job.safeError?.message || (isRefinement ? "Add a focus note or clearer product evidence to continue." : "Try refining the evidence or retrying when available.");
  return (
    <GuidanceState
      icon={<AlertCircle size={22} aria-hidden="true" />}
      title={title}
      message={message}
      tone={isRefinement ? "warning" : "danger"}
      actions={
        <>
          <Button onClick={onRefine} type="button" variant="secondary">Refine evidence</Button>
          {job.retryable ? <Button onClick={onRetry} type="button" variant="primary">Retry</Button> : null}
        </>
      }
    />
  );
}

function ResearchUnavailable({ brief, job, onRetry, onRefine }: { brief: ProductResearchBrief; job: ResearchJob; onRetry: () => void; onRefine: () => void }) {
  return (
    <div className="grid gap-4">
      <GuidanceState
        icon={<AlertCircle size={22} aria-hidden="true" />}
        title="Research sources are unavailable"
        message={brief.trustSummary}
        tone="warning"
        actions={
          <>
            {job.retryable ? <Button onClick={onRetry} type="button" variant="primary">Retry live search</Button> : null}
            <Button onClick={onRefine} type="button">Refine evidence</Button>
          </>
        }
      />
      <ReferenceSignals brief={brief} />
      <TrustEvidence brief={brief} />
    </div>
  );
}

function GuidanceState({ icon, title, message, tone, actions }: { icon: ReactNode; title: string; message: string; tone: "accent" | "warning" | "danger"; actions?: ReactNode }) {
  const toneClass = {
    accent: "border-[color-mix(in_srgb,var(--accent)_30%,var(--border))] bg-[color-mix(in_srgb,var(--accent)_8%,var(--surface))]",
    warning: "border-[color-mix(in_srgb,var(--warning)_35%,var(--border))] bg-[color-mix(in_srgb,var(--warning)_10%,var(--surface))]",
    danger: "border-[color-mix(in_srgb,var(--danger)_35%,var(--border))] bg-[color-mix(in_srgb,var(--danger)_9%,var(--surface))]",
  }[tone];
  const iconClass = {
    accent: "text-[var(--accent)]",
    warning: "text-[var(--warning)]",
    danger: "text-[var(--danger)]",
  }[tone];
  return (
    <Panel className={`p-6 ${toneClass}`}>
      <div className="flex gap-3">
        <div className={`mt-0.5 ${iconClass}`}>{icon}</div>
        <div>
          <h2 className="text-lg font-semibold text-[var(--text-primary)]">{title}</h2>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-[var(--text-secondary)]">{message}</p>
          {actions ? <div className="mt-4 flex flex-wrap gap-2">{actions}</div> : null}
        </div>
      </div>
    </Panel>
  );
}

function PriceContext({ brief }: { brief: ProductResearchBrief }) {
  const stats = priceStats(brief);
  return (
    <Panel className="p-4">
      <div className="flex items-center gap-2 text-sm font-semibold text-[var(--text-primary)]">
        <DollarSign size={17} className="text-[var(--price)]" aria-hidden="true" />
        Price context
      </div>
      {stats ? (
        <div className="mt-4 grid grid-cols-3 gap-2">
          <Metric label="Low" value={formatMoney(stats.low, stats.currency)} />
          <Metric label="High" value={formatMoney(stats.high, stats.currency)} />
          <Metric label="Priced" value={`${stats.count}`} />
        </div>
      ) : (
        <p className="mt-3 text-sm text-[var(--text-secondary)]">No source-backed prices yet.</p>
      )}
    </Panel>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md bg-[var(--surface-raised)] p-3">
      <p className="text-xs text-[var(--text-muted)]">{label}</p>
      <p className="mt-1 truncate text-sm font-semibold text-[var(--text-primary)]">{value}</p>
    </div>
  );
}

function TrustEvidence({ brief }: { brief: ProductResearchBrief }) {
  const evidenceSummary = trustEvidenceSummary(brief);
  const evidenceNotes = trustEvidenceNotes(brief);
  return (
    <Panel className="p-4">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <h2 className="text-sm font-semibold text-[var(--text-primary)]">Trust and evidence</h2>
        <Badge>{brief.sourceCount} sources</Badge>
      </div>
      <p className="mt-2 text-sm leading-6 text-[var(--text-secondary)]">{brief.freshnessNote}</p>
      {evidenceNotes.length ? (
        <ul className="mt-3 grid gap-1 text-sm text-[var(--text-muted)]">
          {evidenceNotes.map((note) => (
            <li key={note}>{note}</li>
          ))}
        </ul>
      ) : null}
      {evidenceSummary ? <p className="mt-3 border-t border-[var(--border)] pt-3 text-sm text-[var(--text-secondary)]">{evidenceSummary}</p> : null}
    </Panel>
  );
}

function ProductBrowser({
  products,
  sharedCaveats,
  suppressedCaveats,
}: {
  products: RankedProduct[];
  sharedCaveats: string[];
  suppressedCaveats: Set<string>;
}) {
  const [selectedGroup, setSelectedGroup] = useState<ProductGroupValue>("all");
  const [page, setPage] = useState(0);
  const productKey = products.map((item) => `${item.product.source}:${item.product.title}:${item.group}`).join("|");
  const counts = useMemo(() => countProductsByGroup(products), [products]);
  const options = groupOptions.filter((option) => option.value === "all" || counts[option.value] > 0);
  const activeGroup = options.some((option) => option.value === selectedGroup) ? selectedGroup : "all";
  const filteredProducts = useMemo(
    () => sortProductsForGroup(activeGroup, activeGroup === "all" ? products : products.filter((item) => item.group === activeGroup)),
    [activeGroup, products],
  );
  const pageCount = Math.max(1, Math.ceil(filteredProducts.length / PRODUCT_PAGE_SIZE));
  const activePage = Math.min(page, pageCount - 1);
  const visibleProducts = filteredProducts.slice(activePage * PRODUCT_PAGE_SIZE, activePage * PRODUCT_PAGE_SIZE + PRODUCT_PAGE_SIZE);
  const activeOption = groupOptions.find((option) => option.value === activeGroup) || groupOptions[0];

  useEffect(() => {
    setSelectedGroup("all");
    setPage(0);
  }, [productKey]);

  function selectGroup(value: ProductGroupValue) {
    setSelectedGroup(value);
    setPage(0);
  }

  if (!products.length) return null;

  return (
    <Panel className="p-4">
      <div className="mb-4 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div>
          <h2 className="text-base font-semibold text-[var(--text-primary)]">{products.length === 1 ? "Available match" : "Explore matches"}</h2>
          <p className="mt-1 text-sm text-[var(--text-secondary)]">
            {products.length === 1
              ? "Only one source-backed candidate was available for this run."
              : "Browse source-backed candidates by match type."}
          </p>
        </div>
        <Badge>{products.length} products</Badge>
      </div>
      {sharedCaveats.length ? (
        <p className="mb-4 rounded-md border border-[var(--border)] bg-[var(--surface-raised)] p-3 text-sm leading-6 text-[var(--text-secondary)]">
          Shared caveat: {sharedCaveats[0]}
        </p>
      ) : null}

      <select
        aria-label="Match group"
        className="mb-4 h-10 w-full rounded-md border border-[var(--border)] bg-[var(--surface-raised)] px-3 text-sm text-[var(--text-primary)] outline-none md:hidden"
        value={activeGroup}
        onChange={(event) => selectGroup(event.target.value as ProductGroupValue)}
      >
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label} ({counts[option.value]})
          </option>
        ))}
      </select>

      <div className="mb-4 hidden border-b border-[var(--border)] md:flex" role="tablist" aria-label="Match groups">
        {options.map((option) => {
          const isActive = option.value === activeGroup;
          return (
            <button
              aria-selected={isActive}
              className={`relative -mb-px h-10 border-b px-3 text-[13px] font-semibold transition ${
                isActive
                  ? "border-[var(--accent)] text-[var(--text-primary)]"
                  : "border-transparent text-[var(--text-secondary)] hover:border-[var(--border-strong)] hover:text-[var(--text-primary)]"
              }`}
              key={option.value}
              onClick={() => selectGroup(option.value)}
              role="tab"
              type="button"
            >
              {option.label} <span className="ml-1 text-[var(--text-muted)]">{counts[option.value]}</span>
            </button>
          );
        })}
      </div>

      <div className="min-h-[420px] sm:min-h-[460px] lg:min-h-[720px] 2xl:min-h-[700px]">
        {visibleProducts.length ? (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4 2xl:grid-cols-5">
            {visibleProducts.map((item, index) => (
              <ProductCard
                compact
                key={productRenderKey(item, activePage * PRODUCT_PAGE_SIZE + index)}
                item={item}
                lowConfidence={item.group === "possible"}
                suppressedCaveats={suppressedCaveats}
              />
            ))}
          </div>
        ) : (
          <p className="rounded-md bg-[var(--surface-raised)] p-4 text-sm text-[var(--text-secondary)]">{activeOption.emptyLabel}</p>
        )}
      </div>

      {visibleProducts.length && pageCount > 1 ? (
        <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-[var(--border)] pt-4">
          <p className="text-sm text-[var(--text-secondary)]">
            Page {activePage + 1} of {pageCount}
          </p>
          <div className="flex gap-2">
            <Button disabled={activePage === 0} onClick={() => setPage(Math.max(0, activePage - 1))} type="button">
              <ChevronLeft size={15} aria-hidden="true" />
              Previous
            </Button>
            <Button disabled={activePage >= pageCount - 1} onClick={() => setPage(Math.min(pageCount - 1, activePage + 1))} type="button">
              Next
              <ChevronRight size={15} aria-hidden="true" />
            </Button>
          </div>
        </div>
      ) : null}
    </Panel>
  );
}

function productRenderKey(item: RankedProduct, index: number): string {
  const product = item.product;
  return [
    product.url || "no-url",
    product.source || "unknown-source",
    product.retailer || "unknown-retailer",
    product.title,
    item.group,
    item.score,
    index,
  ].join("|");
}

function commonCaveatMessages(products: RankedProduct[]): string[] {
  if (products.length < 2) return [];
  const counts = new Map<string, { message: string; count: number }>();
  for (const product of products) {
    const seenForProduct = new Set<string>();
    for (const message of productCaveatMessages(product)) {
      const key = normalizeCaveat(message);
      if (!key || seenForProduct.has(key)) continue;
      const existing = counts.get(key);
      counts.set(key, { message: existing?.message || message, count: (existing?.count || 0) + 1 });
      seenForProduct.add(key);
    }
  }
  return Array.from(counts.values())
    .filter((item) => item.count === products.length)
    .map((item) => item.message);
}

function productCaveatMessages(product: RankedProduct): string[] {
  return (product.mismatches || [])
    .map((mismatch) => mismatch.message?.trim())
    .filter((message): message is string => Boolean(message));
}

function normalizeCaveat(value: string): string {
  return value.toLowerCase().replace(/\s+/g, " ").trim();
}

function sortProductsForGroup(group: ProductGroupValue, products: RankedProduct[]): RankedProduct[] {
  const sortedProducts = [...products];
  if (group === "cheaper") {
    return sortedProducts.sort((left, right) => comparePrices(left, right, "asc"));
  }
  if (group === "premium") {
    return sortedProducts.sort((left, right) => comparePrices(left, right, "desc"));
  }
  return sortedProducts;
}

function comparePrices(left: RankedProduct, right: RankedProduct, direction: "asc" | "desc"): number {
  const leftPrice = left.product.price;
  const rightPrice = right.product.price;
  const leftHasPrice = typeof leftPrice === "number";
  const rightHasPrice = typeof rightPrice === "number";
  if (!leftHasPrice && !rightHasPrice) return 0;
  if (!leftHasPrice) return 1;
  if (!rightHasPrice) return -1;
  return direction === "asc" ? leftPrice - rightPrice : rightPrice - leftPrice;
}

function trustEvidenceSummary(brief: ProductResearchBrief): string {
  const strategySummary = plainSummary(brief.rankingExplanation?.modelSummary || brief.rankingExplanation?.summary || "");
  if (brief.statusReason === "possible_matches_only") {
    if (strategySummary) return strategySummary;
    return brief.sourceCount <= 1
      ? "ThriftLens found one source-backed candidate, but it did not clear the exact-match threshold."
      : `ThriftLens compared ${brief.sourceCount} source-backed candidates and is showing alternatives because none cleared the exact-match threshold.`;
  }
  if (strategySummary) return strategySummary;
  if (brief.sourceCount > 1) {
    return `ThriftLens compared ${brief.sourceCount} source-backed candidates using product details, price, and source quality.`;
  }
  if (brief.sourceCount === 1) {
    return "ThriftLens found one source-backed candidate and compared it with the extracted product details.";
  }
  return strategySummary || "";
}

function plainSummary(value: string): string {
  const text = value.trim();
  if (!text.startsWith("{") || !text.endsWith("}")) return text;
  try {
    const parsed = JSON.parse(text) as Record<string, unknown>;
    for (const key of ["summary", "modelSummary", "explanation", "text"]) {
      const candidate = parsed[key];
      if (typeof candidate === "string" && candidate.trim()) return candidate.trim();
    }
  } catch {
    return text;
  }
  return "";
}

function trustEvidenceNotes(brief: ProductResearchBrief): string[] {
  const mapped = brief.uncertaintyNotes.map((note) => {
    if (isProductInfoNote(note)) return "";
    if (note === "Source data was discovered through the Product Discovery MCP workflow.") {
      return "Matches are based on live source results and the product details extracted from your evidence.";
    }
    if (note === "No verified exact match was found; showing possible alternatives instead.") {
      return "No exact match was verified; review the alternatives before relying on price or fit.";
    }
    if (note === "provider_unavailable") {
      return "Research sources are temporarily unavailable.";
    }
    return note;
  });
  return Array.from(new Set(mapped.filter(Boolean)));
}

function isProductInfoNote(note: string): boolean {
  return (
    note.startsWith("Ranking prioritized shopper signals") ||
    note.startsWith("Search and ranking used") ||
    note.startsWith("Research ran ")
  );
}

function productInfoNotes(brief: ProductResearchBrief): string[] {
  return brief.uncertaintyNotes.filter(isProductInfoNote);
}

function countProductsByGroup(products: RankedProduct[]): Record<ProductGroupValue, number> {
  return {
    all: products.length,
    closest: products.filter((item) => item.group === "closest").length,
    cheaper: products.filter((item) => item.group === "cheaper").length,
    similar: products.filter((item) => item.group === "similar").length,
    premium: products.filter((item) => item.group === "premium").length,
    possible: products.filter((item) => item.group === "possible").length,
  };
}

function ReferenceSignals({ brief }: { brief: ProductResearchBrief }) {
  const reference = brief.productReference;
  const infoNotes = productInfoNotes(brief);
  const signals = [
    ["Type", reference.productType],
    ["Brand", reference.brand || "Unknown"],
    ["Color", reference.color || "Unknown"],
    ["Confidence", reference.confidence ? `${Math.round(reference.confidence * 100)}%` : "Unknown"],
  ];
  return (
    <Panel className="p-4">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <h2 className="text-base font-semibold text-[var(--text-primary)]">Product info and ranking basis</h2>
          <p className="mt-1 text-sm text-[var(--text-secondary)]">The extracted product facts and strategy ThriftLens used to search and compare matches.</p>
        </div>
        <Badge tone="accent">Product profile</Badge>
      </div>
      <div className="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
        {signals.map(([label, value]) => (
          <Metric key={label} label={label} value={value} />
        ))}
      </div>
      {reference.keyFeatures?.length ? (
        <div className="mt-3 flex flex-wrap gap-2">
          {reference.keyFeatures.map((feature) => (
            <Badge key={feature} tone="accent">{feature}</Badge>
          ))}
        </div>
      ) : null}
      {reference.assumptions?.length ? <p className="mt-3 text-sm leading-6 text-[var(--text-muted)]">{reference.assumptions.join(" ")}</p> : null}
      {infoNotes.length ? (
        <div className="mt-4 rounded-md border border-[var(--border)] bg-[var(--surface-raised)] p-3">
          <p className="text-xs font-semibold uppercase tracking-[0.08em] text-[var(--text-muted)]">Research basis</p>
          <ul className="mt-2 grid gap-1.5 text-sm leading-6 text-[var(--text-secondary)]">
            {infoNotes.map((note) => (
              <li key={note}>{note}</li>
            ))}
          </ul>
        </div>
      ) : null}
    </Panel>
  );
}
