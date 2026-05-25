import { useEffect, useMemo, useState } from "react";
import { createStudent, getAdminUsers, getAnalytics, getDocuments, getRecentAnalytics } from "../api/client";
import AnalyticsDashboard from "../components/AnalyticsDashboard";
import DocumentManager from "../components/DocumentManager";
import Navbar from "../components/Navbar";

const tabs = ["overview", "documents", "analytics", "students"];

const AdminDashboard = () => {
  const [activeTab, setActiveTab] = useState("overview");
  const [analytics, setAnalytics] = useState(null);
  const [documentsCount, setDocumentsCount] = useState(0);
  const [recentQueries, setRecentQueries] = useState([]);
  const [students, setStudents] = useState([]);
  const [loading, setLoading] = useState(false);

  const [showStudentForm, setShowStudentForm] = useState(false);
  const [studentEmail, setStudentEmail] = useState("");
  const [studentPassword, setStudentPassword] = useState("");
  const [studentName, setStudentName] = useState("");

  const loadOverview = async () => {
    setLoading(true);
    try {
      const [analyticsData, docsData, recentData, studentsData] = await Promise.all([
        getAnalytics(),
        getDocuments(),
        getRecentAnalytics(20),
        getAdminUsers(),
      ]);
      setAnalytics(analyticsData);
      setDocumentsCount(docsData.total || 0);
      setRecentQueries(recentData.items || []);
      setStudents(studentsData || []);
    } catch (error) {
      window.alert(error.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadOverview();
  }, []);

  const addStudent = async (event) => {
    event.preventDefault();
    try {
      await createStudent({
        email: studentEmail,
        password: studentPassword,
        name: studentName,
      });
      setStudentEmail("");
      setStudentPassword("");
      setStudentName("");
      setShowStudentForm(false);
      const users = await getAdminUsers();
      setStudents(users || []);
    } catch (error) {
      window.alert(error.message);
    }
  };

  const chartPoints = useMemo(() => {
    if (!analytics) {
      return [];
    }
    return [...(analytics.queries_per_day || [])].slice(-7);
  }, [analytics]);

  return (
    <div className="min-h-screen bg-wa-bg">
      <Navbar title="CampusAI Admin Dashboard" subtitle="Manage college chatbot data and students" />

      <main className="mx-auto max-w-7xl px-4 py-5">
        <div className="mb-4 flex flex-wrap gap-2">
          {tabs.map((tab) => (
            <button
              key={tab}
              type="button"
              onClick={() => setActiveTab(tab)}
              className={`rounded-full px-4 py-2 text-sm font-semibold capitalize ${
                activeTab === tab
                  ? "bg-wa-dark text-white"
                  : "border border-gray-300 bg-white text-gray-700 hover:bg-gray-50"
              }`}
            >
              {tab}
            </button>
          ))}
        </div>

        {loading && !analytics ? <p className="text-sm text-gray-500">Loading dashboard...</p> : null}

        {activeTab === "overview" && analytics && (
          <div className="space-y-5">
            <div className="grid gap-4 md:grid-cols-4">
              <div className="rounded-xl bg-white p-4 shadow-sm">
                <p className="text-xs text-gray-500">Total Documents</p>
                <p className="mt-1 text-2xl font-bold text-wa-dark">{documentsCount}</p>
              </div>
              <div className="rounded-xl bg-white p-4 shadow-sm">
                <p className="text-xs text-gray-500">Total Queries</p>
                <p className="mt-1 text-2xl font-bold text-wa-dark">{analytics.total_queries_month}</p>
              </div>
              <div className="rounded-xl bg-white p-4 shadow-sm">
                <p className="text-xs text-gray-500">Resolution Rate</p>
                <p className="mt-1 text-2xl font-bold text-wa-dark">{analytics.resolution_rate}%</p>
              </div>
              <div className="rounded-xl bg-white p-4 shadow-sm">
                <p className="text-xs text-gray-500">Active Students</p>
                <p className="mt-1 text-2xl font-bold text-wa-dark">{students.length}</p>
              </div>
            </div>

            <div className="rounded-xl bg-white p-4 shadow-sm">
              <h3 className="text-sm font-semibold text-gray-700">Queries per Day (Last 7 Days)</h3>
              <div className="mt-4 flex h-44 items-end gap-3">
                {chartPoints.map((point) => {
                  const maxValue = Math.max(1, ...chartPoints.map((row) => row.count));
                  const height = Math.max(10, (point.count / maxValue) * 160);
                  return (
                    <div key={point.day} className="flex min-w-10 flex-col items-center gap-2">
                      <div className="w-8 rounded-t bg-wa-green" style={{ height }} />
                      <span className="text-[10px] text-gray-500">{point.day.slice(5)}</span>
                    </div>
                  );
                })}
              </div>
            </div>

            <div className="rounded-xl bg-white p-4 shadow-sm">
              <h3 className="text-sm font-semibold text-gray-700">Recent Queries</h3>
              <div className="mt-3 overflow-x-auto">
                <table className="min-w-full text-left text-sm">
                  <thead className="text-xs uppercase text-gray-500">
                    <tr>
                      <th className="py-2 pr-4">Query</th>
                      <th className="py-2 pr-4">Language</th>
                      <th className="py-2 pr-4">Confidence</th>
                      <th className="py-2 pr-4">Escalated</th>
                      <th className="py-2 pr-4">Time (ms)</th>
                    </tr>
                  </thead>
                  <tbody>
                    {recentQueries.map((item) => (
                      <tr key={item.id} className="border-t border-gray-100">
                        <td className="py-2 pr-4">{item.query_text}</td>
                        <td className="py-2 pr-4">{item.language}</td>
                        <td className="py-2 pr-4">{item.confidence}</td>
                        <td className="py-2 pr-4">{item.escalated ? "Yes" : "No"}</td>
                        <td className="py-2 pr-4">{item.response_time_ms}</td>
                      </tr>
                    ))}
                    {recentQueries.length === 0 && (
                      <tr>
                        <td className="py-4 text-sm text-gray-500" colSpan={5}>
                          No queries logged yet.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {activeTab === "documents" && <DocumentManager />}

        {activeTab === "analytics" && <AnalyticsDashboard />}

        {activeTab === "students" && (
          <div className="space-y-4">
            <div className="flex items-center justify-between rounded-xl bg-white p-4 shadow-sm">
              <h3 className="text-sm font-semibold text-gray-800">Registered Students</h3>
              <button
                type="button"
                onClick={() => setShowStudentForm((prev) => !prev)}
                className="rounded-md bg-wa-dark px-3 py-2 text-sm font-semibold text-white"
              >
                Add Student
              </button>
            </div>

            {showStudentForm && (
              <form onSubmit={addStudent} className="rounded-xl bg-white p-4 shadow-sm">
                <div className="grid gap-3 md:grid-cols-3">
                  <input
                    type="text"
                    required
                    placeholder="Student name"
                    value={studentName}
                    onChange={(event) => setStudentName(event.target.value)}
                    className="rounded-md border border-gray-300 p-2 text-sm"
                  />
                  <input
                    type="email"
                    required
                    placeholder="student@college.com"
                    value={studentEmail}
                    onChange={(event) => setStudentEmail(event.target.value)}
                    className="rounded-md border border-gray-300 p-2 text-sm"
                  />
                  <input
                    type="password"
                    required
                    placeholder="Password"
                    value={studentPassword}
                    onChange={(event) => setStudentPassword(event.target.value)}
                    className="rounded-md border border-gray-300 p-2 text-sm"
                  />
                </div>
                <button
                  type="submit"
                  className="mt-3 rounded-md bg-wa-green px-4 py-2 text-sm font-semibold text-white"
                >
                  Create Student Account
                </button>
              </form>
            )}

            <div className="overflow-x-auto rounded-xl bg-white p-4 shadow-sm">
              <table className="min-w-full text-left text-sm">
                <thead className="text-xs uppercase text-gray-500">
                  <tr>
                    <th className="py-2 pr-4">Name</th>
                    <th className="py-2 pr-4">Email</th>
                    <th className="py-2 pr-4">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {students.map((student) => (
                    <tr key={student.id} className="border-t border-gray-100">
                      <td className="py-2 pr-4">{student.name}</td>
                      <td className="py-2 pr-4">{student.email}</td>
                      <td className="py-2 pr-4">{student.is_active ? "Active" : "Inactive"}</td>
                    </tr>
                  ))}
                  {students.length === 0 && (
                    <tr>
                      <td colSpan={3} className="py-4 text-sm text-gray-500">
                        No students found.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </main>
    </div>
  );
};

export default AdminDashboard;
