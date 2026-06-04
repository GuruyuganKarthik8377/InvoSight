import { LayoutDashboard, Upload, History, Sparkles, User } from "lucide-react";

const navItems = [
  { label: "Dashboard", icon: LayoutDashboard, key: "dashboard" },
  { label: "Upload", icon: Upload, key: "upload", active: true },
  { label: "History", icon: History, key: "history" },
];

export default function Sidebar() {
  return (
    <aside className="w-64 bg-white border-r border-gray-200 flex flex-col h-screen sticky top-0">
      <div className="px-6 py-5 border-b border-gray-100">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-brand-600 flex items-center justify-center text-white font-bold">
            IE
          </div>
          <span className="font-semibold text-gray-800">Invoice Extractor</span>
        </div>
      </div>

      <nav className="flex-1 px-3 py-4 space-y-1">
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <button
              key={item.key}
              className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition ${
                item.active
                  ? "bg-brand-50 text-brand-700"
                  : "text-gray-600 hover:bg-gray-100"
              }`}
            >
              <Icon size={18} />
              {item.label}
            </button>
          );
        })}
      </nav>

      <div className="p-3 border-t border-gray-100 space-y-3">
        <div className="rounded-xl bg-gradient-to-br from-brand-600 to-brand-700 text-white p-4 shadow-md">
          <div className="flex items-center gap-2 mb-2">
            <Sparkles size={16} />
            <span className="text-sm font-semibold">Upgrade to Pro</span>
          </div>
          <p className="text-xs text-blue-100 mb-3">
            Unlock unlimited extractions and priority support.
          </p>
          <button className="w-full bg-white text-brand-700 text-xs font-semibold py-1.5 rounded-md hover:bg-blue-50">
            Upgrade
          </button>
        </div>

        <div className="flex items-center gap-3 px-2 py-2 rounded-lg hover:bg-gray-50">
          <div className="w-9 h-9 rounded-full bg-gray-200 flex items-center justify-center">
            <User size={16} className="text-gray-600" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="text-sm font-medium text-gray-800 truncate">
              Yuvi G.
            </div>
            <div className="text-xs text-gray-500 truncate">Free plan</div>
          </div>
        </div>
      </div>
    </aside>
  );
}
