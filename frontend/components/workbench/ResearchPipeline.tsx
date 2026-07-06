import { Check, Circle, Loader2, Minus, X } from "lucide-react";

import { RESEARCH_STAGES, stageState, stageSubsteps, statusLabel, type StageState } from "@/lib/presentation";
import type { ResearchJob } from "@/lib/types";

export function ResearchPipeline({ job }: { job: ResearchJob | null }) {
  return (
    <section aria-label="Research progress" className="rounded-lg border border-[var(--border)] bg-[var(--surface)] p-3">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <p className="text-sm font-semibold text-[var(--text-primary)]">Research progress</p>
        <p className="text-sm text-[var(--text-secondary)]">{job ? statusLabel(job.status) : "Ready to capture product evidence"}</p>
      </div>
      <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-5">
        {RESEARCH_STAGES.map((stage) => {
          const state = stageState(stage.id, job?.status);
          const substeps = stageSubsteps(stage.id, job);
          return (
            <div
              key={stage.id}
              className={`min-h-[108px] rounded-md border px-3 py-3 transition ${
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
              {substeps.length ? (
                <div className="mt-3 flex items-start gap-2 rounded-md border border-[color-mix(in_srgb,var(--accent)_24%,var(--border))] bg-[color-mix(in_srgb,var(--accent)_8%,var(--surface))] px-2.5 py-2 text-xs leading-5 text-[var(--text-primary)]">
                  <SubstepIcon state={substeps[0].state} />
                  <span>{substeps[0].label}</span>
                </div>
              ) : null}
              {stage.id === "research" && state === "active" ? (
                <p className="mt-2 text-xs leading-5 text-[var(--text-secondary)]">Live sources may take a minute.</p>
              ) : null}
            </div>
          );
        })}
      </div>
    </section>
  );
}

function StageIcon({ state }: { state: StageState }) {
  const className = "shrink-0";
  if (state === "active") return <Loader2 className={`${className} animate-spin text-[var(--accent)]`} size={15} aria-hidden="true" />;
  if (state === "complete") return <Check className={`${className} text-[var(--success)]`} size={15} aria-hidden="true" />;
  if (state === "failed") return <X className={`${className} text-[var(--danger)]`} size={15} aria-hidden="true" />;
  if (state === "skipped") return <Minus className={`${className} text-[var(--warning)]`} size={15} aria-hidden="true" />;
  return <Circle className={`${className} text-[var(--text-muted)]`} size={13} aria-hidden="true" />;
}

function SubstepIcon({ state }: { state: StageState }) {
  const className = "mt-[3px] shrink-0";
  if (state === "active") return <Loader2 className={`${className} animate-spin text-[var(--accent)]`} size={12} aria-hidden="true" />;
  return <Circle className={`${className} text-[var(--text-muted)]`} size={9} aria-hidden="true" />;
}
