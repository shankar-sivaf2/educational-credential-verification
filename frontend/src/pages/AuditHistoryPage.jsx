import { useEffect, useState } from "react";
import { errorMessage } from "../services/api";
import * as certificateService from "../services/certificateService";
import { formatDate } from "../services/format";

const PAGE_SIZE = 25;
const EVENT_TYPES = ["", "ISSUE", "REVOKE", "VERIFY", "STATUS_LOOKUP", "STUDENT_ACCESS", "LOGIN"];

export default function AuditHistoryPage() {
  const [eventType, setEventType] = useState("");
  const [offset, setOffset] = useState(0);
  const [data, setData] = useState({ items: [], total: 0 });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError("");
    certificateService
      .auditLog({ eventType, limit: PAGE_SIZE, offset })
      .then((result) => {
        if (!cancelled) setData(result);
      })
      .catch((err) => {
        if (!cancelled) setError(errorMessage(err));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [eventType, offset]);

  const from = data.total === 0 ? 0 : offset + 1;
  const to = Math.min(offset + PAGE_SIZE, data.total);

  return (
    <section>
      <div className="page-head">
        <h1>Audit history</h1>
        <label className="inline">
          Event
          <select
            value={eventType}
            onChange={(e) => {
              setEventType(e.target.value);
              setOffset(0);
            }}
          >
            {EVENT_TYPES.map((t) => (
              <option key={t} value={t}>{t || "All events"}</option>
            ))}
          </select>
        </label>
      </div>

      <p className="muted small">
        The log records what happened and the outcome. It never stores names or grades.
      </p>

      {error && <div className="alert alert-bad" role="alert">{error}</div>}

      <div className="card">
        {loading ? (
          <p className="muted">Loading…</p>
        ) : data.items.length === 0 ? (
          <p className="muted">No events yet.</p>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Time</th>
                  <th>Event</th>
                  <th>Outcome</th>
                  <th>Actor</th>
                  <th>Certificate</th>
                  <th>Detail</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((e) => (
                  <tr key={e.id}>
                    <td>{formatDate(e.created_at)}</td>
                    <td>{e.event_type}</td>
                    <td>{e.outcome}</td>
                    <td>{e.actor}</td>
                    <td className="mono">{e.certificate_id || "-"}</td>
                    <td className="small">{e.detail || ""}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        <div className="pager">
          <span className="muted small">{from}–{to} of {data.total}</span>
          <div className="row">
            <button
              type="button"
              className="btn btn-ghost btn-sm"
              disabled={offset === 0 || loading}
              onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
            >
              Previous
            </button>
            <button
              type="button"
              className="btn btn-ghost btn-sm"
              disabled={offset + PAGE_SIZE >= data.total || loading}
              onClick={() => setOffset(offset + PAGE_SIZE)}
            >
              Next
            </button>
          </div>
        </div>
      </div>
    </section>
  );
}