// axiosClient.js
// Paper: "API-based communication between modules"
// All backend API calls go through this single client

import axios from "axios";

const API_BASE = import.meta.env.VITE_API_URL || "http://127.0.0.1:5000/api";

const axiosClient = axios.create({
  baseURL: API_BASE,
  timeout: 60000, // 60s — fine for most calls (uploads, skill-gap, feedback)
  headers: { "Content-Type": "application/json" },
});

// AI-generation-heavy calls (question generation, answer evaluation) run
// FLAN-T5 on CPU. Cold-start (first call after server start/reload) has to
// load the base model + LoRA adapter into memory before it can generate
// anything, which alone can take well over 60s — separate from the actual
// generation time for N questions. Give these calls more room; the 60s
// default stays for everything else so real connectivity failures still
// surface quickly instead of hanging for 3 minutes.
const AI_GENERATION_TIMEOUT_MS = 180000; // 3 min

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
  axiosClient.post("/interview/generate-questions", data, {
    timeout: AI_GENERATION_TIMEOUT_MS,
  });

export const evaluateAllAnswers = (data) =>
  axiosClient.post("/interview/evaluate-all", data, {
    timeout: AI_GENERATION_TIMEOUT_MS,
  });

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