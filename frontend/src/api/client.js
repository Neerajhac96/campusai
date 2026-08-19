import axios from "axios";

const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";
const TOKEN_KEY = "campusai_token";

let unauthorizedHandler = null;

export const setUnauthorizedHandler = (handler) => {
  unauthorizedHandler = handler;
};

export const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 45000,
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_KEY);
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error?.response?.status;
    if (status === 401) {
      let handled = false;
      if (unauthorizedHandler) {
        handled = Boolean(unauthorizedHandler({
          reason: "unauthorized",
          message: "Session expired. Please login again.",
        }));
      }
      if (!handled && window.location.pathname !== "/login") {
        window.location.replace("/login");
      }
    }

    const detail =
      error?.response?.data?.detail ||
      error?.message ||
      "Something went wrong while contacting CampusAI server";
    const apiError = new Error(detail);
    apiError.status = status;
    apiError.data = error?.response?.data;
    return Promise.reject(apiError);
  }
);

export const clearAuthToken = () => {
  localStorage.removeItem(TOKEN_KEY);
};

export const setAuthToken = (token) => {
  localStorage.setItem(TOKEN_KEY, token);
};

export const getAuthToken = () => localStorage.getItem(TOKEN_KEY);

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

export const checkAdmission = async (collegeId, admissionNo) => {
  const response = await api.get("/auth/check-admission", {
    params: { college_id: collegeId, admission_no: admissionNo },
  });
  return response.data;
};

export const registerStudent = async (data) => {
  const response = await api.post("/auth/register", data);
  return response.data;
};

export const sendQuery = async (query, conversationId = null) => {
  const response = await api.post("/chat/query", {
    query,
    conversation_id: conversationId,
  });
  return response.data;
};

export const getConversations = async () => {
  const response = await api.get("/chat/conversations");
  return response.data;
};

export const getConversation = async (conversationId) => {
  const response = await api.get(`/chat/conversations/${conversationId}`);
  return response.data;
};

export const newConversation = async () => {
  const response = await api.post("/chat/conversations/new");
  return response.data;
};

export const deleteConversation = async (conversationId) => {
  const response = await api.delete(`/chat/conversations/${conversationId}`);
  return response.data;
};

export const updateConversationTitle = async (conversationId, title) => {
  const response = await api.put(`/chat/conversations/${conversationId}/title`, { title });
  return response.data;
};

export const getChatHistory = async (page = 1, limit = 20) => {
  const response = await api.get("/chat/history", { params: { page, limit } });
  return response.data;
};

export const uploadDocument = async (file, category = "general", options = {}) => {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("category", category);
  if (options.department) {
    formData.append("department", options.department);
  }
  if (options.subject) {
    formData.append("subject", options.subject);
  }
  if (options.doc_scope) {
    formData.append("doc_scope", options.doc_scope);
  }
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

export const bulkUploadStudents = async (file) => {
  const formData = new FormData();
  formData.append("file", file);
  const response = await api.post("/admin/students/bulk-upload", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return response.data;
};

export const getAdmittedStudents = async (filters = {}) => {
  const response = await api.get("/admin/students/admitted", { params: filters });
  return response.data;
};

export const getStudentProfile = async () => {
  const response = await api.get("/student/profile");
  return response.data;
};

export const updateStudentProfile = async (data) => {
  const response = await api.put("/student/profile", data);
  return response.data;
};

export const getStudentDashboard = async () => {
  const response = await api.get("/student/dashboard");
  return response.data;
};

export const createFaculty = async (data) => {
  const response = await api.post("/admin/faculty", data);
  return response.data;
};

export const getFaculty = async (filters = {}) => {
  const response = await api.get("/admin/faculty", { params: filters });
  return response.data;
};

export const deleteFaculty = async (userId) => {
  const response = await api.delete(`/admin/faculty/${userId}`);
  return response.data;
};

export const createDepartment = async (data) => {
  const response = await api.post("/admin/departments", data);
  return response.data;
};

export const getDepartments = async () => {
  const response = await api.get("/admin/departments");
  return response.data;
};

export const getFacultyProfile = async () => {
  const response = await api.get("/faculty/profile");
  return response.data;
};

export const getFacultyDashboard = async () => {
  const response = await api.get("/faculty/dashboard");
  return response.data;
};

export const getFacultyStudents = async (filters = {}) => {
  const response = await api.get("/faculty/students", { params: filters });
  return response.data;
};

export const updateFacultyProfile = async (data) => {
  const response = await api.put("/faculty/profile", data);
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
