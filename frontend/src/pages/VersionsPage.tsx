import { CheckCircle2, Plus } from "lucide-react";
import { FormEvent, useEffect, useMemo, useState } from "react";
import { adminApi } from "../lib/api";
import type { AppItem, VersionItem } from "../types";
import { EmptyState, RefreshButton, SectionHeader, SummaryCard, formatDate } from "../components/Shared";

const initialVersionForm = {
  version_name: "",
  base_version_id: "",
  prompt_template: "你是一个专业助手，请基于已知信息给出清晰回答。",
  model_name: "mock-model",
  endpoint_url: "mock://llm",
  temperature: "0.2",
  top_p: "0.9",
  max_tokens: "1024",
  rag_enabled: true,
  top_k: "5",
  created_by: "operator",
};

const initialVersionDetailForm = {
  version_name: "",
  base_version_id: "",
  prompt_template: "",
  model_name: "",
  endpoint_url: "",
  temperature: "0.2",
  top_p: "0.9",
  max_tokens: "1024",
  rag_enabled: false,
  top_k: "5",
};

export function VersionsPage() {
  const [apps, setApps] = useState<AppItem[]>([]);
  const [selectedAppId, setSelectedAppId] = useState("");
  const [versions, setVersions] = useState<VersionItem[]>([]);
  const [selectedVersionId, setSelectedVersionId] = useState("");
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [savingVersion, setSavingVersion] = useState(false);
  const [promotingVersionId, setPromotingVersionId] = useState("");
  const [error, setError] = useState("");
  const [form, setForm] = useState(initialVersionForm);
  const [detailForm, setDetailForm] = useState(initialVersionDetailForm);
  const [isVersionModalOpen, setIsVersionModalOpen] = useState(false);
  const selectedApp = apps.find((item) => item.app_id === selectedAppId);
  const selectedVersion = versions.find((item) => item.version_id === selectedVersionId) ?? null;

  async function loadApps() {
    const result = await adminApi.listApps();
    setApps(result.items);
    if (!selectedAppId && result.items[0]) {
      setSelectedAppId(result.items[0].app_id);
    }
  }

  async function loadVersions(appId: string) {
    if (!appId) {
      setVersions([]);
      setSelectedVersionId("");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const result = await adminApi.listVersions(appId);
      setVersions(result.items);
      setSelectedVersionId((prev) => {
        if (prev && result.items.some((item) => item.version_id === prev)) {
          return prev;
        }
        return result.items[0]?.version_id || "";
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "版本加载失败");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadApps();
  }, []);

  useEffect(() => {
    void loadVersions(selectedAppId);
  }, [selectedAppId]);

  const baseVersionOptions = useMemo(
    () => versions.map((item) => ({ label: item.version_name, value: item.version_id })),
    [versions],
  );
  const detailBaseVersionOptions = useMemo(
    () => versions
      .filter((item) => item.version_id !== selectedVersionId)
      .map((item) => ({ label: item.version_name, value: item.version_id })),
    [selectedVersionId, versions],
  );
  const stableCount = versions.filter((item) => item.status === "stable").length;
  const draftCount = versions.filter((item) => item.status === "draft").length;
  const ragCount = versions.filter((item) => item.rag_enabled).length;
  const versionDetailBlockedReason = !selectedVersion
    ? "请先选择版本"
    : !detailForm.version_name.trim()
      ? "版本名称不能为空"
      : !detailForm.prompt_template.trim()
        ? "Prompt 模板不能为空"
        : !detailForm.model_name.trim()
          ? "模型名不能为空"
          : !detailForm.endpoint_url.trim()
            ? "模型地址不能为空"
            : "";

  useEffect(() => {
    if (!form.base_version_id) {
      return;
    }
    const baseVersion = versions.find((item) => item.version_id === form.base_version_id);
    if (!baseVersion) {
      return;
    }
    setForm((prev) => ({
      ...prev,
      prompt_template: baseVersion.prompt_template,
      model_name: baseVersion.model_name,
      endpoint_url: baseVersion.endpoint_url,
      temperature: String(baseVersion.temperature),
      top_p: String(baseVersion.top_p),
      max_tokens: String(baseVersion.max_tokens),
      rag_enabled: baseVersion.rag_enabled,
      top_k: String((baseVersion.rag_config.top_k as number | undefined) ?? 5),
    }));
  }, [form.base_version_id, versions]);

  useEffect(() => {
    if (!selectedVersion) {
      setDetailForm(initialVersionDetailForm);
      setIsVersionModalOpen(false);
      return;
    }
    setDetailForm({
      version_name: selectedVersion.version_name,
      base_version_id: selectedVersion.base_version_id || "",
      prompt_template: selectedVersion.prompt_template,
      model_name: selectedVersion.model_name,
      endpoint_url: selectedVersion.endpoint_url,
      temperature: String(selectedVersion.temperature),
      top_p: String(selectedVersion.top_p),
      max_tokens: String(selectedVersion.max_tokens),
      rag_enabled: selectedVersion.rag_enabled,
      top_k: String((selectedVersion.rag_config.top_k as number | undefined) ?? 5),
    });
  }, [selectedVersion]);

  function openVersionModal() {
    if (!selectedVersion) {
      return;
    }
    setIsVersionModalOpen(true);
  }

  function closeVersionModal() {
    setIsVersionModalOpen(false);
    if (!selectedVersion) {
      setDetailForm(initialVersionDetailForm);
      return;
    }
    setDetailForm({
      version_name: selectedVersion.version_name,
      base_version_id: selectedVersion.base_version_id || "",
      prompt_template: selectedVersion.prompt_template,
      model_name: selectedVersion.model_name,
      endpoint_url: selectedVersion.endpoint_url,
      temperature: String(selectedVersion.temperature),
      top_p: String(selectedVersion.top_p),
      max_tokens: String(selectedVersion.max_tokens),
      rag_enabled: selectedVersion.rag_enabled,
      top_k: String((selectedVersion.rag_config.top_k as number | undefined) ?? 5),
    });
  }

  async function handleCreateVersion(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedAppId) {
      return;
    }
    setSubmitting(true);
    setError("");
    try {
      await adminApi.createVersion(selectedAppId, {
        version_name: form.version_name,
        base_version_id: form.base_version_id || null,
        prompt_template: form.prompt_template,
        model_name: form.model_name,
        endpoint_url: form.endpoint_url,
        temperature: Number(form.temperature),
        top_p: Number(form.top_p),
        max_tokens: Number(form.max_tokens),
        rag_enabled: form.rag_enabled,
        rag_config: {
          vector_db: "Milvus",
          top_k: Number(form.top_k),
          reranker_enabled: false,
        },
        output_schema: { type: "markdown" },
        created_by: form.created_by,
      });
      setForm(initialVersionForm);
      await loadVersions(selectedAppId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "版本创建失败");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleSaveVersion(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedVersionId || versionDetailBlockedReason) {
      setError(versionDetailBlockedReason || "版本保存失败");
      return;
    }
    setSavingVersion(true);
    setError("");
    try {
      await adminApi.updateVersion(selectedVersionId, {
        version_name: detailForm.version_name.trim(),
        base_version_id: detailForm.base_version_id || null,
        prompt_template: detailForm.prompt_template,
        model_name: detailForm.model_name.trim(),
        endpoint_url: detailForm.endpoint_url.trim(),
        temperature: Number(detailForm.temperature),
        top_p: Number(detailForm.top_p),
        max_tokens: Number(detailForm.max_tokens),
        rag_enabled: detailForm.rag_enabled,
        rag_config: {
          vector_db: "Milvus",
          top_k: Number(detailForm.top_k),
          reranker_enabled: false,
        },
        output_schema: selectedVersion?.output_schema || { type: "markdown" },
      });
      await loadVersions(selectedAppId);
      setIsVersionModalOpen(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "版本保存失败");
    } finally {
      setSavingVersion(false);
    }
  }

  async function handleVersionStatusChange(versionId: string, nextStatus: "stable" | "draft") {
    if (!selectedAppId) {
      return;
    }
    const currentVersion = versions.find((item) => item.version_id === versionId);
    if (!currentVersion || currentVersion.status === nextStatus) {
      return;
    }
    const currentStable = versions.find((item) => item.status === "stable" && item.version_id !== versionId);
    if (
      nextStatus === "stable" &&
      currentStable &&
      !window.confirm(`当前已经有 Stable 版本「${currentStable.version_name}」，继续会替换它。确认继续吗？`)
    ) {
      return;
    }
    const previousVersions = versions;
    const previousApps = apps;
    setPromotingVersionId(versionId);
    setError("");
    try {
      setVersions((current) => {
        if (nextStatus === "stable") {
          return current.map((item) => ({
            ...item,
            status: item.version_id === versionId ? "stable" : "draft",
          }));
        }
        return current.map((item) => ({
          ...item,
          status: item.version_id === versionId ? "draft" : item.status,
        }));
      });
      setApps((current) =>
        current.map((item) =>
          item.app_id === selectedAppId
            ? {
                ...item,
                stable_version_id:
                  nextStatus === "stable"
                    ? versionId
                    : item.stable_version_id === versionId
                      ? null
                      : item.stable_version_id,
              }
            : item,
        ),
      );
      await adminApi.setVersionStatus(versionId, nextStatus, "operator");
      await Promise.all([loadVersions(selectedAppId), loadApps()]);
    } catch (err) {
      setVersions(previousVersions);
      setApps(previousApps);
      setError(err instanceof Error ? err.message : "版本状态更新失败");
    } finally {
      setPromotingVersionId("");
    }
  }

  return (
    <div className="page-grid two-columns">
      <section className="panel">
        <SectionHeader
          title="版本列表"
          description="按应用查看版本，确认当前稳定版和草稿版。"
          action={<RefreshButton onClick={() => void loadVersions(selectedAppId)} loading={loading} />}
        />
        <div className="toolbar versions-toolbar">
          <label className="inline-field versions-filter">
            <span>应用</span>
            <select value={selectedAppId} onChange={(event) => setSelectedAppId(event.target.value)}>
              <option value="">请选择应用</option>
              {apps.map((item) => (
                <option key={item.app_id} value={item.app_id}>
                  {item.app_name}
                </option>
              ))}
            </select>
          </label>
        </div>
        <div className="summary-grid">
          <div className="summary-card summary-slate current-app-card">
            <span>当前应用</span>
            <strong className="current-app-name" title={selectedApp?.app_name || "-"}>
              {selectedApp?.app_name || "-"}
            </strong>
            <p className="current-app-meta">
              {selectedApp ? `${selectedApp.app_type} · ${selectedApp.owner}` : "请选择应用"}
            </p>
            {selectedApp ? <code className="current-app-id">{selectedApp.app_id}</code> : null}
          </div>
          <SummaryCard label="稳定版本" value={stableCount} accent="green" />
          <SummaryCard label="草稿版本" value={draftCount} accent="blue" />
          <SummaryCard label="RAG 版本" value={ragCount} accent="amber" />
        </div>
        {error ? <div className="error-banner">{error}</div> : null}
        {versions.length === 0 && !loading ? (
          <EmptyState title="当前应用还没有版本。" />
        ) : (
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>版本</th>
                  <th>模型</th>
                  <th>RAG</th>
                  <th>状态</th>
                  <th>创建人</th>
                  <th>创建时间</th>
                </tr>
              </thead>
              <tbody>
                {versions.map((item) => (
                  <tr
                    key={item.version_id}
                    className={item.version_id === selectedVersionId ? "table-row-selected" : ""}
                    onClick={() => setSelectedVersionId(item.version_id)}
                  >
                    <td>
                      <button className="table-entity-button" type="button">
                        <div className="cell-title">{item.version_name}</div>
                        <div className="cell-subtitle">{item.version_id}</div>
                      </button>
                    </td>
                    <td>{item.model_name}</td>
                    <td>{item.rag_enabled ? "开启" : "关闭"}</td>
                    <td>
                      <select
                        className="status-select"
                        value={item.status}
                        disabled={promotingVersionId === item.version_id}
                        onClick={(event) => event.stopPropagation()}
                        onChange={(event) =>
                          void handleVersionStatusChange(item.version_id, event.target.value as "stable" | "draft")
                        }
                      >
                        <option value="stable">Stable</option>
                        <option value="draft">Draft</option>
                      </select>
                    </td>
                    <td>{item.created_by}</td>
                    <td>{formatDate(item.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section className="panel">
        <SectionHeader
          title={selectedVersion ? "版本详情" : "创建版本"}
          description={selectedVersion ? "在这里查看当前版本；点击按钮后用弹窗修改 Prompt 和版本配置。" : "先选应用，再登记 prompt、模型和 RAG 参数。"}
        />
        {selectedVersion ? (
          <>
            <div className="detail-stack">
              <div className="panel-note">当前选中 `{selectedVersion.version_name}`。Prompt 和版本配置改为通过弹窗编辑。</div>
              <div className="detail-grid">
                <div className="detail-block">
                  <span>版本名称</span>
                  <strong>{selectedVersion.version_name}</strong>
                </div>
                <div className="detail-block">
                  <span>状态</span>
                  <strong>{selectedVersion.status}</strong>
                </div>
                <div className="detail-block">
                  <span>基线版本</span>
                  <strong>
                    {versions.find((item) => item.version_id === selectedVersion.base_version_id)?.version_name ||
                      selectedVersion.base_version_id ||
                      "不复制"}
                  </strong>
                </div>
                <div className="detail-block">
                  <span>模型名</span>
                  <strong>{selectedVersion.model_name}</strong>
                </div>
                <div className="detail-block">
                  <span>模型地址</span>
                  <strong>{selectedVersion.endpoint_url}</strong>
                </div>
                <div className="detail-block">
                  <span>Prompt 模板</span>
                  <strong>{selectedVersion.prompt_template}</strong>
                </div>
              </div>
            </div>
            <div className="detail-actions">
              <button className="secondary-button" type="button" onClick={() => setSelectedVersionId("")}>
                返回创建
              </button>
              <button className="primary-button" type="button" onClick={openVersionModal}>
                <CheckCircle2 size={16} />
                <span>弹窗修改</span>
              </button>
            </div>
          </>
        ) : (
          <>
            <div className="panel-note">
              选择“基线版本”后，会自动带出它的核心配置，适合做 prompt 或模型迭代。
            </div>
            <form className="form-stack" onSubmit={handleCreateVersion}>
              <label>
                <span>版本名称</span>
                <input
                  value={form.version_name}
                  onChange={(event) => setForm((prev) => ({ ...prev, version_name: event.target.value }))}
                  required
                />
              </label>

              <label>
                <span>基线版本</span>
                <select
                  value={form.base_version_id}
                  onChange={(event) => setForm((prev) => ({ ...prev, base_version_id: event.target.value }))}
                >
                  <option value="">不复制</option>
                  {baseVersionOptions.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </label>

              <label>
                <span>Prompt 模板</span>
                <textarea
                  rows={4}
                  value={form.prompt_template}
                  onChange={(event) => setForm((prev) => ({ ...prev, prompt_template: event.target.value }))}
                />
              </label>

              <div className="field-grid">
                <label>
                  <span>模型名</span>
                  <input
                    value={form.model_name}
                    onChange={(event) => setForm((prev) => ({ ...prev, model_name: event.target.value }))}
                  />
                </label>
                <label>
                  <span>创建人</span>
                  <input
                    value={form.created_by}
                    onChange={(event) => setForm((prev) => ({ ...prev, created_by: event.target.value }))}
                  />
                </label>
              </div>

              <label>
                <span>模型地址</span>
                <input
                  value={form.endpoint_url}
                  onChange={(event) => setForm((prev) => ({ ...prev, endpoint_url: event.target.value }))}
                />
              </label>

              <div className="field-grid compact-grid">
                <label>
                  <span>temperature</span>
                  <input
                    type="number"
                    step="0.1"
                    value={form.temperature}
                    onChange={(event) => setForm((prev) => ({ ...prev, temperature: event.target.value }))}
                  />
                </label>
                <label>
                  <span>top_p</span>
                  <input
                    type="number"
                    step="0.1"
                    value={form.top_p}
                    onChange={(event) => setForm((prev) => ({ ...prev, top_p: event.target.value }))}
                  />
                </label>
                <label>
                  <span>max_tokens</span>
                  <input
                    type="number"
                    value={form.max_tokens}
                    onChange={(event) => setForm((prev) => ({ ...prev, max_tokens: event.target.value }))}
                  />
                </label>
                <label>
                  <span>top_k</span>
                  <input
                    type="number"
                    value={form.top_k}
                    onChange={(event) => setForm((prev) => ({ ...prev, top_k: event.target.value }))}
                  />
                </label>
              </div>

              <label className="checkbox-field">
                <input
                  type="checkbox"
                  checked={form.rag_enabled}
                  onChange={(event) => setForm((prev) => ({ ...prev, rag_enabled: event.target.checked }))}
                />
                <span>启用 RAG</span>
              </label>

              <button className="primary-button" type="submit" disabled={submitting || !selectedAppId}>
                <Plus size={16} />
                <span>{submitting ? "创建中..." : "创建版本"}</span>
              </button>
            </form>
          </>
        )}
      </section>

      {selectedVersion && isVersionModalOpen ? (
        <div className="console-modal-backdrop" onClick={closeVersionModal}>
          <div className="console-modal" onClick={(event) => event.stopPropagation()}>
            <div className="console-modal-header">
              <div>
                <h3>修改版本</h3>
                <p>{selectedVersion.version_name} 的 Prompt 和版本配置会直接同步到后端。</p>
              </div>
              <button className="secondary-button" type="button" onClick={closeVersionModal}>
                关闭
              </button>
            </div>
            <form className="console-modal-body form-stack" onSubmit={handleSaveVersion}>
              <label>
                <span>版本名称</span>
                <input
                  value={detailForm.version_name}
                  onChange={(event) => setDetailForm((prev) => ({ ...prev, version_name: event.target.value }))}
                  required
                />
              </label>

              <label>
                <span>基线版本</span>
                <select
                  value={detailForm.base_version_id}
                  onChange={(event) => setDetailForm((prev) => ({ ...prev, base_version_id: event.target.value }))}
                >
                  <option value="">不复制</option>
                  {detailBaseVersionOptions.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </label>

              <label>
                <span>Prompt 模板</span>
                <textarea
                  rows={10}
                  value={detailForm.prompt_template}
                  onChange={(event) => setDetailForm((prev) => ({ ...prev, prompt_template: event.target.value }))}
                />
              </label>

              <div className="field-grid">
                <label>
                  <span>模型名</span>
                  <input
                    value={detailForm.model_name}
                    onChange={(event) => setDetailForm((prev) => ({ ...prev, model_name: event.target.value }))}
                  />
                </label>
                <label>
                  <span>模型地址</span>
                  <input
                    value={detailForm.endpoint_url}
                    onChange={(event) => setDetailForm((prev) => ({ ...prev, endpoint_url: event.target.value }))}
                  />
                </label>
              </div>

              <div className="field-grid compact-grid">
                <label>
                  <span>temperature</span>
                  <input
                    type="number"
                    step="0.1"
                    value={detailForm.temperature}
                    onChange={(event) => setDetailForm((prev) => ({ ...prev, temperature: event.target.value }))}
                  />
                </label>
                <label>
                  <span>top_p</span>
                  <input
                    type="number"
                    step="0.1"
                    value={detailForm.top_p}
                    onChange={(event) => setDetailForm((prev) => ({ ...prev, top_p: event.target.value }))}
                  />
                </label>
                <label>
                  <span>max_tokens</span>
                  <input
                    type="number"
                    value={detailForm.max_tokens}
                    onChange={(event) => setDetailForm((prev) => ({ ...prev, max_tokens: event.target.value }))}
                  />
                </label>
                <label>
                  <span>top_k</span>
                  <input
                    type="number"
                    value={detailForm.top_k}
                    onChange={(event) => setDetailForm((prev) => ({ ...prev, top_k: event.target.value }))}
                  />
                </label>
              </div>

              <label className="checkbox-field">
                <input
                  type="checkbox"
                  checked={detailForm.rag_enabled}
                  onChange={(event) => setDetailForm((prev) => ({ ...prev, rag_enabled: event.target.checked }))}
                />
                <span>启用 RAG</span>
              </label>

              {versionDetailBlockedReason ? <div className="panel-note">{versionDetailBlockedReason}</div> : null}

              <div className="detail-actions">
                <button className="secondary-button" type="button" onClick={closeVersionModal}>
                  取消
                </button>
                <button className="primary-button" type="submit" disabled={savingVersion || Boolean(versionDetailBlockedReason)}>
                  <CheckCircle2 size={16} />
                  <span>{savingVersion ? "保存中..." : "保存版本"}</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      ) : null}
    </div>
  );
}
