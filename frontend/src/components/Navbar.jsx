import { Link, NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";

export default function Navbar() {
  const { isAuthenticated, username, logout } = useAuth();
  const navigate = useNavigate();

  function handleLogout() {
    logout();
    navigate("/");
  }

  return (
    <header className="nav">
      <div className="nav-inner">
        <Link to="/" className="brand">
          <span className="brand-mark" aria-hidden="true">✓</span>
          Credential Verification
        </Link>

        <nav className="nav-links" aria-label="Main">
          <NavLink to="/verify">Verify</NavLink>
          <NavLink to="/student">My Certificates</NavLink>
          {isAuthenticated && (
            <>
              <NavLink to="/admin" end>Dashboard</NavLink>
              <NavLink to="/admin/issue">Issue</NavLink>
              <NavLink to="/admin/audit">Audit</NavLink>
            </>
          )}
          <NavLink to="/health">System</NavLink>
        </nav>

        <div className="nav-user">
          {isAuthenticated ? (
            <>
              <span className="muted small">Signed in as {username}</span>
              <button type="button" className="btn btn-ghost btn-sm" onClick={handleLogout}>
                Log out
              </button>
            </>
          ) : (
            <Link to="/login" className="btn btn-primary btn-sm">Admin login</Link>
          )}
        </div>
      </div>
    </header>
  );
}