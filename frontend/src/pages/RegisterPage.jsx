import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { checkAdmission, registerStudent } from "../api/client";

const RegisterPage = () => {
  const navigate = useNavigate();
  const [collegeId, setCollegeId] = useState("col_demo");
  const [admissionNo, setAdmissionNo] = useState("");
  const [verifiedStudent, setVerifiedStudent] = useState(null);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [parentPhone, setParentPhone] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const verifyAdmission = async (event) => {
    event.preventDefault();
    setError("");
    setVerifiedStudent(null);
    setLoading(true);
    try {
      const result = await checkAdmission(collegeId.trim(), admissionNo.trim());
      if (!result.valid) {
        setError(result.message || "Invalid admission number");
        return;
      }
      setVerifiedStudent(result);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const createAccount = async (event) => {
    event.preventDefault();
    setError("");
    setLoading(true);
    try {
      await registerStudent({
        college_id: collegeId.trim(),
        admission_no: admissionNo.trim(),
        email,
        password,
        confirm_password: confirmPassword,
        parent_phone: parentPhone || null,
      });
      navigate("/login", {
        replace: true,
        state: { message: "Account created successfully. Please login." },
      });
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-wa-bg px-4 py-8">
      <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-xl">
        <div className="text-center">
          <div className="mx-auto mb-3 flex h-16 w-16 items-center justify-center rounded-full bg-wa-dark text-2xl font-bold text-white">
            CA
          </div>
          <h1 className="text-2xl font-bold text-wa-dark">Student Registration</h1>
          <p className="mt-1 text-sm text-gray-500">Create your CampusAI account using college admission details</p>
        </div>

        <form onSubmit={verifyAdmission} className="mt-6 space-y-4">
          <div>
            <label htmlFor="collegeId" className="mb-1 block text-sm font-medium text-gray-700">
              College ID
            </label>
            <input
              id="collegeId"
              type="text"
              value={collegeId}
              onChange={(event) => setCollegeId(event.target.value)}
              required
              className="w-full rounded-md border border-gray-300 p-2.5 text-sm focus:border-wa-dark focus:outline-none"
            />
          </div>

          <div>
            <label htmlFor="admissionNo" className="mb-1 block text-sm font-medium text-gray-700">
              Admission Number
            </label>
            <input
              id="admissionNo"
              type="text"
              value={admissionNo}
              onChange={(event) => setAdmissionNo(event.target.value)}
              required
              className="w-full rounded-md border border-gray-300 p-2.5 text-sm focus:border-wa-dark focus:outline-none"
            />
          </div>

          <button
            type="submit"
            disabled={loading || !collegeId.trim() || !admissionNo.trim()}
            className="w-full rounded-md bg-wa-dark px-4 py-2.5 text-sm font-semibold text-white hover:bg-[#05453e] disabled:opacity-60"
          >
            {loading && !verifiedStudent ? "Verifying..." : "Verify"}
          </button>
        </form>

        {verifiedStudent && (
          <div className="mt-5 rounded-lg border border-green-200 bg-green-50 p-3 text-sm text-green-800">
            Welcome, {verifiedStudent.name}! Your admission number is verified.
          </div>
        )}

        {verifiedStudent && (
          <form onSubmit={createAccount} className="mt-5 space-y-4">
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

            <div className="grid gap-3 sm:grid-cols-2">
              <div>
                <label htmlFor="password" className="mb-1 block text-sm font-medium text-gray-700">
                  Password
                </label>
                <input
                  id="password"
                  type="password"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  minLength={6}
                  required
                  className="w-full rounded-md border border-gray-300 p-2.5 text-sm focus:border-wa-dark focus:outline-none"
                />
              </div>
              <div>
                <label htmlFor="confirmPassword" className="mb-1 block text-sm font-medium text-gray-700">
                  Confirm Password
                </label>
                <input
                  id="confirmPassword"
                  type="password"
                  value={confirmPassword}
                  onChange={(event) => setConfirmPassword(event.target.value)}
                  minLength={6}
                  required
                  className="w-full rounded-md border border-gray-300 p-2.5 text-sm focus:border-wa-dark focus:outline-none"
                />
              </div>
            </div>

            <div>
              <label htmlFor="parentPhone" className="mb-1 block text-sm font-medium text-gray-700">
                Parent Phone
              </label>
              <input
                id="parentPhone"
                type="tel"
                value={parentPhone}
                onChange={(event) => setParentPhone(event.target.value)}
                className="w-full rounded-md border border-gray-300 p-2.5 text-sm focus:border-wa-dark focus:outline-none"
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full rounded-md bg-wa-green px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-60"
            >
              {loading ? "Creating account..." : "Create Account"}
            </button>
          </form>
        )}

        {error && <p className="mt-4 rounded-md bg-red-50 px-3 py-2 text-sm text-red-600">{error}</p>}

        <div className="mt-6 rounded-lg border border-gray-200 bg-gray-50 p-3 text-xs text-gray-600">
          <p className="font-semibold text-gray-700">Demo College</p>
          <p>College ID = col_demo</p>
        </div>

        <p className="mt-4 text-center text-sm text-gray-600">
          Already registered?{" "}
          <Link to="/login" className="font-semibold text-wa-dark">
            Login here
          </Link>
        </p>
      </div>
    </div>
  );
};

export default RegisterPage;
