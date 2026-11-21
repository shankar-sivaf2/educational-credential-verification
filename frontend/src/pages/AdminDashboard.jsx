import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import StatusBadge from "../components/StatusBadge";
import { useCertificates } from "../hooks/useCertificates";
import { downloadFile, errorMessage } from "../services/api";
import * as certificateService from "../services/certificateService";
import { formatDate } from "../services/format";

const FILTERS = ["ALL", "REGISTERED", "REVOKED", "FAILED", "PENDING"];

export default function AdminDashboard() {
  const { items, total, loading, error, reload } = useCertificates({ limit: 200 });
  const [filter, setFilter] = useState("ALL");
  const [busyId, setBusyId] = useState("");
  const [actionError, setActionError] = useState("");

  const counts = useMemo(() => {
    const c = { REGISTERED: 0, REVOKED: 0, FAILED: 0, PENDING: 0 };
    items.forEach((item) => {
      c[item.status] = (c[item.status] || 0) + 1;
    });
    return c;
  }, [items]);

  const shown = filter === "ALL" ? items : items.filter((item) => item.status === filter);

  async function handleRevoke(cert) {
    const ok = window.confirm(
      `Revoke ${cert.certificate_id}? This is recorded on the blockchain and cannot be undone.`
    );
    if (!ok) return;
    setBusyId(cert.certificate_id);
    setActionError("");
    try {
      await certificateService.revoke(cert.certificate_id);
      await reload();
    } catch (err) {
      setActionError(errorMessage(err));
    } finally {
      setBusyId("");
    }
  }

  async function handleQr(cert) {
    setActionError("");
    try {
      const blob = await certificateService.downloadQr(cert.certificate_id);
      downloadFile(blob, `${cert.certificate_id}-qr.png`);
    } catch (err) {
      setActionError(errorMessage(err));
    }
  }

  return (
    <section>
      <div className="page-head">
        <h1>Dashboard</h1>
        <div className="row">
          <button type="button" className="btn btn-ghost btn-sm" onClick={reload} disabled={loading}>
            Refresh
          </button>
          <Link to="/admin/issue" className="btn btn-primary btn-sm">Issue certificate</Link>
        </div>
      </div>

      <div className="stats">
        <div className="stat"><span className="stat-num">{total}</span><span>Total</span></div>
        <div className="stat"><span className="stat-num">{counts.REGISTERED}</span><span>Registered</span></div>
        <div className="stat"><span className="stat-num">{counts.REVOKED}</span><span>Revoked</span></div>
        <div className="stat"><span className="stat-num">{counts.FAILED + counts.PENDING}</span><span>Failed / pending</span></div>
      </div>

      {error && <div className="alert alert-bad" role="alert">{error}</div>}
      {actionError && <div className="alert alert-bad" role="alert">{actionError}</div>}

      <div className="card">
        <div className="table-head">
          <h2>Certificates</h2>
          <label className="inline">
            Show
            <select value={filter} onChange={(e) => setFilter(e.target.value)}>
              {FILTERS.map((f) => (
                <option key={f} value={f}>{f === "ALL" ? "All" : f.charAt(0) + f.slice(1).toLowerCase()}</option>
              ))}
            </select>
          </label>
        </div>

        {loading ? (
          <p className="muted">Loading…</p>
        ) : shown.length === 0 ? (
          <p className="muted">No certificates to show yet.</p>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Certificate ID</th>
                  <th>Student</th>
                  <th>Degree</th>
                  <th>Year</th>
                  <th>Status</th>
                  <th>Registered</th>
                  <th aria-label="Actions" />
                </tr>
              </thead>
              <tbody>
                {shown.map((cert) => (
                  <tr key={cert.certificate_id}>
                    <td className="mono">{cert.certificate_id}</td>
                    <td>{cert.student_name}</td>
                    <td>{cert.degree}</td>
                    <td>{cert.graduation_year}</td>
                    <td>
                      <StatusBadge status={cert.status} />
                      {cert.failure_reason && <div className="muted small">{cert.failure_reason}</div>}
                    </td>
                    <td>{formatDate(cert.registered_at)}</td>
                    <td className="actions">
                      {cert.status === "REGISTERED" && (
                        <>
                          <button type="button" className="btn btn-ghost btn-sm" onClick={() => handleQr(cert)}>
                            QR
                          </button>
                          <button
                            type="button"
                            className="btn btn-danger btn-sm"
                            disabled={busyId === cert.certificate_id}
                            onClick={() => handleRevoke(cert)}
                          >
                            {busyId === cert.certificate_id ? "Revoking…" : "Revoke"}
                          </button>
                        </>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {total > items.length && (
          <p className="muted small">Showing the newest {items.length} of {total} certificates.</p>
        )}
      </div>
    </section>
  );
}