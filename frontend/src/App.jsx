import { Navigate, Route, Routes } from "react-router-dom";
import LoginPage from "./pages/LoginPage";
import StudentChat from "./pages/StudentChat";
import AdminDashboard from "./pages/AdminDashboard";
import SuperAdminPanel from "./pages/SuperAdminPanel";
import RegisterPage from "./pages/RegisterPage";
import StudentDashboard from "./pages/StudentDashboard";
import FacultyDashboard from "./pages/FacultyDashboard";
import HODDashboard from "./pages/HODDashboard";
import CoordinatorDashboard from "./pages/CoordinatorDashboard";
import { useAuth } from "./context/AuthContext";

const FullPageStatus = ({ title, subtitle }) => (
  <div className="flex min-h-screen items-center justify-center bg-wa-bg px-4">
    <div className="rounded-xl bg-white px-5 py-4 text-center shadow-sm">
      <p className="text-sm font-semibold text-wa-dark">{title}</p>
      {subtitle ? <p className="mt-1 text-xs text-gray-500">{subtitle}</p> : null}
    </div>
  </div>
);

const ProtectedRoute = ({ children, allowedRoles }) => {
  const { user, loading, isAuthenticated } = useAuth();

  if (loading) {
    return <FullPageStatus title="Checking session..." subtitle="Please wait" />;
  }
  if (!isAuthenticated || !user) {
    return <Navigate to="/login" replace />;
  }
  if (allowedRoles && !allowedRoles.includes(user.role)) {
    if (user.role === "student") {
      return <Navigate to="/dashboard" replace />;
    }
    if (user.role === "admin") {
      return <Navigate to="/admin" replace />;
    }
    if (user.role === "hod") {
      return <Navigate to="/hod" replace />;
    }
    if (user.role === "dept_coordinator") {
      return <Navigate to="/coordinator" replace />;
    }
    if (user.role === "faculty") {
      return <Navigate to="/faculty" replace />;
    }
    return <Navigate to="/super" replace />;
  }
  return children;
};

const RootRedirect = () => {
  const { user, isAuthenticated, loading } = useAuth();

  if (loading) {
    return <FullPageStatus title="Checking session..." subtitle="Please wait" />;
  }
  if (!isAuthenticated || !user) {
    return <Navigate to="/login" replace />;
  }
  if (user.role === "student") {
    return <Navigate to="/dashboard" replace />;
  }
  if (user.role === "admin") {
    return <Navigate to="/admin" replace />;
  }
  if (user.role === "hod") {
    return <Navigate to="/hod" replace />;
  }
  if (user.role === "dept_coordinator") {
    return <Navigate to="/coordinator" replace />;
  }
  if (user.role === "faculty") {
    return <Navigate to="/faculty" replace />;
  }
  return <Navigate to="/super" replace />;
};

const App = () => (
  <Routes>
    <Route path="/" element={<RootRedirect />} />
    <Route path="/login" element={<LoginPage />} />
    <Route path="/register" element={<RegisterPage />} />
    <Route
      path="/dashboard"
      element={
        <ProtectedRoute allowedRoles={["student"]}>
          <StudentDashboard />
        </ProtectedRoute>
      }
    />
    <Route
      path="/chat"
      element={
        <ProtectedRoute allowedRoles={["student", "admin", "faculty", "hod", "dept_coordinator"]}>
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
      path="/faculty"
      element={
        <ProtectedRoute allowedRoles={["faculty"]}>
          <FacultyDashboard />
        </ProtectedRoute>
      }
    />
    <Route
      path="/hod"
      element={
        <ProtectedRoute allowedRoles={["hod"]}>
          <HODDashboard />
        </ProtectedRoute>
      }
    />
    <Route
      path="/coordinator"
      element={
        <ProtectedRoute allowedRoles={["dept_coordinator"]}>
          <CoordinatorDashboard />
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
