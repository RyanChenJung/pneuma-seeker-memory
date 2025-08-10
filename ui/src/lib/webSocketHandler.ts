// frontend: lib/webSocketHandler.ts
import { useChatStore } from "@/stores/chatStore";

const BASE_URL = "localhost:8000";
const userId = "testing"; // fix or get from auth later

type SocketEntry = {
  socket: WebSocket;
  queue: string[];
};

const sockets: Record<string, SocketEntry> = {};

function connectSocket(chatId: string) {
  const socket = new WebSocket(`ws://${BASE_URL}/ws/${userId}/${chatId}`);

  sockets[chatId] = { socket, queue: [] };

  socket.onopen = () => {
    console.log(`Socket for chat ${chatId} connected`);
    // flush queue
    while (sockets[chatId].queue.length > 0) {
      const msg = sockets[chatId].queue.shift();
      if (msg) {
        socket.send(msg);
        console.log(`Sent queued message for ${chatId}:`, msg);
      }
    }
  };

  socket.onmessage = (event) => {
    const msg = event.data;
    if (msg.startsWith("LOG: ")) {
      useChatStore.getState().addMessage(chatId, { text: msg.slice(5), sender: "log" });
    } else {
      useChatStore.getState().addMessage(chatId, { text: msg, sender: "assistant" });
    }
  };

  socket.onclose = () => {
    console.log(`Socket for chat ${chatId} closed, reconnecting in 2s...`);
    setTimeout(() => connectSocket(chatId), 2000);
  };

  socket.onerror = (err) => {
    console.error(`Socket error for chat ${chatId}:`, err);
    socket.close();
  };
}

// Call once for the initial chat
connectSocket("chat-1");

export function sendPrompt(chatId: string, prompt: string) {
  const entry = sockets[chatId];
  if (!entry || entry.socket.readyState === WebSocket.CLOSED) {
    connectSocket(chatId);
    sockets[chatId].queue.push(prompt);
    return;
  }
  if (entry.socket.readyState === WebSocket.OPEN) {
    entry.socket.send(prompt);
  } else {
    entry.queue.push(prompt);
  }
}
