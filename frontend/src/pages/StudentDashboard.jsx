import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { getStudentDashboard } from "../api/client";
import { useAuth } from "../context/AuthContext";

const Field = ({ label, value }) => (
  <div>
    <p className="text-xs text-gray-500">{label}</p>
    <p className="mt-1 text-sm font-semibold text-gray-800">{value || "Not provided"}</p>
  </div>
);

const StudentDashboard = () => {
  const { logout } = useAuth();
  const navigate = useNavigate();
  const [dashboard, setDashboard] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;

    const loadDashboard = async () => {
      try {
        const data = await getStudentDashboard();
        if (active) {
          setDashboard(data);
        }
      } catch (err) {
        if (err.status === 401 || err.status === 404) {
          await logout({
            message: err.status === 404 ? "Student profile not found. Please login with a registered student account." : err.message,
          });
          return;
        }
        if (active) {
          setError(err.message);
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    };

    loadDashboard();
    return () => {
      active = false;
    };
  }, [logout]);

  if (loading) {
    return <div className="flex min-h-screen items-center justify-center bg-wa-bg text-gray-500">Loading...</div>;
  }

  if (error) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-wa-bg px-4">
        <div className="rounded-xl bg-white p-5 text-sm text-red-600 shadow-sm">{error}</div>
      </div>
    );
  }

  if (!dashboard) {
    return <div className="flex min-h-screen items-center justify-center bg-wa-bg text-gray-500">Redirecting...</div>;
  }

  const student = dashboard.student;

  return (
    <div className="min-h-screen bg-wa-bg">
      <header className="bg-wa-dark px-4 py-4 text-white shadow">
        <div className="mx-auto flex max-w-7xl items-center justify-between">
          <div>
            <p className="text-xs text-emerald-100">{dashboard.college_name}</p>
            <h1 className="text-xl font-bold">{student.name}</h1>
          </div>
          <button
            type="button"
            onClick={logout}
            className="rounded-md border border-white/40 px-3 py-2 text-sm font-semibold"
          >
            Logout
          </button>
        </div>
      </header>

      <main className="mx-auto max-w-7xl space-y-5 px-4 py-5">
        <section className="grid gap-3 md:grid-cols-5">
          <div className="rounded-xl bg-white p-4 shadow-sm">
            <Field label="Department" value={student.department} />
          </div>
          <div className="rounded-xl bg-white p-4 shadow-sm">
            <Field label="Year" value={student.year} />
          </div>
          <div className="rounded-xl bg-white p-4 shadow-sm">
            <Field label="Semester" value={student.semester} />
          </div>
          <div className="rounded-xl bg-white p-4 shadow-sm">
            <Field label="Section" value={student.section} />
          </div>
          <div className="rounded-xl bg-white p-4 shadow-sm">
            <Field label="Session" value={student.session} />
          </div>
        </section>

        <section className="grid gap-5 lg:grid-cols-[1.4fr_1fr]">
          <div className="rounded-xl bg-white p-5 shadow-sm">
            <h2 className="text-base font-bold text-wa-dark">Profile</h2>
            <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              <Field label="Full Name" value={student.name} />
              <Field label="Admission No" value={student.admission_no} />
              <Field label="Department" value={student.department} />
              <Field label="Course" value={student.course} />
              <Field label="Year" value={student.year} />
              <Field label="Semester" value={student.semester} />
              <Field label="Section" value={student.section} />
              <Field label="Session" value={student.session} />
              <Field label="Batch" value={student.batch} />
              <Field label="Roll No" value={student.roll_no} />
              <Field label="Phone" value={student.phone} />
              <Field label="Category" value={student.category} />
              <Field label="Hosteler" value={student.is_hosteler ? "Yes" : "No"} />
            </div>
          </div>

          <div className="space-y-5">
            <div className="rounded-xl bg-white p-5 shadow-sm">
              <h2 className="text-base font-bold text-wa-dark">Quick Stats</h2>
              <div className="mt-4 grid gap-3">
                <Field label="Total AI Queries" value={dashboard.total_queries} />
                <Field label="Active Documents" value={dashboard.quick_stats.documents_available} />
              </div>
              <button
                type="button"
                onClick={() => navigate("/chat")}
                className="mt-5 w-full rounded-md bg-wa-green px-4 py-2.5 text-sm font-semibold text-white"
              >
                Ask AI Assistant
              </button>
            </div>

            <div className="rounded-xl bg-white p-5 shadow-sm">
              <h2 className="text-base font-bold text-wa-dark">Recent Queries</h2>
              <div className="mt-3 space-y-2">
                {dashboard.recent_queries.map((query) => (
                  <div key={query.id} className="rounded-md bg-gray-50 px-3 py-2">
                    <p className="text-sm font-medium text-gray-800">{query.query_text}</p>
                    <p className="mt-1 text-xs text-gray-500">{query.confidence}</p>
                  </div>
                ))}
                {dashboard.recent_queries.length === 0 && (
                  <p className="text-sm text-gray-500">No recent queries yet.</p>
                )}
              </div>
            </div>
          </div>
        </section>
      </main>
    </div>
  );
};

export default StudentDashboard;
