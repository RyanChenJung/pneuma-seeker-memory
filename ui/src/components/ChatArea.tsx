import ChatWindow from "./ChatWindow";
import ChatInput from "./ChatInput";
import { MessageFormat as MessageType } from "../models/message";
import { Eye, EyeOff, PanelRightClose } from "lucide-react";

interface Props {
  messages: MessageType[];
  onSend: (text: string) => void;
  statusVisible: boolean;
  toolsVisible: boolean;
  onToggleStatus: () => void;
  onToggleTools: () => void;
}

export default function ChatArea({ messages, onSend, statusVisible, toolsVisible, onToggleStatus, onToggleTools }: Props) {
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
          onClick={onToggleStatus}
          aria-label="Show Status Panel"
          className="absolute top-2 left-2 px-3 py-1 rounded bg-[#800000] text-white hover:bg-[#510400] cursor-pointer transition"
        >
          {<PanelRightClose />}
        </button>
      )}

      <div className="bg-white border-b border-gray-300 px-6 py-4 text-xl font-semibold shadow-sm text-center">
        Pneuma-Seeker: Data Assistant System
      </div>

      <button
        onClick={onToggleTools}
        aria-label="Show Tools"
        className="absolute top-2 right-2 px-5 py-1 rounded bg-[#800000] text-white hover:bg-[#510400] cursor-pointer transition flex items-center gap-2"
      >
        {toolsVisible ? (
          <>
            Tools <EyeOff className="w-4 h-4" />
          </>
        ) : (
          <>
            Tools <Eye className="w-4 h-4" />
          </>
        )}
      </button>


      <ChatWindow messages={messages} toolsVisible={toolsVisible} />
      <ChatInput onSend={onSend} />
    </main>
  );
}
