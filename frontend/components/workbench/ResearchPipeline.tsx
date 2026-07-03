import { Check, Circle, Loader2, Minus, X } from "lucide-react";

import { RESEARCH_STAGES, stageState, statusLabel } from "@/lib/presentation";
import type { ResearchJob } from "@/lib/types";

export function ResearchPipeline({ job }: { job: ResearchJob | null }) {
  return (
    <section className="rounded-lg border border-[var(--border)] bg-[var(--surface)] p-3">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <p className="text-sm font-semibold text-[var(--text-primary)]">Research progress</p>
        <p className="text-sm text-[var(--text-secondary)]">{job ? statusLabel(job.status) : "Ready to capture product evidence"}</p>
      </div>
      <div className="grid gap-2 md:grid-cols-5">
        {RESEARCH_STAGES.map((stage) => {
          const state = stageState(stage.id, job?.status);
          return (
            <div
              key={stage.id}
              className={`rounded-md border px-3 py-3 transition ${
                state === "active"
                  ? "border-[var(--accent)] bg-[color-mix(in_srgb,var(--accent)_12%,var(--surface))] ring-1 ring-[color-mix(in_srgb,var(--accent)_45%,transparent)]"
                  : "border-[var(--border)] bg-[var(--surface)]"
              }`}
            >
              <div className="flex items-center gap-2">
                <StageIcon state={state} />
                <span className="text-sm font-semibold text-[var(--text-primary)]">{stage.label}</span>
              </div>
              <p className="mt-1 text-xs text-[var(--text-muted)]">{stage.description}</p>
            </div>
          );
        })}
      </div>
    </section>
  );
}

function StageIcon({ state }: { state: ReturnType<typeof stageState> }) {
  const className = "shrink-0";
  if (state === "active") return <Loader2 className={`${className} animate-spin text-[var(--accent)]`} size={15} aria-hidden="true" />;
  if (state === "complete") return <Check className={`${className} text-[var(--success)]`} size={15} aria-hidden="true" />;
  if (state === "failed") return <X className={`${className} text-[var(--danger)]`} size={15} aria-hidden="true" />;
  if (state === "skipped") return <Minus className={`${className} text-[var(--warning)]`} size={15} aria-hidden="true" />;
  return <Circle className={`${className} text-[var(--text-muted)]`} size={13} aria-hidden="true" />;
}
