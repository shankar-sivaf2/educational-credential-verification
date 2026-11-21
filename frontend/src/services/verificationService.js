import api from "./api";

/** Verify by uploading the certificate JSON file. */
export async function verifyFile(file) {
  const form = new FormData();
  form.append("file", file);
  const { data } = await api.post("/verify/upload", form);
  return data;
}

/** Verify by sending certificate data (the parsed JSON). */
export async function verifyPackage(pkg) {
  const { data } = await api.post("/verify", pkg);
  return data;
}

/** QR-code lookup: status by certificate ID only, no personal data. */
export async function lookupStatus(certificateId) {
  const { data } = await api.get(`/verify/status/${encodeURIComponent(certificateId)}`);
  return data;
}

export async function studentRecords(studentId, accessCode) {
  const { data } = await api.post("/student/records", {
    student_id: studentId,
    access_code: accessCode,
  });
  return data; // { records: [{ certificate, package, verify_url }] }
}

export async function health() {
  const { data } = await api.get("/health");
  return data;
}