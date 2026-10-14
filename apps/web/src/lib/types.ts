export type RunStatus =
  | "queued"
  | "running"
  | "waiting_approval"
  | "succeeded"
  | "failed"
  | "cancelled";

export type ApprovalStatus = "pending" | "approved" | "rejected" | "expired";

export interface AgentRunSummary {
  run_id: string;
  thread_id: string;
  request_preview: string;
  status: RunStatus;
  model_label: string;
  provider_label: string;
  terminal_reason?: string | null;
  started_at?: string | null;
  finished_at?: string | null;
  created_at: string;
}

export interface ToolEventItem {
  sequence: number;
  stage: string;
  tool_name?: string | null;
  status: "ok" | "error" | "skipped" | "waiting_approval";
  duration_ms: number;
  retry_count: number;
  error_category?: string | null;
  detail_summary: string;
  created_at: string;
}

export interface ApprovalRecord {
  approval_id: string;
  action_type: string;
  status: ApprovalStatus;
  reviewer?: string | null;
  decided_at?: string | null;
}

export interface AgentRunDetails extends AgentRunSummary {
  final_answer?: string | null;
  tool_call_count: number;
  duration_ms: number;
  timeline: ToolEventItem[];
  approvals: ApprovalRecord[];
}

export interface ApprovalItem {
  id: string;
  action_type: string;
  action_reference: string;
  arguments: Record<string, unknown>;
  status: ApprovalStatus;
  reviewer?: string | null;
  created_at: string;
  decided_at?: string | null;
  expires_at?: string | null;
}

export interface HealthStatusResponse {
  status: string;
  dependencies: Array<{
    name: string;
    status: string;
    required: boolean;
  }>;
}

export interface EvaluationReport {
  metrics: {
    dataset_version: string;
    timestamp: string;
    model_label: string;
    total_cases: number;
    passed_cases: number;
    task_completion_rate: number;
    error_rate: number;
    safety_policy_violations: number;
    latency_median_ms: number;
    latency_p95_ms: number;
  };
  results: Array<{
    scenario_id: string;
    status: string;
    used_tools: string[];
    answer?: string | null;
    error?: string | null;
    success: boolean;
    latency_ms: number;
  }>;
  known_limitations: string[];
}
