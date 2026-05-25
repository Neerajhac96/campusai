import { useEffect, useMemo, useRef, useState } from "react";
import { deleteDocument, getDocuments, replaceDocument, uploadDocument } from "../api/client";
import UploadModal from "./UploadModal";

const DocumentManager = () => {
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [categoryFilter, setCategoryFilter] = useState("");
  const [search, setSearch] = useState("");
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [replaceDocId, setReplaceDocId] = useState(null);
  const [pendingFile, setPendingFile] = useState(null);
  const fileInputRef = useRef(null);

  const categories = [
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

  const hasProcessing = useMemo(
    () => documents.some((document) => document.status === "processing"),
    [documents]
  );

  const loadDocuments = async () => {
    setLoading(true);
    try {
      const data = await getDocuments({
        ...(categoryFilter ? { category: categoryFilter } : {}),
        ...(search ? { search } : {}),
      });
      setDocuments(data.items || []);
    } catch (error) {
      window.alert(error.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDocuments();
  }, [categoryFilter]);

  useEffect(() => {
    if (!hasProcessing) {
      return undefined;
    }
    const timer = setInterval(() => {
      loadDocuments();
    }, 3000);
    return () => clearInterval(timer);
  }, [hasProcessing, categoryFilter, search]);

  const handleUpload = async (file, category) => {
    try {
      setUploading(true);
      await uploadDocument(file, category);
      setShowUploadModal(false);
      setPendingFile(null);
      await loadDocuments();
    } catch (error) {
      window.alert(error.message);
    } finally {
      setUploading(false);
    }
  };

  const handleReplace = async (file, category) => {
    if (!replaceDocId) {
      return;
    }
    try {
      setUploading(true);
      await replaceDocument(replaceDocId, file, category);
      setReplaceDocId(null);
      await loadDocuments();
    } catch (error) {
      window.alert(error.message);
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (docId) => {
    const confirmed = window.confirm("Delete this document permanently?");
    if (!confirmed) {
      return;
    }
    try {
      await deleteDocument(docId);
      await loadDocuments();
    } catch (error) {
      window.alert(error.message);
    }
  };

  const filteredDocuments = documents.filter((doc) =>
    search ? doc.original_name.toLowerCase().includes(search.toLowerCase()) : true
  );

  const renderStatus = (status, chunks) => {
    if (status === "processing") {
      return <span className="text-amber-600">Processing...</span>;
    }
    if (status === "active") {
      return <span className="text-green-600">✓ Active ({chunks} chunks)</span>;
    }
    if (status === "error") {
      return <span className="text-red-600">Error</span>;
    }
    return <span className="text-gray-600">{status}</span>;
  };

  return (
    <div className="space-y-4">
      <div
        role="button"
        tabIndex={0}
        onClick={() => fileInputRef.current?.click()}
        onDragOver={(event) => event.preventDefault()}
        onDrop={(event) => {
          event.preventDefault();
          const droppedFile = event.dataTransfer.files?.[0];
          if (droppedFile) {
            setPendingFile(droppedFile);
            setShowUploadModal(true);
          }
        }}
        className="rounded-xl border-2 border-dashed border-wa-dark/30 bg-white p-5 text-center"
      >
        <p className="text-sm text-gray-700">Drag and drop documents here</p>
        <p className="mt-1 text-xs text-gray-500">or click to browse files</p>
        <button
          type="button"
          onClick={(event) => {
            event.stopPropagation();
            setShowUploadModal(true);
          }}
          className="mt-3 rounded-md bg-wa-dark px-4 py-2 text-sm font-semibold text-white"
        >
          Upload Document
        </button>
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.docx,.txt"
          className="hidden"
          onChange={(event) => {
            const selectedFile = event.target.files?.[0] || null;
            setPendingFile(selectedFile);
            setShowUploadModal(true);
          }}
        />
      </div>

      <div className="grid gap-3 sm:grid-cols-3">
        <select
          value={categoryFilter}
          onChange={(event) => setCategoryFilter(event.target.value)}
          className="rounded-md border border-gray-300 bg-white p-2 text-sm"
        >
          <option value="">All categories</option>
          {categories.map((category) => (
            <option key={category} value={category}>
              {category}
            </option>
          ))}
        </select>
        <input
          type="text"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          placeholder="Search by filename"
          className="rounded-md border border-gray-300 bg-white p-2 text-sm sm:col-span-2"
        />
      </div>

      <div className="overflow-x-auto rounded-xl border border-gray-200 bg-white">
        <table className="min-w-full text-left text-sm">
          <thead className="bg-gray-50 text-gray-600">
            <tr>
              <th className="px-4 py-3">Name</th>
              <th className="px-4 py-3">Category</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3">Chunks</th>
              <th className="px-4 py-3">Uploaded</th>
              <th className="px-4 py-3">Actions</th>
            </tr>
          </thead>
          <tbody>
            {filteredDocuments.map((doc) => (
              <tr key={doc.id} className="border-t border-gray-100">
                <td className="px-4 py-3">{doc.original_name}</td>
                <td className="px-4 py-3 capitalize">{doc.category}</td>
                <td className="px-4 py-3">{renderStatus(doc.status, doc.chunk_count)}</td>
                <td className="px-4 py-3">{doc.chunk_count}</td>
                <td className="px-4 py-3">{new Date(doc.uploaded_at).toLocaleDateString()}</td>
                <td className="px-4 py-3">
                  <div className="flex gap-2">
                    <button
                      type="button"
                      onClick={() => setReplaceDocId(doc.id)}
                      className="rounded-md border border-gray-300 px-2.5 py-1 text-xs font-semibold text-gray-700"
                    >
                      Replace
                    </button>
                    <button
                      type="button"
                      onClick={() => handleDelete(doc.id)}
                      className="rounded-md bg-red-600 px-2.5 py-1 text-xs font-semibold text-white"
                    >
                      Delete
                    </button>
                  </div>
                </td>
              </tr>
            ))}
            {!loading && filteredDocuments.length === 0 && (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-gray-500">
                  No documents found
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {loading && <p className="text-sm text-gray-500">Loading documents...</p>}

      <UploadModal
        open={showUploadModal}
        title="Upload new document"
        loading={uploading}
        initialFile={pendingFile}
        onClose={() => {
          setShowUploadModal(false);
          setPendingFile(null);
        }}
        onSubmit={handleUpload}
      />

      <UploadModal
        open={Boolean(replaceDocId)}
        title="Replace document"
        loading={uploading}
        onClose={() => setReplaceDocId(null)}
        onSubmit={handleReplace}
      />
    </div>
  );
};

export default DocumentManager;
