// axiosClient.js
// Paper: "API-based communication between modules"
// All backend API calls go through this single client

import axios from "axios";

const API_BASE = import.meta.env.VITE_API_URL || "http://127.0.0.1:5000/api";

const axiosClient = axios.create({
  baseURL: API_BASE,
  timeout: 60000, // 60s — AI models take time
  headers: { "Content-Type": "application/json" },
});

// ── Resume APIs ───────────────────────────────────────────────────────────────
export const uploadResume = (formData) =>
  axiosClient.post("/resume/upload", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });

// ── Analysis APIs ─────────────────────────────────────────────────────────────
export const analyzeSkillGap = (data) =>
  axiosClient.post("/analysis/skill-gap", data);

// ── Interview APIs ────────────────────────────────────────────────────────────
export const generateQuestions = (data) =>
  axiosClient.post("/interview/generate-questions", data);

export const evaluateAllAnswers = (data) =>
  axiosClient.post("/interview/evaluate-all", data);

// ── Feedback APIs ─────────────────────────────────────────────────────────────
export const generateFeedback = (data) =>
  axiosClient.post("/feedback/generate", data);

export const generateTodo = (data) =>
  axiosClient.post("/feedback/todo", data);

export const deleteAccount = (userId) =>
  axiosClient.delete("/feedback/delete-account", { data: { user_id: userId } });

// ── Bias APIs ─────────────────────────────────────────────────────────────────
export const auditJD = (jdText) =>
  axiosClient.post("/bias/audit-jd", { jd_text: jdText });

export const getTransparencyReport = (scores) =>
  axiosClient.post("/bias/transparency", scores);

export default axiosClient;