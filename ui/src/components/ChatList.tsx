// components/ChatList.tsx
interface Props {
  chatList: string[];
  currentChatId: string;
  onSelectChat: (chatId: string) => void;
  onAddChat: () => void;
}

export default function ChatList({ chatList, currentChatId, onSelectChat, onAddChat }: Props) {
  return (
    <aside className="w-56 bg-gray-100 border-r p-4 overflow-y-auto flex flex-col">
      <h2 className="font-bold mb-2">Chats</h2>
      <ul className="flex-grow overflow-auto">
        {chatList.map((chatId) => (
          <li
            key={chatId}
            onClick={() => onSelectChat(chatId)}
            className={`cursor-pointer py-2 px-3 rounded mb-1 ${
              chatId === currentChatId ? "bg-[#800000] text-white" : "hover:bg-gray-300"
            }`}
          >
            {chatId}
          </li>
        ))}
      </ul>
      <button
        onClick={onAddChat}
        className="mt-2 p-2 bg-[#800000] text-white rounded hover:bg-[#510400] transition"
      >
        + New Chat
      </button>
    </aside>
  );
}
