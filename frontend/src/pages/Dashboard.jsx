import { useEffect, useState } from "react";
import Sidebar from "../components/Sidebar.jsx";
import Header from "../components/Header.jsx";
import UploadBox from "../components/UploadBox.jsx";
import InvoicePreview from "../components/InvoicePreview.jsx";
import ExtractedData from "../components/ExtractedData.jsx";
import { extractInvoiceFile } from "../services/api.js";

export default function Dashboard() {
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [rawText, setRawText] = useState("");
  const [confidence, setConfidence] = useState(0.9);

  useEffect(() => {
    if (!file) {
      setPreview(null);
      return;
    }
    const url = URL.createObjectURL(file);
    setPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);

  const handleFile = (f) => {
    setFile(f);
    setData(null);
    setProgress(0);
  };

  const handleExtract = async () => {
    if (!file) return;
    setLoading(true);
    setProgress(10);

    const tick = setInterval(() => {
      setProgress((p) => (p < 85 ? p + 3 : p));
    }, 400);

    try {
      const result = await extractInvoiceFile(file);
      // Backend returns the schema plus _ocr_text so we can reuse for Excel export.
      const { _ocr_text, ...clean } = result || {};
      setRawText(_ocr_text || "");
      if (typeof clean.confidence === "number") setConfidence(clean.confidence);
      setData(clean);
      setProgress(100);
    } catch (err) {
      console.error(err);
      const detail =
        err?.response?.data?.detail ||
        err?.response?.data?.errors?.join?.(", ") ||
        err?.message ||
        "unknown_error";
      setData({
        extraction_status: "failed",
        errors: [String(detail)],
        confidence: 0.0,
        line_items: [],
      });
      setProgress(100);
    } finally {
      clearInterval(tick);
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen bg-gray-100">
      <Sidebar />

      <main className="flex-1 flex flex-col">
        <Header progress={progress} loading={loading} />

        <div className="flex-1 p-8 grid grid-cols-1 xl:grid-cols-3 gap-6">
          <div className="xl:col-span-2 flex flex-col gap-6">
            <UploadBox
              file={file}
              onFile={handleFile}
              onExtract={handleExtract}
              loading={loading}
            />
            <InvoicePreview file={file} preview={preview} />
          </div>

          <div className="xl:col-span-1">
            <ExtractedData
              data={data}
              loading={loading}
              rawText={rawText}
              confidence={confidence}
            />
          </div>
        </div>
      </main>
    </div>
  );
}
