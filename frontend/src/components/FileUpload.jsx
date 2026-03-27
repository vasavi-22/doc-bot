import { uploadFile, getDocuments, deleteDocument } from "../services/api";
import { useState, useEffect } from "react";

export default function FileUpload() {
  const [loading, setLoading] = useState(false);
  const [showModal, setShowModal] = useState(false);
  const [docs, setDocs] = useState([]);

  const fetchDocs = async () => {
    const res = await getDocuments();
    setDocs(res.data.documents);
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
      alert("File uploaded successfully!");
      fetchDocs(); // refresh list
    } catch (err) {
      console.error(err);
      alert("Upload failed");
    }

    setLoading(false);
  };

  const handleDelete = async (filename) => {
    await deleteDocument(filename);
    fetchDocs();
  };

  return (
    <>
      {/* Upload + View */}
      <div className="flex justify-center gap-4 p-4">
        <label className="cursor-pointer bg-gray-800 text-white px-4 py-2 rounded-xl hover:bg-gray-700">
          {loading ? "Uploading..." : "Upload Document"}
          <input
            type="file"
            className="hidden"
            onChange={handleUpload}
          />
        </label>

        <button
          onClick={() => setShowModal(true)}
          className="bg-gray-700 text-white px-4 py-2 rounded-xl hover:bg-gray-600"
        >
          View Docs
        </button>
      </div>

      {/* Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/50 flex justify-center items-center">
          <div className="bg-gray-900 text-white p-6 rounded-xl w-[400px] max-h-[500px] overflow-y-auto">
            
            <div className="flex justify-between mb-4">
              <h2 className="text-lg font-semibold">Uploaded Documents</h2>
              <button onClick={() => setShowModal(false)}>✖</button>
            </div>

            {docs.length === 0 ? (
              <p>No documents uploaded</p>
            ) : (
              docs.map((doc, i) => (
                <div
                  key={i}
                  className="flex justify-between items-center bg-gray-800 p-2 rounded-lg mb-2"
                >
                  <span className="truncate">{doc}</span>

                  <button
                    onClick={() => handleDelete(doc)}
                    className="text-red-400 hover:text-red-600"
                  >
                    ✖
                  </button>
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </>
  );
}