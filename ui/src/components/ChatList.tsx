"use client";
import { useEffect, useRef, useState } from "react";
import { getChatsForUser, createChat, renameChat, deleteChat } from "@/lib/api";
import { useSessionStore } from "@/stores/sessionStore";
import { ChevronLeft, ChevronRight, Edit, X } from "lucide-react";

/**
 * ChatList.tsx
 * - collapsible sidebar in the normal flex flow so ChatArea expands
 * - mobile: full-screen overlay when open
 * - inline rename (ChatGPT style)
 */
export default function ChatList() {
  const { currentUserId, currentChatId, setCurrentChatId } = useSessionStore();

  const [chats, setChats] = useState<[string, string][]>([]);
  const [chatToDelete, setChatToDelete] = useState<string | null>(null);

  // UI state
  const [isOpen, setIsOpen] = useState<boolean>(true); // sidebar open/closed
  const [isMobile, setIsMobile] = useState<boolean>(false);
  const [editingChatId, setEditingChatId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState("");
  const [viewStateOpen, setViewStateOpen] = useState(false); // NEW: modal state

  const inputRef = useRef<HTMLInputElement | null>(null);

  // fetch chats
  useEffect(() => {
    if (currentUserId) {
      getChatsForUser(currentUserId).then(setChats);
    }
  }, [currentUserId]);

  // determine mobile on mount and on resize
  useEffect(() => {
    const handleResize = () => {
      const mobile = window.innerWidth < 768;
      setIsMobile(mobile);
      // default open behavior per device:
      setIsOpen(!mobile);
    };

    handleResize(); // initial
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  // lock body scrolling when mobile overlay open
  useEffect(() => {
    if (isMobile) {
      document.body.style.overflow = isOpen ? "hidden" : "";
    } else {
      document.body.style.overflow = "";
    }
    return () => {
      document.body.style.overflow = "";
    };
  }, [isMobile, isOpen]);

  // auto-focus editing input
  useEffect(() => {
    if (editingChatId && inputRef.current) {
      inputRef.current.focus();
      inputRef.current.select();
    }
  }, [editingChatId]);

  if (!currentUserId) return null;

  const handleAddChat = async () => {
    const chatId = await createChat(currentUserId);
    setChats((prev) => [...prev, [chatId, "Untitled Chat"]]);
    setCurrentChatId(chatId);
    if (isMobile) setIsOpen(false); // collapse on mobile after creation
  };

  const saveRename = async (chatId: string) => {
    const trimmed = editTitle.trim();
    if (!trimmed) {
      // cancel if empty
      setEditingChatId(null);
      return;
    }
    const ok = await renameChat(currentUserId, chatId, trimmed);
    if (ok) {
      setChats((prev) =>
        prev.map(([id, title]) => (id === chatId ? [id, trimmed] : [id, title]))
      );
    }
    setEditingChatId(null);
  };

  const onEditKeyDown = (
    e: React.KeyboardEvent<HTMLInputElement>,
    chatId: string
  ) => {
    if (e.key === "Enter") {
      e.preventDefault();
      saveRename(chatId);
    } else if (e.key === "Escape") {
      setEditingChatId(null);
    }
  };

  const onSelectChat = (id: string) => {
    setCurrentChatId(id);
    if (isMobile) setIsOpen(false);
  };

  const confirmDeleteChat = async () => {
    if (!chatToDelete) return;
    const ok = await deleteChat(currentUserId, chatToDelete);
    if (ok) {
      setChats((prev) => prev.filter(([id]) => id !== chatToDelete));
      // if current chat is deleted, reset selection
      if (currentChatId === chatToDelete) setCurrentChatId(null);
    }
    setChatToDelete(null);
  };

  /**
   * Layout decisions:
   * - This wrapper participates in flex layout of ChatLayout.
   * - On md+ it's a collapsible column with width toggling.
   * - On small screens, when open it becomes fixed overlay (fullscreen).
   */
  return (
    <>
      <aside
        // keep in flow so ChatArea grows/shrinks
        className={`flex-shrink-0 transition-width duration-300 ease-in-out
          ${isOpen ? "w-64" : "w-10"}
          md:${isOpen ? "w-64" : "w-10"}
          border-r border-gray-200 bg-white flex flex-col z-30
          ${isMobile && isOpen ? "fixed inset-0 w-full h-full" : "relative"}
        `}
      >
        {/* collapse/expand control - visible on all sizes; visually floats at right edge */}
        <button
          onClick={() => setIsOpen((s) => !s)}
          aria-label={isOpen ? "Collapse sidebar" : "Expand sidebar"}
          className={`absolute top-4 right-[-18px] z-40 w-8 h-8 rounded-full cursor-pointer
            flex items-center justify-center text-white shadow-md transition duration-300
            bg-[#7A0C2E] hover:bg-[#8B1036] focus:outline-none focus:ring-2 focus:ring-[#7A0C2E]`}
        >
          {isOpen ? <ChevronLeft size={16} /> : <ChevronRight size={16} />}
        </button>

        {/* header area: View State button + New Chat */}
        <div className={`p-3 flex items-center ${isOpen ? "" : "hidden"}`}>
          <button
            onClick={() => setViewStateOpen(true)}
            className="py-2 px-3 rounded-md border border-[#7A0C2E] text-[#7A0C2E] font-semibold hover:bg-[#7A0C2E] hover:text-white transition duration-300 cursor-pointer"
          >
            State
          </button>

          <button
            onClick={handleAddChat}
            className="ml-3 py-2 px-3 rounded-md bg-[#7A0C2E] text-white font-semibold hover:bg-[#8B1036] transition duration-300 cursor-pointer"
          >
            + New Chat
          </button>
        </div>

        {/* when collapsed (narrow) you might show just the plus icon instead */}
        {!isOpen && (
          <div className="flex items-center justify-center p-1">
            <button
              onClick={handleAddChat}
              aria-label="New chat"
              className="cursor-pointer w-8 h-8 rounded-md flex items-center justify-center bg-[#7A0C2E] hover:bg-[#8B1036] text-white transition duration-300"
            >
              +
            </button>
          </div>
        )}

        {/* chat list */}
        <div className={`flex-1 overflow-y-auto ${isOpen ? "p-2" : "p-1"}`}>
          {chats.map(([id, title]) => {
            const isCurrent = currentChatId === id;
            const isEditing = editingChatId === id;
            return (
              <div
                key={id}
                onClick={() => onSelectChat(id)}
                className={`flex items-center justify-between gap-2 rounded-lg transition-colors duration-200
                  ${
                    isCurrent
                      ? "bg-[#F4E6E9] text-[#7A0C2E]"
                      : "hover:bg-[#F9F2F4] text-gray-900"
                  }
                  ${isOpen ? "px-3 py-2 my-2" : "px-1 py-1 my-1"}
                `}
              >
                {/* left: title or input */}
                <div className="flex-1 min-w-0 cursor-pointer">
                  {isEditing ? (
                    <input
                      ref={inputRef}
                      value={editTitle}
                      onChange={(e) => setEditTitle(e.target.value)}
                      onBlur={() => saveRename(id)}
                      onKeyDown={(e) => onEditKeyDown(e, id)}
                      className="w-full rounded px-2 py-1 border border-gray-300 text-sm"
                      aria-label="Edit chat title"
                    />
                  ) : (
                    <div className="flex items-center gap-2">
                      <span
                        className={`truncate text-sm ${
                          isOpen
                            ? "max-w-[180px]"
                            : "max-w-[40px] text-center text-xs"
                        }`}
                        title={title}
                      >
                        {title}
                      </span>
                    </div>
                  )}
                </div>

                {/* right: actions (hidden when collapsed to save space) */}
                {isOpen && !isEditing && (
                  <div className="flex items-center gap-2 text-sm">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setEditingChatId(id);
                        setEditTitle(title);
                      }}
                      className="flex items-center gap-1 text-blue-800 hover:text-blue-500 cursor-pointer transition duration-200"
                      aria-label={`Rename ${title}`}
                    >
                      <Edit size={14} />
                      <span>Rename</span>
                    </button>

                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setChatToDelete(id);
                      }}
                      className="flex items-center gap-1 text-[#B02C3D] hover:text-[#8B1036] cursor-pointer transition duration-200"
                      aria-label={`Delete ${title}`}
                    >
                      <X size={14} />
                      <span>Delete</span>
                    </button>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </aside>

      {/* mobile overlay backdrop (only when open on mobile) */}
      {isMobile && isOpen && (
        <div
          className="fixed inset-0 bg-black/30 z-20"
          onClick={() => setIsOpen(false)}
          aria-hidden
        />
      )}

      {/* delete modal (same as before) */}
      {chatToDelete && (
        <div
          className="fixed inset-0 flex items-center justify-center bg-black bg-opacity-60 z-50"
          onClick={() => setChatToDelete(null)}
        >
          <div
            className="bg-white rounded-lg shadow-lg p-6 w-80 max-w-full"
            onClick={(e) => e.stopPropagation()}
          >
            <h2 className="text-lg font-semibold mb-4 text-[#7A0C2E]">
              Confirm Deletion
            </h2>
            <p className="mb-6 text-gray-700">
              Are you sure you want to delete this chat? This action cannot be
              undone.
            </p>
            <div className="flex justify-end space-x-4">
              <button
                onClick={() => setChatToDelete(null)}
                className="cursor-pointer px-4 py-2 rounded-md border border-gray-300 text-gray-700 hover:bg-gray-100 transition"
              >
                Cancel
              </button>
              <button
                onClick={confirmDeleteChat}
                className="cursor-pointer px-4 py-2 rounded-md bg-[#B02C3D] text-white hover:bg-[#8B1036] transition"
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      )}

      {/* VIEW STATE MODAL */}
      {viewStateOpen && (
        <>
          <div
            className="fixed inset-0 bg-black/40 z-50"
            onClick={() => setViewStateOpen(false)}
            aria-hidden="true"
          />
          <div className="fixed inset-0 z-50 flex items-center justify-center px-4">
            <div
              className="bg-white rounded-lg shadow-lg p-6 max-w-md w-full"
              onClick={(e) => e.stopPropagation()}
            >
              <h3 className="text-xl font-semibold mb-4 text-[#7A0C2E]">
                Current State
              </h3>
              <pre className="bg-gray-100 p-3 rounded-md max-h-60 overflow-auto text-sm">
                {JSON.stringify(
                  {
                    currentUserId,
                    currentChatId,
                    isOpen,
                    isMobile,
                    editingChatId,
                    editTitle,
                    chats,
                  },
                  null,
                  2
                )}
              </pre>
              <div className="flex justify-end gap-3 mt-4">
                <button
                  type="button"
                  onClick={() => setViewStateOpen(false)}
                  className="cursor-pointer transition duration-300 px-4 py-2 rounded-md border border-gray-300 text-gray-700 hover:bg-gray-100"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        </>
      )}
    </>
  );
}
