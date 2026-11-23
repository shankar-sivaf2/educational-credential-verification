// One shared axios client + session helpers.
// The admin token lives in sessionStorage (cleared when the tab closes). If the browser
// blocks storage, an in-memory fallback keeps the app working for the current page only.
import axios from "axios";

const TOKEN_KEY = "ecv_token";
const USER_KEY = "ecv_user";
const memory = {};

function read(key) {
  try {
    return sessionStorage.getItem(key);
  } catch {
    return memory[key] ?? null;
  }
}
function write(key, value) {
  memory[key] = value;
  try {
    sessionStorage.setItem(key, value);
  } catch {
    /* storage unavailable: memory fallback is used */
  }
}
function remove(key) {
  delete memory[key];
  try {
    sessionStorage.removeItem(key);
  } catch {
    /* ignore */
  }
}

export const getToken = () => read(TOKEN_KEY);
export const getStoredUser = () => read(USER_KEY);
export function saveSession(token, username) {
  write(TOKEN_KEY, token);
  write(USER_KEY, username);
}
export function clearSession() {
  remove(TOKEN_KEY);
  remove(USER_KEY);
}

const requireHostedApi = import.meta.env.VITE_REQUIRE_HOSTED_API === "true";

function resolveApiBase(configuredBase) {
  const value = configuredBase?.trim();
  if (!requireHostedApi) return value || "/api";
  if (!value) return undefined;

  try {
    const url = new URL(value);
    const hostname = url.hostname.replace(/\.$/, "");
    const loopback = /^(?:localhost|\[::1\]|0\.0\.0\.0)$|^127\.|\.localhost$/.test(hostname);
    const path = url.pathname.replace(/\/+$/, "");
    if (url.protocol !== "https:" || loopback || url.username || url.password ||
        url.search || url.hash || (path && path !== "/api")) return undefined;
    return `${url.origin}/api`;
  } catch {
    return undefined;
  }
}

const apiBase = resolveApiBase(import.meta.env.VITE_API_BASE_URL);
const api = axios.create({
  baseURL: apiBase,
  timeout: 30000,
});

api.interceptors.request.use((config) => {
  if (!apiBase) {
    throw new Error("The backend API is not configured. Set VITE_API_BASE_URL to the public HTTPS FastAPI URL and redeploy.");
  }
  const token = getToken();
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    // An expired/invalid admin session: drop it so the UI sends the user to the login page.
    if (error.response?.status === 401 && getToken()) {
      clearSession();
      window.dispatchEvent(new Event("ecv-auth-expired"));
    }
    return Promise.reject(error);
  }
);

/** Turn any axios error into one readable sentence. */
export function errorMessage(err) {
  const data = err?.response?.data;
  if (data?.error?.message) return data.error.message;
  if (Array.isArray(data?.detail)) {
    return data.detail
      .map((d) => `${(d.loc || []).filter((p) => p !== "body").join(".")}: ${d.msg}`)
      .join("; ");
  }
  if (typeof data?.detail === "string") return data.detail;
  if (err?.code === "ERR_NETWORK") {
    if (requireHostedApi) return "Cannot reach the hosted backend. Check that it is online and allows requests from this site.";
    return "Cannot reach the backend. Is it running on port 8000?";
  }
  if (err?.code === "ECONNABORTED") return "The request timed out. Please try again.";
  return err?.message || "Something went wrong.";
}

/** Save a Blob or text as a file download. */
export function downloadFile(content, filename, type = "application/octet-stream") {
  const blob = content instanceof Blob ? content : new Blob([content], { type });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

export default api;
