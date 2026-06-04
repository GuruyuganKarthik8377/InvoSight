import { useRef, useState } from "react";
import { UploadCloud, FileText, Loader2, X } from "lucide-react";

export default function UploadBox({ file, onFile, onExtract, loading }) {
  const inputRef = useRef(null);
  const [dragOver, setDragOver] = useState(false);

  const handleFiles = (files) => {
    if (!files || files.length === 0) return;
    const f = files[0];
    const allowed = ["application/pdf", "image/png", "image/jpeg"];
    if (!allowed.includes(f.type)) {
      alert("Only PDF, PNG, or JPG files are accepted.");
      return;
    }
    onFile(f);
  };

  const onDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    handleFiles(e.dataTransfer.files);
  };

  return (
    <div className="bg-white rounded-xl shadow-md p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-base font-semibold text-gray-800">Upload File</h2>
        {file && (
          <button
            onClick={() => onFile(null)}
            className="text-gray-400 hover:text-gray-600 text-sm flex items-center gap-1"
          >
            <X size={14} /> Remove
          </button>
        )}
      </div>

      {!file ? (
        <div
          onDragOver={(e) => {
            e.preventDefault();
            setDragOver(true);
          }}
          onDragLeave={() => setDragOver(false)}
          onDrop={onDrop}
          onClick={() => inputRef.current?.click()}
          className={`cursor-pointer border-2 border-dashed rounded-xl p-10 text-center transition ${
            dragOver
              ? "border-brand-500 bg-brand-50"
              : "border-gray-300 hover:border-brand-400 hover:bg-gray-50"
          }`}
        >
          <UploadCloud className="mx-auto mb-3 text-brand-500" size={36} />
          <p className="text-sm font-medium text-gray-700">
            Drag & drop your invoice here
          </p>
          <p className="text-xs text-gray-500 mt-1">
            or click to browse — PDF, PNG, JPG
          </p>
          <input
            ref={inputRef}
            type="file"
            accept=".pdf,image/png,image/jpeg"
            className="hidden"
            onChange={(e) => handleFiles(e.target.files)}
          />
        </div>
      ) : (
        <div className="border border-gray-200 rounded-lg p-4 flex items-center gap-3">
          <FileText className="text-brand-600" size={28} />
          <div className="flex-1 min-w-0">
            <div className="text-sm font-medium text-gray-800 truncate">
              {file.name}
            </div>
            <div className="text-xs text-gray-500">
              {(file.size / 1024).toFixed(1)} KB · {file.type || "unknown"}
            </div>
          </div>
        </div>
      )}

      <button
        disabled={!file || loading}
        onClick={onExtract}
        className="mt-5 w-full flex items-center justify-center gap-2 bg-brand-600 hover:bg-brand-700 disabled:bg-gray-300 disabled:cursor-not-allowed text-white text-sm font-semibold py-2.5 rounded-lg transition"
      >
        {loading ? (
          <>
            <Loader2 className="animate-spin" size={16} /> Extracting…
          </>
        ) : (
          "Extract Invoice Data"
        )}
      </button>
    </div>
  );
}
