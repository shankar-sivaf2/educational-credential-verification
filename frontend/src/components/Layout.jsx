import { Outlet } from "react-router-dom";
import Navbar from "./Navbar";

export default function Layout() {
  return (
    <div className="shell">
      <Navbar />
      <main className="main">
        <Outlet />
      </main>
      <footer className="footer">
        An Efficient Blockchain-Based Approach to Educational Credential Verification
      </footer>
    </div>
  );
}