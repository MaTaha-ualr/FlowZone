import { useState, useCallback, useEffect, useRef } from "react";

export const API_BASE_URL = (import.meta.env.VITE_API_URL ?? "").replace(/\/$/, "");

export function apiUrl(path: string): string {
  if (/^https?:\/\//i.test(path)) return path;
  return `${API_BASE_URL}${path}`;
}

export function webSocketUrl(path: string): string {
  const base = API_BASE_URL || window.location.origin;
  const url = new URL(path, base);
  url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
  return url.toString();
}

export function getToken(): string | null {
  const auth = localStorage.getItem("flowzone_auth");
  if (!auth) return null;
  try {
    return JSON.parse(auth).access_token ?? null;
  } catch {
    return null;
  }
}

export function getUserId(): string | null {
  const auth = localStorage.getItem("flowzone_auth");
  if (!auth) return null;
  try {
    return JSON.parse(auth).user?.id ?? null;
  } catch {
    return null;
  }
}

export function getUserRole(): string | null {
  const auth = localStorage.getItem("flowzone_auth");
  if (!auth) return null;
  try {
    return JSON.parse(auth).user?.role ?? null;
  } catch {
    return null;
  }
}

function headersFor(options: RequestInit): Headers {
  const headers = new Headers(options.headers);
  const token = getToken();
  const isFormData = options.body instanceof FormData;

  if (!isFormData && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  if (token && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  return headers;
}

async function errorMessage(response: Response): Promise<string> {
  const payload = await response.json().catch(() => null);
  if (typeof payload?.detail === "string") return payload.detail;
  if (Array.isArray(payload?.detail)) {
    return payload.detail
      .map((item: { msg?: string }) => item.msg)
      .filter(Boolean)
      .join("; ");
  }
  return `HTTP ${response.status}`;
}

export async function apiFetchResponse(path: string, options: RequestInit = {}): Promise<Response> {
  const response = await fetch(apiUrl(path), { ...options, headers: headersFor(options) });

  if (response.status === 401) {
    localStorage.removeItem("flowzone_auth");
    window.location.href = "#/login";
    throw new Error("Session expired. Please log in again.");
  }

  if (!response.ok) {
    throw new Error(await errorMessage(response));
  }

  return response;
}

export async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await apiFetchResponse(path, options);
  if (response.status === 204) return {} as T;
  return response.json() as Promise<T>;
}

export async function apiFetchBlob(path: string, options: RequestInit = {}): Promise<Blob> {
  const response = await apiFetchResponse(path, options);
  return response.blob();
}

export async function get<T>(path: string): Promise<T> {
  return apiFetch<T>(path, { method: "GET" });
}

export async function post<T>(path: string, body?: unknown): Promise<T> {
  return apiFetch<T>(path, {
    method: "POST",
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
  });
}

export async function put<T>(path: string, body?: unknown): Promise<T> {
  return apiFetch<T>(path, {
    method: "PUT",
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
  });
}

export async function del<T>(path: string): Promise<T> {
  return apiFetch<T>(path, { method: "DELETE" });
}

export function useApi<T>(fetcher: () => Promise<T>, immediate = true) {
  const fetcherRef = useRef(fetcher);
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(immediate);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetcherRef.current = fetcher;
  }, [fetcher]);

  const execute = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await fetcherRef.current();
      setData(result);
      return result;
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Something went wrong";
      setError(msg);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (immediate) {
      execute().catch(() => undefined);
    }
  }, [execute, immediate]);

  return { data, loading, error, refetch: execute };
}

export async function login(username: string, password: string) {
  return post("/api/v1/auth/login", { username, password });
}

export async function register(data: Record<string, unknown>) {
  return post("/api/v1/auth/register", data);
}

export function getCurrentProfile() {
  return get("/api/v1/profile/me");
}

export function getRainbowCircle() {
  return get("/api/v1/profile/rainbow-circle");
}

export function getTrustScore(userId: string) {
  return get(`/api/v1/trust/${userId}`);
}

export function getVouches(userId: string) {
  return get(`/api/v1/trust/${userId}/vouches`);
}

export function getRewards() {
  return get("/api/v1/profile/rewards");
}

export function redeemReward(userId: string, key: string) {
  return post(`/api/v1/trust/${userId}/vouch?vouch_type=${encodeURIComponent(key)}`);
}

export function submitIntake(userId: string, answers: Record<string, unknown>) {
  return post(`/api/v1/users/${userId}/intake`, answers);
}

export function createSession(userId: string) {
  return post(`/api/v1/sessions/${userId}`);
}

export function getSession(sessionId: string) {
  return get(`/api/v1/sessions/${sessionId}`);
}

export function getSessions(userId: string) {
  return get(`/api/v1/sessions/${userId}`);
}

export function getCurrentSession(userId: string) {
  return get(`/api/v1/sessions/${userId}/current`);
}

export function vibeCheck(sessionId: string, vibe: string, notes?: string | null) {
  return post("/api/v1/vibe/check", { session_id: sessionId, vibe, notes });
}

export function sendChatMessage(sessionId: string, content: string, vibe?: string) {
  return post(`/api/v1/chat/${sessionId}`, { content, ...(vibe ? { vibe } : {}) });
}

export function getChatHistory(sessionId: string) {
  return get(`/api/v1/chat/${sessionId}/history`);
}

export function endSession(sessionId: string) {
  return put(`/api/v1/sessions/${sessionId}/end`);
}

export function getVoiceOptions() {
  return get("/api/v1/voice/voices");
}

export function transcribeVoice(audioBlob: Blob) {
  const formData = new FormData();
  formData.append("file", audioBlob, "recording.webm");
  return apiFetch<{ text: string; confidence?: number; duration_seconds?: number; provider: string }>(
    "/api/v1/voice/transcribe",
    { method: "POST", body: formData },
  );
}

export function synthesizeVoice(text: string, character: string) {
  return apiFetchBlob("/api/v1/voice/synthesize", {
    method: "POST",
    body: JSON.stringify({ text, character }),
  });
}

export function getDocuments(userId: string) {
  return get(`/api/v1/documents/${userId}`);
}

export function uploadDocument(userId: string, file: File, documentType = "uploaded") {
  const formData = new FormData();
  formData.append("file", file);
  return apiFetch(
    `/api/v1/documents/upload?user_id=${encodeURIComponent(userId)}&document_type=${encodeURIComponent(documentType)}`,
    { method: "POST", body: formData },
  );
}

export function searchDocuments(_userId: string, query: string) {
  return get(`/api/v1/rag/search?q=${encodeURIComponent(query)}`);
}

export function getMentorRoster() {
  return get("/api/v1/mentors/roster");
}

export function getMentorDashboard(userId: string) {
  return get(`/api/v1/mentors/dashboard/${userId}`);
}

export function getMentorNotes(youthId: string) {
  return get(`/api/v1/mentors/notes/${youthId}`);
}

export function createMentorNote(note: Record<string, unknown>) {
  return post("/api/v1/mentors/notes", note);
}

export function getActivityFeed(userId: string, limit = 20) {
  return get(`/api/v1/users/${userId}/activity?limit=${limit}`);
}
