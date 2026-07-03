import { DollarSign, Layers, Target } from "lucide-react";
import type { ReactNode } from "react";

import { priceContext } from "@/lib/presentation";
import type { ProductResearchBrief, ResearchJob } from "@/lib/types";

import { Badge, Panel } from "./ui";

export function InsightHeader({ job, brief }: { job: ResearchJob | null; brief: ProductResearchBrief | null }) {
  const reference = brief?.productReference;
  const isSample = !job || (brief?.label || job.providerMode || "").toLowerCase().includes("sample");
  return (
    <Panel className="p-4">
      <div className="grid gap-4">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <Badge tone={isSample ? "warning" : "success"}>{job ? (isSample ? "Sample/static" : "Live sources") : "Pending"}</Badge>
            {job ? <Badge>{job.status.replace(/_/g, " ")}</Badge> : <Badge>Ready</Badge>}
          </div>
          <h1 className="mt-3 text-2xl font-semibold leading-tight tracking-normal text-[var(--text-primary)]">
            {reference?.title || "Product research workbench"}
          </h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-[var(--text-secondary)]">
            {brief?.trustSummary || "Add product evidence and ThriftLens will build a source-backed brief with price context and alternatives."}
          </p>
        </div>
        <div className="grid gap-2 sm:grid-cols-3">
          <Metric icon={<Target size={16} aria-hidden="true" />} label="Confidence" value={reference?.confidence ? `${Math.round(reference.confidence * 100)}%` : "Pending"} />
          <Metric icon={<Layers size={16} aria-hidden="true" />} label="Sources" value={brief ? String(brief.sourceCount) : "0"} />
          <Metric icon={<DollarSign size={16} aria-hidden="true" />} label="Price" value={priceContext(brief).replace("Observed ", "")} />
        </div>
      </div>
    </Panel>
  );
}

function Metric({ icon, label, value }: { icon: ReactNode; label: string; value: string }) {
  return (
    <div className="min-w-0 rounded-md border border-[var(--border)] bg-[var(--surface-raised)] p-3">
      <div className="flex items-center gap-2 text-sm font-medium text-[var(--text-secondary)]">
        {icon}
        {label}
      </div>
      <p className="mt-2 truncate text-sm font-semibold text-[var(--text-primary)]">{value}</p>
    </div>
  );
}
