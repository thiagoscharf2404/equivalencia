const API = import.meta.env.VITE_API_URL || "http://localhost:8000/api";

async function request(path, options) {
  const response = await fetch(API + path, { ...options, credentials: "include" });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || "Não foi possível concluir a operação.");
  }
  return response;
}

export async function getSession() { return (await request("/auth/me")).json(); }
export async function getUnits() { return (await request("/auth/units")).json(); }
export async function login(data) {
  return (await request("/auth/login", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(data) })).json();
}
export async function logout() { return (await request("/auth/logout", { method: "POST" })).json(); }

export async function getCourses() {
  return (await request("/courses")).json();
}
export async function searchStudents(query) {
  return (await request("/students?limit=100&query=" + encodeURIComponent(query || ""))).json();
}
export async function createStudent(data) {
  return (await request("/students", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  })).json();
}
export async function updateStudent(id, data) {
  return (await request("/students/" + id, {
    method: "PUT", headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  })).json();
}
export async function getMatrices(courseId) {
  return (await request("/courses/" + courseId + "/matrices")).json();
}
export async function getAnalyses() {
  return (await request("/analyses")).json();
}
export async function createAnalysis(data) {
  const form = new FormData();
  ["student_id", "origin_institution", "origin_course",
    "origin_status", "target_course_id", "target_matrix_id", "term"].forEach((key) =>
    form.append(key, data[key] || "")
  );
  form.append("history", data.history);
  data.plans.forEach((file) => form.append("plans", file));
  return (await request("/analyses", { method: "POST", body: form })).json();
}
export async function getAnalysis(id) {
  return (await request("/analyses/" + id)).json();
}
export async function extractHistory(id) {
  return (await request("/analyses/" + id + "/extract", { method: "POST" })).json();
}
export async function saveHistoryReview(id, rows, confirm) {
  return (await request("/analyses/" + id + "/history-review", {
    method: "PUT", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ rows, confirm }),
  })).json();
}
export async function requestAiAnalysis(id) {
  return (await request("/analyses/" + id + "/ai-analysis", { method: "POST" })).json();
}
export async function getCandidates(id) {
  return (await request("/analyses/" + id + "/candidates")).json();
}
export async function addManualSuggestion(id, data) {
  return (await request("/analyses/" + id + "/manual-suggestions", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  })).json();
}
export async function decideSuggestion(id, suggestionId, decision, note) {
  return (await request("/analyses/" + id + "/suggestions/" + suggestionId, {
    method: "PATCH", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ decision, note }),
  })).json();
}
export async function downloadReport(id, coordinatorNote) {
  return request("/analyses/" + id + "/report", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ coordinator_note: coordinatorNote || "" }),
  }).then((r) => r.blob());
}
