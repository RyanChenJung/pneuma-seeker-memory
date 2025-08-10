'use client';
import { useEffect, useRef } from "react";
import Message from "./Message";
import { MessageFormat as MessageType } from "../models/message";

interface Props {
  messages: MessageType[];
  toolsVisible: boolean;
}

export default function ChatWindow({ messages, toolsVisible }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [messages]);

  if (!toolsVisible) {
    messages = messages.filter((m) => m.sender !== 'log');
  }

  return (
    <div
      ref={containerRef}
      className="flex-1 overflow-y-auto p-4 flex flex-col bg-gray-50"
    >
      {messages.map((msg, i) => (
        <Message key={i} message={msg} />
      ))}
    </div>
  );
}
