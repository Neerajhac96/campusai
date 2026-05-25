import { Navigate, Route, Routes } from "react-router-dom";
import LoginPage from "./pages/LoginPage";
import StudentChat from "./pages/StudentChat";
import AdminDashboard from "./pages/AdminDashboard";
import SuperAdminPanel from "./pages/SuperAdminPanel";
import { useAuth } from "./context/AuthContext";

const ProtectedRoute = ({ children, allowedRoles }) => {
  const { user, loading, isAuthenticated } = useAuth();

  if (loading) {
    return <div className="flex min-h-screen items-center justify-center text-gray-500">Loading...</div>;
  }
  if (!isAuthenticated || !user) {
    return <Navigate to="/login" replace />;
  }
  if (allowedRoles && !allowedRoles.includes(user.role)) {
    if (user.role === "student") {
      return <Navigate to="/chat" replace />;
    }
    if (user.role === "admin") {
      return <Navigate to="/admin" replace />;
    }
    return <Navigate to="/super" replace />;
  }
  return children;
};

const RootRedirect = () => {
  const { user, isAuthenticated, loading } = useAuth();

  if (loading) {
    return <div className="flex min-h-screen items-center justify-center text-gray-500">Loading...</div>;
  }
  if (!isAuthenticated || !user) {
    return <Navigate to="/login" replace />;
  }
  if (user.role === "student") {
    return <Navigate to="/chat" replace />;
  }
  if (user.role === "admin") {
    return <Navigate to="/admin" replace />;
  }
  return <Navigate to="/super" replace />;
};

const App = () => (
  <Routes>
    <Route path="/" element={<RootRedirect />} />
    <Route path="/login" element={<LoginPage />} />
    <Route
      path="/chat"
      element={
        <ProtectedRoute allowedRoles={["student", "admin"]}>
          <StudentChat />
        </ProtectedRoute>
      }
    />
    <Route
      path="/admin"
      element={
        <ProtectedRoute allowedRoles={["admin"]}>
          <AdminDashboard />
        </ProtectedRoute>
      }
    />
    <Route
      path="/super"
      element={
        <ProtectedRoute allowedRoles={["super_admin"]}>
          <SuperAdminPanel />
        </ProtectedRoute>
      }
    />
    <Route path="*" element={<Navigate to="/" replace />} />
  </Routes>
);

export default App;
