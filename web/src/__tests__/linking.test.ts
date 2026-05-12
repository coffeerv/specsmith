import { describe, expect, it } from "vitest";
import { buildLinkMap, findingKey } from "../state/linking";
import type { SpecifyResponse } from "../types/specsmith";

function response(overrides: Partial<SpecifyResponse> = {}): SpecifyResponse {
  return {
    target: "PRD",
    spec: { findings: [] },
    trace: { run_id: "r", entries: [] },
    ...overrides,
  };
}

describe("buildLinkMap", () => {
  it("links a CritiqueFinding to the entry whose prompts include matching prompt_id", () => {
    const res = response({
      spec: {
        findings: [
          {
            kind: "critique",
            critique_prompt_id: "critique.spec.v0",
            model: "m",
            severity: "warn",
            target_field: null,
            message: "x",
          },
        ],
      },
      trace: {
        run_id: "r",
        entries: [
          {
            entry_id: "e1",
            run_id: "r",
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
          },
          {
            entry_id: "e2",
            run_id: "r",
            node: "critique",
            started_at: "",
            ended_at: "",
            duration_ms: 0,
            input_hash: "",
            output_keys: [],
            model: "m",
            token_usage: null,
            prompts: [{ prompt_id: "critique.spec.v0", prompt_text: "p" }],
            status: "success",
          },
        ],
      },
    });
    const map = buildLinkMap(res);
    const key = findingKey(res.spec.findings[0], 0);
    expect(map.get(key)).toBe("e2");
  });

  it("links a RuleFinding to the entry whose node matches produced_by_node", () => {
    const res = response({
      spec: {
        findings: [
          {
            kind: "rule",
            rule_id: "nfr.presence",
            severity: "warn",
            target_field: null,
            message: "x",
            produced_by_node: "revise",
          },
        ],
      },
      trace: {
        run_id: "r",
        entries: [
          {
            entry_id: "e1",
            run_id: "r",
            node: "critique",
            started_at: "",
            ended_at: "",
            duration_ms: 0,
            input_hash: "",
            output_keys: [],
            model: null,
            token_usage: null,
            prompts: [],
            status: "success",
          },
          {
            entry_id: "e2",
            run_id: "r",
            node: "revise",
            started_at: "",
            ended_at: "",
            duration_ms: 0,
            input_hash: "",
            output_keys: [],
            model: null,
            token_usage: null,
            prompts: [],
            status: "success",
          },
        ],
      },
    });
    const map = buildLinkMap(res);
    const key = findingKey(res.spec.findings[0], 0);
    expect(map.get(key)).toBe("e2");
  });

  it("omits findings without a resolvable target rather than throwing", () => {
    const res = response({
      spec: {
        findings: [
          {
            kind: "rule",
            rule_id: "nfr.presence",
            severity: "warn",
            target_field: null,
            message: "x",
          },
        ],
      },
    });
    const map = buildLinkMap(res);
    const key = findingKey(res.spec.findings[0], 0);
    expect(map.get(key)).toBeUndefined();
  });
});
