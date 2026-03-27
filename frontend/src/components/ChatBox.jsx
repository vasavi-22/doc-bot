import { useState, useRef, useEffect } from "react";
import { useChatStore } from "../store/useChatStore";
import { sendMessage } from "../services/api";
import MessageBubble from "./MessageBubble";

export default function ChatBox() {
  const [input, setInput] = useState("");
  const { messages, addMessage, loading, setLoading } = useChatStore();

  const bottomRef = useRef(null);

  // auto-scroll
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim()) return;

    addMessage({ role: "user", text: input });
    setLoading(true);

    try {
      const res = await sendMessage(input);

      addMessage({
        role: "bot",
        text: res.data.response,
      });
    } catch (err) {
      addMessage({
        role: "bot",
        text: "Something went wrong...",
      });
    }

    setLoading(false);
    setInput("");
  };

  return (
    <div className="flex flex-col h-full w-full max-w-5xl mx-auto">
      {/* Messages */}
      <div className="flex-1 overflow-y-auto py-6 pr-2">
        <div className="px-4">
          {messages.map((m, i) => (
            <MessageBubble key={i} role={m.role} text={m.text} />
          ))}

          {loading && <div className="text-gray-400 text-sm">Thinking...</div>}
          <div ref={bottomRef} />
        </div>
      </div>

      {/* Input */}
      <div className="border-t border-gray-700 p-4">
        <div className="flex gap-2">
          <input
            className="flex-1 bg-gray-800 text-white px-4 py-2 rounded-xl outline-none"
            placeholder="Ask something..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
          />

          <button
            onClick={handleSend}
            className="bg-blue-600 hover:bg-blue-700 px-4 py-2 rounded-xl text-white"
          >
            Send
          </button>
        </div>
      </div>
    </div>
  );
}
