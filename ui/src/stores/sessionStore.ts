import { create } from "zustand";
import { persist } from "zustand/middleware";

interface SessionState {
  currentUserId: string | null;
  currentChatId: string | null;
  setCurrentUserId: (id: string | null) => void;
  setCurrentChatId: (id: string | null) => void;
}

export const useSessionStore = create<SessionState>()(
  persist(
    (set) => ({
      currentUserId: null,
      currentChatId: null,
      setCurrentUserId: (id) => set({ currentUserId: id, currentChatId: null }),
      setCurrentChatId: (id) => set({ currentChatId: id }),
    }),
    {
      name: "session-storage", // name of the item in storage
      // you can also customize storage: localStorage, sessionStorage, or custom
    }
  )
);
