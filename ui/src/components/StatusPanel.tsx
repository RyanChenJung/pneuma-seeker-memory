import { PanelRightOpen } from "lucide-react";
import { Message as MessageType } from "../models/message";

interface Props {
  messages: MessageType[];
  visible: boolean;
  onToggle: () => void;
}

export default function StatusPanel({ messages, visible, onToggle }: Props) {
  return (
    <aside
      className={`
        relative bg-white border-gray-300 flex flex-col transition-all duration-500 ease-in-out overflow-hidden
        ${visible
          ? "md:max-w-[33%] max-w-full border-r md:border-r border-b md:border-b-0 p-6"
          : "max-w-0 border-0 p-0"}
      `}
      style={{ minWidth: 0 }}
    >
      {visible && (
        <>
          <button
            onClick={onToggle}
            aria-label="Hide Status Panel"
            className="absolute top-2 right-2 px-3 py-1 rounded bg-[#800000] cursor-pointer text-white hover:bg-[#510400] transition"
          >
            <PanelRightOpen />
          </button>

          <h2 className="text-xl font-semibold mb-4">System's State</h2>
          <div className="flex-grow overflow-auto">
            <p className="mb-2">
              <strong>S:</strong> (target tables)
            </p>
            <p className="mb-2">
              <strong>Q:</strong> (SQL queries)
            </p>
            <p className="mb-2">
              <strong>Currently Retrieved Documents</strong> (currently retrieved docs)
            </p>
          </div>
        </>
      )}
    </aside>
  );
}
