export type AppItem = {
  app_id: string;
  app_name: string;
  app_type: string;
  description?: string | null;
  owner: string;
  business_scene?: string | null;
  stable_version_id?: string | null;
  running_experiment_id?: string | null;
  status: string;
  created_at: string;
  updated_at?: string;
};

export type VersionItem = {
  version_id: string;
  app_id: string;
  version_name: string;
  base_version_id?: string | null;
  prompt_template: string;
  model_name: string;
  endpoint_url: string;
  temperature: number;
  top_p: number;
  max_tokens: number;
  rag_enabled: boolean;
  rag_config: Record<string, unknown>;
  output_schema: Record<string, unknown>;
  status: string;
  created_by: string;
  created_at: string;
  updated_at: string;
};

export type ExperimentItem = {
  experiment_id: string;
  app_id: string;
  experiment_name: string;
  control_version_id: string;
  treatment_version_id: string;
  traffic_control: number;
  traffic_treatment: number;
  routing_rules: {
    hash_key: string;
    whitelist_user_ids: string[];
    channels: string[];
  };
  guardrails: {
    max_error_rate: number;
    max_latency_ratio: number;
    min_sample_size: number;
  };
  status: string;
  auto_rollback: boolean;
  start_time?: string | null;
  end_time?: string | null;
  started_at?: string | null;
  stopped_at?: string | null;
  stop_reason?: string | null;
  created_by: string;
  created_at: string;
};

export type RequestTraceItem = {
  request_id: string;
  trace_id: string;
  app_id: string;
  user_id: string;
  model_name: string;
  experiment_id?: string | null;
  version_id: string;
  routing_reason: string;
  latency_ms: number;
  cost: number;
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
  status: string;
  created_at: string;
  answer?: string;
  query?: string;
  retrieval_docs?: string[];
  error_message?: string | null;
};

export type ApiConsoleEvent = {
  event_id: string;
  service: "admin" | "gateway" | "rag" | "unknown";
  method: string;
  path: string;
  status: "pending" | "success" | "error";
  started_at: string;
  duration_ms?: number;
  response_code?: number;
  message?: string;
  request_body?: string;
  response_preview?: string;
};

export type MetricsOverview = {
  experiment_id: string;
  control: MetricsCard;
  treatment: MetricsCard;
  generated_at: string;
};

export type DecisionSnapshot = {
  experiment_id: string;
  decision_type: string;
  risk_level: string;
  triggered_rules: Array<{
    rule_name: string;
    reason: string;
  }>;
  recommended_next_split: string | null;
  requires_manual_approval: boolean;
  evaluated_at: string;
};

export type MetricsCard = {
  version_id: string;
  request_count: number;
  success_count: number;
  error_count: number;
  error_rate: number;
  avg_latency_ms: number;
  p95_latency_ms: number;
  avg_cost: number;
  avg_input_tokens: number;
  avg_output_tokens: number;
};

export type ExpandRecommendation = {
  experiment_id: string;
  current_split: string;
  recommended_split: string | null;
  decision_type: string;
  risk_level: string;
  reasons: string[];
  requires_manual_approval: boolean;
  generated_at: string;
};

export type ApprovalResult = {
  approval_id: string;
  experiment_id: string;
  old_split: {
    control: number;
    treatment: number;
  };
  new_split: {
    control: number;
    treatment: number;
  };
  approved_by: string;
  status: string;
  approved_at: string;
};

export type ApprovalLogItem = {
  approval_id: string;
  experiment_id: string;
  current_split: string;
  recommended_split: string;
  approved_by: string;
  approval_reason?: string | null;
  status: string;
  created_at: string;
};

export type RollbackResult = {
  rollback_id: string;
  experiment_id: string;
  from_version_id: string;
  to_version_id: string;
  status: string;
  reason: string;
  rollback_at: string;
};

export type RollbackLogItem = {
  rollback_id: string;
  experiment_id: string;
  from_version_id: string;
  to_version_id: string;
  trigger_rule?: string | null;
  reason: string;
  operator: string;
  status: string;
  created_at: string;
};
