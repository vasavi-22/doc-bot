import { useState, useRef, useEffect, useCallback } from "react";
import { Plus, MessageCircle, ChevronRight, Send } from "lucide-react";
import { sendMessage } from "../services/api";
import MessageBubble from "./MessageBubble";
import { useToast } from "./Toast";

let conversationCounter = 0;

export default function ChatPage() {
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const { addToast } = useToast();
  const [conversations, setConversations] = useState(() => {
    const id = `conv_${++conversationCounter}`;
    return [{ id, title: "New Chat", messages: [], active: true }];
  });
  const [activeConvId, setActiveConvId] = useState(() => conversations[0].id);
  const bottomRef = useRef(null);

  const activeConv = conversations.find((c) => c.id === activeConvId);
  const messages = activeConv?.messages || [];

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleNewChat = () => {
    const id = `conv_${++conversationCounter}`;
    setConversations((prev) => [
      ...prev.map((c) => ({ ...c, active: false })),
      { id, title: "New Chat", messages: [], active: true },
    ]);
    setActiveConvId(id);
  };

  const switchConversation = (id) => {
    setActiveConvId(id);
    setConversations((prev) =>
      prev.map((c) => ({ ...c, active: c.id === id }))
    );
  };

  const addMessageToActive = useCallback(
    (msg) => {
      setConversations((prev) =>
        prev.map((c) =>
          c.id === activeConvId
            ? { ...c, messages: [...c.messages, msg] }
            : c
        )
      );
    },
    [activeConvId]
  );

  const handleSend = async () => {
    if (!input.trim() || loading) return;

    const userMessage = input.trim();
    addMessageToActive({ role: "user", text: userMessage });
    setInput("");
    setLoading(true);

    // Update conversation title based on first user message
    setConversations((prev) =>
      prev.map((c) =>
        c.id === activeConvId && c.title === "New Chat"
          ? {
              ...c,
              title:
                userMessage.length > 40
                  ? userMessage.slice(0, 40) + "..."
                  : userMessage,
            }
          : c
      )
    );

    try {
      const res = await sendMessage(userMessage);
      addMessageToActive({
        role: "bot",
        text: res.data.answer,
        sources: res.data.sources || [],
      });
    } catch (err) {
      const errorMsg = err.response?.data?.error || "Failed to get response";
      addToast(errorMsg, "error");
      addMessageToActive({
        role: "bot",
        text: "Something went wrong. Please try again.",
      });
    }

    setLoading(false);
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex h-full">
      {/* Conversation Panel */}
      <div className="w-[260px] border-r border-[#E5E7EB] bg-white flex flex-col shrink-0">
        <div className="flex items-center justify-between px-5 pt-6 pb-4">
          <h2 className="text-sm font-semibold text-[#111827]">
            Conversations
          </h2>
          <button
            onClick={handleNewChat}
            className="p-1.5 rounded-lg hover:bg-gray-100 transition-colors"
            title="New conversation"
          >
            <Plus className="w-4 h-4 text-[#6B7280]" />
          </button>
        </div>
        <div className="flex-1 overflow-y-auto px-3 space-y-1 pb-4">
          {conversations.map((conv) => (
            <button
              key={conv.id}
              onClick={() => switchConversation(conv.id)}
              className={`w-full flex items-center gap-2.5 px-3 py-2.5 rounded-lg text-left transition-colors ${
                conv.active
                  ? "bg-[#EFF6FF] text-[#2563EB]"
                  : "text-[#374151] hover:bg-gray-50"
              }`}
            >
              <MessageCircle className="w-4 h-4 shrink-0" />
              <span className="text-sm truncate flex-1">{conv.title}</span>
              {conv.active && (
                <ChevronRight className="w-3.5 h-3.5 shrink-0" />
              )}
            </button>
          ))}
        </div>
      </div>

      {/* Chat Area */}
      <div className="flex-1 flex flex-col bg-white">
        {messages.length === 0 ? (
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center max-w-md">
              <MessageCircle className="w-12 h-12 text-[#E5E7EB] mx-auto mb-4" />
              <h3 className="text-lg font-semibold text-[#111827] mb-2">
                Ask anything
              </h3>
              <p className="text-sm text-[#6B7280]">
                Ask questions about your uploaded documents and get AI-powered
                answers with source citations.
              </p>
            </div>
          </div>
        ) : (
          <div className="flex-1 overflow-y-auto px-6 py-6">
            <div className="max-w-4xl mx-auto">
              {messages.map((m, i) => (
                <MessageBubble
                  key={i}
                  role={m.role}
                  text={m.text}
                  sources={m.sources}
                />
              ))}
              {loading && (
                <div className="flex justify-start mb-6">
                  <div className="bg-white border border-[#E5E7EB] rounded-xl px-5 py-3 shadow-sm">
                    <div className="flex items-center gap-2">
                      <div
                        className="w-2 h-2 bg-[#2563EB] rounded-full animate-bounce"
                        style={{ animationDelay: "0ms" }}
                      />
                      <div
                        className="w-2 h-2 bg-[#2563EB] rounded-full animate-bounce"
                        style={{ animationDelay: "150ms" }}
                      />
                      <div
                        className="w-2 h-2 bg-[#2563EB] rounded-full animate-bounce"
                        style={{ animationDelay: "300ms" }}
                      />
                    </div>
                  </div>
                </div>
              )}
              <div ref={bottomRef} />
            </div>
          </div>
        )}

        {/* Input Area */}
        <div className="px-6 pb-6 pt-4 border-t border-[#E5E7EB]">
          <div className="max-w-4xl mx-auto relative">
            <input
              type="text"
              placeholder="Ask a question about your documents..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={loading}
              className="w-full h-12 pl-5 pr-12 text-sm border border-[#E5E7EB] rounded-xl outline-none focus:border-[#2563EB] focus:ring-1 focus:ring-[#2563EB] transition-colors placeholder:text-[#9CA3AF]"
            />
            <button
              onClick={handleSend}
              disabled={loading || !input.trim()}
              className="absolute right-2 top-1/2 -translate-y-1/2 p-2 rounded-lg text-[#2563EB] hover:bg-blue-50 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
            >
              <Send className="w-5 h-5" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
