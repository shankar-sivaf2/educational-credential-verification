import { useState } from "react";
import CertificateCard from "../components/CertificateCard";
import { errorMessage } from "../services/api";
import * as verificationService from "../services/verificationService";

export default function StudentRecordsPage() {
  const [studentId, setStudentId] = useState("");
  const [accessCode, setAccessCode] = useState("");
  const [records, setRecords] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const data = await verificationService.studentRecords(studentId.trim(), accessCode.trim());
      setRecords(data.records);
      setAccessCode(""); // do not keep the code in the form after use
    } catch (err) {
      setRecords(null);
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section>
      <div className="narrow">
        <h1>My certificates</h1>
        <p className="muted">
          Enter your student ID and the access code your institution gave you. You can then
          download your certificate file to share with an employer.
        </p>
        <form className="card form" onSubmit={handleSubmit}>
          <label>
            Student ID
            <input value={studentId} onChange={(e) => setStudentId(e.target.value)} required />
          </label>
          <label>
            Access code
            <input value={accessCode} onChange={(e) => setAccessCode(e.target.value)}
              autoComplete="off" required className="mono" />
          </label>
          {error && <div className="alert alert-bad" role="alert">{error}</div>}
          <button type="submit" className="btn btn-primary" disabled={busy}>
            {busy ? "Looking up…" : "Show my certificates"}
          </button>
        </form>
      </div>

      {records && records.map((r) => (
        <CertificateCard key={r.certificate.certificate_id}
          certificate={r.certificate} pkg={r.package} verifyUrl={r.verify_url} />
      ))}
    </section>
  );
}