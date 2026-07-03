"use client";

import type { FormEvent, ReactNode } from "react";
import { useEffect, useMemo, useState } from "react";
import Image from "next/image";
import { ArrowRight, Camera, Layers, Search, ShieldCheck, SlidersHorizontal, Sparkles } from "lucide-react";

import { InsightHeader } from "@/components/workbench/InsightHeader";
import { ResearchPipeline } from "@/components/workbench/ResearchPipeline";
import { ResultsWorkbench } from "@/components/workbench/ResultModules";
import { ThemeToggle } from "@/components/workbench/ThemeToggle";
import { UnifiedInput } from "@/components/workbench/UnifiedInput";
import { WorkbenchChrome } from "@/components/workbench/WorkbenchChrome";
import { ApiError, createResearchJob, getResearchJob, getRuntimeHealth, retryResearchJob } from "@/lib/api";
import { buildSummary, currentBrief } from "@/lib/presentation";
import type { JobStatus, ResearchJob, ResearchPreferences } from "@/lib/types";

const TERMINAL_STATUSES = new Set<JobStatus>(["complete", "partial", "failed", "expired", "needs_refinement"]);
const MAX_IMAGE_BYTES = 8 * 1024 * 1024;
const SUPPORTED_IMAGE_TYPES = new Set(["image/jpeg", "image/png", "image/webp"]);

export default function Home() {
  const [text, setText] = useState("");
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [imagePreviewUrl, setImagePreviewUrl] = useState<string | null>(null);
  const [job, setJob] = useState<ResearchJob | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [runtimeProviderMode, setRuntimeProviderMode] = useState<string | undefined>();

  const brief = currentBrief(job);
  const displayedProviderMode = job?.providerMode || runtimeProviderMode;

  useEffect(() => {
    let isMounted = true;

    async function loadRuntimeHealth() {
      try {
        const health = await getRuntimeHealth();
        if (isMounted) {
          setRuntimeProviderMode(health.providerMode);
        }
      } catch {
        if (isMounted) {
          setRuntimeProviderMode("UNKNOWN");
        }
      }
    }

    void loadRuntimeHealth();
    return () => {
      isMounted = false;
    };
  }, []);

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

  const researchPreferences = useMemo(
    (): ResearchPreferences => ({
      rankingPreference: "grouped",
    }),
    [],
  );

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setCopied(false);

    const trimmedText = text.trim();
    if (!imageFile && !trimmedText) {
      setError("Add a product image, a description, or both before starting research.");
      return;
    }

    setIsSubmitting(true);
    try {
      const nextJob = imageFile
        ? await createResearchJob({
            inputType: "image",
            image: imageFile,
            targetDescription: trimmedText || undefined,
            researchPreferences,
          })
        : await createResearchJob({
            inputType: "text",
            textDescription: trimmedText,
            researchPreferences,
          });
      setJob(nextJob);
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

  function handleRefineEvidence() {
    document.getElementById("workbench")?.scrollIntoView({ behavior: "smooth", block: "start" });
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
    <main className="app-shell min-h-screen text-[var(--text-primary)]">
      <LandingIntro />
      <section id="workbench" className="workbench-section border-t border-[var(--border)]">
        <div className="mx-auto grid w-full max-w-7xl gap-6 px-4 py-10 md:px-6 lg:px-8">
          <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_auto] xl:items-end">
            <div className="max-w-3xl">
              <h2 className="text-3xl font-semibold tracking-normal text-[var(--text-primary)]">Try the research flow.</h2>
              <p className="mt-3 text-base leading-7 text-[var(--text-secondary)]">
                Add evidence once. ThriftLens keeps it visible while it extracts, searches, ranks, and asks for refinement only when confidence is low.
              </p>
            </div>
            <WorkbenchChrome providerMode={displayedProviderMode} />
          </div>
          <UnifiedInput
            text={text}
            setText={setText}
            imageFile={imageFile}
            imagePreviewUrl={imagePreviewUrl}
            onImage={handleImage}
            error={error}
            isSubmitting={isSubmitting}
            onSubmit={handleSubmit}
          />
          <ResearchPipeline job={job} />
          <InsightHeader job={job} brief={brief} />
          <ResultsWorkbench job={job} brief={brief} copied={copied} onCopy={handleCopy} onRetry={handleRetry} onRefine={handleRefineEvidence} />
        </div>
      </section>
    </main>
  );
}

function LandingIntro() {
  return (
    <section className="landing-section">
      <div className="relative overflow-hidden border-b border-[var(--border)]">
        <Image
          alt="A studio archive of products with visual research overlays"
          className="absolute inset-0 h-full w-full object-cover"
          fill
          priority
          sizes="100vw"
          src="/assets/thriftlens-hero.png"
        />
        <div className="absolute inset-0 bg-[image:var(--hero-overlay)]" />
        <div className="relative z-10 mx-auto grid min-h-[640px] w-full max-w-7xl content-between gap-12 px-4 py-6 md:px-6 lg:px-8">
          <header className="flex items-center justify-between gap-4">
            <a className="text-sm font-semibold text-[var(--hero-text-primary)]" href="#workbench">
              ThriftLens
            </a>
            <nav className="hidden items-center gap-6 text-sm text-[var(--hero-text-secondary)] md:flex" aria-label="Landing navigation">
              <a className="hover:text-[var(--hero-text-primary)]" href="#archive">Research paths</a>
              <a className="hover:text-[var(--hero-text-primary)]" href="#process">How it works</a>
              <a className="hover:text-[var(--hero-text-primary)]" href="#workbench">Try it</a>
            </nav>
            <div className="flex items-center gap-2">
              <ThemeToggle />
              <a className="rounded-md bg-[var(--hero-text-primary)] px-4 py-2 text-sm font-semibold text-[var(--landing-bg)]" href="#workbench">
                Try it
              </a>
            </div>
          </header>

          <div className="max-w-2xl pb-10">
            <h1 className="text-6xl font-semibold leading-[0.96] tracking-normal text-[var(--hero-text-primary)] md:text-7xl">
              Find the product behind an image.
            </h1>
            <p className="mt-6 max-w-xl text-base leading-7 text-[var(--hero-text-secondary)]">
              Upload a photo, screenshot, or rough description. ThriftLens extracts a searchable reference, checks source-backed products, and organizes matches by price and confidence.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <a className="inline-flex h-10 items-center gap-2 rounded-md border border-[var(--accent)] bg-[var(--accent)] px-4 text-[13px] font-semibold leading-5 text-[var(--accent-contrast)]" href="#workbench">
                Try product research
                <ArrowRight size={16} aria-hidden="true" />
              </a>
              <a className="inline-flex h-10 items-center rounded-md border border-[color-mix(in_srgb,var(--hero-text-primary)_24%,transparent)] px-4 text-[13px] font-semibold text-[var(--hero-text-primary)] hover:border-[color-mix(in_srgb,var(--hero-text-primary)_48%,transparent)]" href="#process">
                See how it works
              </a>
            </div>
          </div>
        </div>
      </div>

      <div className="mx-auto grid w-full max-w-7xl gap-16 px-4 py-16 md:px-6 lg:px-8">
        <HeroArchive />
        <ProcessNarrative />
      </div>
    </section>
  );
}

function HeroArchive() {
  const cards = [
    {
      title: "From a room photo",
      meta: "detect the product to research",
      src: "/assets/thriftlens-home-card.png",
      span: "lg:col-span-2",
    },
    {
      title: "From a rough reference",
      meta: "turn words into a searchable brief",
      src: "/assets/thriftlens-gear-card.png",
      span: "",
    },
    {
      title: "From similar alternatives",
      meta: "compare source-backed matches",
      src: "/assets/thriftlens-accessories-card.png",
      span: "",
    },
  ];
  return (
    <section id="archive">
      <div className="mb-8 flex flex-col justify-between gap-4 md:flex-row md:items-end">
        <div>
          <h2 className="text-3xl font-semibold tracking-normal text-[var(--text-primary)]">Start with the clues you already have.</h2>
          <p className="mt-3 max-w-2xl text-base leading-7 text-[var(--text-secondary)]">
            ThriftLens is built for the messy start: a photo from a room, a screenshot, or a few words. The app converts that into a structured reference and only then searches live sources.
          </p>
        </div>
        <a className="inline-flex h-10 w-fit items-center gap-2 rounded-md border border-[var(--border)] px-4 text-[13px] font-semibold text-[var(--text-primary)] hover:border-[var(--border-strong)]" href="#workbench">
          Start with your evidence
          <ArrowRight size={16} aria-hidden="true" />
        </a>
      </div>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {cards.map((card) => (
          <div
            className={`group relative min-h-80 overflow-hidden rounded-lg border border-[var(--border)] bg-[var(--surface)] ${card.span}`}
            key={card.title}
          >
            <Image
              alt={`${card.title} product research example`}
              className="h-full w-full object-cover"
              fill
              sizes="(min-width: 1024px) 33vw, (min-width: 640px) 50vw, 100vw"
              src={card.src}
            />
            <div className="absolute inset-0 bg-[linear-gradient(180deg,rgb(0_0_0_/_0)_36%,rgb(0_0_0_/_0.78)_100%)]" />
            <div className="absolute inset-x-0 bottom-0 flex items-end justify-between gap-3 p-5">
              <div>
                <p className="text-lg font-semibold text-white">{card.title}</p>
                <p className="mt-1 text-sm text-[rgb(255_255_255_/_0.72)]">{card.meta}</p>
              </div>
              <span className="rounded-md border border-[rgb(255_255_255_/_0.18)] px-2 py-1 text-xs font-medium text-[rgb(255_255_255_/_0.72)]">source-backed</span>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

function ProcessNarrative() {
  const steps = [
    {
      icon: <Camera size={17} aria-hidden="true" />,
      title: "Add evidence",
      text: "Start with image, text, or image plus text when the picture contains more than one possible product.",
    },
    {
      icon: <ShieldCheck size={17} aria-hidden="true" />,
      title: "Gate the input",
      text: "The vision pass rejects unsafe, non-product, or ambiguous inputs instead of guessing silently.",
    },
    {
      icon: <Sparkles size={17} aria-hidden="true" />,
      title: "Extract reference",
      text: "A structured product reference captures category, visible attributes, constraints, and confidence.",
    },
    {
      icon: <Search size={17} aria-hidden="true" />,
      title: "Search sources",
      text: "Research providers fetch source-backed products and prices through the same provider contract.",
    },
    {
      icon: <Layers size={17} aria-hidden="true" />,
      title: "Rank and group",
      text: "Deterministic scoring separates closest candidates from lower priced, similar price, and higher-end options.",
    },
    {
      icon: <SlidersHorizontal size={17} aria-hidden="true" />,
      title: "Refine when needed",
      text: "When confidence is low, the product asks for better evidence instead of presenting a fabricated answer.",
    },
  ];

  return (
    <section id="process" className="grid gap-8 lg:grid-cols-[0.85fr_1.15fr] lg:items-start">
      <div className="lg:sticky lg:top-8">
        <h2 className="text-3xl font-semibold tracking-normal text-[var(--text-primary)]">How ThriftLens keeps results grounded.</h2>
        <p className="mt-4 max-w-xl text-base leading-7 text-[var(--text-secondary)]">
          The technical shape is part of the product: vision gating, structured extraction, source-backed research, deterministic grouping, and clear retry or refinement states.
        </p>
      </div>
      <div className="grid gap-3 sm:grid-cols-2">
        {steps.map((step, index) => (
          <ProcessStep key={step.title} index={index + 1} {...step} />
        ))}
      </div>
    </section>
  );
}

function ProcessStep({ icon, index, title, text }: { icon: ReactNode; index: number; title: string; text: string }) {
  return (
    <div className="rounded-lg border border-[var(--border)] bg-[var(--surface)] p-4">
      <div className="mb-5 flex items-center justify-between gap-4">
        <div className="text-[var(--accent)]">{icon}</div>
        <span className="text-sm font-medium text-[var(--text-muted)]">{String(index).padStart(2, "0")}</span>
      </div>
      <h3 className="text-base font-semibold text-[var(--text-primary)]">{title}</h3>
      <p className="mt-2 text-sm leading-6 text-[var(--text-secondary)]">{text}</p>
    </div>
  );
}
