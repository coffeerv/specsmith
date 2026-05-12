import clsx from "clsx";
import type {
  ButtonHTMLAttributes,
  HTMLAttributes,
  ReactNode,
  SelectHTMLAttributes,
  TextareaHTMLAttributes,
} from "react";
import "./primitives.css";

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "default" | "primary";
};

export function Button({ variant = "default", className, ...rest }: ButtonProps) {
  return (
    <button
      type="button"
      className={clsx("btn", variant === "primary" && "btn--primary", className)}
      {...rest}
    />
  );
}

type FieldProps = {
  label?: string;
  hint?: ReactNode;
  htmlFor?: string;
  children: ReactNode;
};

export function Field({ label, hint, htmlFor, children }: FieldProps) {
  return (
    <div className="field">
      {label ? (
        <label className="field__label" htmlFor={htmlFor}>
          {label}
        </label>
      ) : null}
      {children}
      {hint ? <div className="field__hint">{hint}</div> : null}
    </div>
  );
}

export function Textarea({
  className,
  ...rest
}: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return <textarea className={clsx("field__textarea", className)} {...rest} />;
}

export function Select({
  className,
  ...rest
}: SelectHTMLAttributes<HTMLSelectElement>) {
  return <select className={clsx("field__select", className)} {...rest} />;
}

type PillProps = {
  children: ReactNode;
  mono?: boolean;
  tone?: "default" | "rule" | "critique";
  onRemove?: () => void;
  removeLabel?: string;
};

export function Pill({ children, mono, tone = "default", onRemove, removeLabel }: PillProps) {
  return (
    <span
      className={clsx(
        "pill",
        mono && "pill--mono",
        tone === "rule" && "pill--rule",
        tone === "critique" && "pill--critique",
      )}
    >
      {children}
      {onRemove ? (
        <button
          type="button"
          className="pill__remove"
          onClick={onRemove}
          aria-label={removeLabel ?? "Remove"}
        >
          ×
        </button>
      ) : null}
    </span>
  );
}

type SectionProps = HTMLAttributes<HTMLElement> & {
  title?: ReactNode;
  actions?: ReactNode;
  children: ReactNode;
};

export function Section({ title, actions, children, className, ...rest }: SectionProps) {
  return (
    <section className={clsx("section", className)} {...rest}>
      {title ? (
        <header className="section__header">
          <span>{title}</span>
          {actions ? <span>{actions}</span> : null}
        </header>
      ) : null}
      <div className="section__body">{children}</div>
    </section>
  );
}

export function Skeleton({
  width,
  height,
  className,
  ...rest
}: HTMLAttributes<HTMLDivElement> & { width?: number | string; height?: number | string }) {
  return (
    <div
      className={clsx("skeleton", className)}
      style={{ width, height, ...(rest.style ?? {}) }}
      aria-hidden
    />
  );
}

type BannerProps = {
  title: string;
  meta?: ReactNode;
  children: ReactNode;
};

export function Banner({ title, meta, children }: BannerProps) {
  return (
    <div className="banner" role="alert">
      <div className="banner__title">{title}</div>
      <div>{children}</div>
      {meta ? <div className="banner__meta">{meta}</div> : null}
    </div>
  );
}

type SegmentedOption<T extends string> = { value: T; label: string };

export function Segmented<T extends string>({
  value,
  onChange,
  options,
  ariaLabel,
}: {
  value: T;
  onChange: (v: T) => void;
  options: SegmentedOption<T>[];
  ariaLabel: string;
}) {
  return (
    <div className="segmented" role="group" aria-label={ariaLabel}>
      {options.map((opt) => (
        <button
          key={opt.value}
          type="button"
          className={clsx(
            "segmented__btn",
            value === opt.value && "segmented__btn--active",
          )}
          aria-pressed={value === opt.value}
          onClick={() => onChange(opt.value)}
        >
          {opt.label}
        </button>
      ))}
    </div>
  );
}
