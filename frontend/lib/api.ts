import type { CreateJobInput, ResearchJob } from "./types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  retryable: boolean;

  constructor(message: string, options: { status: number; retryable?: boolean }) {
    super(message);
    this.name = "ApiError";
    this.status = options.status;
    this.retryable = options.retryable ?? false;
  }
}

function errorMessageFromDetail(detail: unknown): string {
  if (typeof detail === "string") {
    return detail;
  }
  if (detail && typeof detail === "object" && "message" in detail) {
    const message = (detail as { message?: unknown }).message;
    if (typeof message === "string") {
      return message;
    }
  }
  if (Array.isArray(detail) && detail.length > 0) {
    const first = detail[0] as { msg?: unknown };
    if (typeof first.msg === "string") {
      return first.msg;
    }
  }
  return "Research service returned an unexpected response.";
}

async function parseJsonResponse<T>(response: Response): Promise<T> {
  const payload = (await response.json().catch(() => null)) as unknown;
  if (!response.ok) {
    const detail = payload && typeof payload === "object" && "detail" in payload ? (payload as { detail: unknown }).detail : payload;
    throw new ApiError(errorMessageFromDetail(detail), { status: response.status, retryable: response.status >= 500 });
  }
  return payload as T;
}

export async function createResearchJob(input: CreateJobInput): Promise<ResearchJob> {
  if (input.inputType === "image") {
    const formData = new FormData();
    formData.append("inputType", "image");
    formData.append("image", input.image);
    formData.append("researchPreferences", JSON.stringify(input.researchPreferences));

    const response = await fetch(`${API_BASE_URL}/api/research-jobs`, {
      method: "POST",
      body: formData,
    });
    return parseJsonResponse<ResearchJob>(response);
  }

  const response = await fetch(`${API_BASE_URL}/api/research-jobs`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  return parseJsonResponse<ResearchJob>(response);
}

export async function getResearchJob(jobId: string): Promise<ResearchJob> {
  const response = await fetch(`${API_BASE_URL}/api/research-jobs/${jobId}`, {
    cache: "no-store",
  });
  return parseJsonResponse<ResearchJob>(response);
}

export async function retryResearchJob(jobId: string): Promise<ResearchJob> {
  const response = await fetch(`${API_BASE_URL}/api/research-jobs/${jobId}/retry`, {
    method: "POST",
  });
  return parseJsonResponse<ResearchJob>(response);
}
