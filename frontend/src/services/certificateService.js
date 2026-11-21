import api from "./api";

export async function issue(payload) {
  const { data } = await api.post("/certificates", payload);
  return data; // { certificate, access_code, package, verify_url }
}

export async function list({ status, limit = 50, offset = 0 } = {}) {
  const params = { limit, offset };
  if (status) params.status = status;
  const { data } = await api.get("/certificates", { params });
  return data; // { items, total }
}

export async function revoke(certificateId) {
  const { data } = await api.post(`/certificates/${encodeURIComponent(certificateId)}/revoke`);
  return data;
}

export async function downloadQr(certificateId) {
  const { data } = await api.get(`/certificates/${encodeURIComponent(certificateId)}/qr.png`, {
    responseType: "blob",
  });
  return data; // Blob (PNG)
}

export async function auditLog({ eventType, limit = 25, offset = 0 } = {}) {
  const params = { limit, offset };
  if (eventType) params.event_type = eventType;
  const { data } = await api.get("/audit", { params });
  return data; // { items, total }
}