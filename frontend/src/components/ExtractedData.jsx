import { useState } from "react";
import { Download, FileJson, FileSpreadsheet, CheckCircle2, AlertCircle, XCircle } from "lucide-react";

const StatusBadge = ({ status }) => {
  const map = {
    success: { c: "bg-green-100 text-green-700", I: CheckCircle2, l: "Success" },
    partial: { c: "bg-yellow-100 text-yellow-700", I: AlertCircle, l: "Partial" },
    failed: { c: "bg-red-100 text-red-700", I: XCircle, l: "Failed" },
  };
  const cfg = map[status] || map.failed;
  const Icon = cfg.I;
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${cfg.c}`}>
      <Icon size={12} /> {cfg.l}
    </span>
  );
};

export default function ExtractedData({ data, loading, rawText = "", confidence = 0.9 }) {
  const [tab, setTab] = useState("json");

  const downloadJSON = () => {
    if (!data) return;
    const blob = new Blob([JSON.stringify(data, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `invoice_${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const downloadExcel = async () => {
    if (!rawText) {
      alert("No OCR text available. Run extraction first.");
      return;
    }
    try {
      const res = await fetch("http://localhost:8000/export/excel", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ raw_text: rawText, confidence }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `invoice_${Date.now()}.xlsx`;
      a.click();
      window.URL.revokeObjectURL(url);
    } catch (e) {
      console.error(e);
      alert("Excel export failed");
    }
  };

  return (
    <div className="bg-white rounded-xl shadow-md p-6 h-full flex flex-col">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-base font-semibold text-gray-800">
            Extracted Data
          </h2>
          {data?.extraction_status && (
            <div className="mt-1 flex items-center gap-2">
              <StatusBadge status={data.extraction_status} />
              {typeof data.confidence === "number" && (
                <span className="text-xs text-gray-500">
                  Confidence: {(data.confidence * 100).toFixed(0)}%
                </span>
              )}
            </div>
          )}
        </div>

        <div className="flex bg-gray-100 rounded-lg p-1">
          <button
            onClick={() => setTab("json")}
            className={`px-3 py-1 text-xs font-medium rounded-md flex items-center gap-1 ${
              tab === "json" ? "bg-white shadow text-gray-800" : "text-gray-500"
            }`}
          >
            <FileJson size={12} /> JSON
          </button>
          <button
            onClick={() => setTab("excel")}
            className={`px-3 py-1 text-xs font-medium rounded-md flex items-center gap-1 ${
              tab === "excel" ? "bg-white shadow text-gray-800" : "text-gray-500"
            }`}
          >
            <FileSpreadsheet size={12} /> Excel
          </button>
        </div>
      </div>

      <div className="flex-1 min-h-[300px] rounded-lg overflow-hidden border border-gray-800 bg-gray-900">
        {loading ? (
          <div className="h-full flex items-center justify-center text-gray-400 text-sm">
            Extracting…
          </div>
        ) : !data ? (
          <div className="h-full flex items-center justify-center text-gray-500 text-sm p-6 text-center">
            Upload an invoice and click <b className="mx-1">Extract</b> to see
            results here.
          </div>
        ) : tab === "json" ? (
          <pre className="text-xs text-green-300 p-4 overflow-auto h-full font-mono leading-relaxed">
{JSON.stringify(data, null, 2)}
          </pre>
        ) : (
          <div className="h-full flex items-center justify-center text-gray-300 text-sm p-6 text-center">
            <div>
              <FileSpreadsheet size={32} className="mx-auto mb-3 text-green-400" />
              <p>Click "Download Excel" to save a 2-sheet workbook</p>
              <p className="text-xs text-gray-500 mt-1">
                (Invoice + Line Items)
              </p>
            </div>
          </div>
        )}
      </div>

      {data?.errors?.length > 0 && (
        <div className="mt-3 text-xs text-red-600">
          <b>Errors:</b> {data.errors.join(", ")}
        </div>
      )}

      <div className="mt-4 grid grid-cols-2 gap-3">
        <button
          disabled={!data}
          onClick={downloadJSON}
          className="flex items-center justify-center gap-2 bg-brand-600 hover:bg-brand-700 disabled:bg-gray-300 text-white text-sm font-semibold py-2 rounded-lg transition"
        >
          <Download size={14} /> Download JSON
        </button>
        <button
          disabled={!data}
          onClick={downloadExcel}
          className="flex items-center justify-center gap-2 bg-green-600 hover:bg-green-700 disabled:bg-gray-300 text-white text-sm font-semibold py-2 rounded-lg transition"
        >
          <Download size={14} /> Download Excel
        </button>
      </div>
    </div>
  );
}
