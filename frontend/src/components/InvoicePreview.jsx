import { useState } from "react";
import { ZoomIn, ZoomOut, FileText } from "lucide-react";

export default function InvoicePreview({ file, preview }) {
  const [zoom, setZoom] = useState(1);

  const isPdf = file?.type === "application/pdf";

  return (
    <div className="bg-white rounded-xl shadow-md p-6 flex flex-col">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-base font-semibold text-gray-800">
          Invoice Preview
        </h2>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setZoom((z) => Math.max(0.5, z - 0.1))}
            className="p-1.5 rounded-md hover:bg-gray-100 text-gray-600"
          >
            <ZoomOut size={16} />
          </button>
          <span className="text-xs text-gray-500 w-10 text-center">
            {Math.round(zoom * 100)}%
          </span>
          <button
            onClick={() => setZoom((z) => Math.min(3, z + 0.1))}
            className="p-1.5 rounded-md hover:bg-gray-100 text-gray-600"
          >
            <ZoomIn size={16} />
          </button>
          <span className="ml-3 text-xs text-gray-500">Page 1 / 1</span>
        </div>
      </div>

      <div className="flex-1 min-h-[300px] bg-gray-50 rounded-lg border border-gray-200 overflow-auto flex items-center justify-center p-4">
        {!preview ? (
          <div className="text-center text-gray-400">
            <FileText size={36} className="mx-auto mb-2" />
            <p className="text-sm">No file selected</p>
          </div>
        ) : isPdf ? (
          <iframe
            src={preview}
            title="invoice-pdf"
            className="w-full h-[500px] bg-white"
            style={{ transform: `scale(${zoom})`, transformOrigin: "top left" }}
          />
        ) : (
          <img
            src={preview}
            alt="invoice"
            style={{ transform: `scale(${zoom})`, transformOrigin: "top left" }}
            className="max-w-full"
          />
        )}
      </div>
    </div>
  );
}
