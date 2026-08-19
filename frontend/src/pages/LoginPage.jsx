import { useEffect, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

const LoginPage = () => {
  const { login, user, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const routeForRole = (role) => {
    if (role === "student") return "/dashboard";
    if (role === "admin") return "/admin";
    if (role === "hod") return "/hod";
    if (role === "dept_coordinator") return "/coordinator";
    if (role === "faculty") return "/faculty";
    return "/super";
  };

  useEffect(() => {
    if (!isAuthenticated || !user) {
      return;
    }
    navigate(routeForRole(user.role), { replace: true });
  }, [isAuthenticated, user, navigate]);

  const onSubmit = async (event) => {
    event.preventDefault();
    setError("");
    setLoading(true);
    try {
      const loggedInUser = await login(email, password);
      navigate(routeForRole(loggedInUser.role), { replace: true });
    } catch (err) {
      setError(err.message || "Invalid credentials");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-wa-bg px-4">
      <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-xl">
        <div className="text-center">
          <div className="mx-auto mb-3 flex h-16 w-16 items-center justify-center rounded-full bg-wa-dark text-2xl font-bold text-white">
            CA
          </div>
          <h1 className="text-2xl font-bold text-wa-dark">CampusAI</h1>
          <p className="mt-1 text-sm text-gray-500">
            AI Assistant for college students in Hindi and English
          </p>
        </div>

        <form onSubmit={onSubmit} className="mt-6 space-y-4">
          {location.state?.message && (
            <p
              className={`rounded-md px-3 py-2 text-sm ${
                location.state.kind === "auth" ? "bg-amber-50 text-amber-700" : "bg-green-50 text-green-700"
              }`}
            >
              {location.state.message}
            </p>
          )}

          <div>
            <label htmlFor="email" className="mb-1 block text-sm font-medium text-gray-700">
              Email
            </label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              required
              className="w-full rounded-md border border-gray-300 p-2.5 text-sm focus:border-wa-dark focus:outline-none"
            />
          </div>

          <div>
            <label htmlFor="password" className="mb-1 block text-sm font-medium text-gray-700">
              Password
            </label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
              className="w-full rounded-md border border-gray-300 p-2.5 text-sm focus:border-wa-dark focus:outline-none"
            />
          </div>

          {error && <p className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-600">{error}</p>}

          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-md bg-wa-dark px-4 py-2.5 text-sm font-semibold text-white hover:bg-[#05453e] disabled:opacity-60"
          >
            {loading ? "Signing in..." : "Login to CampusAI"}
          </button>
        </form>

        <p className="mt-4 text-center text-sm text-gray-600">
          New student?{" "}
          <Link to="/register" className="font-semibold text-wa-dark">
            Register here
          </Link>
        </p>

        <div className="mt-6 rounded-lg border border-gray-200 bg-gray-50 p-3 text-xs text-gray-600">
          <p className="font-semibold text-gray-700">Demo Credentials</p>
          <p>Admin: admin@demo.com / admin123</p>
          <p>Student: student@demo.com / student123</p>
          <p>HOD: hod.cse@demo.com / hod123</p>
          <p>Coordinator: coord.cse@demo.com / coord123</p>
          <p>Faculty: faculty.cse@demo.com / faculty123</p>
          <p>Super Admin: super@chatdeva.com / super123</p>
        </div>
      </div>
    </div>
  );
};

export default LoginPage;
