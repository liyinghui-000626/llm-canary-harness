import { PauseCircle, PlayCircle, Plus } from "lucide-react";
import { FormEvent, useEffect, useMemo, useState } from "react";
import { adminApi, gatewayApi, subscribeApiConsole } from "../lib/api";
import type { ApiConsoleEvent, AppItem, ExperimentItem, RequestTraceItem, VersionItem } from "../types";
import { EmptyState, RefreshButton, SectionHeader, StatusPill, SummaryCard, formatDate } from "../components/Shared";

const initialForm = {
  app_id: "",
  experiment_name: "",
  control_version_id: "",
  treatment_version_id: "",
  traffic_control: "90",
  traffic_treatment: "10",
  whitelist_user_ids: "user_internal_001",
  max_error_rate: "0.05",
  max_latency_ratio: "1.5",
  min_sample_size: "1000",
  created_by: "operator",
};

export function ExperimentsPage() {
  const [apps, setApps] = useState<AppItem[]>([]);
  const [versions, setVersions] = useState<VersionItem[]>([]);
  const [experiments, setExperiments] = useState<ExperimentItem[]>([]);
  const [selectedExperimentId, setSelectedExperimentId] = useState("");
  const [selectedExperiment, setSelectedExperiment] = useState<ExperimentItem | null>(null);
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [form, setForm] = useState(initialForm);
  const [consoleRequests, setConsoleRequests] = useState<RequestTraceItem[]>([]);
  const [consoleVersions, setConsoleVersions] = useState<VersionItem[]>([]);
  const [consoleModal, setConsoleModal] = useState<{ title: string; sections: Array<{ label: string; content: string }> } | null>(
    null,
  );
  const [apiConsoleEvents, setApiConsoleEvents] = useState<ApiConsoleEvent[]>([]);

  async function loadApps() {
    const result = await adminApi.listApps();
    setApps(result.items);
    if (!form.app_id && result.items[0]) {
      setForm((prev) => ({ ...prev, app_id: result.items[0].app_id }));
    }
  }

  async function loadVersions(appId: string) {
    if (!appId) {
      setVersions([]);
      setForm((prev) => ({
        ...prev,
        control_version_id: "",
        treatment_version_id: "",
      }));
      return;
    }
    const result = await adminApi.listVersions(appId);
    setVersions(result.items);
    const stable = result.items.find((item) => item.status === "stable");
    const preferredControl = stable?.version_id || result.items[0]?.version_id || "";
    const preferredTreatment = result.items.find((item) => item.version_id !== preferredControl)?.version_id || "";
    setForm((prev) => ({
      ...prev,
      control_version_id:
        prev.control_version_id && result.items.some((item) => item.version_id === prev.control_version_id)
          ? prev.control_version_id
          : preferredControl,
      treatment_version_id:
        prev.treatment_version_id &&
        result.items.some((item) => item.version_id === prev.treatment_version_id) &&
        prev.treatment_version_id !== (prev.control_version_id || preferredControl)
          ? prev.treatment_version_id
          : preferredTreatment,
    }));
  }

  async function loadExperiments() {
    setLoading(true);
    setError("");
    try {
      const result = await adminApi.listExperiments();
      setExperiments(result.items);
      if (!selectedExperimentId && result.items[0]) {
        setSelectedExperimentId(result.items[0].experiment_id);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "实验加载失败");
    } finally {
      setLoading(false);
    }
  }

  async function loadExperimentDetail(experimentId: string) {
    if (!experimentId) {
      setSelectedExperiment(null);
      return;
    }
    try {
      const result = await adminApi.getExperiment(experimentId);
      setSelectedExperiment(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "实验详情加载失败");
    }
  }

  async function loadConsoleData(experiment: ExperimentItem | null) {
    if (!experiment) {
      setConsoleRequests([]);
      setConsoleVersions([]);
      return;
    }
    try {
      const [requestResult, versionResult] = await Promise.all([
        adminApi.listRequests({
          appId: experiment.app_id,
          experimentId: experiment.experiment_id,
        }),
        adminApi.listVersions(experiment.app_id),
      ]);
      setConsoleRequests(requestResult.items.slice(0, 12));
      setConsoleVersions(versionResult.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : "控制台数据加载失败");
    }
  }

  useEffect(() => {
    void loadApps();
    void loadExperiments();
  }, []);

  useEffect(() => {
    return subscribeApiConsole((events) => {
      setApiConsoleEvents(events);
    });
  }, []);

  useEffect(() => {
    void loadVersions(form.app_id);
  }, [form.app_id]);

  useEffect(() => {
    void loadExperimentDetail(selectedExperimentId);
  }, [selectedExperimentId]);

  useEffect(() => {
    void loadConsoleData(selectedExperiment);
    if (!selectedExperiment) {
      return;
    }
    const timer = window.setInterval(() => {
      void loadConsoleData(selectedExperiment);
    }, 4000);
    return () => window.clearInterval(timer);
  }, [selectedExperiment]);

  const selectedExperimentVersionMap = useMemo(
    () => new Map(consoleVersions.map((item) => [item.version_id, item])),
    [consoleVersions],
  );

  const canStart =
    selectedExperiment?.status === "created" ||
    selectedExperiment?.status === "stopped" ||
    selectedExperiment?.status === "running";
  const canStop = selectedExperiment?.status === "running";
  const runningCount = experiments.filter((item) => item.status === "running").length;
  const restartableCount = experiments.filter((item) => item.status === "created" || item.status === "stopped").length;
  const versionOptions = useMemo(
    () => versions.map((item) => ({ label: `${item.version_name} (${item.status})`, value: item.version_id })),
    [versions],
  );
  const treatmentOptions = useMemo(
    () => versionOptions.filter((item) => item.value !== form.control_version_id),
    [form.control_version_id, versionOptions],
  );
  const createBlockedReason = !form.app_id
    ? "请先选择应用"
    : versions.length < 2
      ? "当前应用至少需要两个不同版本才能创建实验"
      : !form.control_version_id || !form.treatment_version_id
        ? "请选择对照版本和实验版本"
        : form.control_version_id === form.treatment_version_id
          ? "对照版本和实验版本不能相同"
          : "";
  const startedAtMs = selectedExperiment?.started_at ? Date.parse(selectedExperiment.started_at) : null;
  const requestsSinceStarted =
    !selectedExperiment || selectedExperiment.status !== "running" || startedAtMs === null
      ? []
      : consoleRequests.filter((item) => Date.parse(item.created_at) >= startedAtMs);
  const gatewayEvents = requestsSinceStarted.slice(0, 8);
  const ragRows = selectedExperiment
    ? [selectedExperiment.control_version_id, selectedExperiment.treatment_version_id].map((versionId) => {
        const version = selectedExperimentVersionMap.get(versionId);
        const versionRequests = requestsSinceStarted.filter((item) => item.version_id === versionId);
        const latestRequest = versionRequests[0] ?? null;
        return {
          versionId,
          versionName: version?.version_name || versionId,
          endpointUrl: version?.endpoint_url || "-",
          modelName: version?.model_name || "-",
          requestCount: versionRequests.length,
          latestRequest,
        };
      })
    : [];
  const experimentConsoleEvents = selectedExperiment
    ? apiConsoleEvents.filter((item) => item.path.includes(selectedExperiment.experiment_id))
    : [];
  const latestAdminEvent = experimentConsoleEvents.find((item) => item.service === "admin") ?? null;
  const latestGatewayRequest = gatewayEvents[0] ?? null;
  const latestRagRequest =
    ragRows
      .map((row) => row.latestRequest)
      .filter((item): item is RequestTraceItem => Boolean(item))
      .sort((left, right) => Date.parse(right.created_at) - Date.parse(left.created_at))[0] ?? null;
  const latestRagError = ragRows.find((row) => row.latestRequest?.status === "error")?.latestRequest ?? null;
  const progressStages = [
    {
      key: "admin",
      title: "6000 Admin",
      state:
        latestAdminEvent?.status === "error"
          ? "error"
          : latestAdminEvent?.status === "pending"
            ? "pending"
            : selectedExperiment?.status === "running" || selectedExperiment?.status === "stopped"
              ? "success"
              : "idle",
      hint:
        latestAdminEvent?.message ||
        (selectedExperiment ? `实验状态：${selectedExperiment.status}` : "先选择实验"),
      meta:
        latestAdminEvent?.started_at
          ? formatDate(latestAdminEvent.started_at)
          : selectedExperiment?.updated_at
            ? formatDate(selectedExperiment.updated_at)
            : "-",
    },
    {
      key: "gateway",
      title: "6001 Gateway",
      state:
        latestGatewayRequest?.status === "error"
          ? "error"
          : latestGatewayRequest
            ? "success"
            : selectedExperiment?.status === "running"
              ? "pending"
              : "idle",
      hint:
        latestGatewayRequest?.query ||
        (selectedExperiment?.status === "running" ? "等待真实请求进入 6001" : "实验尚未进入真实流量"),
      meta: latestGatewayRequest ? `${latestGatewayRequest.latency_ms} ms` : "-",
    },
    {
      key: "rag",
      title: "目标下游 RAG",
      state:
        latestRagError?.status === "error"
          ? "error"
          : latestRagRequest
            ? "success"
            : latestGatewayRequest
              ? "pending"
              : "idle",
      hint:
        latestRagError?.error_message ||
        latestRagRequest?.answer ||
        (latestGatewayRequest ? "Gateway 已收到请求，等待下游结果" : "还没有下游调用"),
      meta: latestRagRequest ? formatDate(latestRagRequest.created_at) : "-",
    },
  ] as const;

  async function handleCreateExperiment(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (createBlockedReason) {
      setError(createBlockedReason);
      return;
    }
    setSubmitting(true);
    setError("");
    try {
      await adminApi.createExperiment({
        app_id: form.app_id,
        experiment_name: form.experiment_name,
        control_version_id: form.control_version_id,
        treatment_version_id: form.treatment_version_id,
        traffic_control: Number(form.traffic_control),
        traffic_treatment: Number(form.traffic_treatment),
        routing_rules: {
          hash_key: "user_id",
          whitelist_user_ids: form.whitelist_user_ids
            .split(",")
            .map((value) => value.trim())
            .filter(Boolean),
          channels: [],
        },
        guardrails: {
          max_error_rate: Number(form.max_error_rate),
          max_latency_ratio: Number(form.max_latency_ratio),
          min_sample_size: Number(form.min_sample_size),
        },
        auto_rollback: true,
        created_by: form.created_by,
      });
      setForm((prev) => ({ ...initialForm, app_id: prev.app_id }));
      await loadExperiments();
      await loadConsoleData(selectedExperiment);
    } catch (err) {
      setError(err instanceof Error ? err.message : "实验创建失败");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleStart() {
    if (!selectedExperimentId) {
      return;
    }
    setError("");
    try {
      if (selectedExperiment?.status === "running") {
        await adminApi.stopExperiment(selectedExperimentId, "console-operator", "console restart");
      }
      await adminApi.startExperiment(selectedExperimentId, "console-operator");
      const refreshedExperiment = await adminApi.getExperiment(selectedExperimentId);
      await gatewayApi.invoke({
        app_id: refreshedExperiment.app_id,
        user_id: `console-start-${Date.now()}`,
        session_id: `console-start-${selectedExperimentId}`,
        query: "实验启动联调验证",
        metadata: {
          source: "console_auto_start_probe",
          experiment_id: refreshedExperiment.experiment_id,
          triggered_by: "start_button",
        },
      });
      setSelectedExperiment(refreshedExperiment);
      await loadExperiments();
      await loadConsoleData(refreshedExperiment);
    } catch (err) {
      setError(err instanceof Error ? err.message : "实验启动失败");
    }
  }

  async function handleStop() {
    if (!selectedExperimentId) {
      return;
    }
    await adminApi.stopExperiment(selectedExperimentId, "console-operator", "console stop");
    await loadExperiments();
    await loadExperimentDetail(selectedExperimentId);
    await loadConsoleData(selectedExperiment);
  }

  return (
    <div className="page-grid experiments-layout">
      <section className="panel panel-span-2">
        <SectionHeader
          title="联调控制台"
          description="只看真实经过 6001 Gateway 和下游 RAG 的运行情况。"
          action={selectedExperiment ? <RefreshButton onClick={() => void loadConsoleData(selectedExperiment)} /> : undefined}
        />
        {!selectedExperiment ? (
          <EmptyState title="先在左侧选中一个实验，再看联调过程。" />
        ) : (
          <>
            <div className="pipeline-progress">
              {progressStages.map((stage, index) => (
                <div key={stage.key} className={`pipeline-stage stage-${stage.state}`}>
                  <div className="pipeline-stage-top">
                    <span className="pipeline-stage-index">{index + 1}</span>
                    <strong>{stage.title}</strong>
                  </div>
                  <div className="pipeline-stage-body">
                    <p>{stage.hint}</p>
                    <span>{stage.meta}</span>
                  </div>
                  {index < progressStages.length - 1 ? <div className={`pipeline-link link-${stage.state}`} /> : null}
                </div>
              ))}
            </div>

            <div className="runtime-console">
            <div className="console-column">
              <div className="console-card">
                <div className="console-card-header">
                  <h3>6001 Gateway</h3>
                  <span>这里只展示真实经过 6001 的业务请求，不再自动注入启动探测流量。</span>
                </div>
                <div className="console-summary-row">
                  <div className="console-summary-pill">
                    <span>实验状态</span>
                    <strong>{selectedExperiment.status}</strong>
                  </div>
                  <div className="console-summary-pill">
                    <span>启动后请求</span>
                    <strong>{requestsSinceStarted.length}</strong>
                  </div>
                </div>
                {gatewayEvents.length === 0 ? (
                  <div className="empty-state compact-empty">
                    还没有看到 6001 请求。启动实验后，需要真实业务请求进入 Gateway，记录才会出现在这里。
                  </div>
                ) : (
                  <>
                    <div className="console-log-list">
                    {gatewayEvents.map((item) => (
                      <button
                        key={item.request_id}
                        className={`console-log-item console-log-button console-${item.status === "success" ? "success" : "error"}`}
                        onClick={() =>
                          setConsoleModal({
                            title: `6001 Gateway · ${item.request_id}`,
                            sections: [
                              { label: "Query", content: item.query || "-" },
                              { label: "Answer / Error", content: item.error_message || item.answer || "-" },
                              {
                                label: "路由详情",
                                content: `${item.routing_reason}\n${item.version_id}\n${item.user_id} · ${item.latency_ms} ms`,
                              },
                            ],
                          })
                        }
                      >
                        <div className="console-log-top">
                          <strong>{item.request_id}</strong>
                          <span>{item.status}</span>
                        </div>
                        <div className="console-log-path">{item.routing_reason}</div>
                        <div className="console-log-meta">
                          <span>{item.user_id}</span>
                          <span>{item.latency_ms} ms</span>
                        </div>
                        <div className="console-log-message">{item.version_id}</div>
                      </button>
                    ))}
                    </div>
                  </>
                )}
              </div>
            </div>

            <div className="console-column">
              <div className="console-card">
                <div className="console-card-header">
                  <h3>RAG 下游</h3>
                  <span>按 control / treatment 看目标 endpoint 和最新一次调用结果</span>
                </div>
                <div className="console-log-list">
                  {ragRows.map((row) => (
                    <button
                      key={row.versionId}
                      className={`console-log-item console-log-button console-${row.latestRequest?.status === "error" ? "error" : "success"}`}
                      onClick={() =>
                        setConsoleModal({
                          title: `RAG 下游 · ${row.versionName}`,
                          sections: [
                            { label: "Endpoint / Model", content: `${row.endpointUrl}\n${row.modelName}` },
                            { label: "最近一次下游请求", content: row.latestRequest?.query || "还没有发到下游" },
                            {
                              label: "最近一次下游响应",
                              content:
                                row.latestRequest?.error_message ||
                                row.latestRequest?.answer ||
                                "当前版本还没有被 Gateway 实际调用。",
                            },
                          ],
                        })
                      }
                    >
                      <div className="console-log-top">
                        <strong>{row.versionName}</strong>
                        <span>{row.requestCount} req</span>
                      </div>
                      <div className="console-log-path">{row.endpointUrl}</div>
                      <div className="console-log-meta">
                        <span>{row.modelName}</span>
                        <span>{row.latestRequest ? formatDate(row.latestRequest.created_at) : "还未触发"}</span>
                      </div>
                      <div className="console-log-message">
                        {row.latestRequest?.error_message ||
                          row.latestRequest?.answer ||
                          "当前版本还没有被 Gateway 实际调用。"}
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            </div>
            </div>
          </>
        )}
      </section>

      <section className="panel experiments-detail-panel">
        <SectionHeader
          title="实验详情"
          description="挑一个实验看当前分流、护栏和操作状态。"
          action={<RefreshButton onClick={() => void loadExperiments()} loading={loading} />}
        />
        <div className="summary-grid">
          <SummaryCard label="实验总数" value={experiments.length} accent="blue" />
          <SummaryCard label="运行中" value={runningCount} accent="green" />
          <SummaryCard label="可启动" value={restartableCount} accent="amber" />
        </div>

        <div className="toolbar stacked-on-mobile experiment-toolbar">
          <label className="inline-field grow">
            <span>实验</span>
            <select value={selectedExperimentId} onChange={(event) => setSelectedExperimentId(event.target.value)}>
              <option value="">请选择实验</option>
              {experiments.map((item) => (
                <option key={item.experiment_id} value={item.experiment_id}>
                  {item.experiment_name}
                </option>
              ))}
            </select>
          </label>
          <div className="button-row">
            <button className="primary-button" onClick={() => void handleStart()} disabled={!canStart}>
              <PlayCircle size={16} />
              <span>启动</span>
            </button>
            <button className="secondary-button" onClick={() => void handleStop()} disabled={!canStop}>
              <PauseCircle size={16} />
              <span>停止</span>
            </button>
          </div>
        </div>

        {error ? <div className="error-banner">{error}</div> : null}
        <div className="experiment-detail-scroll">
          {!selectedExperiment ? (
            <EmptyState title="还没有选中实验。" />
          ) : (
            <div className="detail-form">
              <div className="detail-grid">
                <div className="detail-block">
                  <span>状态</span>
                  <strong>
                    <StatusPill value={selectedExperiment.status} />
                  </strong>
                </div>
                <div className="detail-block">
                  <span>实验名称</span>
                  <strong>{selectedExperiment.experiment_name}</strong>
                </div>
                <div className="detail-block">
                  <span>对照版本</span>
                  <strong>
                    {selectedExperimentVersionMap.get(selectedExperiment.control_version_id)?.version_name || selectedExperiment.control_version_id}
                  </strong>
                </div>
                <div className="detail-block">
                  <span>实验版本</span>
                  <strong>
                    {selectedExperimentVersionMap.get(selectedExperiment.treatment_version_id)?.version_name || selectedExperiment.treatment_version_id}
                  </strong>
                </div>
                <div className="detail-block">
                  <span>control %</span>
                  <strong>{selectedExperiment.traffic_control}</strong>
                </div>
                <div className="detail-block">
                  <span>treatment %</span>
                  <strong>{selectedExperiment.traffic_treatment}</strong>
                </div>
                <div className="detail-block">
                  <span>错误率护栏</span>
                  <strong>{selectedExperiment.guardrails.max_error_rate}</strong>
                </div>
                <div className="detail-block">
                  <span>延迟倍率护栏</span>
                  <strong>{selectedExperiment.guardrails.max_latency_ratio}</strong>
                </div>
                <div className="detail-block">
                  <span>最小样本量</span>
                  <strong>{selectedExperiment.guardrails.min_sample_size}</strong>
                </div>
                <div className="detail-block">
                  <span>白名单</span>
                  <strong>{selectedExperiment.routing_rules.whitelist_user_ids.join(", ") || "-"}</strong>
                </div>
                <div className="detail-block">
                  <span>自动回滚</span>
                  <strong>{selectedExperiment.auto_rollback ? "开启" : "关闭"}</strong>
                </div>
                <div className="detail-block">
                  <span>创建时间</span>
                  <strong>{formatDate(selectedExperiment.created_at)}</strong>
                </div>
                <div className="detail-block">
                  <span>停止原因</span>
                  <strong>{selectedExperiment.stop_reason || "-"}</strong>
                </div>
              </div>
              <div className="panel-note">实验页现在只负责查看和启停。版本与 Prompt 请到“版本”页里通过弹窗修改。</div>
            </div>
          )}
        </div>
      </section>

      <section className="panel">
        <SectionHeader title="创建实验" description="最小化配置一个实验，立刻在左侧查看并操作。" />
        <div className="panel-note">
          默认按 90/10 起步，适合先观察 treatment 的延迟和错误率。
        </div>
        <form className="form-stack" onSubmit={handleCreateExperiment}>
          <label>
            <span>应用</span>
            <select
              value={form.app_id}
              onChange={(event) =>
                setForm((prev) => ({
                  ...prev,
                  app_id: event.target.value,
                  control_version_id: "",
                  treatment_version_id: "",
                }))
              }
            >
              <option value="">请选择应用</option>
              {apps.map((item) => (
                <option key={item.app_id} value={item.app_id}>
                  {item.app_name}
                </option>
              ))}
            </select>
          </label>

          <label>
            <span>实验名称</span>
            <input
              value={form.experiment_name}
              onChange={(event) => setForm((prev) => ({ ...prev, experiment_name: event.target.value }))}
              required
            />
          </label>

          <div className="field-grid">
            <label>
              <span>对照版本</span>
              <select
                value={form.control_version_id}
                onChange={(event) =>
                  setForm((prev) => {
                    const nextControlVersionId = event.target.value;
                    const nextTreatmentVersionId =
                      prev.treatment_version_id && prev.treatment_version_id !== nextControlVersionId
                        ? prev.treatment_version_id
                        : versionOptions.find((item) => item.value !== nextControlVersionId)?.value || "";
                    return {
                      ...prev,
                      control_version_id: nextControlVersionId,
                      treatment_version_id: nextTreatmentVersionId,
                    };
                  })
                }
              >
                <option value="">请选择</option>
                {versionOptions.map((item) => (
                  <option key={item.value} value={item.value}>
                    {item.label}
                  </option>
                ))}
              </select>
            </label>

            <label>
              <span>实验版本</span>
              <select
                value={form.treatment_version_id}
                onChange={(event) => setForm((prev) => ({ ...prev, treatment_version_id: event.target.value }))}
              >
                <option value="">请选择</option>
                {treatmentOptions.map((item) => (
                  <option key={item.value} value={item.value}>
                    {item.label}
                  </option>
                ))}
              </select>
            </label>
          </div>

          <div className="field-grid compact-grid">
            <label>
              <span>control %</span>
              <input
                type="number"
                value={form.traffic_control}
                onChange={(event) => setForm((prev) => ({ ...prev, traffic_control: event.target.value }))}
              />
            </label>
            <label>
              <span>treatment %</span>
              <input
                type="number"
                value={form.traffic_treatment}
                onChange={(event) => setForm((prev) => ({ ...prev, traffic_treatment: event.target.value }))}
              />
            </label>
            <label>
              <span>max_error_rate</span>
              <input
                type="number"
                step="0.01"
                value={form.max_error_rate}
                onChange={(event) => setForm((prev) => ({ ...prev, max_error_rate: event.target.value }))}
              />
            </label>
            <label>
              <span>max_latency_ratio</span>
              <input
                type="number"
                step="0.1"
                value={form.max_latency_ratio}
                onChange={(event) => setForm((prev) => ({ ...prev, max_latency_ratio: event.target.value }))}
              />
            </label>
          </div>

          <label>
            <span>最小样本量</span>
            <input
              type="number"
              value={form.min_sample_size}
              onChange={(event) => setForm((prev) => ({ ...prev, min_sample_size: event.target.value }))}
            />
          </label>

          <label>
            <span>白名单用户</span>
            <input
              value={form.whitelist_user_ids}
              onChange={(event) => setForm((prev) => ({ ...prev, whitelist_user_ids: event.target.value }))}
            />
          </label>

          {createBlockedReason ? <div className="panel-note">{createBlockedReason}</div> : null}

          <button className="primary-button" type="submit" disabled={submitting || Boolean(createBlockedReason)}>
            <Plus size={16} />
            <span>{submitting ? "创建中..." : "创建实验"}</span>
          </button>
        </form>
      </section>

      {consoleModal ? (
        <div className="console-modal-backdrop" onClick={() => setConsoleModal(null)}>
          <div className="console-modal" onClick={(event) => event.stopPropagation()}>
            <div className="console-modal-header">
              <h3>{consoleModal.title}</h3>
              <button className="secondary-button" onClick={() => setConsoleModal(null)}>
                关闭
              </button>
            </div>
            <div className="console-modal-body">
              {consoleModal.sections.map((section) => (
                <div key={section.label} className="console-modal-section">
                  <span>{section.label}</span>
                  <pre>{section.content}</pre>
                </div>
              ))}
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
