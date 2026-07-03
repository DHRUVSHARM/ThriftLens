import { Activity, ScanSearch } from "lucide-react";

import { Badge } from "./ui";

export function WorkbenchChrome({ providerMode }: { providerMode?: string }) {
  const sourceStatus = sourceStatusFromProviderMode(providerMode);
  return (
    <header className="flex flex-wrap items-center justify-between gap-3">
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-md border border-[var(--border)] bg-[var(--surface)] text-[var(--accent-strong)]">
          <ScanSearch size={21} aria-hidden="true" />
        </div>
        <div>
          <p className="text-xl font-semibold tracking-normal text-[var(--text-primary)]">ThriftLens</p>
          <p className="text-sm text-[var(--text-muted)]">Source-backed product research</p>
        </div>
      </div>
      <div className="flex items-center gap-2">
        <Badge tone={sourceStatus.tone}>
          <Activity className="mr-1.5" size={13} aria-hidden="true" />
          {sourceStatus.label}
        </Badge>
      </div>
    </header>
  );
}

function sourceStatusFromProviderMode(providerMode?: string): {
  label: string;
  tone: "neutral" | "success" | "warning";
} {
  if (!providerMode) {
    return { label: "Checking sources", tone: "neutral" };
  }
  if (providerMode === "REAL_MODE") {
    return { label: "Live sources", tone: "success" };
  }
  if (providerMode === "SAMPLE_MODE") {
    return { label: "Sample mode", tone: "warning" };
  }
  if (providerMode === "TEST_MODE") {
    return { label: "Test mode", tone: "neutral" };
  }
  return { label: "Source status unavailable", tone: "warning" };
}
