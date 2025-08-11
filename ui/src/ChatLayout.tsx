// ChatLayout.tsx (same level with parent folder of components)
"use client";
import UserSelector from "@/components/UserSelector";
import ChatList from "@/components/ChatList";
import ChatArea from "@/components/ChatArea";
import { useSessionStore } from "@/stores/sessionStore";

export default function ChatLayout() {
  const { currentUserId } = useSessionStore();

  return (
    <div className="h-screen flex flex-col">
      <UserSelector />
      <div className="flex flex-1">
        {currentUserId && <ChatList />}
        <ChatArea />
      </div>
    </div>
  );
}
