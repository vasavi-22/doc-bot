import axios from "axios";

const API = "http://localhost:5000";
const API_URL = import.meta.env.VITE_API_URL;

export const sendMessage = (message) =>
  axios.post(`${API_URL}/chat`, { message });

export const sendMessageStream = (message, onToken, onSources, onError) => {
  const controller = new AbortController();

  fetch(`${API_URL}/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
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

  return axios.post(`${API_URL}/upload`, formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });
};

export const getDocuments = () =>
  axios.get(`${API_URL}/documents`);

export const deleteDocument = (filename) =>
  axios.delete(`${API_URL}/documents/${filename}`);