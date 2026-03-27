import { create } from "zustand";

export const useChatStore = create((set) => ({
  messages: [],
  loading: false,

  addMessage: (msg) =>
    set((state) => ({
      messages: [...state.messages, msg],
    })),

  setLoading: (value) => set({ loading: value }),

  clearChat: () => set({ messages: [] }),
}));