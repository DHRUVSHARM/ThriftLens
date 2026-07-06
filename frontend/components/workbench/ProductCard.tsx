import { ExternalLink, Image as ImageIcon } from "lucide-react";

import { priceLabel } from "@/lib/presentation";
import type { RankedProduct } from "@/lib/types";

import { Badge } from "./ui";

const groupLabels: Record<RankedProduct["group"], string> = {
  closest: "Closest",
  cheaper: "Lower priced",
  similar: "Similar price",
  premium: "Higher-end",
  possible: "Other match",
};

export function ProductCard({
  item,
  featured = false,
  lowConfidence = false,
  compact = false,
  suppressedCaveats = new Set<string>(),
}: {
  item: RankedProduct;
  featured?: boolean;
  lowConfidence?: boolean;
  compact?: boolean;
  suppressedCaveats?: Set<string>;
}) {
  const product = item.product;
  const caveat = primaryCaveat(item, suppressedCaveats);
  const importantPoint = cardImportantPoint(item, caveat);
  const reasonText = cardReason(item.reason);
  const noteIsCaveat = importantPoint.startsWith("Review caveat:");
  if (compact) {
    return (
      <article
        className={`flex min-h-full flex-col rounded-lg border p-3 ${
          lowConfidence ? "border-dashed border-[var(--border-strong)] bg-[var(--surface-raised)]" : "border-[var(--border)] bg-[var(--surface)]"
        }`}
      >
        <div className="flex h-36 items-center justify-center overflow-hidden rounded-md bg-[var(--surface-subtle)]">
          {product.imageUrl ? (
            <img alt="" className="h-full w-full object-cover" src={product.imageUrl} />
          ) : (
            <ImageIcon className="text-[var(--text-muted)]" size={28} aria-hidden="true" />
          )}
        </div>
        <div className="mt-3 flex min-h-0 flex-1 flex-col">
          <div className="flex items-start justify-between gap-2">
            <h3 className="line-clamp-2 text-sm font-semibold leading-snug text-[var(--text-primary)]">{product.title}</h3>
            <Badge tone={item.confidence === "high" ? "success" : item.confidence === "medium" ? "warning" : "neutral"}>{item.confidence}</Badge>
          </div>
          <p className="mt-1 truncate text-sm text-[var(--text-muted)]">{product.retailer || product.source}</p>
          <p className="mt-3 text-xl font-semibold text-[var(--price)]">{priceLabel(item)}</p>
          {importantPoint ? <MatchNote caveat={noteIsCaveat} detail={matchNoteDetail(reasonText, caveat)}>{importantPoint}</MatchNote> : null}
          <div className="mt-auto flex flex-wrap items-center gap-2 pt-4">
            <Badge tone="accent">{groupLabels[item.group]}</Badge>
            {product.url ? (
              <a
                className="ml-auto inline-flex h-8 items-center gap-1.5 rounded-md border border-[var(--border)] px-2.5 text-[13px] font-semibold text-[var(--text-primary)] transition hover:border-[var(--accent)]"
                href={product.url}
                rel="noreferrer"
                target="_blank"
              >
                Source
                <ExternalLink size={13} aria-hidden="true" />
              </a>
            ) : null}
          </div>
        </div>
      </article>
    );
  }

  return (
    <article
      className={`grid gap-4 rounded-lg border p-4 ${
        featured
          ? "border-[color-mix(in_srgb,var(--accent)_42%,var(--border))] bg-[color-mix(in_srgb,var(--accent)_7%,var(--surface))] md:grid-cols-[180px_1fr]"
          : lowConfidence
            ? "border-dashed border-[var(--border-strong)] bg-[var(--surface-raised)] md:grid-cols-[104px_1fr]"
            : "border-[var(--border)] bg-[var(--surface)] md:grid-cols-[104px_1fr]"
      }`}
    >
      <div className={`${featured ? "min-h-44" : "h-28"} flex items-center justify-center overflow-hidden rounded-md bg-[var(--surface-subtle)]`}>
        {product.imageUrl ? (
          <img alt="" className="h-full w-full object-cover" src={product.imageUrl} />
        ) : (
          <ImageIcon className="text-[var(--text-muted)]" size={featured ? 38 : 26} aria-hidden="true" />
        )}
      </div>
      <div className="min-w-0">
        <div className="flex flex-wrap items-start justify-between gap-2">
          <div className="min-w-0">
            <h3 className={`${featured ? "text-xl" : "text-sm"} line-clamp-2 font-semibold leading-snug text-[var(--text-primary)]`}>{product.title}</h3>
            <p className="mt-1 truncate text-sm text-[var(--text-muted)]">{product.retailer || product.source}</p>
          </div>
          <Badge tone={item.confidence === "high" ? "success" : item.confidence === "medium" ? "warning" : "neutral"}>{item.confidence}</Badge>
        </div>
        <p className={`${featured ? "text-3xl" : "text-xl"} mt-4 font-semibold text-[var(--price)]`}>{priceLabel(item)}</p>
        <p className="mt-1 text-sm text-[var(--text-muted)]">{product.availability || "Availability unknown"}</p>
        {importantPoint ? <MatchNote caveat={noteIsCaveat} detail={matchNoteDetail(reasonText, caveat)}>{importantPoint}</MatchNote> : null}
        <div className="mt-4 flex flex-wrap items-center gap-2">
          <Badge tone="accent">{groupLabels[item.group]}</Badge>
          <Badge>{product.freshness || "source-backed"}</Badge>
          {product.url ? (
            <a
              className="ml-auto inline-flex h-9 items-center gap-1.5 rounded-md border border-[var(--border)] px-3 text-sm font-semibold text-[var(--text-primary)] transition hover:border-[var(--accent)]"
              href={product.url}
              rel="noreferrer"
              target="_blank"
            >
              Source
              <ExternalLink size={14} aria-hidden="true" />
            </a>
          ) : null}
        </div>
      </div>
    </article>
  );
}

function MatchNote({ caveat, detail, children }: { caveat: boolean; detail: string; children: string }) {
  const hasDetail = detail && detail !== children;
  return (
    <p
      className={`mt-3 line-clamp-2 border-l-2 pl-2 text-xs leading-5 ${
        caveat ? "border-[var(--warning)] text-[var(--warning)]" : "border-[var(--border-strong)] text-[var(--text-secondary)]"
      }`}
      aria-label={hasDetail ? detail : undefined}
      title={hasDetail ? detail : undefined}
    >
      {children}
    </p>
  );
}

function cardImportantPoint(item: RankedProduct, caveat: string | null): string {
  const signals = topScoreLabels(item).slice(0, 2);
  if (signals.length) return `Selected for ${signals.join(" and ")}.`;
  const firstSentence = cardReason(item.reason).split(".")[0]?.trim();
  if (firstSentence) return `${firstSentence}.`;
  return caveat ? `Review caveat: ${caveat}.` : "";
}

function primaryCaveat(item: RankedProduct, suppressedCaveats: Set<string>): string | null {
  const mismatch = item.mismatches?.find((candidate) => candidate.severity === "high") || item.mismatches?.[0];
  const message = mismatch?.message?.trim() || "";
  if (!message || suppressedCaveats.has(normalizeCaveat(message))) return null;
  return message;
}

function cardReason(reason: string): string {
  return reason.replace(/\s*Caveat:\s.*$/i, "").trim();
}

function matchNoteDetail(reason: string, caveat: string | null): string {
  return caveat ? `${reason} Caveat: ${caveat}`.trim() : reason;
}

function topScoreLabels(item: RankedProduct): string[] {
  const breakdown = item.scoreBreakdown;
  if (!breakdown) return [];
  const values: Array<[string, number | undefined]> = [
    ["product type", breakdown.productTypeMatch],
    ["brand/model", breakdown.brandModelMatch],
    ["visual details", breakdown.visualAttributeMatch],
    ["features", breakdown.featureMatch],
    ["material/color/style", breakdown.materialColorStyleMatch],
    ["price fit", breakdown.pricePreferenceFit],
    ["source confidence", breakdown.sourceConfidence],
    ["availability", breakdown.availabilityConfidence],
  ];
  return values
    .filter(([, score]) => typeof score === "number" && score >= 0.45)
    .sort((left, right) => (right[1] || 0) - (left[1] || 0))
    .map(([label]) => label);
}

function normalizeCaveat(value: string): string {
  return value.toLowerCase().replace(/\s+/g, " ").trim();
}
