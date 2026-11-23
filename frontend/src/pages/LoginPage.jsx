import { useState } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import { errorMessage } from "../services/api";

export default function LoginPage() {
  const { isAuthenticated, login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const destination = location.state?.from || "/admin";
  if (isAuthenticated) return <Navigate to={destination} replace />;

  async function handleSubmit(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
  await login(username.trim(), password);
      navigate(destination, { replace: true });
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="narrow">
      <h1>Administrator login</h1>
      <form className="card form" onSubmit={handleSubmit}>
        <label>
          Username
    <input
      value={username}
      onChange={(e) => setUsername(e.target.value)}
      autoComplete="username"
      autoCapitalize="none"
       autoCorrect="off"
       spellCheck={false}
       required
     />
        </label>
        <label>
          Password
         <input
      type="password"
      value={password}
      onChange={(e) => setPassword(e.target.value)}
      autoComplete="current-password"
      autoCapitalize="none"
      autoCorrect="off"
      spellCheck={false}
      required
    />
        </label>
        {error && <div className="alert alert-bad" role="alert">{error}</div>}
        <button type="submit" className="btn btn-primary" disabled={busy}>
          {busy ? "Signing in…" : "Sign in"}
        </button>
      </form>
    </section>
  );
}