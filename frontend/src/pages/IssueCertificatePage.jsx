import { useState } from "react";
import CertificateCard from "../components/CertificateCard";
import CertificateForm from "../components/CertificateForm";
import { downloadFile, errorMessage } from "../services/api";
import * as certificateService from "../services/certificateService";

export default function IssueCertificatePage() {
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);
  const [copied, setCopied] = useState(false);

  async function handleSubmit(payload) {
    setSubmitting(true);
    setError("");
    try {
      setResult(await certificateService.issue(payload));
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setSubmitting(false);
    }
  }

  async function copyCode() {
    try {
      await navigator.clipboard.writeText(result.access_code);
      setCopied(true);
    } catch {
      setCopied(false); // clipboard blocked: the code is still visible to copy by hand
    }
  }

  async function downloadQr() {
    try {
      const blob = await certificateService.downloadQr(result.certificate.certificate_id);
      downloadFile(blob, `${result.certificate.certificate_id}-qr.png`);
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  if (result) {
    return (
      <section>
        <h1>Certificate issued</h1>
        <div className="alert alert-ok" role="status">
          The certificate was registered on the blockchain.
        </div>

        <div className="card callout">
          <h2>Student access code</h2>
          <p className="code-box mono">{result.access_code}</p>
          <p className="muted small">
            Give this code to the student together with their student ID
            (<strong>{result.certificate.student_id}</strong>). It is shown only once and cannot be recovered.
          </p>
          <button type="button" className="btn btn-ghost btn-sm" onClick={copyCode}>
            {copied ? "Copied" : "Copy code"}
          </button>
        </div>

        <CertificateCard certificate={result.certificate} pkg={result.package} verifyUrl={result.verify_url} />

        {error && <div className="alert alert-bad" role="alert">{error}</div>}
        <div className="row">
          <button type="button" className="btn btn-ghost" onClick={downloadQr}>Download QR code (PNG)</button>
          <button
            type="button"
            className="btn btn-primary"
            onClick={() => {
              setResult(null);
              setCopied(false);
            }}
          >
            Issue another certificate
          </button>
        </div>
      </section>
    );
  }

  return (
    <section className="narrow">
      <h1>Issue a certificate</h1>
      <CertificateForm onSubmit={handleSubmit} submitting={submitting} error={error} />
    </section>
  );
}