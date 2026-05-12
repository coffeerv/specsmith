import type { SpecifyResponse } from "../types/specsmith";

const BASE_URL =
  import.meta.env.VITE_SPECSMITH_API_BASE_URL ?? "http://localhost:8000";

export type SpecifyInput = {
  specscript: string;
  files: File[];
  target?: string;
};

export class SpecifyError extends Error {
  status: number;
  detail: unknown;
  runId: string | null;
  partialTrace: SpecifyResponse["trace"] | null;

  constructor(
    status: number,
    detail: unknown,
    runId: string | null,
    partialTrace: SpecifyResponse["trace"] | null,
    message: string,
  ) {
    super(message);
    this.name = "SpecifyError";
    this.status = status;
    this.detail = detail;
    this.runId = runId;
    this.partialTrace = partialTrace;
  }
}

export async function submitSpecify(input: SpecifyInput): Promise<SpecifyResponse> {
  const form = new FormData();
  if (input.specscript) form.append("specscript", input.specscript);
  if (input.target) form.append("target", input.target);
  for (const file of input.files) form.append("files", file);

  let response: Response;
  try {
    response = await fetch(`${BASE_URL}/specify`, {
      method: "POST",
      body: form,
    });
  } catch (err) {
    throw new SpecifyError(
      0,
      null,
      null,
      null,
      err instanceof Error ? err.message : "Network error",
    );
  }

  const contentType = response.headers.get("content-type") ?? "";
  const isJson = contentType.includes("application/json");
  const body = isJson ? await response.json().catch(() => null) : await response.text();

  if (!response.ok) {
    const detail =
      body && typeof body === "object" && "detail" in body ? body.detail : body;
    const runId =
      body && typeof body === "object" && "trace" in body && body.trace?.run_id
        ? String(body.trace.run_id)
        : null;
    const partialTrace =
      body && typeof body === "object" && "trace" in body && body.trace
        ? body.trace
        : null;
    throw new SpecifyError(
      response.status,
      detail,
      runId,
      partialTrace,
      `HTTP ${response.status}`,
    );
  }

  return body as SpecifyResponse;
}
