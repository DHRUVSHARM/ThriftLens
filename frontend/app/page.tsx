"use client";

import {
  AlertCircle,
  BadgeCheck,
  Clipboard,
  DollarSign,
  ExternalLink,
  FileImage,
  Image as ImageIcon,
  Loader2,
  RefreshCw,
  Search,
  SlidersHorizontal,
  Sparkles,
  Upload,
  X,
} from "lucide-react";
import type { FormEvent, ReactNode } from "react";
import { useEffect, useMemo, useState } from "react";

import { ApiError, createResearchJob, getResearchJob, retryResearchJob } from "@/lib/api";
import { buildSummary, currentBrief, groupRankedProducts, priceContext, priceLabel } from "@/lib/presentation";
import type { InputMode, JobStatus, ProductResearchBrief, RankedProduct, ResearchJob } from "@/lib/types";

const TERMINAL_STATUSES = new Set<JobStatus>(["complete", "partial", "failed", "expired", "needs_refinement"]);
const MAX_IMAGE_BYTES = 8 * 1024 * 1024;
const SUPPORTED_IMAGE_TYPES = new Set(["image/jpeg", "image/png", "image/webp"]);

function formatStatus(status: JobStatus): string {
  return status.replace(/_/g, " ");
}

function statusTone(status: JobStatus): string {
  if (status === "complete") return "bg-emerald-100 text-emerald-800";
  if (status === "partial" || status === "needs_refinement") return "bg-amber-100 text-amber-800";
  if (status === "failed" || status === "expired") return "bg-rose-100 text-rose-800";
  return "bg-sky-100 text-sky-800";
}

function parseOptionalAmount(value: string): number | undefined {
  if (!value.trim()) return undefined;
  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed >= 0 ? parsed : undefined;
}

export default function Home() {
  const [mode, setMode] = useState<InputMode>("image");
  const [textDescription, setTextDescription] = useState("minimal black desk lamp with wireless charging");
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [imagePreviewUrl, setImagePreviewUrl] = useState<string | null>(null);
  const [rankingPreference, setRankingPreference] = useState<"closest" | "grouped">("grouped");
  const [budgetMin, setBudgetMin] = useState("");
  const [budgetMax, setBudgetMax] = useState("");
  const [job, setJob] = useState<ResearchJob | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const brief = currentBrief(job);
  const isRunning = Boolean(job && !TERMINAL_STATUSES.has(job.status));

  useEffect(() => {
    if (!imageFile) {
      setImagePreviewUrl(null);
      return;
    }
    const previewUrl = URL.createObjectURL(imageFile);
    setImagePreviewUrl(previewUrl);
    return () => URL.revokeObjectURL(previewUrl);
  }, [imageFile]);

  useEffect(() => {
    if (!job || TERMINAL_STATUSES.has(job.status)) return;

    const timeout = window.setTimeout(async () => {
      try {
        setJob(await getResearchJob(job.jobId));
      } catch (pollError) {
        setError(pollError instanceof ApiError ? pollError.message : "Could not refresh research status.");
      }
    }, 1400);

    return () => window.clearTimeout(timeout);
  }, [job]);

  const observedPriceContext = useMemo(() => priceContext(brief), [brief]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setCopied(false);

    const researchPreferences = {
      rankingPreference,
      budgetMin: parseOptionalAmount(budgetMin),
      budgetMax: parseOptionalAmount(budgetMax),
    };

    if (mode === "text") {
      const trimmed = textDescription.trim();
      if (!trimmed) {
        setError("Describe the product before starting research.");
        return;
      }
      setIsSubmitting(true);
      try {
        setJob(
          await createResearchJob({
            inputType: "text",
            textDescription: trimmed,
            researchPreferences,
          }),
        );
      } catch (submitError) {
        setError(submitError instanceof ApiError ? submitError.message : "Could not start research.");
      } finally {
        setIsSubmitting(false);
      }
      return;
    }

    if (!imageFile) {
      setError("Upload a JPEG, PNG, or WebP image before starting research.");
      return;
    }
    setIsSubmitting(true);
    try {
      setJob(await createResearchJob({ inputType: "image", image: imageFile, researchPreferences }));
    } catch (submitError) {
      setError(submitError instanceof ApiError ? submitError.message : "Could not start research.");
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleRetry() {
    if (!job?.retryable) return;
    setError(null);
    setCopied(false);
    try {
      setJob(await retryResearchJob(job.jobId));
    } catch (retryError) {
      setError(retryError instanceof ApiError ? retryError.message : "Could not retry this research job.");
    }
  }

  async function handleCopy() {
    if (!brief) return;
    await navigator.clipboard.writeText(buildSummary(brief));
    setCopied(true);
  }

  function handleImage(file: File | null) {
    setError(null);
    if (!file) {
      setImageFile(null);
      return;
    }
    if (!SUPPORTED_IMAGE_TYPES.has(file.type)) {
      setError("Unsupported image type. Use JPEG, PNG, or WebP.");
      setImageFile(null);
      return;
    }
    if (file.size > MAX_IMAGE_BYTES) {
      setError("Uploaded image must be 8MB or smaller.");
      setImageFile(null);
      return;
    }
    setImageFile(file);
  }

  return (
    <main className="min-h-screen bg-[#f6f4ef] text-neutral-950">
      <div className="mx-auto grid min-h-screen w-full max-w-7xl gap-4 px-4 py-4 lg:grid-cols-[390px_1fr] lg:py-6">
        <section className="flex flex-col gap-4 rounded-md border border-neutral-200 bg-white p-4 shadow-sm lg:sticky lg:top-6 lg:max-h-[calc(100vh-3rem)] lg:overflow-auto">
          <WorkbenchHeader providerMode={job?.providerMode} />

          <form className="flex flex-col gap-4" onSubmit={handleSubmit}>
            <ModeSwitch mode={mode} setMode={setMode} />

            {mode === "image" ? (
              <ImageInput imageFile={imageFile} imagePreviewUrl={imagePreviewUrl} onImage={handleImage} />
            ) : (
              <TextInput textDescription={textDescription} setTextDescription={setTextDescription} />
            )}

            <fieldset className="rounded-md border border-neutral-200 p-3">
              <legend className="flex items-center gap-2 px-1 text-sm font-semibold text-neutral-800">
                <SlidersHorizontal size={16} aria-hidden="true" />
                Preferences
              </legend>
              <div className="mt-3 grid gap-3">
                <label className="grid gap-1 text-sm">
                  <span className="font-medium text-neutral-700">Ranking</span>
                  <select
                    className="h-10 rounded-md border border-neutral-300 bg-white px-3 text-sm outline-none focus:border-emerald-700"
                    value={rankingPreference}
                    onChange={(event) => setRankingPreference(event.target.value as "closest" | "grouped")}
                  >
                    <option value="grouped">Grouped alternatives</option>
                    <option value="closest">Closest match first</option>
                  </select>
                </label>

                <div className="grid grid-cols-2 gap-2">
                  <label className="grid gap-1 text-sm">
                    <span className="font-medium text-neutral-700">Min budget</span>
                    <input
                      className="h-10 min-w-0 rounded-md border border-neutral-300 px-3 text-sm outline-none focus:border-emerald-700"
                      inputMode="decimal"
                      min="0"
                      placeholder="Optional"
                      type="number"
                      value={budgetMin}
                      onChange={(event) => setBudgetMin(event.target.value)}
                    />
                  </label>
                  <label className="grid gap-1 text-sm">
                    <span className="font-medium text-neutral-700">Max budget</span>
                    <input
                      className="h-10 min-w-0 rounded-md border border-neutral-300 px-3 text-sm outline-none focus:border-emerald-700"
                      inputMode="decimal"
                      min="0"
                      placeholder="Optional"
                      type="number"
                      value={budgetMax}
                      onChange={(event) => setBudgetMax(event.target.value)}
                    />
                  </label>
                </div>
              </div>
            </fieldset>

            {error ? <InlineError message={error} /> : null}

            <button
              className="flex h-11 items-center justify-center gap-2 rounded-md bg-neutral-950 px-4 text-sm font-semibold text-white transition hover:bg-neutral-800 disabled:cursor-not-allowed disabled:bg-neutral-400"
              disabled={isSubmitting}
              type="submit"
            >
              {isSubmitting ? <Loader2 className="animate-spin" size={18} aria-hidden="true" /> : <Search size={18} aria-hidden="true" />}
              Start research
            </button>
          </form>

          <JobStatusPanel job={job} isRunning={isRunning} onRetry={handleRetry} />
          <ReferencePanel brief={brief} />
        </section>

        <section className="min-h-[calc(100vh-2rem)] rounded-md border border-neutral-200 bg-white p-4 shadow-sm lg:p-5">
          <ResultsHeader job={job} brief={brief} priceContext={observedPriceContext} copied={copied} onCopy={handleCopy} />
          <ResultsBody job={job} brief={brief} />
        </section>
      </div>
    </main>
  );
}

function WorkbenchHeader({ providerMode }: { providerMode?: string }) {
  const isSample = providerMode === "SAMPLE_MODE" || providerMode === undefined;
  return (
    <header className="border-b border-neutral-200 pb-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-emerald-700">ThriftLens</p>
          <h1 className="mt-1 text-2xl font-semibold tracking-normal text-neutral-950">Product research workbench</h1>
        </div>
        <span className={`shrink-0 rounded-full px-3 py-1 text-xs font-semibold ${isSample ? "bg-amber-100 text-amber-800" : "bg-emerald-100 text-emerald-800"}`}>
          {isSample ? "Sample" : "Live"}
        </span>
      </div>
    </header>
  );
}

function ModeSwitch({ mode, setMode }: { mode: InputMode; setMode: (mode: InputMode) => void }) {
  return (
    <div className="grid grid-cols-2 rounded-md border border-neutral-200 bg-neutral-100 p-1 text-sm" role="tablist" aria-label="Input mode">
      <button
        aria-selected={mode === "image"}
        className={`flex h-10 items-center justify-center gap-2 rounded px-3 font-medium ${mode === "image" ? "bg-neutral-950 text-white" : "text-neutral-700 hover:bg-white"}`}
        onClick={() => setMode("image")}
        type="button"
      >
        <Upload size={16} aria-hidden="true" />
        Image
      </button>
      <button
        aria-selected={mode === "text"}
        className={`flex h-10 items-center justify-center gap-2 rounded px-3 font-medium ${mode === "text" ? "bg-neutral-950 text-white" : "text-neutral-700 hover:bg-white"}`}
        onClick={() => setMode("text")}
        type="button"
      >
        <Search size={16} aria-hidden="true" />
        Text
      </button>
    </div>
  );
}

function ImageInput({
  imageFile,
  imagePreviewUrl,
  onImage,
}: {
  imageFile: File | null;
  imagePreviewUrl: string | null;
  onImage: (file: File | null) => void;
}) {
  return (
    <div className="grid gap-2">
      <label
        className="flex min-h-56 cursor-pointer flex-col items-center justify-center rounded-md border border-dashed border-neutral-300 bg-neutral-50 p-4 text-center transition hover:border-emerald-700"
        htmlFor="product-image"
      >
        {imagePreviewUrl ? (
          <img alt="Selected product preview" className="max-h-48 w-full rounded object-contain" src={imagePreviewUrl} />
        ) : (
          <>
            <FileImage size={34} className="text-neutral-500" aria-hidden="true" />
            <span className="mt-3 text-sm font-semibold text-neutral-800">Upload product image</span>
            <span className="mt-1 text-xs text-neutral-500">JPEG, PNG, or WebP up to 8MB</span>
          </>
        )}
      </label>
      <input
        id="product-image"
        className="sr-only"
        accept="image/jpeg,image/png,image/webp"
        type="file"
        onChange={(event) => onImage(event.target.files?.[0] || null)}
      />
      {imageFile ? (
        <div className="flex items-center justify-between gap-2 rounded-md bg-neutral-100 px-3 py-2 text-sm text-neutral-700">
          <span className="truncate">{imageFile.name}</span>
          <button className="rounded p-1 hover:bg-neutral-200" onClick={() => onImage(null)} type="button" aria-label="Remove image">
            <X size={16} aria-hidden="true" />
          </button>
        </div>
      ) : null}
    </div>
  );
}

function TextInput({
  textDescription,
  setTextDescription,
}: {
  textDescription: string;
  setTextDescription: (value: string) => void;
}) {
  return (
    <label className="grid gap-2 text-sm">
      <span className="font-semibold text-neutral-800">Product description</span>
      <textarea
        className="min-h-48 resize-y rounded-md border border-neutral-300 bg-white p-3 text-sm leading-6 outline-none focus:border-emerald-700"
        maxLength={2000}
        value={textDescription}
        onChange={(event) => setTextDescription(event.target.value)}
      />
      <span className="text-xs text-neutral-500">{textDescription.length}/2000 characters</span>
    </label>
  );
}

function InlineError({ message }: { message: string }) {
  return (
    <div className="flex gap-2 rounded-md border border-rose-200 bg-rose-50 p-3 text-sm text-rose-800">
      <AlertCircle className="mt-0.5 shrink-0" size={16} aria-hidden="true" />
      <p>{message}</p>
    </div>
  );
}

function JobStatusPanel({ job, isRunning, onRetry }: { job: ResearchJob | null; isRunning: boolean; onRetry: () => void }) {
  const steps: JobStatus[] = ["queued", "extracting_reference", "researching_sources", "ranking_results", "complete"];
  return (
    <section className="rounded-md border border-neutral-200 p-3">
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-neutral-500">Status</p>
          <h2 className="mt-1 text-base font-semibold text-neutral-950">{job ? formatStatus(job.status) : "Ready"}</h2>
        </div>
        {isRunning ? <Loader2 className="animate-spin text-emerald-700" size={20} aria-hidden="true" /> : null}
      </div>
      <p className="mt-2 text-sm text-neutral-600">{job?.progressMessage || "Start with an image or text description."}</p>
      <div className="mt-3 grid gap-2">
        {steps.map((step) => (
          <div key={step} className="flex items-center gap-2 text-xs text-neutral-600">
            <span className={`h-2.5 w-2.5 rounded-full ${job?.status === step ? "bg-emerald-700" : "bg-neutral-300"}`} />
            <span>{formatStatus(step)}</span>
          </div>
        ))}
      </div>
      {job?.safeError ? <InlineError message={job.safeError.message} /> : null}
      {job?.retryable ? (
        <button
          className="mt-3 flex h-9 w-full items-center justify-center gap-2 rounded-md border border-neutral-300 text-sm font-semibold text-neutral-800 hover:bg-neutral-100"
          onClick={onRetry}
          type="button"
        >
          <RefreshCw size={16} aria-hidden="true" />
          Retry
        </button>
      ) : null}
    </section>
  );
}

function ReferencePanel({ brief }: { brief: ProductResearchBrief | null }) {
  const reference = brief?.productReference;
  if (!reference) return null;

  const attributes = [
    ["Type", reference.productType],
    ["Brand", reference.brand || "Unknown"],
    ["Color", reference.color || "Unknown"],
    ["Confidence", `${Math.round((reference.confidence || 0) * 100)}%`],
  ];

  return (
    <section className="rounded-md border border-neutral-200 p-3">
      <p className="text-xs font-semibold uppercase tracking-wide text-neutral-500">Reference</p>
      <h2 className="mt-1 text-base font-semibold text-neutral-950">{reference.title}</h2>
      <dl className="mt-3 grid grid-cols-2 gap-2 text-sm">
        {attributes.map(([label, value]) => (
          <div key={label} className="rounded bg-neutral-50 p-2">
            <dt className="text-xs text-neutral-500">{label}</dt>
            <dd className="mt-1 truncate font-medium text-neutral-800">{value}</dd>
          </div>
        ))}
      </dl>
      {reference.keyFeatures?.length ? (
        <div className="mt-3 flex flex-wrap gap-2">
          {reference.keyFeatures.map((feature) => (
            <span key={feature} className="rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-medium text-emerald-800">
              {feature}
            </span>
          ))}
        </div>
      ) : null}
      {reference.assumptions?.length ? <p className="mt-3 text-xs leading-5 text-neutral-500">{reference.assumptions.join(" ")}</p> : null}
    </section>
  );
}

function ResultsHeader({
  job,
  brief,
  priceContext,
  copied,
  onCopy,
}: {
  job: ResearchJob | null;
  brief: ProductResearchBrief | null;
  priceContext: string;
  copied: boolean;
  onCopy: () => void;
}) {
  return (
    <header className="flex flex-col gap-3 border-b border-neutral-200 pb-4 md:flex-row md:items-start md:justify-between">
      <div>
        <div className="flex flex-wrap items-center gap-2">
          <span className={`rounded-full px-3 py-1 text-xs font-semibold ${job ? statusTone(job.status) : "bg-neutral-100 text-neutral-700"}`}>
            {job ? formatStatus(job.status) : "ready"}
          </span>
          {brief?.label ? <span className="rounded-full bg-amber-100 px-3 py-1 text-xs font-semibold text-amber-800">{brief.label}</span> : null}
        </div>
        <h2 className="mt-3 text-2xl font-semibold tracking-normal text-neutral-950">Source-backed matches</h2>
        <p className="mt-1 text-sm text-neutral-600">{brief?.trustSummary || "Research results will appear here after the job starts."}</p>
        <p className="mt-2 flex items-center gap-2 text-sm font-semibold text-neutral-800">
          <DollarSign size={16} aria-hidden="true" />
          {priceContext}
        </p>
      </div>
      <button
        className="flex h-10 items-center justify-center gap-2 rounded-md border border-neutral-300 px-3 text-sm font-semibold text-neutral-800 hover:bg-neutral-100 disabled:cursor-not-allowed disabled:opacity-50"
        disabled={!brief}
        onClick={onCopy}
        type="button"
      >
        <Clipboard size={16} aria-hidden="true" />
        {copied ? "Copied" : "Copy"}
      </button>
    </header>
  );
}

function ResultsBody({ job, brief }: { job: ResearchJob | null; brief: ProductResearchBrief | null }) {
  if (!job) {
    return <EmptyState />;
  }
  if (!brief && !TERMINAL_STATUSES.has(job.status)) {
    return <RunningState message={job.progressMessage} />;
  }
  if (!brief && job.status === "failed") {
    return <FailureState message={job.safeError?.message || "Research failed. Try a clearer input or retry when available."} />;
  }
  if (!brief) {
    return <EmptyState />;
  }
  if (brief.statusReason === "research_unavailable") {
    return <ResearchUnavailable brief={brief} />;
  }

  const { closest, cheaper, similar, premium, possible } = groupRankedProducts(brief.rankedProducts);

  return (
    <div className="grid gap-5 py-5">
      <TrustPanel brief={brief} />
      <ProductSection title="Closest match" icon={<BadgeCheck size={18} aria-hidden="true" />} products={closest} emptyMessage="No verified closest match found." />
      <ProductSection title="Cheaper" products={cheaper} />
      <ProductSection title="Similar price" products={similar} />
      <ProductSection title="Premium" products={premium} />
      {possible.length ? <ProductSection title="Possible matches" products={possible} lowConfidence /> : null}
    </div>
  );
}

function EmptyState() {
  return (
    <div className="grid min-h-[520px] place-items-center text-center">
      <div className="max-w-md">
        <Sparkles className="mx-auto text-emerald-700" size={34} aria-hidden="true" />
        <p className="mt-4 text-lg font-semibold text-neutral-950">Ready for product research</p>
        <p className="mt-2 text-sm leading-6 text-neutral-600">Upload a product image or describe what you are looking for to build a source-backed research brief.</p>
      </div>
    </div>
  );
}

function RunningState({ message }: { message: string }) {
  return (
    <div className="grid min-h-[520px] place-items-center text-center">
      <div>
        <Loader2 className="mx-auto animate-spin text-emerald-700" size={36} aria-hidden="true" />
        <p className="mt-4 text-lg font-semibold text-neutral-950">{message}</p>
        <p className="mt-2 text-sm text-neutral-600">The browser can refresh safely; job state is stored server-side.</p>
      </div>
    </div>
  );
}

function FailureState({ message }: { message: string }) {
  return (
    <div className="mt-5 rounded-md border border-rose-200 bg-rose-50 p-4 text-rose-900">
      <div className="flex gap-3">
        <AlertCircle className="mt-0.5 shrink-0" size={18} aria-hidden="true" />
        <p className="text-sm">{message}</p>
      </div>
    </div>
  );
}

function ResearchUnavailable({ brief }: { brief: ProductResearchBrief }) {
  return (
    <div className="grid gap-4 py-5">
      <TrustPanel brief={brief} />
      <div className="rounded-md border border-amber-200 bg-amber-50 p-4 text-amber-950">
        <p className="font-semibold">Research sources are unavailable.</p>
        <p className="mt-2 text-sm leading-6">{brief.trustSummary}</p>
      </div>
    </div>
  );
}

function TrustPanel({ brief }: { brief: ProductResearchBrief }) {
  return (
    <section className="rounded-md border border-neutral-200 bg-neutral-50 p-4">
      <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
        <div>
          <p className="text-sm font-semibold text-neutral-950">{brief.trustSummary}</p>
          <p className="mt-1 text-sm text-neutral-600">{brief.freshnessNote}</p>
        </div>
        <span className="w-fit rounded-full bg-white px-3 py-1 text-xs font-semibold text-neutral-700">{brief.sourceCount} sources</span>
      </div>
      {brief.uncertaintyNotes.length ? (
        <ul className="mt-3 grid gap-1 text-sm text-neutral-600">
          {brief.uncertaintyNotes.map((note) => (
            <li key={note}>- {note}</li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}

function ProductSection({
  title,
  products,
  icon,
  lowConfidence = false,
  emptyMessage,
}: {
  title: string;
  products: RankedProduct[];
  icon?: ReactNode;
  lowConfidence?: boolean;
  emptyMessage?: string;
}) {
  if (!products.length && !emptyMessage) return null;
  return (
    <section>
      <div className="mb-3 flex items-center gap-2">
        {icon}
        <h3 className="text-base font-semibold text-neutral-950">{title}</h3>
      </div>
      {products.length ? (
        <div className="grid gap-3 xl:grid-cols-2">
          {products.map((item) => (
            <ProductCard key={`${item.product.source}-${item.product.title}-${item.group}`} item={item} lowConfidence={lowConfidence} />
          ))}
        </div>
      ) : (
        <p className="rounded-md border border-neutral-200 bg-neutral-50 p-4 text-sm text-neutral-600">{emptyMessage}</p>
      )}
    </section>
  );
}

function ProductCard({ item, lowConfidence }: { item: RankedProduct; lowConfidence: boolean }) {
  const product = item.product;
  return (
    <article className={`grid min-h-48 grid-cols-[88px_1fr] gap-3 rounded-md border p-3 ${lowConfidence ? "border-dashed border-neutral-300 bg-neutral-50" : "border-neutral-200 bg-white"}`}>
      <div className="flex h-24 w-22 items-center justify-center overflow-hidden rounded-md bg-neutral-100">
        {product.imageUrl ? (
          <img alt="" className="h-full w-full object-cover" src={product.imageUrl} />
        ) : (
          <ImageIcon className="text-neutral-400" size={24} aria-hidden="true" />
        )}
      </div>
      <div className="min-w-0">
        <div className="flex items-start justify-between gap-2">
          <h4 className="line-clamp-2 text-sm font-semibold leading-5 text-neutral-950">{product.title}</h4>
          <span className="shrink-0 rounded-full bg-neutral-100 px-2 py-1 text-[11px] font-semibold uppercase text-neutral-600">{item.confidence}</span>
        </div>
        <p className="mt-1 truncate text-xs text-neutral-500">{product.retailer || product.source}</p>
        <p className="mt-2 text-lg font-semibold text-neutral-950">{priceLabel(item)}</p>
        <p className="mt-1 text-xs text-neutral-500">{product.availability || "Availability unknown"}</p>
        <p className="mt-2 text-sm leading-5 text-neutral-700">{item.reason}</p>
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <span className="rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-semibold text-emerald-800">{item.group}</span>
          <span className="rounded-full bg-neutral-100 px-2.5 py-1 text-xs font-medium text-neutral-600">{product.freshness || "source-backed"}</span>
          {product.url ? (
            <a
              className="ml-auto flex h-8 items-center gap-1 rounded-md border border-neutral-300 px-2 text-xs font-semibold text-neutral-800 hover:bg-neutral-100"
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
