import { useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import StatusBadge from "../components/StatusBadge";
import VerificationResult from "../components/VerificationResult";
import { errorMessage } from "../services/api";
import * as verificationService from "../services/verificationService";

export default function VerifyPage() {
  const [params] = useSearchParams();
  const certParam = params.get("cert");

  const [mode, setMode] = useState("file");
  const [file, setFile] = useState(null);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);
  const [lookup, setLookup] = useState(null);
  const fileInput = useRef(null);

  // Opened from a QR code: show the status for that certificate ID (no personal data).
  useEffect(() => {
    if (!certParam) return;
    let cancelled = false;
    setBusy(true);
    verificationService
      .lookupStatus(certParam)
      .then((data) => !cancelled && setLookup(data))
      .catch((err) => !cancelled && setError(errorMessage(err)))
      .finally(() => !cancelled && setBusy(false));
    return () => {
      cancelled = true;
    };
  }, [certParam]);

  function reset() {
    setResult(null);
    setError("");
  }

  async function handleSubmit(event) {
    event.preventDefault();
    reset();
    setBusy(true);
    try {
      if (mode === "file") {
        if (!file) throw new Error("Choose a certificate file first.");
        setResult(await verificationService.verifyFile(file));
      } else {
        let parsed;
        try {
          parsed = JSON.parse(text);
        } catch {
          throw new Error("That text is not valid JSON. Paste the whole certificate file.");
        }
        setResult(await verificationService.verifyPackage(parsed));
      }
    } catch (err) {
      setError(err.response ? errorMessage(err) : err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="narrow">
      <h1>Verify a certificate</h1>
      <p className="muted">
        Upload the certificate file the candidate gave you. The check is made against the
        blockchain record, not against any database.
      </p>

      {certParam && (
        <div className="card callout">
          <h2>Status from QR code</h2>
          {busy && !lookup && <p className="muted">Checking…</p>}
          {lookup && (
            <>
              <p>
                <StatusBadge status={lookup.status} /> <span className="mono">{lookup.certificate_id}</span>
              </p>
              <p>{lookup.message}</p>
            </>
          )}
          <p className="muted small">
            A QR code shows only whether this ID is registered or revoked. It does not check the
            certificate's contents. To fully verify a certificate, upload the file below.
          </p>
        </div>
      )}

      <form className="card form" onSubmit={handleSubmit}>
        <div className="tabs" role="tablist">
          <button type="button" role="tab" aria-selected={mode === "file"}
            className={mode === "file" ? "tab active" : "tab"} onClick={() => { setMode("file"); reset(); }}>
            Upload file
          </button>
          <button type="button" role="tab" aria-selected={mode === "text"}
            className={mode === "text" ? "tab active" : "tab"} onClick={() => { setMode("text"); reset(); }}>
            Paste JSON
          </button>
        </div>

        {mode === "file" ? (
          <label>
            Certificate file (.json, max 64 KB)
            <input
              ref={fileInput}
              type="file"
              accept=".json,application/json"
              onChange={(e) => { setFile(e.target.files?.[0] || null); reset(); }}
            />
          </label>
        ) : (
          <label>
            Certificate JSON
            <textarea rows={10} value={text} onChange={(e) => { setText(e.target.value); reset(); }}
              placeholder='{"schema": "ecv-cert/1", ...}' spellCheck={false} className="mono" />
          </label>
        )}

        {error && <div className="alert alert-bad" role="alert">{error}</div>}

        <button type="submit" className="btn btn-primary" disabled={busy}>
          {busy ? "Verifying…" : "Verify"}
        </button>
        <p className="muted small">The file is checked in memory and is not stored.</p>
      </form>

      {result && <VerificationResult result={result} />}
    </section>
  );
}