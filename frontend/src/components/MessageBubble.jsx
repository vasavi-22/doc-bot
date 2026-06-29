import { MessageCircle } from "lucide-react";

export default function MessageBubble({ role, text, sources = [], streaming = false }) {
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
            {text || streaming ? (
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
              <div className="space-y-1">
                {sources.map((source, index) => (
                  <div key={index} className="flex items-center gap-1.5 text-xs text-[#6B7280]">
                    <MessageCircle className="w-3 h-3 text-[#9CA3AF]" />
                    <span>
                      {source.filename} — Page {source.page}
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