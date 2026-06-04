export default function Header({ progress = 0, loading = false }) {
  return (
    <div className="bg-white border-b border-gray-200 px-8 py-5">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">Upload Invoice</h1>
          <p className="text-sm text-gray-500 mt-1">
            Upload a PDF or image to extract structured invoice data using AI.
          </p>
        </div>
        <div className="text-xs text-gray-500">
          {loading ? "Processing…" : progress === 100 ? "Done" : "Idle"}
        </div>
      </div>

      <div className="mt-4 h-1.5 w-full bg-gray-100 rounded-full overflow-hidden">
        <div
          className={`h-full transition-all duration-300 ${
            loading ? "bg-brand-500 animate-pulse" : "bg-green-500"
          }`}
          style={{ width: `${progress}%` }}
        />
      </div>
    </div>
  );
}
