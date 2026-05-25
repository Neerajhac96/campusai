import { useEffect, useState } from "react";
import { addCollege, getColleges, getSuperStats } from "../api/client";
import Navbar from "../components/Navbar";

const SuperAdminPanel = () => {
  const [stats, setStats] = useState(null);
  const [colleges, setColleges] = useState([]);
  const [loading, setLoading] = useState(false);

  const [collegeId, setCollegeId] = useState("");
  const [collegeName, setCollegeName] = useState("");
  const [collegeSlug, setCollegeSlug] = useState("");
  const [plan, setPlan] = useState("starter");

  const loadData = async () => {
    setLoading(true);
    try {
      const [statsData, collegesData] = await Promise.all([getSuperStats(), getColleges()]);
      setStats(statsData);
      setColleges(collegesData || []);
    } catch (error) {
      window.alert(error.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const onAddCollege = async (event) => {
    event.preventDefault();
    try {
      await addCollege({
        id: collegeId,
        name: collegeName,
        slug: collegeSlug,
        plan,
      });
      setCollegeId("");
      setCollegeName("");
      setCollegeSlug("");
      setPlan("starter");
      await loadData();
    } catch (error) {
      window.alert(error.message);
    }
  };

  return (
    <div className="min-h-screen bg-wa-bg">
      <Navbar title="CampusAI Super Admin" subtitle="Platform-level operations and growth metrics" />
      <main className="mx-auto max-w-7xl space-y-5 px-4 py-5">
        {loading && !stats ? <p className="text-sm text-gray-500">Loading platform stats...</p> : null}

        {stats && (
          <div className="grid gap-4 md:grid-cols-5">
            <div className="rounded-xl bg-white p-4 shadow-sm">
              <p className="text-xs text-gray-500">Total Colleges</p>
              <p className="mt-1 text-2xl font-bold text-wa-dark">{stats.total_colleges}</p>
            </div>
            <div className="rounded-xl bg-white p-4 shadow-sm">
              <p className="text-xs text-gray-500">Total Students</p>
              <p className="mt-1 text-2xl font-bold text-wa-dark">{stats.total_students}</p>
            </div>
            <div className="rounded-xl bg-white p-4 shadow-sm">
              <p className="text-xs text-gray-500">Queries Today</p>
              <p className="mt-1 text-2xl font-bold text-wa-dark">{stats.total_queries_today}</p>
            </div>
            <div className="rounded-xl bg-white p-4 shadow-sm">
              <p className="text-xs text-gray-500">Queries This Month</p>
              <p className="mt-1 text-2xl font-bold text-wa-dark">{stats.total_queries_month}</p>
            </div>
            <div className="rounded-xl bg-white p-4 shadow-sm">
              <p className="text-xs text-gray-500">Revenue Estimate</p>
              <p className="mt-1 text-2xl font-bold text-wa-dark">₹{stats.revenue_estimate_inr}</p>
            </div>
          </div>
        )}

        <form onSubmit={onAddCollege} className="rounded-xl bg-white p-4 shadow-sm">
          <h3 className="text-sm font-semibold text-gray-800">Add New College</h3>
          <div className="mt-3 grid gap-3 md:grid-cols-4">
            <input
              type="text"
              required
              value={collegeId}
              onChange={(event) => setCollegeId(event.target.value)}
              placeholder="col_aktu"
              className="rounded-md border border-gray-300 p-2 text-sm"
            />
            <input
              type="text"
              required
              value={collegeName}
              onChange={(event) => setCollegeName(event.target.value)}
              placeholder="College Name"
              className="rounded-md border border-gray-300 p-2 text-sm"
            />
            <input
              type="text"
              required
              value={collegeSlug}
              onChange={(event) => setCollegeSlug(event.target.value)}
              placeholder="college-slug"
              className="rounded-md border border-gray-300 p-2 text-sm"
            />
            <select
              value={plan}
              onChange={(event) => setPlan(event.target.value)}
              className="rounded-md border border-gray-300 p-2 text-sm"
            >
              <option value="starter">starter</option>
              <option value="growth">growth</option>
              <option value="university">university</option>
            </select>
          </div>
          <button
            type="submit"
            className="mt-3 rounded-md bg-wa-dark px-4 py-2 text-sm font-semibold text-white"
          >
            Create College
          </button>
        </form>

        <div className="overflow-x-auto rounded-xl bg-white p-4 shadow-sm">
          <h3 className="mb-3 text-sm font-semibold text-gray-800">All Colleges</h3>
          <table className="min-w-full text-left text-sm">
            <thead className="text-xs uppercase text-gray-500">
              <tr>
                <th className="py-2 pr-4">College</th>
                <th className="py-2 pr-4">Plan</th>
                <th className="py-2 pr-4">Users</th>
                <th className="py-2 pr-4">Documents</th>
                <th className="py-2 pr-4">Queries</th>
                <th className="py-2 pr-4">Status</th>
              </tr>
            </thead>
            <tbody>
              {colleges.map((college) => (
                <tr key={college.id} className="border-t border-gray-100">
                  <td className="py-2 pr-4">
                    <p className="font-semibold text-gray-800">{college.name}</p>
                    <p className="text-xs text-gray-500">{college.id}</p>
                  </td>
                  <td className="py-2 pr-4 capitalize">{college.plan}</td>
                  <td className="py-2 pr-4">{college.total_users}</td>
                  <td className="py-2 pr-4">{college.total_documents}</td>
                  <td className="py-2 pr-4">{college.total_queries}</td>
                  <td className="py-2 pr-4">{college.is_active ? "Active" : "Inactive"}</td>
                </tr>
              ))}
              {colleges.length === 0 && (
                <tr>
                  <td className="py-4 text-sm text-gray-500" colSpan={6}>
                    No colleges available.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {stats?.most_active_colleges?.length > 0 && (
          <div className="rounded-xl bg-white p-4 shadow-sm">
            <h3 className="mb-3 text-sm font-semibold text-gray-800">Most Active Colleges</h3>
            <div className="space-y-2">
              {stats.most_active_colleges.map((item) => (
                <div key={item.college_id} className="flex items-center justify-between rounded-md bg-gray-50 px-3 py-2">
                  <span className="text-sm text-gray-800">{item.college_name}</span>
                  <span className="text-sm font-semibold text-wa-dark">{item.queries} queries</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </main>
    </div>
  );
};

export default SuperAdminPanel;
