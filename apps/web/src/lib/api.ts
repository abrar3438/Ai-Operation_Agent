import {
  AgentRunDetails,
  AgentRunSummary,
  ApprovalItem,
  EvaluationReport,
  HealthStatusResponse,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001/api/v1";
const HEALTH_BASE = process.env.NEXT_PUBLIC_API_HEALTH_URL || "http://localhost:8001/health";

function getHeaders(operatorRole = "operator"): HeadersInit {
  return {
    "Content-Type": "application/json",
    "X-Operator-Role": operatorRole,
  };
}

export async function fetchHealth(): Promise<{ live: HealthStatusResponse | null; ready: HealthStatusResponse | null }> {
  try {
    const [liveRes, readyRes] = await Promise.all([
      fetch(`${HEALTH_BASE}/live`, { cache: "no-store" }),
      fetch(`${HEALTH_BASE}/ready`, { cache: "no-store" }),
    ]);
    const live = liveRes.ok ? await liveRes.json() : null;
    const ready = readyRes.ok ? await readyRes.json() : null;
    return { live, ready };
  } catch {
    return { live: null, ready: null };
  }
}

export async function submitAgentRun(userRequest: string, threadId?: string): Promise<{ run_id: string; status: string; final_answer?: string }> {
  const res = await fetch(`${API_BASE}/runs`, {
    method: "POST",
    headers: getHeaders(),
    body: JSON.stringify({ user_request: userRequest, thread_id: threadId }),
  });
  if (!res.ok) {
    const err = (await res.json().catch(() => ({ detail: "Unknown error" }))) as { detail?: string };
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

export async function listRuns(statusFilter?: string, modelLabel?: string): Promise<AgentRunSummary[]> {
  const params = new URLSearchParams();
  if (statusFilter) params.append("status", statusFilter);
  if (modelLabel) params.append("model_label", modelLabel);

  const res = await fetch(`${API_BASE}/runs?${params.toString()}`, {
    headers: getHeaders(),
    cache: "no-store",
  });
  if (!res.ok) throw new Error("Failed to fetch run history");
  return res.json();
}

export async function getRunDetails(runId: string): Promise<AgentRunDetails> {
  const res = await fetch(`${API_BASE}/runs/${runId}`, {
    headers: getHeaders(),
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`Run not found: ${runId}`);
  return res.json();
}

export async function listApprovals(statusFilter?: string): Promise<ApprovalItem[]> {
  const params = new URLSearchParams();
  if (statusFilter) params.append("status_filter", statusFilter);

  const res = await fetch(`${API_BASE}/approvals?${params.toString()}`, {
    headers: getHeaders(),
    cache: "no-store",
  });
  if (!res.ok) throw new Error("Failed to fetch approvals inbox");
  return res.json();
}

export async function decideApproval(approvalId: string, decision: "approve" | "reject", reviewer: string): Promise<unknown> {
  const res = await fetch(`${API_BASE}/approvals/${approvalId}/${decision}`, {
    method: "POST",
    headers: getHeaders(),
    body: JSON.stringify({ reviewer }),
  });
  if (!res.ok) {
    const err = (await res.json().catch(() => ({ detail: "Action failed" }))) as { detail?: string };
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

export async function triggerEvaluation(): Promise<EvaluationReport> {
  const res = await fetch(`${API_BASE}/evals/run`, {
    method: "POST",
    headers: getHeaders(),
  });
  if (!res.ok) throw new Error("Failed to execute evaluation suite");
  return res.json();
}
