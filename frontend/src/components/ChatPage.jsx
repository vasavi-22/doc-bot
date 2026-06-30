import { useState, useRef, useEffect, useCallback } from "react";
import { Plus, MessageCircle, ChevronRight, Send, Trash2 } from "lucide-react";
import {
  sendMessageStreamWithChat,
  getConversations,
  createConversation,
  getConversation,
  deleteConversation,
} from "../services/api";
import MessageBubble from "./MessageBubble";
import { useToast } from "./Toast";
import ConfirmDialog from "./ConfirmDialog";

export default function ChatPage() {
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const { addToast } = useToast();
  const [conversations, setConversations] = useState([]);
  const [activeConvId, setActiveConvId] = useState(null);
  const [initialLoading, setInitialLoading] = useState(true);
  const [deleteTarget, setDeleteTarget] = useState(null);
  const bottomRef = useRef(null);
  const abortRef = useRef(null);

  const activeConv = conversations.find((c) => c.id === activeConvId);
  const messages = activeConv?.messages || [];

  // Load conversations on mount
  useEffect(() => {
    getConversations()
      .then((res) => {
        const convs = res.data.conversations || [];
        if (convs.length > 0) {
          // Load the most recent conversation's messages
          const latest = convs[0];
          setActiveConvId(latest.id);
          return getConversation(latest.id).then((msgRes) => {
            const loadedMsgs = (msgRes.data.messages || []).map((m) => ({
              id: m.id,
              role: m.role === "assistant" ? "bot" : m.role,
              text: m.content,
              sources: m.sources ? JSON.parse(m.sources) : [],
              streaming: false,
            }));
            setConversations(
              convs.map((c) =>
                c.id === latest.id
                  ? { ...c, messages: loadedMsgs }
                  : { ...c, messages: [] }
              )
            );
          });
        } else {
          // Create initial chat
          return createConversation("New Chat").then((res) => {
            const chat = res.data.conversation;
            setConversations([{ ...chat, messages: [], active: true }]);
            setActiveConvId(chat.id);
          });
        }
      })
      .catch(() => {
        addToast("Failed to load conversations", "error");
        // Create a fallback local conversation
        const id = "local_fallback";
        setConversations([{ id, title: "New Chat", messages: [], active: true }]);
        setActiveConvId(id);
      })
      .finally(() => setInitialLoading(false));
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleNewChat = async () => {
    try {
      const res = await createConversation("New Chat");
      const chat = res.data.conversation;
      setConversations((prev) => [
        ...prev.map((c) => ({ ...c, active: false })),
        { ...chat, messages: [], active: true },
      ]);
      setActiveConvId(chat.id);
    } catch {
      addToast("Failed to create conversation", "error");
    }
  };

  const switchConversation = async (id) => {
    setActiveConvId(id);

    // Check if messages are already loaded (before setState)
    const conv = conversations.find((c) => c.id === id);
    const needsLoad = conv && conv.messages.length === 0;

    setConversations((prev) =>
      prev.map((c) => ({ ...c, active: c.id === id }))
    );

    // Load messages if not already loaded
    if (needsLoad) {
      try {
        const res = await getConversation(id);
        const loadedMsgs = (res.data.messages || []).map((m) => ({
          id: m.id,
          role: m.role === "assistant" ? "bot" : m.role,
          text: m.content,
          sources: m.sources ? JSON.parse(m.sources) : [],
          streaming: false,
        }));
        setConversations((prev) =>
          prev.map((c) =>
            c.id === id ? { ...c, messages: loadedMsgs } : c
          )
        );
      } catch {
        // Messages will load on next try
      }
    }
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

  const updateMessage = useCallback(
    (msgId, updater) => {
      setConversations((prev) =>
        prev.map((c) =>
          c.id === activeConvId
            ? {
                ...c,
                messages: c.messages.map((m) => {
                  if (m.id !== msgId) return m;
                  const resolved = {};
                  for (const [key, value] of Object.entries(updater)) {
                    resolved[key] = typeof value === "function" ? value(m[key]) : value;
                  }
                  return { ...m, ...resolved };
                }),
              }
            : c
        )
      );
    },
    [activeConvId]
  );

  const handleDeleteChat = async (e, chatId) => {
    e.stopPropagation();
    setDeleteTarget(chatId);
  };

  const confirmDeleteChat = async () => {
    if (!deleteTarget) return;
    try {
      await deleteConversation(deleteTarget);
      const updated = conversations.filter((c) => c.id !== deleteTarget);
      setConversations(updated);

      if (deleteTarget === activeConvId) {
        if (updated.length > 0) {
          setActiveConvId(updated[0].id);
          switchConversation(updated[0].id);
        } else {
          // Create a new one
          const res = await createConversation("New Chat");
          const chat = res.data.conversation;
          setConversations([{ ...chat, messages: [], active: true }]);
          setActiveConvId(chat.id);
        }
      }
      addToast("Conversation deleted", "success");
    } catch {
      addToast("Failed to delete conversation", "error");
    }
    setDeleteTarget(null);
  };

  const handleSend = async () => {
    if (!input.trim() || loading || !activeConvId) return;

    const userMessage = input.trim();
    const userMsgId = `user_${Date.now()}`;
    addMessageToActive({ id: userMsgId, role: "user", text: userMessage });
    setInput("");
    setLoading(true);

    // Auto-generate title from first user message (backend also does this atomically)
    const conv = conversations.find((c) => c.id === activeConvId);
    if (conv && conv.title === "New Chat") {
      const clean = userMessage.replace(/\s+/g, " ").trim();
      const title =
        clean.length > 50 ? clean.slice(0, 47) + "..." : clean;

      // Update local state immediately for responsive UI
      setConversations((prev) =>
        prev.map((c) =>
          c.id === activeConvId ? { ...c, title } : c
        )
      );
    }

    // Cancel any previous stream in progress
    if (abortRef.current) {
      abortRef.current.abort();
    }

    // Add a placeholder bot message for streaming
    const msgId = `bot_${Date.now()}`;
    addMessageToActive({
      id: msgId,
      role: "bot",
      text: "",
      sources: [],
      streaming: true,
    });

    abortRef.current = sendMessageStreamWithChat(
      userMessage,
      activeConvId,
      // onToken
      (token) => {
        updateMessage(msgId, {
          text: (prev) => (prev || "") + token,
        });
      },
      // onSources
      (sources) => {
        updateMessage(msgId, { sources, streaming: false });
        setLoading(false);
      },
      // onChatId - for new chats, update the conversation ID
      (chatId) => {
        if (chatId && chatId !== activeConvId) {
          setActiveConvId(chatId);
          setConversations((prev) =>
            prev.map((c) =>
              c.id === activeConvId ? { ...c, id: chatId } : c
            )
          );
        }
      },
      // onError
      (error) => {
        addToast(error, "error");
        updateMessage(msgId, {
          text: (prev) => prev || "Something went wrong. Please try again.",
          streaming: false,
        });
        setLoading(false);
      }
    );
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  if (initialLoading) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="w-6 h-6 border-2 border-[#2563EB] border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

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
            <div key={conv.id} className="group relative">
              <button
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
              <button
                onClick={(e) => handleDeleteChat(e, conv.id)}
                className="absolute right-1 top-1/2 -translate-y-1/2 p-1 rounded opacity-0 group-hover:opacity-100 hover:bg-red-50 transition-all"
                title="Delete conversation"
              >
                <Trash2 className="w-3.5 h-3.5 text-red-400 hover:text-red-600" />
              </button>
            </div>
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
                answers with source citations. Your conversation history is
                saved automatically.
              </p>
            </div>
          </div>
        ) : (
          <div className="flex-1 overflow-y-auto px-6 py-6">
            <div className="max-w-4xl mx-auto">
              {messages.map((m) => (
                <MessageBubble
                  key={m.id}
                  role={m.role}
                  text={m.text}
                  sources={m.sources}
                  streaming={m.streaming}
                />
              ))}
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

      {/* Delete Confirmation */}
      <ConfirmDialog
        open={!!deleteTarget}
        title="Delete Conversation"
        message="Are you sure you want to delete this conversation and all its messages? This action cannot be undone."
        confirmLabel="Delete"
        cancelLabel="Cancel"
        onConfirm={confirmDeleteChat}
        onCancel={() => setDeleteTarget(null)}
        variant="danger"
      />
    </div>
  );
}
