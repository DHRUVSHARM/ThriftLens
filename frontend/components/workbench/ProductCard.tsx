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
}: {
  item: RankedProduct;
  featured?: boolean;
  lowConfidence?: boolean;
  compact?: boolean;
}) {
  const product = item.product;
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
          <p className="mt-2 line-clamp-3 text-sm leading-6 text-[var(--text-secondary)]">{item.reason}</p>
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
        <p className={`${featured ? "text-base" : "text-sm"} mt-3 leading-6 text-[var(--text-secondary)]`}>{item.reason}</p>
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
