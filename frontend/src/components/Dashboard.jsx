import { useState, useEffect, useMemo } from "react";
import { FileText, BookOpen, MessageCircle, HelpCircle, Clock } from "lucide-react";
import { getDocuments, getDashboardStats } from "../services/api";

const statCards = [
  {
    title: "Total Documents",
    key: "total_documents",
    description: "Across all your uploads",
    icon: FileText,
    bgColor: "#F5F9FF",
    iconColor: "#3B82F6",
  },
  {
    title: "Total Pages",
    key: "total_pages",
    description: "In all documents",
    icon: BookOpen,
    bgColor: "#F0FDF4",
    iconColor: "#22C55E",
  },
  {
    title: "Total Chats",
    key: "total_chats",
    description: "Conversations started",
    icon: MessageCircle,
    bgColor: "#FFF7ED",
    iconColor: "#F97316",
  },
  {
    title: "Total Questions",
    key: "total_questions",
    description: "Questions asked",
    icon: HelpCircle,
    bgColor: "#FAF5FF",
    iconColor: "#A855F7",
  },
];

const fileIconColors = {
  PDF: "text-red-500",
  DOCX: "text-blue-500",
  PPTX: "text-orange-500",
  TXT: "text-gray-500",
  XLSX: "text-green-500",
};

function getFileType(filename) {
  return filename.split(".").pop().toUpperCase();
}

function getFileIconColor(type) {
  return fileIconColors[type] || "text-gray-400";
}

function formatRelativeTime(dateString) {
  if (!dateString) return "";
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now - date;
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
  const hours = date.getHours();
  const minutes = date.getMinutes();
  const ampm = hours >= 12 ? "PM" : "AM";
  const hour12 = hours % 12 || 12;
  const timeStr = `${hour12}:${minutes.toString().padStart(2, "0")} ${ampm}`;

  if (diffDays === 0) {
    return `Today, ${timeStr}`;
  } else if (diffDays === 1) {
    return `Yesterday, ${timeStr}`;
  } else if (diffDays < 7) {
    return `${diffDays} days ago, ${timeStr}`;
  } else {
    return `${date.toLocaleDateString("en-US", { month: "short", day: "numeric" })}, ${timeStr}`;
  }
}

export default function Dashboard({ refreshKey = 0, onTabChange }) {
  const [documents, setDocuments] = useState([]);
  const [stats, setStats] = useState(null);
  const [recentChats, setRecentChats] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    Promise.all([
      getDocuments(),
      getDashboardStats(),
    ])
      .then(([docRes, statsRes]) => {
        setDocuments(docRes.data.documents || []);
        const s = statsRes.data;
        setStats({
          total_documents: s.total_documents || 0,
          total_pages: s.total_pages || 0,
          total_chats: s.total_chats || 0,
          total_questions: s.total_questions || 0,
        });
        setRecentChats(s.recent_chats || []);
      })
      .catch(() => {
        setStats({
          total_documents: 0,
          total_pages: 0,
          total_chats: 0,
          total_questions: 0,
        });
      })
      .finally(() => setLoading(false));
  }, [refreshKey]);

  const statValues = useMemo(() => {
    if (!stats) {
      return statCards.map((s) => ({ ...s, value: 0 }));
    }
    return statCards.map((s) => ({
      ...s,
      value: stats[s.key] ?? 0,
    }));
  }, [stats]);

  const recentDocs = useMemo(
    () =>
      documents.length > 0
        ? documents.slice(0, 4).map((doc) => {
            const displayName = doc.original_filename || doc.filename || "Untitled";
            const type = getFileType(displayName);
            return {
              name: displayName,
              type,
              pages: doc.total_pages || doc.chunks || 0,
              uploadedAt: doc.upload_time
                ? formatRelativeTime(doc.upload_time)
                : "Unknown",
            };
          })
        : [],
    [documents]
  );

  if (loading) {
    return (
      <div className="p-6 max-w-7xl mx-auto">
        <div className="mb-6">
          <h1 className="text-[32px] font-bold text-[#111827]">Dashboard</h1>
          <p className="text-[#6B7280] mt-1">Loading your overview...</p>
        </div>
        <div className="flex items-center justify-center py-20">
          <div className="w-6 h-6 border-2 border-[#2563EB] border-t-transparent rounded-full animate-spin" />
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="mb-6">
        <h1 className="text-[32px] font-bold text-[#111827]">Dashboard</h1>
        <p className="text-[#6B7280] mt-1">Welcome back! Here's an overview of your content.</p>
      </div>

      <div className="grid grid-cols-4 gap-5 mb-6">
        {statValues.map((stat) => {
          const Icon = stat.icon;
          return (
            <div
              key={stat.title}
              className="rounded-xl border border-[#E5E7EB] p-6 shadow-sm"
              style={{ backgroundColor: stat.bgColor }}
            >
              <div className="mb-4">
                <Icon className="w-5 h-5" style={{ color: stat.iconColor }} />
              </div>
              <p className="text-sm text-[#6B7280] mb-1">{stat.title}</p>
              <p className="text-[30px] font-bold text-[#111827] mb-1">{stat.value}</p>
              <p className="text-xs text-[#9CA3AF]">{stat.description}</p>
            </div>
          );
        })}
      </div>

      <div className="grid grid-cols-2 gap-5">
        <div className="rounded-xl border border-[#E5E7EB] p-6 bg-white shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-base font-semibold text-[#111827]">Recent Documents</h2>
            {documents.length > 0 && onTabChange && (
              <button
                onClick={() => onTabChange("documents")}
                className="text-xs text-[#2563EB] hover:text-blue-700 font-medium transition-colors"
              >
                View All
              </button>
            )}
          </div>
          {recentDocs.length > 0 ? (
            <table className="w-full">
              <thead>
                <tr className="text-xs text-[#9CA3AF] text-left">
                  <th className="pb-3 font-medium">Document Name</th>
                  <th className="pb-3 font-medium">Pages</th>
                  <th className="pb-3 font-medium">Uploaded At</th>
                </tr>
              </thead>
              <tbody>
                {recentDocs.map((doc, i) => (
                  <tr key={i} className="border-t border-[#E5E7EB]">
                    <td className="py-3 text-sm text-[#374151] flex items-center gap-2">
                      <FileText className={`w-4 h-4 shrink-0 ${getFileIconColor(doc.type)}`} />
                      <span className="truncate">{doc.name}</span>
                    </td>
                    <td className="py-3 text-sm text-[#6B7280]">{doc.pages}</td>
                    <td className="py-3 text-sm text-[#6B7280]">{doc.uploadedAt}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p className="text-sm text-[#9CA3AF] py-8 text-center">No documents uploaded yet.</p>
          )}
        </div>

        <div className="rounded-xl border border-[#E5E7EB] p-6 bg-white shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-base font-semibold text-[#111827]">Recent Chats</h2>
            {recentChats.length > 0 && onTabChange && (
              <button
                onClick={() => onTabChange("chat")}
                className="text-xs text-[#2563EB] hover:text-blue-700 font-medium transition-colors"
              >
                View All
              </button>
            )}
          </div>
          {recentChats.length > 0 ? (
            <div className="space-y-0">
              {recentChats.map((chat, i) => (
                <div
                  key={chat.id || i}
                  className="flex items-start gap-3 py-3 border-b border-[#E5E7EB] last:border-b-0"
                >
                  <MessageCircle className="w-4 h-4 text-[#9CA3AF] mt-0.5 shrink-0" />
                  <div className="min-w-0 flex-1">
                    <p className="text-sm text-[#374151] truncate">
                      {chat.first_question || chat.title}
                    </p>
                    <p className="text-xs text-[#9CA3AF] mt-0.5 flex items-center gap-1">
                      <Clock className="w-3 h-3 inline" />
                      {formatRelativeTime(chat.updated_at || chat.created_at)}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-[#9CA3AF] py-8 text-center">No conversations yet. Start a chat!</p>
          )}
        </div>
      </div>
    </div>
  );
}
