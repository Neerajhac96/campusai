import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  createFaculty,
  deleteDocument,
  getDocuments,
  getFaculty,
  getFacultyDashboard,
  getFacultyStudents,
  uploadDocument,
} from "../api/client";
import { useAuth } from "../context/AuthContext";

const categories = ["general", "notices", "rules", "exam", "placement", "syllabus", "notes"];

const StatCard = ({ label, value }) => (
  <div className="rounded-xl bg-white p-4 shadow-sm">
    <p className="text-xs text-gray-500">{label}</p>
    <p className="mt-1 text-2xl font-bold text-wa-dark">{value}</p>
  </div>
);

const DocumentTable = ({ documents, onDelete, allowDelete = true }) => (
  <div className="overflow-x-auto rounded-xl bg-white p-4 shadow-sm">
    <table className="min-w-full text-left text-sm">
      <thead className="text-xs uppercase text-gray-500">
        <tr>
          <th className="py-2 pr-4">Name</th>
          <th className="py-2 pr-4">Subject</th>
          <th className="py-2 pr-4">Scope</th>
          <th className="py-2 pr-4">Status</th>
          <th className="py-2 pr-4">Date</th>
          {allowDelete ? <th className="py-2 pr-4">Action</th> : null}
        </tr>
      </thead>
      <tbody>
        {documents.map((doc) => (
          <tr key={doc.id} className="border-t border-gray-100">
            <td className="py-2 pr-4 font-semibold text-gray-800">{doc.original_name}</td>
            <td className="py-2 pr-4">{doc.subject || "-"}</td>
            <td className="py-2 pr-4">
              <span className="rounded-full bg-green-50 px-2 py-1 text-xs font-semibold text-wa-dark">
                {doc.doc_scope || "college"}
              </span>
            </td>
            <td className="py-2 pr-4">{doc.status}</td>
            <td className="py-2 pr-4">{doc.uploaded_at ? String(doc.uploaded_at).slice(0, 10) : "-"}</td>
            {allowDelete ? (
              <td className="py-2 pr-4">
                <button
                  type="button"
                  onClick={() => onDelete(doc.id)}
                  className="rounded-md border border-red-200 px-3 py-1 text-xs font-semibold text-red-600"
                >
                  Delete
                </button>
              </td>
            ) : null}
          </tr>
        ))}
        {documents.length === 0 && (
          <tr>
            <td className="py-4 text-sm text-gray-500" colSpan={allowDelete ? 6 : 5}>
              No documents found.
            </td>
          </tr>
        )}
      </tbody>
    </table>
  </div>
);

export const FacultyDashboardBase = ({ mode = "faculty" }) => {
  const navigate = useNavigate();
  const { logout } = useAuth();
  const uploadInputRef = useRef(null);
  const [dashboard, setDashboard] = useState(null);
  const [students, setStudents] = useState([]);
  const [departmentDocs, setDepartmentDocs] = useState([]);
  const [departmentFaculty, setDepartmentFaculty] = useState([]);
  const [activeTab, setActiveTab] = useState(mode === "faculty" ? "documents" : "departmentDocuments");
  const [loading, setLoading] = useState(true);
  const [category, setCategory] = useState("general");
  const [docScope, setDocScope] = useState(mode === "faculty" ? "subject" : "department");
  const [subject, setSubject] = useState("");
  const [studentSearch, setStudentSearch] = useState("");
  const [facultyForm, setFacultyForm] = useState({
    name: "",
    email: "",
    employee_id: "",
    designation: "Assistant Professor",
    role_type: "faculty",
    subjects: "",
  });

  const isHod = mode === "hod";
  const isCoordinator = mode === "coordinator";

  const loadData = async () => {
    setLoading(true);
    try {
      const [dashboardData, studentsData] = await Promise.all([
        getFacultyDashboard(),
        getFacultyStudents(),
      ]);
      setDashboard(dashboardData);
      setStudents(studentsData.items || []);

      if (isHod || isCoordinator) {
        const docsData = await getDocuments();
        setDepartmentDocs(docsData.items || []);
      }
      if (isHod) {
        const facultyData = await getFaculty();
        setDepartmentFaculty(facultyData || []);
      }
    } catch (error) {
      if (error.status === 401 || error.status === 403 || error.status === 404) {
        logout({ replace: true });
        return;
      }
      window.alert(error.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [mode]);

  const profile = dashboard?.profile;
  const departmentInfo = dashboard?.department_info;
  const myDocuments = dashboard?.my_documents || [];
  const currentDocuments = isHod || isCoordinator ? departmentDocs : myDocuments;

  const filteredStudents = useMemo(() => {
    const query = studentSearch.trim().toLowerCase();
    if (!query) {
      return students;
    }
    return students.filter((student) => (student.name || "").toLowerCase().includes(query));
  }, [students, studentSearch]);

  const tabs = useMemo(() => {
    if (isHod) {
      return ["documents", "students", "analytics", "faculty", "departmentDocuments"];
    }
    if (isCoordinator) {
      return ["departmentDocuments", "students", "analytics"];
    }
    return ["documents", "students", "analytics"];
  }, [isHod, isCoordinator]);

  const handleUpload = async (event) => {
    const file = event.target.files?.[0];
    if (!file) {
      return;
    }
    try {
      await uploadDocument(file, category, {
        doc_scope: isCoordinator ? "department" : docScope,
        subject,
      });
      await loadData();
      window.alert("Document upload started. Status will update after indexing.");
    } catch (error) {
      window.alert(error.message);
    } finally {
      event.target.value = "";
    }
  };

  const handleDeleteDocument = async (docId) => {
    if (!window.confirm("Delete this document?")) {
      return;
    }
    try {
      await deleteDocument(docId);
      await loadData();
    } catch (error) {
      window.alert(error.message);
    }
  };

  const handleCreateFaculty = async (event) => {
    event.preventDefault();
    try {
      const result = await createFaculty({
        ...facultyForm,
        department: profile.department,
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
        designation: "Assistant Professor",
        role_type: "faculty",
        subjects: "",
      });
      await loadData();
    } catch (error) {
      window.alert(error.message);
    }
  };

  if (loading && !dashboard) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-wa-bg px-4">
        <div className="rounded-xl bg-white px-5 py-4 text-center shadow-sm">
          <p className="text-sm font-semibold text-wa-dark">Loading dashboard...</p>
          <p className="mt-1 text-xs text-gray-500">Checking your faculty access</p>
        </div>
      </div>
    );
  }

  if (!dashboard) {
    return null;
  }

  return (
    <div className="min-h-screen bg-wa-bg">
      <header className="bg-wa-dark px-4 py-4 text-white shadow-sm">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-xs uppercase tracking-wide text-white/70">{profile.college_name}</p>
            <h1 className="text-xl font-bold">{profile.name}</h1>
            <p className="text-sm text-white/80">
              {profile.designation} | {profile.department}
            </p>
          </div>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => navigate("/chat")}
              className="rounded-md bg-white/10 px-3 py-2 text-sm font-semibold"
            >
              Ask AI
            </button>
            <button
              type="button"
              onClick={() => logout({ replace: true })}
              className="rounded-md bg-wa-green px-3 py-2 text-sm font-semibold text-wa-dark"
            >
              Logout
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-4 py-5">
        <div className="grid gap-4 md:grid-cols-3">
          <StatCard label="My Documents" value={dashboard.total_documents} />
          <StatCard label="Student Queries Today" value={dashboard.student_queries_today} />
          <StatCard label="Department Students" value={departmentInfo.total_students} />
        </div>

        <div className="my-4 flex flex-wrap gap-2">
          {tabs.map((tab) => (
            <button
              key={tab}
              type="button"
              onClick={() => setActiveTab(tab)}
              className={`rounded-full px-4 py-2 text-sm font-semibold capitalize ${
                activeTab === tab
                  ? "bg-wa-dark text-white"
                  : "border border-gray-300 bg-white text-gray-700"
              }`}
            >
              {tab.replace(/([A-Z])/g, " $1")}
            </button>
          ))}
        </div>

        {(activeTab === "documents" || activeTab === "departmentDocuments") && (
          <div className="space-y-4">
            <div className="rounded-xl bg-white p-4 shadow-sm">
              <div className="grid gap-3 md:grid-cols-5">
                <select
                  value={category}
                  onChange={(event) => setCategory(event.target.value)}
                  className="rounded-md border border-gray-300 p-2 text-sm"
                >
                  {categories.map((item) => (
                    <option key={item} value={item}>
                      {item}
                    </option>
                  ))}
                </select>
                {!isCoordinator && (
                  <select
                    value={docScope}
                    onChange={(event) => setDocScope(event.target.value)}
                    className="rounded-md border border-gray-300 p-2 text-sm"
                  >
                    {isHod ? <option value="department">Department</option> : null}
                    <option value="subject">Subject</option>
                  </select>
                )}
                <input
                  value={subject}
                  onChange={(event) => setSubject(event.target.value)}
                  placeholder="Subject, required for subject scope"
                  className="rounded-md border border-gray-300 p-2 text-sm md:col-span-2"
                />
                <button
                  type="button"
                  onClick={() => uploadInputRef.current?.click()}
                  className="rounded-md bg-wa-dark px-3 py-2 text-sm font-semibold text-white"
                >
                  Upload Document
                </button>
                <input ref={uploadInputRef} type="file" className="hidden" onChange={handleUpload} />
              </div>
            </div>
            <DocumentTable documents={currentDocuments} onDelete={handleDeleteDocument} />
          </div>
        )}

        {activeTab === "students" && (
          <div className="space-y-4">
            <input
              type="text"
              value={studentSearch}
              onChange={(event) => setStudentSearch(event.target.value)}
              placeholder="Search by student name"
              className="w-full rounded-xl border border-gray-300 bg-white p-3 text-sm shadow-sm"
            />
            <div className="overflow-x-auto rounded-xl bg-white p-4 shadow-sm">
              <table className="min-w-full text-left text-sm">
                <thead className="text-xs uppercase text-gray-500">
                  <tr>
                    <th className="py-2 pr-4">Name</th>
                    <th className="py-2 pr-4">Admission No</th>
                    <th className="py-2 pr-4">Year</th>
                    <th className="py-2 pr-4">Semester</th>
                    <th className="py-2 pr-4">Section</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredStudents.map((student) => (
                    <tr key={student.admission_no} className="border-t border-gray-100">
                      <td className="py-2 pr-4 font-semibold">{student.name}</td>
                      <td className="py-2 pr-4">{student.admission_no}</td>
                      <td className="py-2 pr-4">{student.year}</td>
                      <td className="py-2 pr-4">{student.semester}</td>
                      <td className="py-2 pr-4">{student.section}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {activeTab === "analytics" && (
          <div className="rounded-xl bg-white p-4 shadow-sm">
            <h2 className="text-sm font-semibold text-gray-800">Top department questions today</h2>
            <div className="mt-3 space-y-2">
              {(dashboard.top_queries || []).map((query) => (
                <p key={query} className="rounded-md bg-green-50 p-3 text-sm text-gray-700">
                  {query}
                </p>
              ))}
              {dashboard.top_queries.length === 0 ? (
                <p className="text-sm text-gray-500">No student questions from this department today.</p>
              ) : null}
            </div>
          </div>
        )}

        {activeTab === "faculty" && isHod && (
          <div className="space-y-4">
            <form onSubmit={handleCreateFaculty} className="grid gap-3 rounded-xl bg-white p-4 shadow-sm md:grid-cols-3">
              <input
                value={facultyForm.name}
                onChange={(event) => setFacultyForm({ ...facultyForm, name: event.target.value })}
                placeholder="Full name"
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
                <option value="dept_coordinator">Coordinator</option>
              </select>
              <input
                value={facultyForm.subjects}
                onChange={(event) => setFacultyForm({ ...facultyForm, subjects: event.target.value })}
                placeholder="Subjects, comma separated"
                className="rounded-md border border-gray-300 p-2 text-sm"
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
                    <th className="py-2 pr-4">Employee ID</th>
                    <th className="py-2 pr-4">Designation</th>
                    <th className="py-2 pr-4">Subjects</th>
                  </tr>
                </thead>
                <tbody>
                  {departmentFaculty.map((member) => (
                    <tr key={member.user_id} className="border-t border-gray-100">
                      <td className="py-2 pr-4 font-semibold">{member.name}</td>
                      <td className="py-2 pr-4">{member.employee_id}</td>
                      <td className="py-2 pr-4">{member.designation}</td>
                      <td className="py-2 pr-4">{(member.subjects || []).join(", ") || "-"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </main>
    </div>
  );
};

const FacultyDashboard = () => <FacultyDashboardBase mode="faculty" />;

export default FacultyDashboard;
