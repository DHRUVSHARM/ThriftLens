"use client";

import { Camera, FileImage, Loader2, Search, Upload, X } from "lucide-react";
import type { FormEvent } from "react";
import { useRef, useState } from "react";

import { CameraCaptureDialog } from "./CameraCaptureDialog";
import { Button, FieldLabel, Panel } from "./ui";

type UnifiedInputProps = {
  text: string;
  setText: (value: string) => void;
  imageFile: File | null;
  imagePreviewUrl: string | null;
  onImage: (file: File | null) => void;
  error: string | null;
  isSubmitting: boolean;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
};

export function UnifiedInput(props: UnifiedInputProps) {
  const hasImage = Boolean(props.imageFile);
  const placeholder = hasImage
    ? "Focus this image: the red shirt, the lamp on the left, navy wool blazer..."
    : "Describe only the product: red leather tote bag, navy wool blazer, walnut desk lamp...";
  const guidance = hasImage
    ? "Use text to focus one visible item or add details from the image."
    : "Describe the product itself. Requests to find, rank, list, or browse sources will ask for refinement.";

  return (
    <Panel elevated className="p-4 md:p-5">
      <form className="grid gap-4 lg:grid-cols-[260px_minmax(0,1fr)_180px]" onSubmit={props.onSubmit}>
        <ImageSlot imageFile={props.imageFile} imagePreviewUrl={props.imagePreviewUrl} onImage={props.onImage} />

        <div className="grid gap-3">
          <label className="grid gap-1.5">
            <FieldLabel>{hasImage ? "Focus note" : "Product evidence"}</FieldLabel>
            <textarea
              className="min-h-44 resize-y rounded-md border border-[var(--border)] bg-[var(--surface-raised)] px-3 py-3 text-sm leading-6 text-[var(--text-primary)] outline-none transition placeholder:text-[var(--text-muted)] focus:border-[var(--accent)] focus:ring-2 focus:ring-[color-mix(in_srgb,var(--accent)_14%,transparent)] md:min-h-48 lg:min-h-[206px]"
              maxLength={2000}
              placeholder={placeholder}
              suppressHydrationWarning
              value={props.text}
              onChange={(event) => props.setText(event.target.value)}
            />
          </label>
          {props.error ? <p className="rounded-md border border-[color-mix(in_srgb,var(--danger)_35%,transparent)] bg-[color-mix(in_srgb,var(--danger)_10%,var(--surface))] px-3 py-2 text-sm text-[var(--danger)]">{props.error}</p> : null}
        </div>

        <div className="flex flex-col justify-between gap-3">
          <p className="text-sm leading-6 text-[var(--text-secondary)] lg:max-w-44">
            {guidance}
          </p>
          <Button className="w-full" disabled={props.isSubmitting} padding="compact" type="submit" variant="primary">
            {props.isSubmitting ? <Loader2 className="animate-spin" size={18} aria-hidden="true" /> : <Search size={18} aria-hidden="true" />}
            Start research
          </Button>
        </div>
      </form>
    </Panel>
  );
}

function ImageSlot({
  imageFile,
  imagePreviewUrl,
  onImage,
}: {
  imageFile: File | null;
  imagePreviewUrl: string | null;
  onImage: (file: File | null) => void;
}) {
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [isCameraOpen, setIsCameraOpen] = useState(false);

  return (
    <div className="grid gap-2">
      <FieldLabel>Image optional</FieldLabel>
      <label
        className="flex min-h-48 cursor-pointer flex-col items-center justify-center overflow-hidden rounded-lg border border-dashed border-[var(--border-strong)] bg-[var(--surface-raised)] p-3 text-center transition hover:border-[var(--accent)]"
        htmlFor="product-image"
      >
        {imagePreviewUrl ? (
          <img alt="Selected product preview" className="max-h-44 w-full rounded-md object-contain" src={imagePreviewUrl} />
        ) : (
          <>
            <FileImage size={34} className="text-[var(--text-muted)]" aria-hidden="true" />
            <span className="mt-3 text-sm font-semibold text-[var(--text-primary)]">Click to upload image</span>
            <span className="mt-1 text-xs text-[var(--text-muted)]">JPEG, PNG, WebP up to 8MB</span>
          </>
        )}
      </label>
      <input
        ref={inputRef}
        id="product-image"
        className="sr-only"
        accept="image/jpeg,image/png,image/webp"
        capture="environment"
        suppressHydrationWarning
        type="file"
        onChange={(event) => onImage(event.target.files?.[0] || null)}
      />
      <div className="grid gap-2">
        <Button className="w-full" type="button" variant="secondary" onClick={() => inputRef.current?.click()}>
          <Upload size={16} aria-hidden="true" />
          Upload image
        </Button>
        <Button className="w-full" type="button" variant="secondary" onClick={() => setIsCameraOpen(true)}>
          <Camera size={16} aria-hidden="true" />
          Use camera
        </Button>
      </div>
      {imageFile ? (
        <div className="flex min-w-0 items-center justify-between gap-2 rounded-lg bg-[var(--surface-subtle)] px-3 py-2 text-sm text-[var(--text-secondary)]">
          <span className="truncate">{imageFile.name}</span>
          <button
            className="rounded-md p-1 hover:bg-[var(--surface)]"
            onClick={() => onImage(null)}
            suppressHydrationWarning
            type="button"
            aria-label="Remove image"
          >
            <X size={16} aria-hidden="true" />
          </button>
        </div>
      ) : null}
      <CameraCaptureDialog open={isCameraOpen} onClose={() => setIsCameraOpen(false)} onCapture={onImage} />
    </div>
  );
}
