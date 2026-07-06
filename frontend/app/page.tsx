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
const CAROUSEL_INTERVAL_MS = 4000;
const CAROUSEL_TRANSITION_MS = 1100;

const archiveSlides = [
  {
    title: "Marketplace clues",
    text: "Bring a messy product clue from a listing, shelf, or screenshot. ThriftLens turns the visible evidence into a structured product reference before search.",
    images: [
      { src: "/assets/landing/marketplace_clothes.avif", alt: "Marketplace clothing product evidence" },
      { src: "/assets/landing/marketplace_items.avif", alt: "Marketplace product items" },
      { src: "/assets/landing/marketplace_fruits.avif", alt: "Marketplace produce product evidence" },
    ],
  },
  {
    title: "Capture the product",
    text: "Upload an image or use the camera, crop the product, and add a focus note when the scene has more than one possible item.",
    images: [{ src: "/assets/landing/takeitemphoto.avif", alt: "Taking a product photo for research" }],
  },
  {
    title: "Shop with context",
    text: "Compare source-backed matches with prices, alternatives, caveats, and the ranking basis instead of scrolling through raw links.",
    images: [
      { src: "/assets/landing/shopping1.avif", alt: "Shopping comparison screen" },
      { src: "/assets/landing/shopping2.avif", alt: "Shopping product research" },
    ],
  },
];

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
            <nav className="hidden items-center gap-6 text-sm font-bold text-[var(--nav-text)] md:flex" aria-label="Landing navigation">
              <a className="hover:opacity-72" href="#archive">About</a>
              <a className="hover:opacity-72" href="#process">How it works</a>
              <a className="hover:opacity-72" href="#workbench">Try it</a>
            </nav>
            <div className="flex items-center gap-2">
              <ThemeToggle />
              <a className="rounded-md bg-[var(--hero-text-primary)] px-4 py-2 text-sm font-semibold text-[var(--landing-bg)]" href="#workbench">
                Try it
              </a>
            </div>
          </header>

          <div className="max-w-2xl pb-10">
            <h1 className="text-5xl font-semibold leading-[0.96] tracking-normal text-[var(--hero-text-primary)] sm:text-6xl md:text-7xl">
              Product research at your fingertips.
            </h1>
            <p className="mt-6 max-w-xl text-base leading-7 text-[var(--hero-text-secondary)]">
              Start with a camera photo, uploaded image, or product description. ThriftLens screens the evidence, searches live sources, and explains the product-aware ranking behind every match.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <a className="inline-flex h-10 items-center gap-2 rounded-md border border-[var(--accent)] bg-[var(--accent)] px-4 text-[13px] font-semibold leading-5 text-[var(--accent-contrast)]" href="#workbench">
                Start researching
                <ArrowRight size={16} aria-hidden="true" />
              </a>
              <a className="inline-flex h-10 items-center rounded-md border border-[color-mix(in_srgb,var(--hero-text-primary)_24%,transparent)] px-4 text-[13px] font-semibold text-[var(--hero-text-primary)] hover:border-[color-mix(in_srgb,var(--hero-text-primary)_48%,transparent)]" href="#process">
                See how it works
              </a>
            </div>
          </div>
        </div>
      </div>

      <div className="mx-auto grid w-full max-w-7xl gap-16 px-4 py-14 md:px-6 md:py-16 lg:px-8">
        <HeroArchive />
        <ProcessNarrative />
      </div>
    </section>
  );
}

function HeroArchive() {
  const carouselSlides = useMemo(() => [archiveSlides[archiveSlides.length - 1], ...archiveSlides, archiveSlides[0]], []);
  const [slideIndex, setSlideIndex] = useState(1);
  const [isResetting, setIsResetting] = useState(false);
  const prefersReducedMotion = usePrefersReducedMotion();
  const activeIndex = carouselIndexFromSlideIndex(slideIndex);
  const lastCloneIndex = archiveSlides.length + 1;

  useEffect(() => {
    if (prefersReducedMotion) return;
    const interval = window.setInterval(() => {
      setIsResetting(false);
      setSlideIndex((index) => nextTrackIndex(index));
    }, CAROUSEL_INTERVAL_MS);
    return () => window.clearInterval(interval);
  }, [prefersReducedMotion]);

  useEffect(() => {
    if (slideIndex !== 0 && slideIndex !== lastCloneIndex) return;
    const timeout = window.setTimeout(
      () => {
        setIsResetting(true);
        setSlideIndex(slideIndex === 0 ? archiveSlides.length : 1);
      },
      prefersReducedMotion ? 0 : CAROUSEL_TRANSITION_MS + 80,
    );
    return () => window.clearTimeout(timeout);
  }, [lastCloneIndex, prefersReducedMotion, slideIndex]);

  useEffect(() => {
    if (!isResetting) return;
    const frame = window.requestAnimationFrame(() => setIsResetting(false));
    return () => window.cancelAnimationFrame(frame);
  }, [isResetting, slideIndex]);

  function handleSlideTransitionEnd() {
    if (slideIndex === 0) {
      setIsResetting(true);
      setSlideIndex(archiveSlides.length);
    } else if (slideIndex === archiveSlides.length + 1) {
      setIsResetting(true);
      setSlideIndex(1);
    }
  }

  return (
    <section id="archive" className="mx-auto w-full max-w-6xl">
      <div className="mb-8 flex flex-col justify-between gap-4 md:flex-row md:items-end">
        <div>
          <h2 className="text-3xl font-semibold tracking-normal text-[var(--text-primary)]">Start with the clues you already have.</h2>
          <p className="mt-3 max-w-2xl text-base leading-7 text-[var(--text-secondary)]">
            ThriftLens is built for the messy start: marketplace screenshots, camera photos, or a few words. It keeps the evidence visible while it extracts product facts, searches sources, and shows the ranking basis.
          </p>
        </div>
        <a className="inline-flex h-10 w-fit items-center gap-2 rounded-md border border-[var(--border)] px-4 text-[13px] font-semibold text-[var(--text-primary)] hover:border-[var(--border-strong)]" href="#workbench">
          Try your own product
          <ArrowRight size={16} aria-hidden="true" />
        </a>
      </div>

      <div aria-label="Evidence carousel" className="w-full">
        <div className="overflow-hidden rounded-lg border border-[var(--border)] bg-[color-mix(in_srgb,var(--surface)_68%,transparent)]">
          <div
            className="flex w-full will-change-transform"
            style={{
              transform: `translateX(-${slideIndex * 100}%)`,
              transition: prefersReducedMotion || isResetting ? "none" : `transform ${CAROUSEL_TRANSITION_MS}ms cubic-bezier(0.45, 0, 0.2, 1)`,
            }}
            onTransitionEnd={handleSlideTransitionEnd}
          >
            {carouselSlides.map((slide, index) => (
              <article
                aria-hidden={index !== slideIndex}
                className="grid min-w-full max-w-full shrink-0 overflow-hidden xl:grid-cols-[minmax(0,1.35fr)_minmax(300px,0.65fr)]"
                key={`${slide.title}-${index}`}
              >
                <div className="relative min-h-[240px] overflow-visible bg-black sm:min-h-[300px] md:min-h-[390px] xl:min-h-[520px] xl:overflow-hidden">
                  <SlideImages images={slide.images} title={slide.title} />
                </div>
                <div className="flex min-h-0 min-w-0 flex-col justify-center p-4 sm:p-5 md:p-7 xl:min-h-[520px]">
                  <div className="min-w-0">
                    <h3 className="max-w-sm break-words text-2xl font-semibold leading-tight tracking-normal text-[var(--text-primary)] md:text-3xl">{slide.title}</h3>
                    <p className="mt-3 max-w-md break-words text-sm leading-6 text-[var(--text-secondary)] md:mt-4 md:text-base md:leading-7">{slide.text}</p>
                  </div>
                </div>
              </article>
            ))}
          </div>
        </div>
        <div className="mt-3 flex justify-center">
          <div className="flex gap-2" aria-label="Carousel progress">
            {archiveSlides.map((slide, index) => (
              <span
                key={slide.title}
                aria-current={index === activeIndex ? "true" : undefined}
                className={`h-2.5 w-2.5 rounded-full border transition ${
                  index === activeIndex
                    ? "border-[var(--accent)] bg-[var(--accent)]"
                    : "border-[var(--border-strong)] bg-transparent"
                }`}
              />
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

function SlideImages({ images, title }: { images: Array<{ src: string; alt: string }>; title: string }) {
  if (images.length === 1) {
    return (
      <CarouselImage image={images[0]} sizes="(min-width: 1024px) 62vw, 100vw" />
    );
  }

  if (images.length === 2) {
    return (
      <div className="grid min-h-[240px] grid-cols-1 gap-2 p-2 sm:min-h-[300px] md:min-h-[390px] lg:grid-cols-2 xl:h-full xl:min-h-[520px]" data-testid="carousel-media-grid">
        {images.map((image) => (
          <div className="relative min-h-[160px] overflow-hidden rounded-md sm:min-h-[220px] md:min-h-[374px] xl:min-h-[504px]" key={image.src}>
            <CarouselImage image={image} sizes="(min-width: 1280px) 31vw, (min-width: 1024px) 50vw, 100vw" />
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className="relative grid min-h-[240px] grid-cols-1 gap-2 p-2 sm:min-h-[300px] md:min-h-[390px] lg:grid-cols-2 xl:h-full xl:min-h-[520px]" data-testid="carousel-media-grid">
      <div className="relative min-h-[180px] overflow-hidden rounded-md sm:min-h-[220px] lg:row-span-2 lg:min-h-[374px] xl:min-h-[504px]" key={images[0].src}>
        <CarouselImage image={images[0]} sizes="(min-width: 1280px) 40vw, (min-width: 1024px) 50vw, 100vw" />
      </div>
      {images.slice(1).map((image) => (
        <div className="relative min-h-[136px] overflow-hidden rounded-md sm:min-h-[160px] md:min-h-[183px] xl:min-h-[248px]" key={image.src}>
          <CarouselImage image={image} sizes="(min-width: 1280px) 22vw, (min-width: 1024px) 50vw, 100vw" />
        </div>
      ))}
      <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(180deg,rgb(0_0_0_/_0)_56%,rgb(0_0_0_/_0.32)_100%)]" aria-hidden="true" />
      <p className="sr-only">{title}</p>
    </div>
  );
}

function CarouselImage({ image, sizes }: { image: { src: string; alt: string }; sizes: string }) {
  return <Image alt={image.alt} className="h-full w-full object-cover" fill sizes={sizes} src={image.src} />;
}

function carouselIndexFromSlideIndex(slideIndex: number) {
  return carouselIndexFromTrackIndex(slideIndex);
}

function carouselIndexFromTrackIndex(trackIndex: number) {
  return (trackIndex - 1 + archiveSlides.length) % archiveSlides.length;
}

function nextTrackIndex(trackIndex: number) {
  return Math.min(trackIndex + 1, archiveSlides.length + 1);
}

function previousTrackIndex(trackIndex: number) {
  return Math.max(trackIndex - 1, 0);
}

function ProcessNarrative() {
  const steps = [
    {
      icon: <Camera size={17} aria-hidden="true" />,
      title: "Capture evidence",
      text: "Start from text, upload, or camera capture. If the scene is busy, a focus note tells ThriftLens which product to follow.",
    },
    {
      icon: <ShieldCheck size={17} aria-hidden="true" />,
      title: "Screen intent and clarity",
      text: "The input gate checks product-only intent, image safety, and ambiguity before any source search begins.",
    },
    {
      icon: <Sparkles size={17} aria-hidden="true" />,
      title: "Extract the reference",
      text: "The evidence becomes a structured product reference with type, color, material, features, assumptions, and confidence.",
    },
    {
      icon: <Search size={17} aria-hidden="true" />,
      title: "Profile how shoppers compare",
      text: "Discovery identifies the product family and the details shoppers care about, then plans bounded exact-match and alternatives searches.",
    },
    {
      icon: <Layers size={17} aria-hidden="true" />,
      title: "Search live sources",
      text: "Only product-shaped source results are normalized into candidates, so generic links do not become product cards.",
    },
    {
      icon: <SlidersHorizontal size={17} aria-hidden="true" />,
      title: "Rank and explain",
      text: "Hybrid ranking weighs source data, shopper priorities, extracted details, mismatch checks, caveats, and price context.",
    },
  ];

  return (
    <section id="process" className="mx-auto grid w-full max-w-6xl gap-8 xl:grid-cols-[0.85fr_1.15fr] xl:items-start">
      <div className="min-w-0 xl:sticky xl:top-8">
        <h2 className="break-words text-3xl font-semibold tracking-normal text-[var(--text-primary)]">How ThriftLens keeps results grounded.</h2>
        <p className="mt-4 max-w-xl break-words text-base leading-7 text-[var(--text-secondary)]">
          The workflow is built to avoid guessing: validate the request, understand the product, search bounded live sources, and make each recommendation explainable.
        </p>
      </div>
      <div className="grid min-w-0 gap-3 lg:grid-cols-2" data-testid="process-card-grid">
        {steps.map((step, index) => (
          <ProcessStep key={step.title} index={index + 1} {...step} />
        ))}
      </div>
    </section>
  );
}

function usePrefersReducedMotion() {
  const [prefersReducedMotion, setPrefersReducedMotion] = useState(false);

  useEffect(() => {
    const mediaQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
    setPrefersReducedMotion(mediaQuery.matches);

    function handleChange(event: MediaQueryListEvent) {
      setPrefersReducedMotion(event.matches);
    }

    mediaQuery.addEventListener("change", handleChange);
    return () => mediaQuery.removeEventListener("change", handleChange);
  }, []);

  return prefersReducedMotion;
}

function ProcessStep({ icon, index, title, text }: { icon: ReactNode; index: number; title: string; text: string }) {
  return (
    <div className="min-w-0 rounded-lg border border-[var(--border)] bg-[var(--surface)] p-4">
      <div className="mb-5 flex items-center justify-between gap-4">
        <div className="shrink-0 text-[var(--accent)]">{icon}</div>
        <span className="shrink-0 text-sm font-medium text-[var(--text-muted)]">{String(index).padStart(2, "0")}</span>
      </div>
      <h3 className="break-words text-base font-semibold text-[var(--text-primary)] [overflow-wrap:anywhere]">{title}</h3>
      <p className="mt-2 break-words text-sm leading-6 text-[var(--text-secondary)] [overflow-wrap:anywhere]">{text}</p>
    </div>
  );
}
