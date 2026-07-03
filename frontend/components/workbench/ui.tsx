import type { ButtonHTMLAttributes, HTMLAttributes, ReactNode } from "react";

type ButtonVariant = "primary" | "secondary" | "ghost" | "danger";
type ButtonPadding = "normal" | "compact";

const buttonVariants: Record<ButtonVariant, string> = {
  primary:
    "border-[var(--accent)] bg-[var(--accent)] text-[var(--accent-contrast)] hover:border-[var(--accent-strong)] hover:bg-[var(--accent-strong)]",
  secondary:
    "border-[var(--border)] bg-[var(--surface-raised)] text-[var(--text-primary)] hover:border-[var(--border-strong)] hover:bg-[var(--surface-subtle)]",
  ghost: "border-transparent bg-transparent text-[var(--text-secondary)] hover:bg-[var(--surface-subtle)] hover:text-[var(--text-primary)]",
  danger:
    "border-transparent bg-[color-mix(in_srgb,var(--danger)_14%,var(--surface))] text-[var(--danger)] hover:bg-[color-mix(in_srgb,var(--danger)_20%,var(--surface))]",
};

const buttonPadding: Record<ButtonPadding, string> = {
  normal: "px-4",
  compact: "px-3",
};

export function Button({
  className = "",
  padding = "normal",
  variant = "secondary",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { padding?: ButtonPadding; variant?: ButtonVariant }) {
  return (
    <button
      className={`inline-flex h-10 items-center justify-center gap-2 rounded-md border text-[13px] font-semibold leading-5 transition disabled:opacity-50 ${buttonPadding[padding]} ${buttonVariants[variant]} ${className}`}
      suppressHydrationWarning
      {...props}
    />
  );
}

export function IconButton({
  className = "",
  label,
  children,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { label: string; children: ReactNode }) {
  return (
    <button
      aria-label={label}
      className={`inline-flex h-10 w-10 items-center justify-center rounded-md border border-[var(--border)] bg-[var(--surface)] text-[var(--text-secondary)] transition hover:border-[var(--border-strong)] hover:text-[var(--text-primary)] ${className}`}
      suppressHydrationWarning
      type="button"
      {...props}
    >
      {children}
    </button>
  );
}

export function Badge({
  children,
  tone = "neutral",
  className = "",
}: {
  children: ReactNode;
  tone?: "neutral" | "accent" | "success" | "warning" | "danger";
  className?: string;
}) {
  const tones = {
    neutral: "border-[var(--border)] bg-[var(--surface-raised)] text-[var(--text-secondary)]",
    accent: "border-[color-mix(in_srgb,var(--accent)_35%,transparent)] bg-[color-mix(in_srgb,var(--accent)_12%,var(--surface))] text-[var(--accent-strong)]",
    success: "border-[color-mix(in_srgb,var(--success)_35%,transparent)] bg-[color-mix(in_srgb,var(--success)_12%,var(--surface))] text-[var(--success)]",
    warning: "border-[color-mix(in_srgb,var(--warning)_35%,transparent)] bg-[color-mix(in_srgb,var(--warning)_13%,var(--surface))] text-[var(--warning)]",
    danger: "border-[color-mix(in_srgb,var(--danger)_35%,transparent)] bg-[color-mix(in_srgb,var(--danger)_12%,var(--surface))] text-[var(--danger)]",
  };
  return (
    <span className={`inline-flex min-h-7 items-center rounded-md border px-2.5 py-0.5 text-[13px] font-medium leading-5 ${tones[tone]} ${className}`}>
      {children}
    </span>
  );
}

export function Panel({
  children,
  className = "",
  elevated = false,
  ...props
}: HTMLAttributes<HTMLElement> & { elevated?: boolean }) {
  return (
    <section
      className={`rounded-lg border border-[var(--border)] ${elevated ? "bg-[var(--surface)] shadow-[var(--shadow-soft)]" : "bg-[var(--surface)]"} ${className}`}
      {...props}
    >
      {children}
    </section>
  );
}

export function FieldLabel({ children }: { children: ReactNode }) {
  return <span className="text-sm font-medium text-[var(--text-secondary)]">{children}</span>;
}
