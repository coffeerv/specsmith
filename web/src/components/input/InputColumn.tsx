import { useState, type ChangeEvent } from "react";
import { Button, Field, Pill, Section, Select, Textarea } from "../primitives";
import { TEMPLATES, type Template } from "../../templates";
import "./input-column.css";

const TARGETS: { value: string; label: string }[] = [
  { value: "PRD", label: "PRD" },
  { value: "TechSpec", label: "Tech Spec" },
  { value: "GitHubSpec", label: "GitHub Spec" },
];

type Props = {
  submitting: boolean;
  onSubmit: (payload: {
    specscript: string;
    files: File[];
    target: string;
  }) => void;
};

export function InputColumn({ submitting, onSubmit }: Props) {
  const [templateId, setTemplateId] = useState<string>("text-only-prd");
  const [specscript, setSpecscript] = useState<string>(
    TEMPLATES.find((t) => t.id === "text-only-prd")!.specscript,
  );
  const [files, setFiles] = useState<File[]>([]);
  const [target, setTarget] = useState<string>("PRD");

  const activeTemplate: Template | undefined = TEMPLATES.find(
    (t) => t.id === templateId,
  );

  function pickTemplate(e: ChangeEvent<HTMLSelectElement>) {
    const next = TEMPLATES.find((t) => t.id === e.target.value);
    if (!next) return;
    setTemplateId(next.id);
    setSpecscript(next.specscript);
  }

  function addFiles(e: ChangeEvent<HTMLInputElement>) {
    const list = e.target.files;
    if (!list) return;
    setFiles((prev) => [...prev, ...Array.from(list)]);
    e.target.value = "";
  }

  function removeFile(idx: number) {
    setFiles((prev) => prev.filter((_, i) => i !== idx));
  }

  const canSubmit =
    !submitting && (specscript.trim().length > 0 || files.length > 0);

  return (
    <Section
      className="input-column"
      title="Input"
      actions={
        <Select
          aria-label="Template"
          value={templateId}
          onChange={pickTemplate}
        >
          {TEMPLATES.map((t) => (
            <option key={t.id} value={t.id}>
              {t.label}
            </option>
          ))}
        </Select>
      }
    >
      <Field label="SpecScript" htmlFor="specscript">
        <Textarea
          id="specscript"
          value={specscript}
          onChange={(e) => setSpecscript(e.target.value)}
          spellCheck={false}
        />
      </Field>

      <Field
        label={`Screenshots (${files.length})`}
        htmlFor="files"
        hint={
          activeTemplate && activeTemplate.expectsFiles > 0
            ? `This template expects ${activeTemplate.expectsFiles} screenshot${activeTemplate.expectsFiles === 1 ? "" : "s"} — attach below.`
            : undefined
        }
      >
        <input
          id="files"
          type="file"
          accept="image/*"
          multiple
          onChange={addFiles}
          className="input-column__file"
        />
        {files.length > 0 ? (
          <div className="input-column__pills">
            {files.map((f, i) => (
              <Pill
                key={`${f.name}-${i}`}
                onRemove={() => removeFile(i)}
                removeLabel={`Remove ${f.name}`}
              >
                {f.name}
              </Pill>
            ))}
          </div>
        ) : null}
      </Field>

      <Field label="Target" htmlFor="target">
        <Select
          id="target"
          value={target}
          onChange={(e) => setTarget(e.target.value)}
        >
          {TARGETS.map((t) => (
            <option key={t.value} value={t.value}>
              {t.label}
            </option>
          ))}
        </Select>
      </Field>

      <Button
        variant="primary"
        disabled={!canSubmit}
        onClick={() => onSubmit({ specscript, files, target })}
      >
        {submitting ? "Generating…" : "Generate"}
      </Button>
    </Section>
  );
}
