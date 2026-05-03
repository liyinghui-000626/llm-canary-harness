import { Plus } from "lucide-react";
import { FormEvent, useEffect, useState } from "react";
import { adminApi } from "../lib/api";
import type { AppItem } from "../types";
import { EmptyState, RefreshButton, SectionHeader, StatusPill, SummaryCard, formatDate } from "../components/Shared";

const initialForm = {
  app_name: "",
  app_type: "RAG",
  description: "",
  owner: "",
  business_scene: "",
};

export function AppsPage() {
  const [apps, setApps] = useState<AppItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [form, setForm] = useState(initialForm);
  const activeCount = apps.filter((item) => item.status === "active").length;
  const runningCount = apps.filter((item) => item.running_experiment_id).length;

  async function loadApps() {
    setLoading(true);
    setError("");
    try {
      const result = await adminApi.listApps();
      setApps(result.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : "应用加载失败");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadApps();
  }, []);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError("");
    try {
      await adminApi.createApp(form);
      setForm(initialForm);
      await loadApps();
    } catch (err) {
      setError(err instanceof Error ? err.message : "应用创建失败");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="page-grid two-columns">
      <section className="panel">
        <SectionHeader
          title="应用列表"
          description="查看当前纳入 Canary 治理的应用。"
          action={<RefreshButton onClick={() => void loadApps()} loading={loading} />}
        />
        <div className="summary-grid">
          <SummaryCard label="应用总数" value={apps.length} accent="blue" />
          <SummaryCard label="活跃应用" value={activeCount} accent="green" />
          <SummaryCard label="运行中实验" value={runningCount} accent="amber" />
        </div>
        {error ? <div className="error-banner">{error}</div> : null}
        {apps.length === 0 && !loading ? (
          <EmptyState title="还没有应用，先在右侧创建一个。" />
        ) : (
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>应用</th>
                  <th>负责人</th>
                  <th>稳定版本</th>
                  <th>运行实验</th>
                  <th>状态</th>
                  <th>创建时间</th>
                </tr>
              </thead>
              <tbody>
                {apps.map((item) => (
                  <tr key={item.app_id}>
                    <td>
                      <div className="cell-title">{item.app_name}</div>
                      <div className="cell-subtitle">
                        {item.app_type} · {item.business_scene || "-"}
                      </div>
                    </td>
                    <td>{item.owner}</td>
                    <td>{item.stable_version_id || "-"}</td>
                    <td>{item.running_experiment_id || "-"}</td>
                    <td>
                      <StatusPill value={item.status} />
                    </td>
                    <td>{formatDate(item.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section className="panel">
        <SectionHeader title="创建应用" description="录入治理对象，后续版本和实验都挂在应用下面。" />
        <div className="panel-note">
          应用创建后，建议先去“版本”页补一个稳定版，再进入实验治理。
        </div>
        <form className="form-stack" onSubmit={handleSubmit}>
          <label>
            <span>应用名称</span>
            <input
              value={form.app_name}
              onChange={(event) => setForm((prev) => ({ ...prev, app_name: event.target.value }))}
              required
            />
          </label>

          <label>
            <span>应用类型</span>
            <select
              value={form.app_type}
              onChange={(event) => setForm((prev) => ({ ...prev, app_type: event.target.value }))}
            >
              <option value="RAG">RAG</option>
              <option value="Chatbot">Chatbot</option>
              <option value="Agent">Agent</option>
            </select>
          </label>

          <label>
            <span>负责人</span>
            <input
              value={form.owner}
              onChange={(event) => setForm((prev) => ({ ...prev, owner: event.target.value }))}
              required
            />
          </label>

          <label>
            <span>业务场景</span>
            <input
              value={form.business_scene}
              onChange={(event) => setForm((prev) => ({ ...prev, business_scene: event.target.value }))}
            />
          </label>

          <label>
            <span>描述</span>
            <textarea
              rows={4}
              value={form.description}
              onChange={(event) => setForm((prev) => ({ ...prev, description: event.target.value }))}
            />
          </label>

          <button className="primary-button" type="submit" disabled={submitting}>
            <Plus size={16} />
            <span>{submitting ? "创建中..." : "创建应用"}</span>
          </button>
        </form>
      </section>
    </div>
  );
}
