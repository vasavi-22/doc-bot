import { Home, FileText, MessageCircle, ChevronDown } from "lucide-react";

const navItems = [
  { id: "dashboard", label: "Dashboard", icon: Home },
  { id: "documents", label: "Documents", icon: FileText },
  { id: "chat", label: "Chat", icon: MessageCircle },
];

export default function Sidebar({ activeTab, onTabChange }) {
  return (
    <aside className="w-[220px] bg-white border-r border-gray-200 flex flex-col h-screen shrink-0">
      {/* Logo Section */}
      <div className="flex items-center gap-3 px-6 pt-6 pb-8">
        <div className="w-8 h-8 bg-[#2563EB] rounded-lg flex items-center justify-center shrink-0">
          <MessageCircle className="w-5 h-5 text-white" />
        </div>
        <span className="text-xl font-bold text-[#111827]">DocBot</span>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-4 space-y-1">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => onTabChange(item.id)}
              className={`w-full flex items-center gap-3 px-4 h-11 rounded-xl text-sm font-medium transition-colors duration-150 ${
                isActive
                  ? "bg-[#EFF6FF] text-[#2563EB]"
                  : "text-[#374151] hover:bg-gray-50"
              }`}
            >
              <Icon
                className={`w-5 h-5 shrink-0 ${
                  isActive ? "text-[#2563EB]" : "text-[#6B7280]"
                }`}
              />
              {item.label}
            </button>
          );
        })}
      </nav>

      {/* User Section */}
      <div className="px-4 pb-6 pt-4 border-t border-gray-100 mx-4">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-[#60A5FA] rounded-full flex items-center justify-center text-white text-sm font-medium shrink-0">
            U
          </div>
          <span className="text-sm font-medium text-[#111827] flex-1">User</span>
          <ChevronDown className="w-4 h-4 text-[#9CA3AF]" />
        </div>
      </div>
    </aside>
  );
}
