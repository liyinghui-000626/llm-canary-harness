import { ShieldAlert } from "lucide-react";
import { useEffect, useState } from "react";
import { adminApi } from "../lib/api";
import type { ExperimentItem, RollbackLogItem, RollbackResult, VersionItem } from "../types";
import { EmptyState, RefreshButton, SectionHeader, StatusPill, SummaryCard, formatDate } from "../components/Shared";

export function RollbackPage() {
  const [experiments, setExperiments] = useState<ExperimentItem[]>([]);
  const [selectedExperimentId, setSelectedExperimentId] = useState("");
  const [versions, setVersions] = useState<VersionItem[]>([]);
  const [logs, setLogs] = useState<RollbackLogItem[]>([]);
  const [lastRollbackResult, setLastRollbackResult] = useState<RollbackResult | null>(null);
  const [rollbackReason, setRollbackReason] = useState("manual rollback due to latency spike");
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  async function loadExperiments() {
    const result = await adminApi.listExperiments();
    setExperiments(result.items);
    if (!selectedExperimentId && result.items[0]) {
      setSelectedExperimentId(result.items[0].experiment_id);
    }
  }

  async function loadRollbackLogs(experimentId: string) {
    if (!experimentId) {
      setLogs([]);
      return;
    }
    setLoading(true);
    setError("");
    try {
      const result = await adminApi.listRollbackLogs(experimentId);
      setLogs(result.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : "回滚日志加载失败");
    } finally {
      setLoading(false);
    }
  }

  async function loadVersions(appId: string) {
    if (!appId) {
      setVersions([]);
      return;
    }
    try {
      const result = await adminApi.listVersions(appId);
      setVersions(result.items);
    } catch {
      setVersions([]);
    }
  }

  useEffect(() => {
    void loadExperiments();
  }, []);

  useEffect(() => {
    void loadRollbackLogs(selectedExperimentId);
  }, [selectedExperimentId]);

  const selectedExperiment = experiments.find((item) => item.experiment_id === selectedExperimentId) ?? null;
  useEffect(() => {
    void loadVersions(selectedExperiment?.app_id || "");
  }, [selectedExperiment?.app_id]);

  const rollbackCount = logs.length;
  const autoCount = logs.filter((item) => item.operator === "system").length;
  const manualCount = rollbackCount - autoCount;
  const controlVersion = versions.find((item) => item.version_id === selectedExperiment?.control_version_id) ?? null;
  const treatmentVersion = versions.find((item) => item.version_id === selectedExperiment?.treatment_version_id) ?? null;

  async function handleRollback() {
    if (!selectedExperimentId) {
      return;
    }
    setSubmitting(true);
    setError("");
    try {
      const result = await adminApi.rollbackExperiment(selectedExperimentId, "console-operator", rollbackReason);
      setLastRollbackResult(result);
      await loadExperiments();
      await loadRollbackLogs(selectedExperimentId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "手动回滚失败");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="page-grid approvals-layout">
      <section className="panel">
        <SectionHeader
          title="回滚操作"
          description="当实验出现明显风险时，手动触发回滚并留痕。"
          action={<RefreshButton onClick={() => void loadRollbackLogs(selectedExperimentId)} loading={loading} />}
        />

        <div className="toolbar stacked-on-mobile">
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
        </div>

        <div className="summary-grid">
          <SummaryCard label="实验状态" value={selectedExperiment?.status || "-"} accent="slate" />
          <SummaryCard label="回滚总数" value={rollbackCount} accent="blue" />
          <SummaryCard label="自动回滚" value={autoCount} accent="amber" />
          <SummaryCard label="手动回滚" value={manualCount} accent="green" />
        </div>

        {lastRollbackResult ? (
          <div className="detail-block">
            <span>最近一次回滚结果</span>
            <strong>
              {lastRollbackResult.from_version_id}
              {" -> "}
              {lastRollbackResult.to_version_id}
            </strong>
            <div className="activity-meta">
              <span>{lastRollbackResult.status}</span>
              <span>{formatDate(lastRollbackResult.rollback_at)}</span>
            </div>
            <p>{lastRollbackResult.reason}</p>
          </div>
        ) : null}

        <div className="governance-card">
          <div className="governance-card-header">
            <div>
              <h3>手动回滚</h3>
              <p className="rollback-route">
                <span className="route-target">
                  {controlVersion?.version_name || selectedExperiment?.control_version_id || "-"}
                </span>
                <span className="route-arrow">←</span>
                <span className="route-source">
                  {treatmentVersion?.version_name || selectedExperiment?.treatment_version_id || "-"}
                </span>
              </p>
              <div className="activity-meta">
                <span>{selectedExperiment?.control_version_id || "-"}</span>
                <span>{selectedExperiment?.treatment_version_id || "-"}</span>
              </div>
            </div>
            {selectedExperiment ? <StatusPill value={selectedExperiment.status} /> : null}
          </div>

          <label>
            <span>回滚原因</span>
            <textarea
              rows={4}
              value={rollbackReason}
              onChange={(event) => setRollbackReason(event.target.value)}
            />
          </label>

          <button
            className="primary-button destructive-button"
            onClick={() => void handleRollback()}
            disabled={selectedExperiment?.status !== "running" || submitting}
          >
            <ShieldAlert size={16} />
            <span>{submitting ? "回滚中..." : "执行回滚"}</span>
          </button>
        </div>

        {error ? <div className="error-banner">{error}</div> : null}
      </section>

      <section className="panel">
        <SectionHeader title="回滚日志" description="记录自动回滚和人工回滚，便于对照原因与结果。" />
        {logs.length === 0 ? (
          <EmptyState title="当前实验还没有回滚记录。" />
        ) : (
          <div className="activity-list">
            {logs.map((item) => (
              <div key={item.rollback_id} className="activity-item danger-activity">
                <div className="activity-row">
                  <strong>{item.rollback_id}</strong>
                  <StatusPill value={item.status} />
                </div>
                <div className="activity-meta">
                  <span>{item.from_version_id} → {item.to_version_id}</span>
                  <span>{item.operator}</span>
                  <span>{formatDate(item.created_at)}</span>
                </div>
                <p>{item.reason}</p>
                <div className="activity-meta">
                  <span>trigger_rule: {item.trigger_rule || "-"}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
