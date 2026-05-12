export type Template = {
  id: string;
  label: string;
  specscript: string;
  expectsFiles: number;
};

export const TEMPLATES: Template[] = [
  {
    id: "blank",
    label: "Blank",
    specscript: "",
    expectsFiles: 0,
  },
  {
    id: "text-only-prd",
    label: "Text-only PRD",
    specscript: `#spec
Title: One-click export
Type: PRD
goals:
- reduce support tickets
accept:
- GWT: As an Ops Analyst, when I click Export, I receive a CSV.
`,
    expectsFiles: 0,
  },
  {
    id: "single-screenshot-prd",
    label: "Single screenshot PRD",
    specscript: `#spec
Title: Screenshot-driven spec
Type: PRD
accept:
- GWT: As a user, when I click Save, I see a toast.
`,
    expectsFiles: 1,
  },
  {
    id: "multi-screenshot-prd",
    label: "Multi-screenshot PRD",
    specscript: `#spec
Title: Multi-screenshot PRD
Type: PRD
metrics:
- p95 save < 2s
accept:
- GWT: As an editor, when I press Publish, the article becomes live.
`,
    expectsFiles: 2,
  },
];
