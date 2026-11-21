import { downloadFile } from "../services/api";
import { formatDate, shortHash } from "../services/format";
import QRCodeView from "./QRCodeView";
import StatusBadge from "./StatusBadge";

/**
 * Shows one certificate. Used for the student's records (package + verifyUrl supplied)
 * and for the result after issuing.
 */
export default function CertificateCard({ certificate, pkg, verifyUrl }) {
  function downloadPackage() {
    downloadFile(
      JSON.stringify(pkg, null, 2),
      `${certificate.certificate_id}.json`,
      "application/json"
    );
  }

  return (
    <article className="card cert">
      <header className="cert-head">
        <div>
          <p className="eyebrow">{certificate.institution_name}</p>
          <h3>{certificate.degree}</h3>
          <p className="muted">{certificate.department} · Class of {certificate.graduation_year}</p>
        </div>
        <StatusBadge status={certificate.status} />
      </header>

      <dl className="facts">
        <div><dt>Student</dt><dd>{certificate.student_name}</dd></div>
        <div><dt>Student ID</dt><dd>{certificate.student_id}</dd></div>
        <div><dt>Certificate ID</dt><dd className="mono">{certificate.certificate_id}</dd></div>
        <div><dt>Registered</dt><dd>{formatDate(certificate.registered_at)}</dd></div>
        {certificate.revoked_at && (
          <div><dt>Revoked</dt><dd>{formatDate(certificate.revoked_at)}</dd></div>
        )}
        <div><dt>Commitment</dt><dd className="mono" title={certificate.commitment}>{shortHash(certificate.commitment)}</dd></div>
        <div><dt>Transaction</dt><dd className="mono" title={certificate.tx_hash || ""}>{shortHash(certificate.tx_hash)}</dd></div>
      </dl>

      {(pkg || verifyUrl) && (
        <footer className="cert-foot">
          {verifyUrl && <QRCodeView url={verifyUrl} size={120} />}
          {pkg && (
            <div className="cert-actions">
              <button type="button" className="btn btn-primary btn-sm" onClick={downloadPackage}>
                Download certificate file (.json)
              </button>
              <p className="muted small">
                Give this file to an employer. They upload it on the Verify page to check it.
                It contains private details, so share it only with people you choose.
              </p>
            </div>
          )}
        </footer>
      )}
    </article>
  );
}