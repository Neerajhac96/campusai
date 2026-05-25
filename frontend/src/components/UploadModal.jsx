import { useEffect, useState } from "react";

const CATEGORIES = [
  "fees",
  "attendance",
  "exam",
  "hostel",
  "scholarship",
  "placement",
  "syllabus",
  "rules",
  "notices",
  "general",
];

const UploadModal = ({ open, title, onClose, onSubmit, loading = false, initialFile = null }) => {
  const [file, setFile] = useState(null);
  const [category, setCategory] = useState("general");

  useEffect(() => {
    if (open) {
      setFile(initialFile || null);
    } else {
      setFile(null);
      setCategory("general");
    }
  }, [open, initialFile]);

  if (!open) {
    return null;
  }

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!file) {
      window.alert("Please select a file");
      return;
    }
    await onSubmit(file, category);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4">
      <form onSubmit={handleSubmit} className="w-full max-w-md rounded-xl bg-white p-5 shadow-xl">
        <h3 className="text-lg font-semibold text-gray-800">{title}</h3>
        <p className="mt-1 text-sm text-gray-500">Upload PDF, DOCX, or TXT (max 10MB).</p>

        <div className="mt-4 space-y-3">
          <input
            type="file"
            accept=".pdf,.docx,.txt"
            onChange={(event) => setFile(event.target.files?.[0] || null)}
            className="w-full rounded-md border border-gray-300 p-2 text-sm"
          />
          {file ? <p className="text-xs text-gray-500">Selected: {file.name}</p> : null}
          <select
            value={category}
            onChange={(event) => setCategory(event.target.value)}
            className="w-full rounded-md border border-gray-300 p-2 text-sm"
          >
            {CATEGORIES.map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </select>
        </div>

        <div className="mt-5 flex justify-end gap-2">
          <button
            type="button"
            onClick={onClose}
            className="rounded-md border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={loading}
            className="rounded-md bg-wa-dark px-4 py-2 text-sm font-semibold text-white disabled:opacity-60"
          >
            {loading ? "Uploading..." : "Upload"}
          </button>
        </div>
      </form>
    </div>
  );
};

export default UploadModal;
