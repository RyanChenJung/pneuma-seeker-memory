'use client';
import { useState } from "react";

interface Props {
  onSend: (text: string) => void;
}

export default function ChatInput({ onSend }: Props) {
  const [input, setInput] = useState("");

  const handleSend = () => {
    if (!input.trim()) return;
    onSend(input.trim());
    setInput("");
  };

  const onKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <form
      onSubmit={handleSend}
      className="flex p-4 border-t border-gray-300 bg-white"
    >
      <textarea
        rows={1}
        value={input}
        onChange={(e) => setInput(e.target.value)}
        placeholder="Type your message..."
        required
        className="flex-grow resize-none p-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#800000]"
      />
      <div className="relative group">
        <button
          onClick={handleSend}
          disabled={!input.trim()}
          className={`ml-3 px-4 py-2 rounded-lg font-semibold transition cursor-pointer ${input.trim()
              ? "bg-[#800000] text-white hover:bg-[#510400]"
              : "bg-gray-300 text-gray-500 cursor-not-allowed"
            }`}
        >
          Send
        </button>

        {!input.trim() && (
          <span className="absolute left-1/4 -translate-x-1/2 -top-8 whitespace-nowrap 
                     bg-black text-white text-xs px-2 py-1 rounded opacity-0 group-hover:opacity-100 
                     transition">
            Please type a message
          </span>
        )}
      </div>
    </form>

  );
}
