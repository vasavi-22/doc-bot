import { useState, useEffect, useMemo } from "react";
import { Search, FileText, Eye, Trash2, Upload } from "lucide-react";
import { getDocuments, uploadFile, deleteDocument } from "../services/api";
import { useToast } from "./Toast";
import ConfirmDialog from "./ConfirmDialog";

const fileIconColors = {
  PDF: "text-red-500",
  DOCX: "text-blue-500",
  PPTX: "text-orange-500",
  TXT: "text-gray-500",
  XLSX: "text-green-500",
  DOC: "text-blue-500",
};

function getFileType(filename) {
  return filename.split(".").pop().toUpperCase();
}

function getFileIconColor(type) {
  return fileIconColors[type] || "text-gray-400";
}

export default function Documents() {
  const [documents, setDocuments] = useState([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState(null);
  const { addToast } = useToast();

  const fetchDocs = async () => {
    try {
      const res = await getDocuments();
      setDocuments(res.data.documents || []);
    } catch {
      setDocuments([]);
    }
  };

  useEffect(() => {
    fetchDocs();
  }, []);

  const handleUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    setLoading(true);
    try {
      await uploadFile(file);
      fetchDocs();
      addToast("Document uploaded successfully!", "success");
    } catch (err) {
      addToast(err.response?.data?.error || "Upload failed", "error");
    }
    setLoading(false);
    e.target.value = "";
  };

  const handleView = (documentId) => {
    const token = localStorage.getItem("token");
    const url = token
      ? `http://localhost:5000/documents/${documentId}?token=${encodeURIComponent(token)}`
      : `http://localhost:5000/documents/${documentId}`;
    window.open(url, "_blank");
  };

  const confirmDelete = async () => {
    if (!deleteTarget) return;
    try {
      await deleteDocument(deleteTarget.document_id);
      fetchDocs();
      addToast("Document deleted successfully", "success");
    } catch (err) {
      addToast(err.response?.data?.error || "Delete failed", "error");
    }
    setDeleteTarget(null);
  };

  const filteredDocs = documents.filter((doc) =>
    (doc.original_filename || doc.filename || "")
      .toLowerCase()
      .includes(searchQuery.toLowerCase())
  );

  const docRows = useMemo(
    () =>
      filteredDocs.map((doc) => {
        const displayName = doc.original_filename || doc.filename || "Untitled";
        const type = getFileType(displayName);
        return {
          document_id: doc.document_id,
          name: displayName,
          type,
          pages: doc.total_pages || doc.chunks || 0,
          uploadedAt: doc.upload_time
            ? new Date(doc.upload_time).toLocaleDateString()
            : "Unknown",
        };
      }),
    [filteredDocs]
  );

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-[32px] font-bold text-[#111827]">Documents</h1>
          <p className="text-[#6B7280] mt-1">
            View and manage all your uploaded documents.
          </p>
        </div>
        <label className="inline-flex items-center gap-2 bg-[#2563EB] text-white px-4 py-2.5 rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors cursor-pointer">
          <Upload className="w-4 h-4" />
          {loading ? "Uploading..." : "Upload Document"}
          <input type="file" className="hidden" onChange={handleUpload} />
        </label>
      </div>

      {/* Search Bar */}
      <div className="relative mb-6">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[#9CA3AF]" />
        <input
          type="text"
          placeholder="Search documents..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="w-full h-10 pl-10 pr-4 text-sm border border-[#E5E7EB] rounded-lg outline-none focus:border-[#2563EB] focus:ring-1 focus:ring-[#2563EB] transition-colors"
        />
      </div>

      {/* Documents Table */}
      <div className="rounded-xl border border-[#E5E7EB] bg-white shadow-sm overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="border-b border-[#E5E7EB] bg-gray-50">
              <th className="text-left text-xs font-medium text-[#9CA3AF] px-6 py-4">
                Document Name
              </th>
              <th className="text-left text-xs font-medium text-[#9CA3AF] px-6 py-4">
                Pages
              </th>
              <th className="text-left text-xs font-medium text-[#9CA3AF] px-6 py-4">
                Uploaded At
              </th>
              <th className="text-right text-xs font-medium text-[#9CA3AF] px-6 py-4">
                Actions
              </th>
            </tr>
          </thead>
          <tbody>
            {docRows.length === 0 ? (
              <tr>
                <td colSpan={4} className="px-6 py-12 text-center text-sm text-[#9CA3AF]">
                  {searchQuery
                    ? "No documents match your search."
                    : "No documents uploaded yet."}
                </td>
              </tr>
            ) : (
              docRows.map((doc, i) => (
                <tr
                  key={i}
                  className="border-b border-[#E5E7EB] last:border-b-0 hover:bg-gray-50 transition-colors"
                >
                  <td className="px-6 py-3 text-sm text-[#374151]">
                    <div className="flex items-center gap-3">
                      <FileText
                        className={`w-4 h-4 shrink-0 ${getFileIconColor(doc.type)}`}
                      />
                      <span>{doc.name}</span>
                    </div>
                  </td>
                  <td className="px-6 py-3 text-sm text-[#6B7280]">{doc.pages}</td>
                  <td className="px-6 py-3 text-sm text-[#6B7280]">{doc.uploadedAt}</td>
                  <td className="px-6 py-3 text-right">
                    <div className="flex items-center justify-end gap-2">
                      <button
                        onClick={() => handleView(doc.document_id)}
                        className="p-1.5 rounded-lg hover:bg-gray-100 transition-colors"
                        title="View document"
                      >
                        <Eye className="w-4 h-4 text-[#6B7280]" />
                      </button>
                      <button
                        onClick={() => setDeleteTarget(doc)}
                        className="p-1.5 rounded-lg hover:bg-red-50 transition-colors"
                        title="Delete document"
                      >
                        <Trash2 className="w-4 h-4 text-red-500" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Delete Confirmation */}
      <ConfirmDialog
        open={!!deleteTarget}
        title="Delete Document"
        message={`Are you sure you want to delete "${(deleteTarget?.name || "")}"? This action cannot be undone.`}
        confirmLabel="Delete"
        cancelLabel="Cancel"
        onConfirm={confirmDelete}
        onCancel={() => setDeleteTarget(null)}
        variant="danger"
      />
    </div>
  );
}
