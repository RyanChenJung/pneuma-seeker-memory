import { useEffect, useRef, useState } from "react";

interface Props {
  chatList: string[];
  currentChatId: string;
  onSelectChat: (chatId: string) => void;
  onAddChat: () => void;
  onRenameChat: (oldId: string, newId: string) => void;
  onDeleteChat: (chatId: string) => void;
}

export default function ChatList({
  chatList,
  currentChatId,
  onSelectChat,
  onAddChat,
  onRenameChat,
  onDeleteChat,
}: Props) {
  const [openMenuChatId, setOpenMenuChatId] = useState<string | null>(null);
  const [editingChatId, setEditingChatId] = useState<string | null>(null);
  const [editingName, setEditingName] = useState("");

  const menuRef = useRef<HTMLUListElement | null>(null);
  const buttonRef = useRef<HTMLButtonElement | null>(null);

  // Close menu on outside click
  useEffect(() => {
    function handleDocClick(e: MouseEvent) {
      const target = e.target as Node;
      if (
        (menuRef.current && menuRef.current.contains(target)) ||
        (buttonRef.current && buttonRef.current.contains(target))
      ) {
        return;
      }
      setOpenMenuChatId(null);
    }
    document.addEventListener("mousedown", handleDocClick);
    return () => document.removeEventListener("mousedown", handleDocClick);
  }, []);

  // Handle Enter key or blur on rename input
  function finishRename(oldId: string) {
    const newId = editingName.trim();
    if (newId && newId !== oldId) {
      onRenameChat(oldId, newId);
    }
    setEditingChatId(null);
    setOpenMenuChatId(null);
  }

  return (
    <aside className="w-56 bg-gray-100 border-r p-4 overflow-y-auto flex flex-col">
      <h2 className="font-bold mb-2">Chats</h2>
      <ul className="flex-grow overflow-auto">
        {chatList.map((chatId) => {
          const isOpen = openMenuChatId === chatId;
          const isEditing = editingChatId === chatId;

          return (
            <li
              key={chatId}
              className={`relative select-none mb-1 rounded cursor-pointer flex justify-between items-center px-3 py-2
                ${chatId === currentChatId ? "bg-[#800000]" : "hover:bg-gray-300 transition duration-200"}`}
              onClick={() => {
                if (!isEditing) {
                  onSelectChat(chatId);
                  setOpenMenuChatId(null);
                }
              }}
            >
              <span className="flex-grow truncate mr-2">
                {isEditing ? (
                  <input
                    type="text"
                    autoFocus
                    value={editingName}
                    onChange={(e) => setEditingName(e.target.value)}
                    onBlur={() => finishRename(chatId)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") {
                        finishRename(chatId);
                      } else if (e.key === "Escape") {
                        setEditingChatId(null);
                        setOpenMenuChatId(null);
                      }
                    }}
                    className="w-full p-1 rounded border border-gray-400"
                  />
                ) : (
                  <span className={chatId === currentChatId ? "text-white" : "text-black"}>
                    {chatId}
                  </span>
                )}
              </span>

              <div className="relative">
                <button
                  ref={isOpen ? buttonRef : null}
                  aria-label={`Open menu for ${chatId}`}
                  className="p-1 rounded hover:bg-gray-400 cursor-pointer transition duration-200"
                  onClick={(e) => {
                    e.stopPropagation();
                    setOpenMenuChatId((prev) => (prev === chatId ? null : chatId));
                  }}
                  aria-expanded={isOpen}
                >
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    className="h-5 w-5 text-gray-600"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    strokeWidth={2}
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v.01M12 12v.01M12 18v.01" />
                  </svg>
                </button>

                {isOpen && (
                  <ul
                    ref={menuRef}
                    className="
                      absolute right-0 top-full mt-1 w-28 bg-white border border-gray-300 rounded shadow-md z-50
                      origin-top-right transform transition ease-out duration-200 opacity-100 scale-100
                    "
                    onClick={(e) => e.stopPropagation()}
                    style={{ willChange: "opacity, transform" }}
                  >
                    <li
                      className="px-3 py-2 hover:bg-gray-200 transition duration-200 cursor-pointer"
                      onClick={() => {
                        setEditingChatId(chatId);
                        setEditingName(chatId);
                        setOpenMenuChatId(null);
                      }}
                    >
                      Rename
                    </li>
                    <li
                      className="px-3 py-2 hover:bg-gray-200 transition duration-200 cursor-pointer"
                      onClick={() => {
                        setOpenMenuChatId(null);
                        if (window.confirm(`Are you sure you want to delete chat "${chatId}"?`)) {
                          onDeleteChat(chatId);
                        }
                      }}
                    >
                      Delete
                    </li>
                  </ul>
                )}
              </div>
            </li>
          );
        })}
      </ul>

      <button
        onClick={onAddChat}
        className="mt-2 p-2 bg-[#800000] text-white rounded hover:bg-[#510400] transition duration-200 cursor-pointer"
      >
        + New Chat
      </button>
    </aside>
  );
}
