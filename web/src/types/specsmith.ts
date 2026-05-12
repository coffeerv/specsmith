export type NodeName =
  | "ingest"
  | "classify"
  | "extract"
  | "critique"
  | "revise"
  | "render";

export type Severity = "info" | "warn" | "error";

export type PromptTrace = {
  prompt_id: string;
  prompt_text: string;
};

export type TraceEntry = {
  entry_id: string;
  run_id: string;
  node: NodeName;
  started_at: string;
  ended_at: string;
  duration_ms: number;
  input_hash: string;
  output_keys: string[];
  model: string | null;
  token_usage: Record<string, number> | null;
  prompts: PromptTrace[];
  status: "success";
};

export type RuleFinding = {
  kind: "rule";
  rule_id: string;
  severity: Severity;
  target_field: string | null;
  message: string;
  produced_by_node?: NodeName | null;
};

export type CritiqueFinding = {
  kind: "critique";
  critique_prompt_id: string;
  model: string;
  severity: Severity;
  target_field: string | null;
  message: string;
};

export type Finding = RuleFinding | CritiqueFinding;

export type Spec = {
  title?: string;
  type?: string;
  findings: Finding[];
  [key: string]: unknown;
};

export type SpecifyResponse = {
  target: string;
  spec: Spec;
  trace: {
    run_id: string;
    entries: TraceEntry[];
  };
};

export const NODE_ORDER: NodeName[] = [
  "ingest",
  "classify",
  "extract",
  "critique",
  "revise",
  "render",
];
