import StatusBadge from "../components/StatusBadge";
import { useHealth } from "../hooks/useHealth";

function Row({ label, value, mono }) {
  return (
    <div>
      <dt>{label}</dt>
      <dd className={mono ? "mono" : undefined}>{value ?? "-"}</dd>
    </div>
  );
}

export default function SystemHealthPage() {
  const { data, loading, error, reload } = useHealth();
  const chain = data?.blockchain;

  return (
    <section className="narrow">
      <div className="page-head">
        <h1>System status</h1>
        <button type="button" className="btn btn-ghost btn-sm" onClick={reload} disabled={loading}>
          Refresh
        </button>
      </div>

      {loading && !data && <p className="muted">Checking…</p>}
      {error && <div className="alert alert-bad" role="alert">{error}</div>}

      {data && (
        <>
          <div className={`alert ${data.status === "ok" ? "alert-ok" : "alert-warn"}`} role="status">
            {data.status === "ok"
              ? "All services are working."
              : "Some services are not available. Certificates cannot be issued or verified until they are."}
          </div>

          <div className="card">
            <h2>Backend and database</h2>
            <p>
              <StatusBadge status={data.database.connected ? "REGISTERED" : "FAILED"} />{" "}
              Database {data.database.connected ? "connected" : "not reachable"}
            </p>
          </div>

          <div className="card">
            <h2>Blockchain</h2>
            <p>
              <StatusBadge status={chain.connected ? "REGISTERED" : "FAILED"} />{" "}
              {chain.connected ? "Connected" : "Not connected"}
            </p>
            {chain.error && <div className="alert alert-bad">{chain.error}</div>}
            <dl className="facts">
              <Row label="Chain ID" value={chain.chain_id} />
              <Row label="Latest block" value={chain.block_number} />
              <Row label="Contract" value={chain.contract_address} mono />
              <Row label="Signer account" value={chain.signer} mono />
              <Row
                label="Signer may issue"
                value={chain.signer_is_issuer === null ? "-" : chain.signer_is_issuer ? "Yes" : "No"}
              />
            </dl>
          </div>
        </>
      )}
    </section>
  );
}