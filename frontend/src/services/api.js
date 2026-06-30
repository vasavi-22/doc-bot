import axios from "axios";

const API = import.meta.env.VITE_API_URL || "http://localhost:5000";

// Axios interceptor to attach JWT token to all requests
axios.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Auth API calls
export const loginApi = (email, password) =>
  axios.post(`${API}/api/auth/login`, { email, password });

export const registerApi = (name, email, password) =>
  axios.post(`${API}/api/auth/register`, { name, email, password });

export const getMeApi = () =>
  axios.get(`${API}/api/auth/me`);

// Chat API calls

export const sendMessage = (message) =>
  axios.post(`${API}/chat`, { message });

export const sendMessageStream = (message, onToken, onSources, onError) => {
  const controller = new AbortController();
  const token = localStorage.getItem("token");

  fetch(`${API}/chat/stream`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({ message }),
    signal: controller.signal,
  })
    .then(async (response) => {
      if (!response.ok) {
        const err = await response.json().catch(() => ({ error: "Request failed" }));
        onError(err.error || `HTTP ${response.status}`);
        return;
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      const processLine = (line) => {
        if (!line.startsWith("data: ")) return;
        const jsonStr = line.slice(6);
        try {
          const data = JSON.parse(jsonStr);
          if (data.type === "token") {
            onToken(data.content);
          } else if (data.type === "sources") {
            onSources(data.sources || []);
          } else if (data.type === "error") {
            onError(data.message);
          }
        } catch {
          // Ignore malformed JSON
        }
      };

      const read = async () => {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          // Keep the last potentially incomplete line in the buffer
          buffer = lines.pop() || "";

          for (const line of lines) {
            if (line.trim()) processLine(line.trim());
          }
        }

        // Process any remaining buffer content
        if (buffer.trim()) processLine(buffer.trim());
      };

      read().catch((err) => {
        if (err.name !== "AbortError") {
          onError(err.message || "Stream read error");
        }
      });
    })
    .catch((err) => {
      if (err.name !== "AbortError") {
        onError(err.message || "Network error");
      }
    });

  return controller;
};

export const uploadFile = (file) => {
  const formData = new FormData();
  formData.append("file", file);

  return axios.post(`${API}/upload`, formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });
};

export const getDocuments = () =>
  axios.get(`${API}/documents`);

export const deleteDocument = (documentId) =>
  axios.delete(`${API}/documents/${documentId}`);

// Chat / Conversation API calls

export const getConversations = () =>
  axios.get(`${API}/api/conversations`);

export const createConversation = (title) =>
  axios.post(`${API}/api/conversations`, { title });

export const getConversation = (chatId) =>
  axios.get(`${API}/api/conversations/${chatId}`);

export const updateConversation = (chatId, data) =>
  axios.patch(`${API}/api/conversations/${chatId}`, data);

export const deleteConversation = (chatId) =>
  axios.delete(`${API}/api/conversations/${chatId}`);

export const getMessages = (chatId) =>
  axios.get(`${API}/api/conversations/${chatId}/messages`);

export const getDashboardStats = () =>
  axios.get(`${API}/api/conversations/dashboard-stats`);

// Updated sendMessageStream to include chat_id
export const sendMessageStreamWithChat = (message, chatId, onToken, onSources, onChatId, onError) => {
  const controller = new AbortController();
  const token = localStorage.getItem("token");

  fetch(`${API}/chat/stream`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({ message, chat_id: chatId }),
    signal: controller.signal,
  })
    .then(async (response) => {
      if (!response.ok) {
        const err = await response.json().catch(() => ({ error: "Request failed" }));
        onError(err.error || `HTTP ${response.status}`);
        return;
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      const processLine = (line) => {
        if (!line.startsWith("data: ")) return;
        const jsonStr = line.slice(6);
        try {
          const data = JSON.parse(jsonStr);
          if (data.type === "token") {
            onToken(data.content);
          } else if (data.type === "sources") {
            onSources(data.sources || []);
          } else if (data.type === "chat_id") {
            onChatId(data.chat_id);
          } else if (data.type === "error") {
            onError(data.message);
          }
        } catch {
          // Ignore malformed JSON
        }
      };

      const read = async () => {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() || "";

          for (const line of lines) {
            if (line.trim()) processLine(line.trim());
          }
        }

        if (buffer.trim()) processLine(buffer.trim());
      };

      read().catch((err) => {
        if (err.name !== "AbortError") {
          onError(err.message || "Stream read error");
        }
      });
    })
    .catch((err) => {
      if (err.name !== "AbortError") {
        onError(err.message || "Network error");
      }
    });

  return controller;
};