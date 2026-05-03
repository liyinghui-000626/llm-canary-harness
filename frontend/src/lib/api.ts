import type {
  ApprovalLogItem,
  ApprovalResult,
  ApiConsoleEvent,
  AppItem,
  DecisionSnapshot,
  ExpandRecommendation,
  ExperimentItem,
  MetricsOverview,
  RequestTraceItem,
  RollbackLogItem,
  RollbackResult,
  VersionItem,
} from "../types";

type ApiEnvelope<T> = {
  code: number;
  message: string;
  data: T;
};

const MAX_CONSOLE_EVENTS = 80;
let apiConsoleEvents: ApiConsoleEvent[] = [];
const apiConsoleListeners = new Set<(events: ApiConsoleEvent[]) => void>();

type PageResult<T> = {
  total: number;
  page?: number;
  page_size?: number;
  items: T[];
};

type RequestOptions = RequestInit & {
  timeoutMs?: number;
};

function notifyApiConsoleListeners() {
  const snapshot = [...apiConsoleEvents];
  apiConsoleListeners.forEach((listener) => listener(snapshot));
}

function pushApiConsoleEvent(event: ApiConsoleEvent) {
  apiConsoleEvents = [event, ...apiConsoleEvents].slice(0, MAX_CONSOLE_EVENTS);
  notifyApiConsoleListeners();
}

function updateApiConsoleEvent(eventId: string, patch: Partial<ApiConsoleEvent>) {
  apiConsoleEvents = apiConsoleEvents.map((item) => (item.event_id === eventId ? { ...item, ...patch } : item));
  notifyApiConsoleListeners();
}

function inferService(path: string): ApiConsoleEvent["service"] {
  if (path.startsWith("/canary-admin/")) {
    return "admin";
  }
  if (path.startsWith("/canary-gateway/")) {
    return "gateway";
  }
  if (path.startsWith("/rag-downstream/")) {
    return "rag";
  }
  return "unknown";
}

function normalizePath(path: string) {
  return path.replace("/canary-admin", "").replace("/canary-gateway", "").replace("/rag-downstream", "");
}

function summarizePayload(value: unknown) {
  try {
    const text = JSON.stringify(value, null, 2);
    return text.length > 1200 ? `${text.slice(0, 1200)}\n...` : text;
  } catch {
    return String(value);
  }
}

async function request<T>(path: string, init?: RequestOptions): Promise<T> {
  const method = init?.method ?? "GET";
  const startedAt = new Date().toISOString();
  const startedAtMs = performance.now();
  const eventId = `evt_${Math.random().toString(36).slice(2, 10)}`;
  const controller = new AbortController();
  const timeoutMs = init?.timeoutMs;
  const timeoutId =
    typeof timeoutMs === "number" && timeoutMs > 0
      ? window.setTimeout(() => controller.abort(`Request timed out after ${timeoutMs} ms`), timeoutMs)
      : null;
  pushApiConsoleEvent({
    event_id: eventId,
    service: inferService(path),
    method,
    path: normalizePath(path),
    status: "pending",
    started_at: startedAt,
    request_body: typeof init?.body === "string" ? init.body : undefined,
  });

  try {
    const response = await fetch(path, {
      headers: {
        "Content-Type": "application/json",
        ...(init?.headers ?? {}),
      },
      ...init,
      signal: controller.signal,
    });

    const payload = (await response.json()) as ApiEnvelope<T>;
    if (!response.ok || payload.code !== 0) {
      updateApiConsoleEvent(eventId, {
        status: "error",
        duration_ms: Math.round(performance.now() - startedAtMs),
        response_code: response.status,
        message: payload.message || `Request failed: ${response.status}`,
        response_preview: summarizePayload(payload),
      });
      throw new Error(payload.message || `Request failed: ${response.status}`);
    }
    updateApiConsoleEvent(eventId, {
      status: "success",
      duration_ms: Math.round(performance.now() - startedAtMs),
      response_code: response.status,
      message: payload.message,
      response_preview: summarizePayload(payload),
    });
    return payload.data;
  } catch (error) {
    updateApiConsoleEvent(eventId, {
      status: "error",
      duration_ms: Math.round(performance.now() - startedAtMs),
      message: error instanceof Error ? error.message : "Request failed",
    });
    throw error instanceof Error ? error : new Error("Request failed");
  } finally {
    if (timeoutId !== null) {
      window.clearTimeout(timeoutId);
    }
  }
}

export function subscribeApiConsole(listener: (events: ApiConsoleEvent[]) => void) {
  apiConsoleListeners.add(listener);
  listener([...apiConsoleEvents]);
  return () => {
    apiConsoleListeners.delete(listener);
  };
}

export const adminApi = {
  listApps: () => request<PageResult<AppItem>>("/canary-admin/canary/api/v1/apps"),
  createApp: (body: Record<string, unknown>) =>
    request<AppItem>("/canary-admin/canary/api/v1/apps", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  listVersions: (appId: string) =>
    request<PageResult<VersionItem>>(`/canary-admin/canary/api/v1/apps/${appId}/versions`),
  createVersion: (appId: string, body: Record<string, unknown>) =>
    request<VersionItem>(`/canary-admin/canary/api/v1/apps/${appId}/versions`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  updateVersion: (versionId: string, body: Record<string, unknown>) =>
    request<VersionItem>(`/canary-admin/canary/api/v1/versions/${versionId}`, {
      method: "PUT",
      body: JSON.stringify(body),
    }),
  setStableVersion: (appId: string, versionId: string, operator: string) =>
    request<{ app_id: string; stable_version_id: string; updated_at: string }>(
      `/canary-admin/canary/api/v1/apps/${appId}/stable-version`,
      {
        method: "POST",
        body: JSON.stringify({ version_id: versionId, operator }),
      },
    ),
  setVersionStatus: (versionId: string, status: "stable" | "draft", operator: string) =>
    request<VersionItem>(`/canary-admin/canary/api/v1/versions/${versionId}/status`, {
      method: "POST",
      body: JSON.stringify({ status, operator }),
    }),
  listExperiments: () =>
    request<PageResult<ExperimentItem>>("/canary-admin/canary/api/v1/experiments"),
  getExperiment: (experimentId: string) =>
    request<ExperimentItem>(`/canary-admin/canary/api/v1/experiments/${experimentId}`),
  createExperiment: (body: Record<string, unknown>) =>
    request<ExperimentItem>("/canary-admin/canary/api/v1/experiments", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  updateExperiment: (experimentId: string, body: Record<string, unknown>) =>
    request<ExperimentItem>(`/canary-admin/canary/api/v1/experiments/${experimentId}`, {
      method: "PUT",
      body: JSON.stringify(body),
    }),
  startExperiment: (experimentId: string, operator: string) =>
    request(`/canary-admin/canary/api/v1/experiments/${experimentId}/start`, {
      method: "POST",
      body: JSON.stringify({ operator }),
    }),
  stopExperiment: (experimentId: string, operator: string, reason: string) =>
    request(`/canary-admin/canary/api/v1/experiments/${experimentId}/stop`, {
      method: "POST",
      body: JSON.stringify({ operator, reason }),
    }),
  listRequests: (filters?: { experimentId?: string; appId?: string }) => {
    const params = new URLSearchParams();
    if (filters?.experimentId) {
      params.set("experiment_id", filters.experimentId);
    }
    if (filters?.appId) {
      params.set("app_id", filters.appId);
    }
    const query = params.size > 0 ? `?${params.toString()}` : "";
    return request<PageResult<RequestTraceItem>>(`/canary-admin/canary/api/v1/requests${query}`);
  },
  getMetrics: (experimentId: string) =>
    request<MetricsOverview>(`/canary-admin/canary/api/v1/experiments/${experimentId}/metrics`),
  getExpandRecommendation: (experimentId: string) =>
    request<ExpandRecommendation>(
      `/canary-admin/canary/api/v1/experiments/${experimentId}/expand-recommendation`,
    ),
  getDecision: (experimentId: string) =>
    request<DecisionSnapshot>(`/canary-admin/canary/api/v1/experiments/${experimentId}/decision`),
  recomputeDecision: (experimentId: string, operator: string) =>
    request<DecisionSnapshot>(`/canary-admin/canary/api/v1/experiments/${experimentId}/decision/recompute`, {
      method: "POST",
      body: JSON.stringify({ operator }),
    }),
  approveExpand: (
    experimentId: string,
    body: {
      operator: string;
      approved: boolean;
      approved_split?: { control: number; treatment: number };
      approval_reason?: string;
    },
  ) =>
    request<ApprovalResult>(`/canary-admin/canary/api/v1/experiments/${experimentId}/approve-expand`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  listApprovalLogs: (experimentId: string) =>
    request<{ items: ApprovalLogItem[] }>(
      `/canary-admin/canary/api/v1/experiments/${experimentId}/approval-logs`,
    ),
  rollbackExperiment: (experimentId: string, operator: string, reason: string) =>
    request<RollbackResult>(`/canary-admin/canary/api/v1/experiments/${experimentId}/rollback`, {
      method: "POST",
      body: JSON.stringify({ operator, reason }),
    }),
  listRollbackLogs: (experimentId: string) =>
    request<{ items: RollbackLogItem[] }>(
      `/canary-admin/canary/api/v1/experiments/${experimentId}/rollback-logs`,
    ),
};

export const gatewayApi = {
  invoke: (
    body: {
      app_id: string;
      user_id: string;
      session_id?: string;
      query: string;
      metadata?: Record<string, unknown>;
    },
    options?: {
      timeoutMs?: number;
    },
  ) =>
    request<{
      request_id: string;
      trace_id: string;
      experiment_id?: string | null;
      version_id: string;
      routing_reason: string;
      answer?: string;
      status: string;
      latency_ms?: number;
      cost?: number;
      input_tokens?: number;
      output_tokens?: number;
      total_tokens?: number;
      retrieval_docs?: string[];
      error_message?: string | null;
    }>("/canary-gateway/canary/api/v1/gateway/invoke", {
      method: "POST",
      body: JSON.stringify(body),
      timeoutMs: options?.timeoutMs,
    }),
};
