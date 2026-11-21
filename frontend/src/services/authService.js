import api from "./api";

export async function login(username, password) {
  const { data } = await api.post("/auth/login", { username, password });
  return data; // { access_token, token_type, username }
}

export async function me() {
  const { data } = await api.get("/auth/me");
  return data;
}