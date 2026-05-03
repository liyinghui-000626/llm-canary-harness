import { Activity, Boxes, ClipboardCheck, FlaskConical, GitBranch, LucideIcon, RotateCcw } from "lucide-react";
import { NavLink, Outlet, useLocation } from "react-router-dom";

type NavItem = {
  to: string;
  label: string;
  icon: LucideIcon;
};

const navItems: NavItem[] = [
  { to: "/", label: "应用", icon: Boxes },
  { to: "/versions", label: "版本", icon: GitBranch },
  { to: "/experiments", label: "实验", icon: FlaskConical },
  { to: "/observability", label: "Trace / 指标", icon: Activity },
  { to: "/approvals", label: "审批中心", icon: ClipboardCheck },
  { to: "/rollback", label: "回滚日志", icon: RotateCcw },
];

export function Layout() {
  const location = useLocation();
  const currentItem = navItems.find((item) => item.to === location.pathname) ?? navItems[0];

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">C</div>
          <div>
            <h1>Canary Console</h1>
            <p>LLM V1 控制台</p>
          </div>
        </div>

        <nav className="nav">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === "/"}
                className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`}
              >
                <Icon size={18} />
                <span>{item.label}</span>
              </NavLink>
            );
          })}
        </nav>
      </aside>

      <main className="content">
        <div className="topbar">
          <div>
            <h2>{currentItem.label}</h2>
            <p>V1 最小控制台，覆盖应用、版本、实验和可观测性。</p>
          </div>
          <div className="topbar-meta">
            <span className="meta-chip">Admin · :6000</span>
            <span className="meta-chip">Gateway · :6001</span>
          </div>
        </div>
        <Outlet />
      </main>
    </div>
  );
}
