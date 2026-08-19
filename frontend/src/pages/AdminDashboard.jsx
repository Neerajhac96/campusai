import { useEffect, useMemo, useRef, useState } from "react";
import {
  bulkUploadStudents,
  createFaculty,
  deleteFaculty,
  getAdminUsers,
  getAdmittedStudents,
  getAnalytics,
  getDepartments,
  getDocuments,
  getFaculty,
  getRecentAnalytics,
} from "../api/client";
import AnalyticsDashboard from "../components/AnalyticsDashboard";
import DocumentManager from "../components/DocumentManager";
import Navbar from "../components/Navbar";

const tabs = ["overview", "documents", "analytics", "students", "faculty"];

const AdminDashboard = () => {
  const [activeTab, setActiveTab] = useState("overview");
  const [analytics, setAnalytics] = useState(null);
  const [documentsCount, setDocumentsCount] = useState(0);
  const [recentQueries, setRecentQueries] = useState([]);
  const [students, setStudents] = useState([]);
  const [loading, setLoading] = useState(false);
  const [admittedStudents, setAdmittedStudents] = useState([]);
  const [uploadResult, setUploadResult] = useState(null);
  const [studentSearch, setStudentSearch] = useState("");
  const [departmentFilter, setDepartmentFilter] = useState("");
  const [yearFilter, setYearFilter] = useState("");
  const [sectionFilter, setSectionFilter] = useState("");
  const [registeredFilter, setRegisteredFilter] = useState("");
  const [faculty, setFaculty] = useState([]);
  const [departments, setDepartments] = useState([]);
  const [facultyForm, setFacultyForm] = useState({
    name: "",
    email: "",
    employee_id: "",
    department: "",
    designation: "Assistant Professor",
    role_type: "faculty",
    subjects: "",
  });
  const fileInputRef = useRef(null);

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

  const loadAdmittedStudents = async () => {
    try {
      const data = await getAdmittedStudents({
        ...(departmentFilter ? { department: departmentFilter } : {}),
        ...(yearFilter ? { year: yearFilter } : {}),
        ...(sectionFilter ? { section: sectionFilter } : {}),
        ...(registeredFilter ? { is_registered: registeredFilter } : {}),
      });
      setAdmittedStudents(data.items || []);
    } catch (error) {
      window.alert(error.message);
    }
  };

  useEffect(() => {
    if (activeTab === "students") {
      loadAdmittedStudents();
    }
  }, [activeTab, departmentFilter, yearFilter, sectionFilter, registeredFilter]);

  const loadFaculty = async () => {
    try {
      const [facultyData, departmentData] = await Promise.all([getFaculty(), getDepartments()]);
      setFaculty(facultyData || []);
      setDepartments(departmentData || []);
      if (!facultyForm.department && departmentData?.[0]?.code) {
        setFacultyForm((current) => ({ ...current, department: departmentData[0].code }));
      }
    } catch (error) {
      window.alert(error.message);
    }
  };

  useEffect(() => {
    if (activeTab === "faculty") {
      loadFaculty();
    }
  }, [activeTab]);

  const uploadStudentCsv = async (event) => {
    const file = event.target.files?.[0];
    if (!file) {
      return;
    }
    try {
      const result = await bulkUploadStudents(file);
      setUploadResult(result);
      await loadAdmittedStudents();
    } catch (error) {
      window.alert(error.message);
    } finally {
      event.target.value = "";
    }
  };

  const submitFaculty = async (event) => {
    event.preventDefault();
    try {
      const result = await createFaculty({
        ...facultyForm,
        subjects: facultyForm.subjects
          .split(",")
          .map((item) => item.trim())
          .filter(Boolean),
      });
      window.alert(`Faculty created. Temporary password: ${result.temp_password}`);
      setFacultyForm({
        name: "",
        email: "",
        employee_id: "",
        department: departments[0]?.code || "",
        designation: "Assistant Professor",
        role_type: "faculty",
        subjects: "",
      });
      await loadFaculty();
    } catch (error) {
      window.alert(error.message);
    }
  };

  const deactivateFaculty = async (userId) => {
    if (!window.confirm("Deactivate this faculty account?")) {
      return;
    }
    try {
      await deleteFaculty(userId);
      await loadFaculty();
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

  const filteredAdmittedStudents = useMemo(() => {
    const query = studentSearch.trim().toLowerCase();
    if (!query) {
      return admittedStudents;
    }
    return admittedStudents.filter((student) => {
      const name = (student.name || "").toLowerCase();
      const admissionNo = (student.admission_no || "").toLowerCase();
      return name.includes(query) || admissionNo.includes(query);
    });
  }, [admittedStudents, studentSearch]);

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
              <div>
                <h3 className="text-sm font-semibold text-gray-800">Admitted Students</h3>
                <p className="mt-1 text-xs text-gray-500">Upload college admission lists and track registration.</p>
              </div>
              <div className="flex items-center gap-2">
                <a
                  href="/sample_students.csv"
                  className="rounded-md border border-gray-300 px-3 py-2 text-sm font-semibold text-gray-700"
                >
                  Sample CSV
                </a>
                <button
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  className="rounded-md bg-wa-dark px-3 py-2 text-sm font-semibold text-white"
                >
                  Upload CSV
                </button>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".csv"
                  className="hidden"
                  onChange={uploadStudentCsv}
                />
              </div>
            </div>

            {uploadResult && (
              <div className="rounded-xl bg-white p-4 shadow-sm">
                <div className="grid gap-3 sm:grid-cols-3">
                  <div>
                    <p className="text-xs text-gray-500">Rows Processed</p>
                    <p className="text-xl font-bold text-wa-dark">{uploadResult.total_uploaded}</p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-500">Success</p>
                    <p className="text-xl font-bold text-green-600">{uploadResult.success}</p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-500">Failed</p>
                    <p className="text-xl font-bold text-red-600">{uploadResult.failed}</p>
                  </div>
                </div>
                {uploadResult.errors?.length > 0 && (
                  <div className="mt-3 max-h-32 overflow-y-auto rounded-md bg-red-50 p-3 text-xs text-red-700">
                    {uploadResult.errors.map((item) => (
                      <p key={item}>{item}</p>
                    ))}
                  </div>
                )}
              </div>
            )}

            <div className="grid gap-3 rounded-xl bg-white p-4 shadow-sm md:grid-cols-5">
              <input
                type="text"
                value={studentSearch}
                onChange={(event) => setStudentSearch(event.target.value)}
                placeholder="Search name or admission no"
                className="rounded-md border border-gray-300 p-2 text-sm md:col-span-2"
              />
              <input
                type="text"
                value={departmentFilter}
                onChange={(event) => setDepartmentFilter(event.target.value)}
                placeholder="Department"
                className="rounded-md border border-gray-300 p-2 text-sm"
              />
              <input
                type="text"
                value={sectionFilter}
                onChange={(event) => setSectionFilter(event.target.value)}
                placeholder="Section"
                className="rounded-md border border-gray-300 p-2 text-sm"
              />
              <div className="grid grid-cols-2 gap-2">
                <select
                  value={yearFilter}
                  onChange={(event) => setYearFilter(event.target.value)}
                  className="rounded-md border border-gray-300 p-2 text-sm"
                >
                  <option value="">Year</option>
                  <option value="1">1</option>
                  <option value="2">2</option>
                  <option value="3">3</option>
                  <option value="4">4</option>
                </select>
                <select
                  value={registeredFilter}
                  onChange={(event) => setRegisteredFilter(event.target.value)}
                  className="rounded-md border border-gray-300 p-2 text-sm"
                >
                  <option value="">All</option>
                  <option value="true">Registered</option>
                  <option value="false">Pending</option>
                </select>
              </div>
            </div>

            <div className="overflow-x-auto rounded-xl bg-white p-4 shadow-sm">
              <table className="min-w-full text-left text-sm">
                <thead className="text-xs uppercase text-gray-500">
                  <tr>
                    <th className="py-2 pr-4">Admission No</th>
                    <th className="py-2 pr-4">Name</th>
                    <th className="py-2 pr-4">Department</th>
                    <th className="py-2 pr-4">Year</th>
                    <th className="py-2 pr-4">Section</th>
                    <th className="py-2 pr-4">Registered</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredAdmittedStudents.map((student) => (
                    <tr key={student.id} className="border-t border-gray-100">
                      <td className="py-2 pr-4 font-semibold text-gray-800">{student.admission_no}</td>
                      <td className="py-2 pr-4">{student.name}</td>
                      <td className="py-2 pr-4">{student.department}</td>
                      <td className="py-2 pr-4">{student.year}</td>
                      <td className="py-2 pr-4">{student.section}</td>
                      <td className="py-2 pr-4">
                        <span
                          className={`rounded-full px-2 py-1 text-xs font-semibold ${
                            student.is_registered ? "bg-green-50 text-green-700" : "bg-amber-50 text-amber-700"
                          }`}
                        >
                          {student.is_registered ? "Yes" : "No"}
                        </span>
                      </td>
                    </tr>
                  ))}
                  {filteredAdmittedStudents.length === 0 && (
                    <tr>
                      <td colSpan={6} className="py-4 text-sm text-gray-500">
                        No admitted students found.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {activeTab === "faculty" && (
          <div className="space-y-4">
            <form onSubmit={submitFaculty} className="grid gap-3 rounded-xl bg-white p-4 shadow-sm md:grid-cols-4">
              <input
                value={facultyForm.name}
                onChange={(event) => setFacultyForm({ ...facultyForm, name: event.target.value })}
                placeholder="Faculty name"
                className="rounded-md border border-gray-300 p-2 text-sm"
                required
              />
              <input
                type="email"
                value={facultyForm.email}
                onChange={(event) => setFacultyForm({ ...facultyForm, email: event.target.value })}
                placeholder="Email"
                className="rounded-md border border-gray-300 p-2 text-sm"
                required
              />
              <input
                value={facultyForm.employee_id}
                onChange={(event) => setFacultyForm({ ...facultyForm, employee_id: event.target.value })}
                placeholder="Employee ID"
                className="rounded-md border border-gray-300 p-2 text-sm"
                required
              />
              <select
                value={facultyForm.department}
                onChange={(event) => setFacultyForm({ ...facultyForm, department: event.target.value })}
                className="rounded-md border border-gray-300 p-2 text-sm"
                required
              >
                <option value="">Department</option>
                {departments.map((department) => (
                  <option key={department.id || department.code} value={department.code}>
                    {department.name} ({department.code})
                  </option>
                ))}
              </select>
              <input
                value={facultyForm.designation}
                onChange={(event) => setFacultyForm({ ...facultyForm, designation: event.target.value })}
                placeholder="Designation"
                className="rounded-md border border-gray-300 p-2 text-sm"
              />
              <select
                value={facultyForm.role_type}
                onChange={(event) => setFacultyForm({ ...facultyForm, role_type: event.target.value })}
                className="rounded-md border border-gray-300 p-2 text-sm"
              >
                <option value="faculty">Faculty</option>
                <option value="dept_coordinator">Dept Coordinator</option>
                <option value="hod">HOD</option>
              </select>
              <input
                value={facultyForm.subjects}
                onChange={(event) => setFacultyForm({ ...facultyForm, subjects: event.target.value })}
                placeholder="Subjects, comma separated"
                className="rounded-md border border-gray-300 p-2 text-sm md:col-span-2"
              />
              <button type="submit" className="rounded-md bg-wa-dark px-3 py-2 text-sm font-semibold text-white">
                Add Faculty
              </button>
            </form>

            <div className="overflow-x-auto rounded-xl bg-white p-4 shadow-sm">
              <table className="min-w-full text-left text-sm">
                <thead className="text-xs uppercase text-gray-500">
                  <tr>
                    <th className="py-2 pr-4">Name</th>
                    <th className="py-2 pr-4">Department</th>
                    <th className="py-2 pr-4">Designation</th>
                    <th className="py-2 pr-4">Role</th>
                    <th className="py-2 pr-4">Status</th>
                    <th className="py-2 pr-4">Action</th>
                  </tr>
                </thead>
                <tbody>
                  {faculty.map((member) => (
                    <tr key={member.user_id} className="border-t border-gray-100">
                      <td className="py-2 pr-4 font-semibold text-gray-800">{member.name}</td>
                      <td className="py-2 pr-4">{member.department}</td>
                      <td className="py-2 pr-4">{member.designation}</td>
                      <td className="py-2 pr-4">
                        <span className="rounded-full bg-green-50 px-2 py-1 text-xs font-semibold text-wa-dark">
                          {member.role_type}
                        </span>
                      </td>
                      <td className="py-2 pr-4">{member.is_active ? "Active" : "Inactive"}</td>
                      <td className="py-2 pr-4">
                        <button
                          type="button"
                          onClick={() => deactivateFaculty(member.user_id)}
                          className="rounded-md border border-red-200 px-3 py-1 text-xs font-semibold text-red-600"
                        >
                          Deactivate
                        </button>
                      </td>
                    </tr>
                  ))}
                  {faculty.length === 0 && (
                    <tr>
                      <td colSpan={6} className="py-4 text-sm text-gray-500">
                        No faculty accounts found.
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
