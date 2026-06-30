import { MessageCircle } from "lucide-react";

export default function MessageBubble({ role, text, sources = [], streaming = false, noResults = false }) {
  const isUser = role === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"} mb-6`}>
      {isUser ? (
        <div className="max-w-[70%] bg-[#2563EB] text-white px-5 py-3 rounded-xl text-sm leading-relaxed">
          {text}
        </div>
      ) : (
        <div className="max-w-[70%]">
          <div className="bg-white border border-[#E5E7EB] rounded-xl px-5 py-4 text-sm text-[#374151] leading-relaxed shadow-sm">
            {noResults ? (
              <div className="text-[#6B7280]">
                <p className="font-medium text-[#374151] mb-2">No matching documents found</p>
                <p className="whitespace-pre-line">{text}</p>
              </div>
            ) : text || streaming ? (
              <>
                {text}
                {streaming && (
                  <span className="inline-block w-[2px] h-[1em] bg-[#2563EB] ml-0.5 align-text-bottom animate-pulse" />
                )}
              </>
            ) : (
              <span className="text-[#9CA3AF] italic">Thinking...</span>
            )}
          </div>
          {sources.length > 0 && (
            <div className="mt-3">
              <div className="text-xs text-[#9CA3AF] font-medium mb-1.5">Sources</div>
              <div className="space-y-1.5">
                {sources.map((source, index) => (
                  <div key={index} className="flex items-start gap-1.5 text-xs text-[#6B7280]">
                    <MessageCircle className="w-3 h-3 text-[#9CA3AF] mt-0.5 shrink-0" />
                    <span>
                      {source.filename}
                      {source.page != null && source.page !== "N/A" ? ` — Page ${source.page}` : ""}
                      {source.category && (
                        <span className="ml-1.5 inline-flex items-center px-1.5 py-0.5 bg-[#F3F4F6] rounded text-[10px] text-[#6B7280]">
                          {source.category}
                        </span>
                      )}
                      {source.tags && (
                        <span className="ml-1 inline-flex items-center px-1.5 py-0.5 bg-[#F0FDF4] rounded text-[10px] text-[#22C55E]">
                          {source.tags}
                        </span>
                      )}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}