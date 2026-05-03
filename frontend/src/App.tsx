import { Navigate, Route, Routes } from "react-router-dom";
import { Layout } from "./components/Layout";
import { AppsPage } from "./pages/AppsPage";
import { ApprovalsPage } from "./pages/ApprovalsPage";
import { ExperimentsPage } from "./pages/ExperimentsPage";
import { ObservabilityPage } from "./pages/ObservabilityPage";
import { RollbackPage } from "./pages/RollbackPage";
import { VersionsPage } from "./pages/VersionsPage";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<AppsPage />} />
        <Route path="versions" element={<VersionsPage />} />
        <Route path="experiments" element={<ExperimentsPage />} />
        <Route path="observability" element={<ObservabilityPage />} />
        <Route path="approvals" element={<ApprovalsPage />} />
        <Route path="rollback" element={<RollbackPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
