import { Check, X } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { adminApi } from "../lib/api";
import type { ApprovalLogItem, ApprovalResult, DecisionSnapshot, ExpandRecommendation, ExperimentItem } from "../types";
import { EmptyState, RefreshButton, SectionHeader, StatusPill, SummaryCard, formatDate } from "../components/Shared";

function parseSplit(split: string | null | undefined) {
  if (!split) {
    return { control: 90, treatment: 10 };
  }
  const [control, treatment] = split.split("/").map((value) => Number(value));
  return { control: control || 90, treatment: treatment || 10 };
}

export function ApprovalsPage() {
  const [experiments, setExperiments] = useState<ExperimentItem[]>([]);
  const [selectedExperimentId, setSelectedExperimentId] = useState("");
  const [recommendation, setRecommendation] = useState<ExpandRecommendation | null>(null);
  const [decision, setDecision] = useState<DecisionSnapshot | null>(null);
  const [logs, setLogs] = useState<ApprovalLogItem[]>([]);
  const [lastApprovalResult, setLastApprovalResult] = useState<ApprovalResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [approvalReason, setApprovalReason] = useState("指标稳定，批准扩大实验流量");

  async function loadExperiments() {
    const result = await adminApi.listExperiments();
    setExperiments(result.items);
    if (!selectedExperimentId && result.items[0]) {
      setSelectedExperimentId(result.items[0].experiment_id);
    }
  }

  async function loadApprovalData(experimentId: string) {
    if (!experimentId) {
      setRecommendation(null);
      setLogs([]);
      return;
    }
    setLoading(true);
    setError("");
    try {
      const [rec, decisionResult, logResult] = await Promise.all([
        adminApi.getExpandRecommendation(experimentId),
        adminApi.getDecision(experimentId),
        adminApi.listApprovalLogs(experimentId),
      ]);
      setRecommendation(rec);
      setDecision(decisionResult);
      setLogs(logResult.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : "审批数据加载失败");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadExperiments();
  }, []);

  useEffect(() => {
    void loadApprovalData(selectedExperimentId);
  }, [selectedExperimentId]);

  const selectedExperiment = experiments.find((item) => item.experiment_id === selectedExperimentId) ?? null;
  const recommendedSplit = useMemo(
    () => parseSplit(recommendation?.recommended_split ?? recommendation?.current_split),
    [recommendation],
  );
  const approvalEnabled = recommendation?.decision_type === "recommend_expand";

  async function handleApprove(approved: boolean) {
    if (!selectedExperimentId || !recommendation) {
      return;
    }
    setSubmitting(true);
    setError("");
    try {
      const result = await adminApi.approveExpand(selectedExperimentId, {
        operator: "console-operator",
        approved,
        approved_split: approved ? recommendedSplit : undefined,
        approval_reason: approvalReason,
      });
      setLastApprovalResult(result);
      await loadExperiments();
      await adminApi.recomputeDecision(selectedExperimentId, "console-operator");
      await loadApprovalData(selectedExperimentId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "审批提交失败");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="page-grid approvals-layout">
      <section className="panel">
        <SectionHeader
          title="扩量审批"
          description="根据系统建议确认是否扩大 treatment 流量。"
          action={<RefreshButton onClick={() => void loadApprovalData(selectedExperimentId)} loading={loading} />}
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

        {recommendation ? (
          <>
            <div className="summary-grid">
              <SummaryCard label="当前流量" value={recommendation.current_split} accent="slate" />
              <SummaryCard label="建议流量" value={recommendation.recommended_split || "-"} accent="blue" />
              <SummaryCard label="决策类型" value={recommendation.decision_type} accent="amber" />
              <SummaryCard label="风险等级" value={recommendation.risk_level} accent="green" />
            </div>

            {decision ? (
              <div className="detail-block">
                <span>Decision 展示</span>
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
              </div>
            ) : null}

            {lastApprovalResult ? (
              <div className="detail-block">
                <span>审批后的流量结果</span>
                <strong>
                  {lastApprovalResult.old_split.control}/{lastApprovalResult.old_split.treatment}
                  {" -> "}
                  {lastApprovalResult.new_split.control}/{lastApprovalResult.new_split.treatment}
                </strong>
                <div className="activity-meta">
                  <span>{lastApprovalResult.status}</span>
                  <span>{lastApprovalResult.approved_by}</span>
                  <span>{formatDate(lastApprovalResult.approved_at)}</span>
                </div>
              </div>
            ) : null}

            <div className="governance-card">
              <div className="governance-card-header">
                <div>
                  <h3>当前建议</h3>
                  <p>
                    {selectedExperiment?.experiment_name || "-"} · {selectedExperiment?.app_id || "-"}
                  </p>
                </div>
                <StatusPill value={recommendation.risk_level} />
              </div>

              <div className="reason-list">
                {(recommendation.reasons.length > 0 ? recommendation.reasons : ["keep_observing"]).map((reason) => (
                  <span key={reason} className="reason-chip">
                    {reason}
                  </span>
                ))}
              </div>

              <label>
                <span>审批说明</span>
                <textarea
                  rows={4}
                  value={approvalReason}
                  onChange={(event) => setApprovalReason(event.target.value)}
                />
              </label>

              <div className="button-row">
                <button
                  className="primary-button"
                  onClick={() => void handleApprove(true)}
                  disabled={!approvalEnabled || submitting}
                >
                  <Check size={16} />
                  <span>{submitting ? "提交中..." : "批准扩量"}</span>
                </button>
                <button
                  className="secondary-button"
                  onClick={() => void handleApprove(false)}
                  disabled={!approvalEnabled || submitting}
                >
                  <X size={16} />
                  <span>驳回</span>
                </button>
              </div>
            </div>
          </>
        ) : (
          <EmptyState title="请选择实验查看扩量建议。" />
        )}

        {error ? <div className="error-banner">{error}</div> : null}
      </section>

      <section className="panel">
        <SectionHeader title="审批日志" description="保留所有扩量审批记录，方便审计与复盘。" />
        {logs.length === 0 ? (
          <EmptyState title="当前实验还没有审批记录。" />
        ) : (
          <div className="activity-list">
            {logs.map((item) => (
              <div key={item.approval_id} className="activity-item">
                <div className="activity-row">
                  <strong>{item.approval_id}</strong>
                  <StatusPill value={item.status} />
                </div>
                <div className="activity-meta">
                  <span>{item.current_split} → {item.recommended_split}</span>
                  <span>{item.approved_by}</span>
                  <span>{formatDate(item.created_at)}</span>
                </div>
                <p>{item.approval_reason || "-"}</p>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
