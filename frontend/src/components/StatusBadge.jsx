const STATUS = {
  // certificate record status
  REGISTERED: ["ok", "Registered"],
  PENDING: ["warn", "Pending"],
  FAILED: ["bad", "Failed"],
  REVOKED: ["bad", "Revoked"],
  // verification results
  AUTHENTIC_VALID: ["ok", "Authentic & valid"],
  COMMITMENT_MISMATCH: ["bad", "Data mismatch"],
  UNKNOWN: ["bad", "Unknown"],
  INVALID_ISSUER: ["warn", "Invalid issuer"],
  SERVICE_UNAVAILABLE: ["warn", "Service unavailable"],
};

export default function StatusBadge({ status }) {
  const [tone, label] = STATUS[status] || ["info", status];
  return <span className={`badge badge-${tone}`}>{label}</span>;
}