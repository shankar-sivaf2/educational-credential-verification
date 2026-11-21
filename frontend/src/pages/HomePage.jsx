import { Link } from "react-router-dom";

export default function HomePage() {
  return (
    <>
      <section className="hero">
        <p className="eyebrow">B.Tech CSE final-year project</p>
        <h1>An Efficient Blockchain-Based Approach to Educational Credential Verification</h1>
        <p className="lead">
          Institutions issue certificates, students keep them, and employers check them in
          seconds, without phoning the university and without trusting a photocopy.
        </p>
      </section>

      <section className="grid-3">
        <article className="card">
          <h3>Institution</h3>
          <p>Issue certificates and revoke them if needed. Only authorised accounts can do this.</p>
          <Link to="/login" className="btn btn-primary btn-sm">Admin login</Link>
        </article>
        <article className="card">
          <h3>Student</h3>
          <p>See your certificates and download the file to share with an employer.</p>
          <Link to="/student" className="btn btn-primary btn-sm">My certificates</Link>
        </article>
        <article className="card">
          <h3>Employer</h3>
          <p>Upload a certificate file and get a clear answer: valid, changed, revoked or unknown.</p>
          <Link to="/verify" className="btn btn-primary btn-sm">Verify a certificate</Link>
        </article>
      </section>

      <section className="card">
        <h2>How it works</h2>
        <ol className="steps">
          <li><strong>Issue.</strong> The institution enters the certificate. The system creates a salted SHA-256 hash of it.</li>
          <li><strong>Register.</strong> Only that hash goes to the blockchain, never names or grades.</li>
          <li><strong>Share.</strong> The student gets the certificate file and a QR code.</li>
          <li><strong>Verify.</strong> The employer uploads the file. The system recomputes the hash and compares it with the blockchain record, then checks the issuer and revocation status.</li>
        </ol>
        <p className="muted small">
          A "valid" result means the data is unchanged since an authorised institution registered
          it and it has not been revoked. It does not by itself prove the qualification was earned.
        </p>
      </section>
    </>
  );
}