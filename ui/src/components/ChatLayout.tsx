'use client';
import { useChatStore } from "@/stores/chatStore";
import { sendPrompt } from "@/lib/webSocketHandler";
import { useState } from "react";
import StatusPanel from "./StatusPanel";
import ChatArea from "./ChatArea";
import ChatList from "./ChatList";

export default function ChatLayout() {
  const currentChatId = useChatStore((state) => state.currentChatId);
  const messages = useChatStore((state) => state.messages[currentChatId] || []);
  const chatList = useChatStore((state) => state.chatList);
  const setCurrentChatId = useChatStore((state) => state.setCurrentChatId);
  const addChat = useChatStore((state) => state.addChat);

  const [statusVisible, setStatusVisible] = useState(false);
  const [toolsVisible, setToolsVisible] = useState(true);

  const sendMessage = (text: string) => {
    sendPrompt(currentChatId, text);
    useChatStore.getState().addMessage(currentChatId, { text, sender: "user" });
  };

  const toggleStatus = () => setStatusVisible((v) => !v);
  const toggleTools = () => setToolsVisible((v) => !v);

  const handleAddChat = () => {
    const newChatId = `chat-${Date.now()}`;
    addChat(newChatId);
  };

  return (
    <div className="flex h-screen border border-gray-300 rounded-lg overflow-hidden shadow-lg">
      <ChatList
        chatList={chatList}
        currentChatId={currentChatId}
        onSelectChat={setCurrentChatId}
        onAddChat={handleAddChat}
      />
      <StatusPanel messages={messages} visible={statusVisible} onToggleStatus={toggleStatus} />
      <ChatArea
        messages={messages}
        onSend={sendMessage}
        statusVisible={statusVisible}
        toolsVisible={toolsVisible}
        onToggleStatus={toggleStatus}
        onToggleTools={toggleTools}
      />
    </div>
  );
}
