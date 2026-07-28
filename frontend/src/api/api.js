import axios from "axios";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api",
});

export const extractFromText = (text) =>
  api.post("/complaints/extract-text", { text }).then((r) => r.data);

export const extractFromFile = (file) => {
  const formData = new FormData();
  formData.append("file", file);
  return api.post("/complaints/extract-file", formData).then((r) => r.data);
};

export const saveComplaint = (complaint) =>
  api.post("/complaints", complaint).then((r) => r.data);

export const listComplaints = () => api.get("/complaints").then((r) => r.data);

export const askAssistant = ({ question, contextText }) =>
  api.post("/chat", { question, context_text: contextText }).then((r) => r.data);

export default api;
