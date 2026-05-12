import { describe, expect, it } from "vitest";
import {
  formatDuration,
  serializeSpec,
  shouldShowTokenColumn,
} from "../utils/format";
import type { TraceEntry } from "../types/specsmith";

describe("formatDuration", () => {
  it("formats sub-second values in ms", () => {
    expect(formatDuration(240)).toBe("240ms");
    expect(formatDuration(0)).toBe("0ms");
  });
  it("formats >=1s values in s with one decimal", () => {
    expect(formatDuration(12_148)).toBe("12.1s");
    expect(formatDuration(1_000)).toBe("1.0s");
  });
  it("clamps invalid input", () => {
    expect(formatDuration(-5)).toBe("0ms");
    expect(formatDuration(Number.NaN)).toBe("0ms");
  });
});

describe("shouldShowTokenColumn", () => {
  const base: TraceEntry = {
    entry_id: "x",
    run_id: "x",
    node: "ingest",
    started_at: "",
    ended_at: "",
    duration_ms: 0,
    input_hash: "",
    output_keys: [],
    model: null,
    token_usage: null,
    prompts: [],
    status: "success",
  };

  it("returns false for empty list", () => {
    expect(shouldShowTokenColumn([])).toBe(false);
  });
  it("returns false when all entries have null token_usage", () => {
    expect(shouldShowTokenColumn([base, base])).toBe(false);
  });
  it("returns true when at least one entry has token_usage", () => {
    const withTokens: TraceEntry = {
      ...base,
      token_usage: { input_tokens: 10, output_tokens: 5, total_tokens: 15 },
    };
    expect(shouldShowTokenColumn([base, withTokens])).toBe(true);
  });
});

describe("serializeSpec", () => {
  it("produces stable two-space-indented JSON", () => {
    const spec = { title: "X", findings: [] };
    const out = serializeSpec(spec);
    expect(out).toBe('{\n  "title": "X",\n  "findings": []\n}');
  });
});
