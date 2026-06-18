export default function MessageBubble({ role, text, sources = [] }) {
  const isUser = role === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"} mb-4`}>
      <div
        className={`max-w-xl px-4 py-3 rounded-2xl text-sm leading-relaxed ${
          isUser
            ? "bg-blue-600 text-white"
            : "bg-gray-800 text-gray-200"
        }`}
      >
        {text}
      </div>
      {role === "bot" && sources.length > 0 && (
        <div className="mt-3 border-t border-gray-700 pt-2">
          <div className="text-xs text-gray-400 font-semibold mb-1">
            Sources
          </div>

          {sources.map((source, index) => (
            <div
              key={index}
              className="text-xs text-gray-500"
            >
              📄 {source.filename} — Page {source.page}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}