"use client";
import { useEffect, useState } from "react";
import { getAllUsers, registerUser } from "@/lib/api";
import { useSessionStore } from "@/stores/sessionStore";
import { DatabaseZap, Menu, X } from "lucide-react";

export default function UserSelector() {
  const { currentUserId, setCurrentUserId } = useSessionStore();
  const [users, setUsers] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [registerOpen, setRegisterOpen] = useState(false);
  const [newUserId, setNewUserId] = useState("");

  useEffect(() => {
    setLoading(true);
    getAllUsers()
      .then(setUsers)
      .finally(() => setLoading(false));
  }, []);

  // Prevent background scroll when modals open
  useEffect(() => {
    if (mobileOpen || registerOpen) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "";
    }
    return () => {
      document.body.style.overflow = "";
    };
  }, [mobileOpen, registerOpen]);

  const onSelectUser = (id: string) => {
    setCurrentUserId(id);
    setMobileOpen(false);
  };

  const openRegister = () => {
    setNewUserId("");
    setRegisterOpen(true);
  };

  const logout = () => {
    setCurrentUserId(null);
  }

  const closeRegister = () => setRegisterOpen(false);

  const handleRegisterSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!newUserId.trim()) return; // extra safety
    setLoading(true);
    const success = await registerUser(newUserId.trim());
    setLoading(false);
    if (success) {
      setUsers((prev) => [...prev, newUserId.trim()]);
      setCurrentUserId(newUserId.trim());
      setRegisterOpen(false);
    }
  };

  return (
    <header className="flex items-center justify-between px-4 md:px-6 py-3 md:py-4 border-b border-gray-200 bg-white shadow-md z-20">
      {/* Title */}
      <h1
        className="flex-1 min-w-0 text-xl md:text-3xl font-semibold text-[#7A0C2E] hover:text-[#B84C62] transition duration-300 select-none"
        style={{
          fontFamily:
            '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Open Sans", "Helvetica Neue", sans-serif',
        }}
      >
        <a
          href="https://github.com/TheDataStation/pneuma"
          target="_blank"
          rel="noopener noreferrer"
          className="no-underline truncate flex items-center gap-2"
        >
          <DatabaseZap />
          Pneuma-Seeker
        </a>
      </h1>

      {/* Desktop user select + register button */}
      <div className="hidden md:flex items-center gap-4 ml-6">
        <select
          value={currentUserId || ""}
          onChange={(e) => setCurrentUserId(e.target.value)}
          className="border border-gray-300 rounded-md px-3 py-2 text-gray-900
            focus:outline-none focus:ring-2 focus:ring-[#7A0C2E] focus:border-[#7A0C2E]
            transition"
        >
          <option value="">Select a user...</option>
          {users.map((u) => (
            <option key={u} value={u}>
              {u}
            </option>
          ))}
        </select>

        <button
          onClick={currentUserId ? logout : openRegister}
          className="bg-[#7A0C2E] hover:bg-[#8B1036] text-white font-semibold px-5 py-2 rounded-md transition-colors duration-300 cursor-pointer focus:outline-none focus:ring-2 focus:ring-[#7A0C2E]"
        >
          {currentUserId ? "Logout" : "Register"}
        </button>

        {loading && (
          <span className="text-gray-500 italic select-none">Loading...</span>
        )}
      </div>

      {/* Mobile: compact user label + menu button */}
      <div className="md:hidden flex items-center gap-2 ml-4">
        <span className="text-sm text-gray-700 mr-2 truncate max-w-[110px]">
          {currentUserId ? `User: ${currentUserId}` : "No user"}
        </span>
        <button
          onClick={() => setMobileOpen(true)}
          aria-label="Open user menu"
          className="p-2 rounded-md bg-[#7A0C2E] text-white flex items-center justify-center focus:outline-none focus:ring-2 focus:ring-[#7A0C2E]"
        >
          <Menu size={18} />
        </button>
      </div>

      {/* Mobile full-screen user switch panel */}
      {mobileOpen && (
        <>
          <div
            className="fixed inset-0 bg-black/30 z-30"
            onClick={() => setMobileOpen(false)}
            aria-hidden
          />
          <div className="fixed inset-0 z-40 flex flex-col bg-white">
            <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200">
              <div className="flex items-center gap-3">
                <h2 className="text-lg font-semibold text-[#7A0C2E]">
                  Switch User
                </h2>
                {loading && (
                  <span className="text-sm text-gray-500 italic">
                    Loading...
                  </span>
                )}
              </div>
              <button
                onClick={() => setMobileOpen(false)}
                aria-label="Close"
                className="p-2 rounded-md bg-[#7A0C2E] text-white flex items-center justify-center focus:outline-none focus:ring-2 focus:ring-[#7A0C2E]"
              >
                <X size={18} />
              </button>
            </div>

            <div className="p-6 space-y-4 overflow-y-auto">
              <label className="block text-sm text-gray-700">Choose user</label>
              <select
                value={currentUserId || ""}
                onChange={(e) => onSelectUser(e.target.value)}
                className="w-full border border-gray-300 rounded-md px-3 py-2"
              >
                <option value="">Select a user...</option>
                {users.map((u) => (
                  <option key={u} value={u}>
                    {u}
                  </option>
                ))}
              </select>

              <button
                onClick={() => {
                  setMobileOpen(false);
                  openRegister();
                }}
                className="w-full bg-[#7A0C2E] hover:bg-[#8B1036] text-white font-semibold px-5 py-2 rounded-md transition-colors duration-300 cursor-pointer"
              >
                Register new user
              </button>
            </div>
          </div>
        </>
      )}

      {/* Register Modal */}
      {registerOpen && (
        <>
          <div
            className="fixed inset-0 bg-black/40 z-50"
            onClick={closeRegister}
            aria-hidden
          />
          <div className="fixed inset-0 z-50 flex items-center justify-center px-4">
            <form
              onSubmit={handleRegisterSubmit}
              className="bg-white rounded-lg shadow-lg p-6 max-w-sm w-full"
              onClick={(e) => e.stopPropagation()}
            >
              <h3 className="text-xl font-semibold mb-4 text-[#7A0C2E]">
                Register New User
              </h3>
              <input
                type="text"
                placeholder="Enter user ID"
                value={newUserId}
                onChange={(e) => setNewUserId(e.target.value)}
                required
                autoFocus
                className="w-full border border-gray-300 rounded-md px-3 py-2 mb-4
                  focus:outline-none focus:ring-2 focus:ring-[#7A0C2E] focus:border-[#7A0C2E] transition"
              />
              <div className="flex justify-end gap-3">
                <button
                  type="button"
                  onClick={closeRegister}
                  className="cursor-pointer transition duration-300 px-4 py-2 rounded-md border border-gray-300 text-gray-700 hover:bg-gray-100"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={loading}
                  className="cursor-pointer transition duration-300 px-4 py-2 rounded-md bg-[#7A0C2E] text-white hover:bg-[#8B1036] disabled:opacity-60"
                >
                  {loading ? "Registering..." : "Register"}
                </button>
              </div>
            </form>
          </div>
        </>
      )}
    </header>
  );
}
