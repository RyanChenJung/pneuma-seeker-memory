// stores/chatStore.ts
import { create } from "zustand";
import { persist } from "zustand/middleware";

export type MessageFormat = {
  text: string;
  sender: "user" | "assistant" | "log";
};

type ChatStore = {
  currentChatId: string;
  chatList: string[];
  messages: Record<string, MessageFormat[]>;
  systemStates: Record<string, any>; // optional, for StatusPanel per chat

  setCurrentChatId: (chatId: string) => void;
  addChat: (chatId: string) => void;
  addMessage: (chatId: string, msg: MessageFormat) => void;
  clearMessages: (chatId: string) => void;
  setSystemState: (chatId: string, state: any) => void;
};

export const useChatStore = create<ChatStore>()(
  persist(
    (set, get) => ({
      currentChatId: "chat-1",
      chatList: ["chat-1"],

      messages: {
        "chat-1": [{ text: "Hello! How can I help you today?", sender: "assistant" }],
      },

      systemStates: {},

      setCurrentChatId(chatId) {
        set({ currentChatId: chatId });
      },

      addChat(chatId) {
        if (!get().chatList.includes(chatId)) {
          set((state) => ({
            chatList: [...state.chatList, chatId],
            messages: { ...state.messages, [chatId]: [] },
          }));
        }
        set({ currentChatId: chatId });
      },

      addMessage(chatId, msg) {
        set((state) => ({
          messages: {
            ...state.messages,
            [chatId]: [...(state.messages[chatId] || []), msg],
          },
        }));
      },

      clearMessages(chatId) {
        set((state) => ({
          messages: { ...state.messages, [chatId]: [] },
        }));
      },

      setSystemState(chatId, state) {
        set((store) => ({
          systemStates: {
            ...store.systemStates,
            [chatId]: state,
          },
        }));
      },
    }),
    {
      name: "pneuma-chat-storage", // name of item in localStorage
      partialize: (state) => ({
        currentChatId: state.currentChatId,
        chatList: state.chatList,
        messages: state.messages,
        // optionally, you can add systemStates if you want it persisted too:
        // systemStates: state.systemStates,
      }),
    }
  )
);
