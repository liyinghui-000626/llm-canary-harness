import { Activity, Bot, GitBranch, Radar, RefreshCw } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { adminApi, subscribeApiConsole } from "../lib/api";
import type {
  ApiConsoleEvent,
  AppItem,
  DecisionSnapshot,
  ExperimentItem,
  MetricsCard,
  MetricsOverview,
  RequestTraceItem,
} from "../types";
import { EmptyState, RefreshButton, SectionHeader, StatusPill, SummaryCard, formatDate } from "../components/Shared";

function formatPercent(value: number) {
  return `${(value * 100).toFixed(2)}%`;
}

function formatMoney(value: number) {
  return `¥${value.toFixed(4)}`;
}

function serviceLabel(service: ApiConsoleEvent["service"]) {
  if (service === "admin") {
    return "6000 Admin";
  }
  if (service === "gateway") {
    return "6001 Gateway";
  }
  if (service === "rag") {
    return "RAG Downstream";
  }
  return "Unknown";
}

function metricTitle(label: string, metrics: MetricsCard, experiment: ExperimentItem | null) {
  const versionId = label === "control" ? experiment?.control_version_id : experiment?.treatment_version_id;
  return versionId ? `${label} · ${versionId}` : label;
}

export function ObservabilityPage() {
  const [apps, setApps] = useState<AppItem[]>([]);
  const [experiments, setExperiments] = useState<ExperimentItem[]>([]);
  const [selectedAppId, setSelectedAppId] = useState("");
  const [selectedExperimentId, setSelectedExperimentId] = useState("");
  const [requests, setRequests] = useState<RequestTraceItem[]>([]);
  const [metrics, setMetrics] = useState<MetricsOverview | null>(null);
  const [decision, setDecision] = useState<DecisionSnapshot | null>(null);
  const [apiEvents, setApiEvents] = useState<ApiConsoleEvent[]>([]);
  const [selectedRequestId, setSelectedRequestId] = useState("");
  const [selectedEventId, setSelectedEventId] = useState("");
  const [loading, setLoading] = useState(false);
  const [refreshingDecision, setRefreshingDecision] = useState(false);
  const [error, setError] = useState("");

  const selectedExperiment = useMemo(
    () => experiments.find((item) => item.experiment_id === selectedExperimentId) ?? null,
    [experiments, selectedExperimentId],
  );
  const selectedRequest = useMemo(
    () => requests.find((item) => item.request_id === selectedRequestId) ?? requests[0] ?? null,
    [requests, selectedRequestId],
  );
  const selectedEvent = useMemo(
    () => apiEvents.find((item) => item.event_id === selectedEventId) ?? apiEvents[0] ?? null,
    [apiEvents, selectedEventId],
  );

  async function loadApps() {
    const result = await adminApi.listApps();
    setApps(result.items);
    if (!selectedAppId && result.items[0]) {
      setSelectedAppId(result.items[0].app_id);
    }
  }

  async function loadExperiments() {
    const result = await adminApi.listExperiments();
    setExperiments(result.items);
  }

  async function loadObservability(appId: string, experimentId: string) {
    if (!appId && !experimentId) {
      setRequests([]);
      setMetrics(null);
      setDecision(null);
      return;
    }

    setLoading(true);
    setError("");
    try {
      const [requestResult, metricsResult, decisionResult] = await Promise.all([
        adminApi.listRequests({
          appId: appId || undefined,
          experimentId: experimentId || undefined,
        }),
        experimentId ? adminApi.getMetrics(experimentId) : Promise.resolve(null),
        experimentId ? adminApi.getDecision(experimentId) : Promise.resolve(null),
      ]);

      setRequests(requestResult.items);
      setSelectedRequestId((prev) => {
        if (prev && requestResult.items.some((item) => item.request_id === prev)) {
          return prev;
        }
        return requestResult.items[0]?.request_id || "";
      });
      setMetrics(metricsResult);
      setDecision(decisionResult);
    } catch (err) {
      setError(err instanceof Error ? err.message : "可观测数据加载失败");
    } finally {
      setLoading(false);
    }
  }

  async function refreshDecision() {
    if (!selectedExperimentId) {
      return;
    }
    setRefreshingDecision(true);
    setError("");
    try {
      const result = await adminApi.recomputeDecision(selectedExperimentId, "console-operator");
      setDecision(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "决策刷新失败");
    } finally {
      setRefreshingDecision(false);
    }
  }

  useEffect(() => {
    void loadApps();
    void loadExperiments();
  }, []);

  useEffect(() => {
    const unsubscribe = subscribeApiConsole((events) => {
      setApiEvents(events);
      setSelectedEventId((prev) => {
        if (prev && events.some((item) => item.event_id === prev)) {
          return prev;
        }
        return events[0]?.event_id || "";
      });
    });
    return unsubscribe;
  }, []);

  const appExperiments = useMemo(
    () => experiments.filter((item) => !selectedAppId || item.app_id === selectedAppId),
    [experiments, selectedAppId],
  );

  useEffect(() => {
    if (!selectedAppId) {
      return;
    }
    if (selectedExperimentId && appExperiments.some((item) => item.experiment_id === selectedExperimentId)) {
      return;
    }
    setSelectedExperimentId(appExperiments[0]?.experiment_id || "");
  }, [appExperiments, selectedAppId, selectedExperimentId]);

  useEffect(() => {
    void loadObservability(selectedAppId, selectedExperimentId);
  }, [selectedAppId, selectedExperimentId]);

  useEffect(() => {
    if (!selectedAppId && !selectedExperimentId) {
      return;
    }
    const timer = window.setInterval(() => {
      void loadObservability(selectedAppId, selectedExperimentId);
    }, 5000);
    return () => window.clearInterval(timer);
  }, [selectedAppId, selectedExperimentId]);

  const traceCount = requests.length;
  const successCount = requests.filter((item) => item.status === "success").length;
  const errorCount = requests.filter((item) => item.status === "error").length;
  const avgLatency =
    requests.length > 0 ? Math.round(requests.reduce((sum, item) => sum + item.latency_ms, 0) / requests.length) : 0;
  const totalTokens = requests.reduce((sum, item) => sum + item.total_tokens, 0);
  const totalCost = requests.reduce((sum, item) => sum + item.cost, 0);

  return (
    <div className="page-grid observability-layout">
      <section className="panel panel-span-2">
        <SectionHeader
          title="Trace / 指标"
          description="看真实分流后的请求、指标、决策和接口调用记录。"
          action={<RefreshButton onClick={() => void loadObservability(selectedAppId, selectedExperimentId)} loading={loading} />}
        />

        <div className="toolbar stacked-on-mobile">
          <label className="inline-field">
            <span>应用</span>
            <select value={selectedAppId} onChange={(event) => setSelectedAppId(event.target.value)}>
              <option value="">全部应用</option>
              {apps.map((item) => (
                <option key={item.app_id} value={item.app_id}>
                  {item.app_name}
                </option>
              ))}
            </select>
          </label>

          <label className="inline-field grow">
            <span>实验</span>
            <select value={selectedExperimentId} onChange={(event) => setSelectedExperimentId(event.target.value)}>
              <option value="">全部实验</option>
              {appExperiments.map((item) => (
                <option key={item.experiment_id} value={item.experiment_id}>
                  {item.experiment_name}
                </option>
              ))}
            </select>
          </label>

          <button className="secondary-button" onClick={() => void refreshDecision()} disabled={!selectedExperimentId || refreshingDecision}>
            <RefreshCw size={16} className={refreshingDecision ? "spin" : undefined} />
            <span>刷新 Decision</span>
          </button>
        </div>

        <div className="summary-grid">
          <SummaryCard label="Trace 总数" value={traceCount} accent="slate" />
          <SummaryCard label="成功请求" value={successCount} accent="green" />
          <SummaryCard label="错误请求" value={errorCount} accent="amber" />
          <SummaryCard label="平均延迟" value={`${avgLatency} ms`} accent="blue" />
        </div>

        <div className="summary-grid">
          <SummaryCard label="总 Tokens" value={totalTokens} accent="slate" />
          <SummaryCard label="总成本" value={formatMoney(totalCost)} accent="green" />
          <SummaryCard
            label="当前实验状态"
            value={selectedExperiment?.status || "-"}
            accent="amber"
            hint={selectedExperiment ? formatDate(selectedExperiment.started_at || selectedExperiment.created_at) : undefined}
          />
          <SummaryCard
            label="Decision"
            value={decision?.decision_type || "-"}
            accent="blue"
            hint={decision ? formatDate(decision.evaluated_at) : "未选择实验"}
          />
        </div>

        {error ? <div className="error-banner">{error}</div> : null}
      </section>

      <section className="panel observability-trace-panel">
        <SectionHeader title="请求 Trace" description="每条请求都展示命中版本、耗时、时间和 token 用量。" />
        {requests.length === 0 ? (
          <EmptyState title="当前筛选条件下还没有请求 Trace。" />
        ) : (
          <div className="trace-list">
            {requests.map((item) => (
              <button
                key={item.request_id}
                type="button"
                className={`trace-item ${selectedRequest?.request_id === item.request_id ? "selected" : ""}`}
                onClick={() => setSelectedRequestId(item.request_id)}
              >
                <div className="trace-top">
                  <strong>{item.user_id}</strong>
                  <StatusPill value={item.status} />
                </div>
                <div className="trace-middle">
                  <div>{item.query || "-"}</div>
                  <div className="cell-subtitle">
                    {item.routing_reason} · {item.version_id}
                  </div>
                </div>
                <div className="trace-bottom">
                  <span>{formatDate(item.created_at)}</span>
                  <span>{item.latency_ms} ms</span>
                </div>
                <div className="trace-bottom">
                  <span>{item.total_tokens} tokens</span>
                  <span>{formatMoney(item.cost)}</span>
                </div>
              </button>
            ))}
          </div>
        )}
      </section>

      <section className="panel observability-detail-panel">
        <SectionHeader title="详情 / Decision" description="把 Trace 细节、实验指标和规则决策放在一起看。" />
        <div className="detail-stack">
          <div className="detail-block">
            <span>当前实验</span>
            <strong>{selectedExperiment?.experiment_name || "-"}</strong>
            <div className="activity-meta">
              <span>{selectedExperiment?.control_version_id || "-"}</span>
              <span>{selectedExperiment?.treatment_version_id || "-"}</span>
              <span>{selectedExperiment ? `${selectedExperiment.traffic_control}/${selectedExperiment.traffic_treatment}` : "-"}</span>
            </div>
          </div>

          {decision ? (
            <div className="detail-block">
              <span>Decision Snapshot</span>
              <strong>{decision.decision_type}</strong>
              <div className="activity-meta">
                <span>risk: {decision.risk_level}</span>
                <span>next split: {decision.recommended_next_split || "-"}</span>
                <span>{formatDate(decision.evaluated_at)}</span>
              </div>
              <div className="reason-list">
                {decision.triggered_rules.length > 0 ? (
                  decision.triggered_rules.map((item) => (
                    <span key={`${item.rule_name}-${item.reason}`} className="reason-chip">
                      {item.rule_name}
                    </span>
                  ))
                ) : (
                  <span className="reason-chip">no triggered rule</span>
                )}
              </div>
              <div className="console-log-message">
                {decision.triggered_rules.length > 0
                  ? decision.triggered_rules.map((item) => `${item.rule_name}: ${item.reason}`).join("\n")
                  : decision.requires_manual_approval
                    ? "样本和护栏通过，系统建议继续观察或审批扩量。"
                    : "当前还没有触发额外规则。"}
              </div>
            </div>
          ) : null}

          {metrics ? (
            <div className="metric-panels">
              {(["control", "treatment"] as const).map((key) => (
                <div key={key} className="metric-card">
                  <div className="metric-card-header">
                    <h3>{metricTitle(key, metrics[key], selectedExperiment)}</h3>
                    <StatusPill value={key === "control" ? "stable" : "draft"} />
                  </div>
                  <div className="metric-grid">
                    <div>
                      <span>请求量</span>
                      <strong>{metrics[key].request_count}</strong>
                    </div>
                    <div>
                      <span>错误率</span>
                      <strong>{formatPercent(metrics[key].error_rate)}</strong>
                    </div>
                    <div>
                      <span>P95 延迟</span>
                      <strong>{metrics[key].p95_latency_ms} ms</strong>
                    </div>
                    <div>
                      <span>平均成本</span>
                      <strong>{formatMoney(metrics[key].avg_cost)}</strong>
                    </div>
                    <div>
                      <span>输入 Tokens</span>
                      <strong>{metrics[key].avg_input_tokens.toFixed(1)}</strong>
                    </div>
                    <div>
                      <span>输出 Tokens</span>
                      <strong>{metrics[key].avg_output_tokens.toFixed(1)}</strong>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : null}

          {selectedRequest ? (
            <>
              <div className="detail-block">
                <span>Query</span>
                <strong>{selectedRequest.query || "-"}</strong>
                <div className="activity-meta">
                  <span>{selectedRequest.trace_id}</span>
                  <span>{formatDate(selectedRequest.created_at)}</span>
                </div>
              </div>

              <div className="detail-block">
                <span>Answer / Error</span>
                <strong>{selectedRequest.answer || selectedRequest.error_message || "-"}</strong>
              </div>

              <div className="detail-block">
                <span>检索结果</span>
                <strong>{selectedRequest.retrieval_docs?.length ? selectedRequest.retrieval_docs.join("\n") : "下游没有返回 retrieval_docs"}</strong>
              </div>

              <div className="detail-block">
                <span>Token / Cost / Route</span>
                <div className="metric-grid">
                  <div>
                    <span>输入</span>
                    <strong>{selectedRequest.input_tokens}</strong>
                  </div>
                  <div>
                    <span>输出</span>
                    <strong>{selectedRequest.output_tokens}</strong>
                  </div>
                  <div>
                    <span>总量</span>
                    <strong>{selectedRequest.total_tokens}</strong>
                  </div>
                  <div>
                    <span>延迟</span>
                    <strong>{selectedRequest.latency_ms} ms</strong>
                  </div>
                  <div>
                    <span>成本</span>
                    <strong>{formatMoney(selectedRequest.cost)}</strong>
                  </div>
                  <div>
                    <span>命中</span>
                    <strong>{selectedRequest.routing_reason}</strong>
                  </div>
                </div>
              </div>
            </>
          ) : (
            <EmptyState title="请选择一条 Trace 查看详情。" />
          )}
        </div>
      </section>

      <section className="panel panel-span-2">
        <SectionHeader title="API Console" description="集中看 Admin / Gateway / RAG 的接口事件和返回摘要。" />
        {apiEvents.length === 0 ? (
          <EmptyState title="前端这轮操作还没有接口事件。" />
        ) : (
          <div className="runtime-console">
            <div className="console-column">
              <div className="console-card">
                <div className="console-card-header">
                  <h3>事件流</h3>
                  <span>最近 {apiEvents.length} 条接口事件，点开看请求体和响应摘要。</span>
                </div>
                <div className="console-summary-row">
                  <div className="console-summary-pill">
                    <span>Gateway 事件</span>
                    <strong>{apiEvents.filter((item) => item.service === "gateway").length}</strong>
                  </div>
                  <div className="console-summary-pill">
                    <span>RAG 事件</span>
                    <strong>{apiEvents.filter((item) => item.service === "rag").length}</strong>
                  </div>
                </div>
                <div className="console-log-list">
                  {apiEvents.map((item) => (
                    <button
                      key={item.event_id}
                      type="button"
                      className={`console-log-item console-log-button console-${item.status} ${selectedEvent?.event_id === item.event_id ? "selected" : ""}`}
                      onClick={() => setSelectedEventId(item.event_id)}
                    >
                      <div className="trace-top">
                        <strong>{serviceLabel(item.service)}</strong>
                        <StatusPill value={item.status} />
                      </div>
                      <div className="console-log-path">
                        {item.method} {item.path}
                      </div>
                      <div className="console-log-meta">
                        <span>{formatDate(item.started_at)}</span>
                        <span>{item.duration_ms ? `${item.duration_ms} ms` : "-"}</span>
                      </div>
                      <div className="console-log-message">{item.message || "-"}</div>
                    </button>
                  ))}
                </div>
              </div>
            </div>

            <div className="console-column">
              <div className="console-card">
                <div className="console-card-header">
                  <h3>事件详情</h3>
                  <span>把请求体、返回摘要和链路位置拆开看。</span>
                </div>
                {selectedEvent ? (
                  <div className="detail-stack">
                    <div className="detail-block">
                      <span>服务</span>
                      <strong>{serviceLabel(selectedEvent.service)}</strong>
                      <div className="activity-meta">
                        <span>{selectedEvent.method}</span>
                        <span>{selectedEvent.response_code || "-"}</span>
                        <span>{formatDate(selectedEvent.started_at)}</span>
                      </div>
                    </div>
                    <div className="detail-block">
                      <span>路径</span>
                      <strong>{selectedEvent.path}</strong>
                    </div>
                    <div className="detail-block">
                      <span>请求体</span>
                      <strong>{selectedEvent.request_body || "无请求体"}</strong>
                    </div>
                    <div className="detail-block">
                      <span>响应摘要</span>
                      <strong>{selectedEvent.response_preview || selectedEvent.message || "暂无响应摘要"}</strong>
                    </div>
                  </div>
                ) : (
                  <EmptyState title="请选择一条接口事件查看详情。" />
                )}
              </div>
            </div>
          </div>
        )}
      </section>

      <section className="panel panel-span-2">
        <SectionHeader title="链路说明" description="这一页现在直接对齐最小闭环里最关键的信号。" />
        <div className="summary-grid">
          <SummaryCard label="Gateway 路由" value="6001 分流" accent="blue" hint="按 user_id 稳定命中 control / treatment" />
          <SummaryCard label="真实下游" value="RAG HTTP" accent="green" hint="retrieval_docs 优先使用真实下游结果" />
          <SummaryCard label="Decision 引擎" value={decision?.decision_type || "keep_observing"} accent="amber" hint="基于样本量、错误率、延迟护栏" />
          <SummaryCard label="刷新频率" value="5s" accent="slate" hint="Trace / 指标会自动刷新" />
        </div>
        <div className="console-inline-note">
          <div>
            <Radar size={16} />
            <span>Decision 面板看规则命中和建议分流。</span>
          </div>
          <div>
            <GitBranch size={16} />
            <span>Trace 面板看请求时间、命中版本、token 和成本。</span>
          </div>
          <div>
            <Bot size={16} />
            <span>RAG 检索结果直接展示真实 retrieval_docs，不再默认回填 mock。</span>
          </div>
          <div>
            <Activity size={16} />
            <span>API Console 用来核对前端实际发起了哪些 Admin / Gateway 请求。</span>
          </div>
        </div>
      </section>
    </div>
  );
}
