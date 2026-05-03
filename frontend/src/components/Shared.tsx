import { Loader2, RefreshCw } from "lucide-react";
import { ReactNode } from "react";

export function SectionHeader({
  title,
  description,
  action,
}: {
  title: string;
  description: string;
  action?: ReactNode;
}) {
  return (
    <div className="section-header">
      <div>
        <h2>{title}</h2>
        <p>{description}</p>
      </div>
      {action}
    </div>
  );
}

export function RefreshButton({
  onClick,
  loading,
}: {
  onClick: () => void;
  loading?: boolean;
}) {
  return (
    <button className="secondary-button" onClick={onClick} disabled={loading}>
      {loading ? <Loader2 size={16} className="spin" /> : <RefreshCw size={16} />}
      <span>刷新</span>
    </button>
  );
}

export function EmptyState({ title }: { title: string }) {
  return <div className="empty-state">{title}</div>;
}

export function StatusPill({ value }: { value: string }) {
  return <span className={`status-pill status-${value}`}>{value}</span>;
}

export function SummaryCard({
  label,
  value,
  accent,
  hint,
}: {
  label: string;
  value: string | number;
  accent?: "blue" | "green" | "amber" | "slate";
  hint?: string;
}) {
  return (
    <div className={`summary-card ${accent ? `summary-${accent}` : ""}`}>
      <span>{label}</span>
      <strong>{value}</strong>
      {hint ? <p>{hint}</p> : null}
    </div>
  );
}

export function formatDate(value?: string | null) {
  if (!value) {
    return "-";
  }
  return new Date(value).toLocaleString("zh-CN", { hour12: false });
}
