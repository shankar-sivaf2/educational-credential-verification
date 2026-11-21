import { formatDate } from "../services/format";
import StatusBadge from "./StatusBadge";

const CHECKS = [
  ["registered", "Registered on the blockchain"],
  ["commitment_matches", "Certificate data matches the registered hash"],
  ["issuer_authorized", "Issued by an authorised institution"],
  ["not_revoked", "Not revoked"],
];

function checkMark(value) {
  if (value === true) return ["ok", "✓", "Passed"];
  if (value === false) return ["bad", "✗", "Failed"];
  return ["skip", "–", "Not checked"];
}

export default function VerificationResult({ result }) {
  const tone = result.valid ? "ok" : result.status === "SERVICE_UNAVAILABLE" ? "warn" : "bad";
  return (
    <section className="card result" aria-live="polite">
      <div className={`alert alert-${tone}`} role="status">
        <strong>
          <StatusBadge status={result.status} />
        </strong>{" "}
        {result.message}
      </div>

      <h3>Checks</h3>
      <ul className="checks">
        {CHECKS.map(([key, label]) => {
          const [tone2, symbol, word] = checkMark(result.checks[key]);
          return (
            <li key={key} className={`check check-${tone2}`}>
              <span className="check-mark" aria-hidden="true">{symbol}</span>
              <span>{label}</span>
              <span className="visually-hidden">{word}</span>
            </li>
          );
        })}
      </ul>

      <dl className="facts">
        <div><dt>Certificate ID</dt><dd className="mono">{result.certificate_id}</dd></div>
        <div><dt>Registered</dt><dd>{formatDate(result.registered_at)}</dd></div>
        <div><dt>Issuer account</dt><dd className="mono">{result.issuer || "-"}</dd></div>
        <div><dt>Checked at</dt><dd>{formatDate(result.verified_at)}</dd></div>
      </dl>

      <p className="muted small">{result.note}</p>
    </section>
  );
}