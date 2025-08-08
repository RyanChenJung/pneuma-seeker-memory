import ChatWindow from "./ChatWindow";
import ChatInput from "./ChatInput";
import { Message as MessageType } from "../models/message";
import { PanelRightClose } from "lucide-react";

interface Props {
  messages: MessageType[];
  onSend: (text: string) => void;
  statusVisible: boolean;
  onToggle: () => void;
}

export default function ChatArea({ messages, onSend, statusVisible, onToggle }: Props) {
  return (
    <main
      className={`
        relative flex flex-col flex-grow bg-gray-50 rounded-b-lg md:rounded-r-lg transition-all duration-500 ease-in-out
        ${statusVisible ? "" : "w-full"}
      `}
      style={{ minWidth: 0 }}
    >
      {!statusVisible && (
        <button
          onClick={onToggle}
          aria-label="Show Status Panel"
          className="absolute top-2 left-2 px-3 py-1 rounded bg-[#800000] text-white hover:bg-[#510400] cursor-pointer transition"
        >
          {<PanelRightClose />}
        </button>
      )}

      <div className="bg-white border-b border-gray-300 px-6 py-4 text-xl font-semibold shadow-sm text-center">
        Pneuma-Seeker: Data Assistant System
      </div>

      <ChatWindow messages={messages} />
      <ChatInput onSend={onSend} />
    </main>
  );
}
