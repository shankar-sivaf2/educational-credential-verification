import { BrowserRouter, Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import ProtectedRoute from "./components/ProtectedRoute";
import { AuthProvider } from "./hooks/useAuth";
import AdminDashboard from "./pages/AdminDashboard";
import AuditHistoryPage from "./pages/AuditHistoryPage";
import HomePage from "./pages/HomePage";
import IssueCertificatePage from "./pages/IssueCertificatePage";
import LoginPage from "./pages/LoginPage";
import StudentRecordsPage from "./pages/StudentRecordsPage";
import SystemHealthPage from "./pages/SystemHealthPage";
import VerifyPage from "./pages/VerifyPage";

function NotFound() {
  return (
    <section className="narrow">
      <h1>Page not found</h1>
      <p className="muted">That address does not exist. Use the menu above to go back.</p>
    </section>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route element={<Layout />}>
            <Route path="/" element={<HomePage />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/verify" element={<VerifyPage />} />
            <Route path="/student" element={<StudentRecordsPage />} />
            <Route path="/health" element={<SystemHealthPage />} />
            <Route path="/admin" element={<ProtectedRoute><AdminDashboard /></ProtectedRoute>} />
            <Route path="/admin/issue" element={<ProtectedRoute><IssueCertificatePage /></ProtectedRoute>} />
            <Route path="/admin/audit" element={<ProtectedRoute><AuditHistoryPage /></ProtectedRoute>} />
            <Route path="*" element={<NotFound />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}