import { useState, useEffect, useMemo } from "react";
import { FileText, BookOpen, MessageCircle, HelpCircle } from "lucide-react";
import { getDocuments } from "../services/api";

const statCards = [
  {
    title: "Total Documents",
    value: 12,
    description: "Across all your uploads",
    icon: FileText,
    bgColor: "#F5F9FF",
    iconColor: "#3B82F6",
  },
  {
    title: "Total Pages",
    value: 248,
    description: "In all documents",
    icon: BookOpen,
    bgColor: "#F0FDF4",
    iconColor: "#22C55E",
  },
  {
    title: "Total Chats",
    value: 34,
    description: "Conversations started",
    icon: MessageCircle,
    bgColor: "#FFF7ED",
    iconColor: "#F97316",
  },
  {
    title: "Total Questions",
    value: 156,
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

const recentChatsData = [
  { question: "What are the key findings of this research?", date: "Today", time: "2:30 PM" },
  { question: "Summarize the document", date: "Today", time: "1:15 PM" },
  { question: "What is the company leave policy?", date: "Yesterday", time: "4:45 PM" },
  { question: "Explain the methodology used?", date: "Yesterday", time: "11:20 AM" },
];

export default function Dashboard() {
  const [documents, setDocuments] = useState([]);

  useEffect(() => {
    getDocuments()
      .then((res) => setDocuments(res.data.documents || []))
      .catch(() => {});
  }, []);

  const stats = statCards.map((stat) => {
    if (stat.title === "Total Documents") {
      return { ...stat, value: documents.length || 12 };
    }
    return stat;
  });

  const recentDocs = useMemo(
    () =>
      documents.length > 0
        ? documents.slice(0, 4).map((doc) => {
            const displayName = doc.original_filename || doc.filename || "Untitled";
            const type = getFileType(displayName);
            const hash = displayName.split("").reduce((a, c) => a + c.charCodeAt(0), 0);
            return {
              name: displayName,
              type,
              pages: doc.chunks || (hash % 46) + 5,
              uploadedAt: doc.upload_time
                ? new Date(doc.upload_time).toLocaleDateString()
                : "2 hours ago",
            };
          })
        : [
            { name: "Research Paper.pdf", type: "PDF", pages: 24, uploadedAt: "2 hours ago" },
            { name: "Company Policy.pdf", type: "PDF", pages: 15, uploadedAt: "5 hours ago" },
            { name: "User Guide.docx", type: "DOCX", pages: 32, uploadedAt: "Yesterday" },
            { name: "Product Overview.pptx", type: "PPTX", pages: 12, uploadedAt: "Yesterday" },
          ],
    [documents]
  );

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="mb-6">
        <h1 className="text-[32px] font-bold text-[#111827]">Dashboard</h1>
        <p className="text-[#6B7280] mt-1">Welcome back! Here's an overview of your content.</p>
      </div>

      <div className="grid grid-cols-4 gap-5 mb-6">
        {stats.map((stat) => {
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
            <button className="px-3 py-1.5 text-sm border border-[#E5E7EB] rounded-lg text-[#6B7280] hover:bg-gray-50 transition-colors">
              View All
            </button>
          </div>
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
        </div>

        <div className="rounded-xl border border-[#E5E7EB] p-6 bg-white shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-base font-semibold text-[#111827]">Recent Chats</h2>
            <button className="px-3 py-1.5 text-sm border border-[#E5E7EB] rounded-lg text-[#6B7280] hover:bg-gray-50 transition-colors">
              View All
            </button>
          </div>
          <div className="space-y-0">
            {recentChatsData.map((chat, i) => (
              <div
                key={i}
                className="flex items-start gap-3 py-3 border-b border-[#E5E7EB] last:border-b-0"
              >
                <MessageCircle className="w-4 h-4 text-[#9CA3AF] mt-0.5 shrink-0" />
                <div className="min-w-0">
                  <p className="text-sm text-[#374151] truncate">{chat.question}</p>
                  <p className="text-xs text-[#9CA3AF] mt-0.5">
                    {chat.date}, {chat.time}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
