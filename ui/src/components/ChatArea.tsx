"use client";
import { useEffect, useState, useRef } from "react";
import { getMessagesForChat } from "@/lib/api";
import { useSessionStore } from "@/stores/sessionStore";
import { sendPrompt, closeWebSocket } from "@/lib/webSocketHandler";
import { MessageFormat } from "@/models/message";
import Message from "./Message";

export default function ChatArea() {
  const { currentUserId, currentChatId } = useSessionStore();
  const [messages, setMessages] = useState<MessageFormat[]>([]);
  const [input, setInput] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (currentUserId && currentChatId) {
      getMessagesForChat(currentUserId, currentChatId).then(setMessages);
      return () => {
        closeWebSocket();
      };
    }
  }, [currentUserId, currentChatId]);

  // Scroll to bottom whenever messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  if (!currentChatId) {
    return (
      <div className="flex-1 flex items-center justify-center p-4 text-gray-500 italic select-none">
        Select a chat to start
      </div>
    );
  }

  const onMessage = (event: MessageEvent) => {
    const message: MessageFormat = JSON.parse(event.data);
    setMessages((prevMessages) => [
      ...prevMessages,
      {
        sender: message.sender,
        text: message.text,
        time_stamp: message.time_stamp,
      },
    ]);
  };

  const handleSend = () => {
    if (!input.trim() || !currentUserId || !currentChatId) return;
    setMessages((prevMessages) => [
      ...prevMessages,
      { text: input.trim(), sender: "user", time_stamp: Date.now() },
    ]);
    sendPrompt(currentUserId, currentChatId, input.trim(), onMessage);
    setInput("");
  };

  return (
    <div className="flex-1 flex flex-col bg-white border-l border-gray-200">
      <div
        className="flex-1 overflow-y-auto px-6 py-4 flex flex-col space-y-1 bg-[#F9F4F6]"
        style={{ scrollbarGutter: "stable" }}
      >
        {messages.length === 0 && (
          <div className="text-gray-400 italic text-center mt-8 select-none">
            No messages yet
          </div>
        )}

        {messages.map((msg, i) => (
          <Message key={i} message={msg} />
        ))}

        <div ref={messagesEndRef} />
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          handleSend();
        }}
        className="flex items-center border-t border-gray-300 px-4 py-3 bg-white"
      >
        <input
          type="text"
          placeholder="Type your message..."
          className="flex-1 border border-gray-300 rounded-md px-4 py-2 mr-3
            focus:outline-none focus:ring-2 focus:ring-[#7A0C2E] focus:border-[#7A0C2E] transition"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          autoComplete="off"
        />
        <button
          type="submit"
          className="bg-[#7A0C2E] hover:bg-[#8B1036] text-white font-semibold px-5 py-2 rounded-md
            transition-colors duration-300 cursor-pointer focus:outline-none focus:ring-2 focus:ring-[#7A0C2E]"
        >
          Send
        </button>
      </form>
    </div>
  );
}
