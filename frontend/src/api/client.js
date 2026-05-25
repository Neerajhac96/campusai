import axios from "axios";

const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

let unauthorizedHandler = null;

export const setUnauthorizedHandler = (handler) => {
  unauthorizedHandler = handler;
};

export const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 45000,
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("campusai_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error?.response?.status === 401) {
      if (unauthorizedHandler) {
        unauthorizedHandler();
      }
      if (window.location.pathname !== "/login") {
        window.alert("Session expired. Please login again.");
        window.location.href = "/login";
      }
    }

    const detail =
      error?.response?.data?.detail ||
      error?.message ||
      "Something went wrong while contacting CampusAI server";
    return Promise.reject(new Error(detail));
  }
);

export const login = async (email, password) => {
  const response = await api.post("/auth/login", { email, password });
  return response.data;
};

export const getMe = async () => {
  const response = await api.get("/auth/me");
  return response.data;
};

export const logoutRequest = async () => {
  const response = await api.post("/auth/logout");
  return response.data;
};

export const sendQuery = async (query) => {
  const response = await api.post("/chat/query", { query });
  return response.data;
};

export const getChatHistory = async (page = 1, limit = 20) => {
  const response = await api.get("/chat/history", { params: { page, limit } });
  return response.data;
};

export const uploadDocument = async (file, category) => {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("category", category);
  const response = await api.post("/admin/documents/upload", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return response.data;
};

export const replaceDocument = async (docId, file, category) => {
  const formData = new FormData();
  formData.append("file", file);
  if (category) {
    formData.append("category", category);
  }
  const response = await api.put(`/admin/documents/${docId}/replace`, formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return response.data;
};

export const getDocuments = async (filters = {}) => {
  const response = await api.get("/admin/documents", { params: filters });
  return response.data;
};

export const deleteDocument = async (docId) => {
  const response = await api.delete(`/admin/documents/${docId}`);
  return response.data;
};

export const getDocumentStatus = async (docId) => {
  const response = await api.get(`/admin/documents/status/${docId}`);
  return response.data;
};

export const getAnalytics = async () => {
  const response = await api.get("/admin/analytics/summary");
  return response.data;
};

export const getRecentAnalytics = async (limit = 20) => {
  const response = await api.get("/admin/analytics/recent", { params: { limit } });
  return response.data;
};

export const getAdminUsers = async () => {
  const response = await api.get("/admin/users");
  return response.data;
};

export const createStudent = async (payload) => {
  const response = await api.post("/admin/users", payload);
  return response.data;
};

export const getColleges = async () => {
  const response = await api.get("/super/colleges");
  return response.data;
};

export const addCollege = async (data) => {
  const response = await api.post("/super/colleges", data);
  return response.data;
};

export const getSuperStats = async () => {
  const response = await api.get("/super/stats");
  return response.data;
};

export const getSuperUsers = async () => {
  const response = await api.get("/super/users");
  return response.data;
};
