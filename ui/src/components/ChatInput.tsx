// components/ChatInput.tsx
'use client';
import { useState, useEffect, useRef } from "react";

interface Props {
  onSend: (text: string) => void;
}

export default function ChatInput({ onSend }: Props) {
  const [input, setInput] = useState("");
  const [isMobile, setIsMobile] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    setIsMobile(/Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent));
  }, []);

  const handleSend = () => {
    if (!input.trim()) return;
    onSend(input.trim());
    setInput("");
  };

  const onKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (!isMobile && e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        handleSend();
      }}
      className="flex p-4 border-t border-gray-300 bg-white"
    >
      <textarea
        ref={textareaRef}
        rows={1}
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyDown={onKeyDown}
        placeholder="Type your message..."
        required
        className="flex-grow resize-none p-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#800000]"
      />
      <div className="relative group">
        <button
          type="submit"
          disabled={!input.trim()}
          className={`ml-3 px-4 py-2 rounded-lg font-semibold transition cursor-pointer ${
            input.trim() ? "bg-[#800000] text-white hover:bg-[#510400]" : "bg-gray-300 text-gray-500 cursor-not-allowed"
          }`}
        >
          Send
        </button>

        {!input.trim() && (
          <span className="absolute left-1/2 -translate-x-1/2 -top-8 whitespace-nowrap 
                       bg-black text-white text-xs px-2 py-1 rounded opacity-0 group-hover:opacity-100 
                       transition">
            Please type a message
          </span>
        )}
      </div>
    </form>
  );
}
