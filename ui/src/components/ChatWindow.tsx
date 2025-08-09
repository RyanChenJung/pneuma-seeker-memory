'use client';
import { useEffect, useRef } from "react";
import Message from "./Message";
import { Message as MessageType } from "../models/message";

interface Props {
  messages: MessageType[];
}

export default function ChatWindow({ messages }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [messages]);

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
