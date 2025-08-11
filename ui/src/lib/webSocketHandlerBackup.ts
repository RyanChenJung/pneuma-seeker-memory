// lib/webSocketHandler.ts
let socket: WebSocket | null = null;

/** Connect to WebSocket backend */
export function connectWebSocket(
  url: string,
  onMessage: (msg: string) => void
) {
  socket = new WebSocket(url);

  socket.onopen = () => {
    console.log("WebSocket connected");
  };

  socket.onmessage = (event) => {
    onMessage(event.data);
  };

  socket.onclose = () => {
    console.log("WebSocket disconnected");
    socket = null;
  };

  socket.onerror = (err) => {
    console.error("WebSocket error:", err);
  };
}

/** Send a message through WebSocket */
export function sendPrompt(userId: string, chatId: string, prompt: string) {
  if (socket && socket.readyState === WebSocket.OPEN) {
    socket.send(JSON.stringify({ user_id: userId, chat_id: chatId, prompt }));
  } else {
    console.error("WebSocket is not connected");
  }
}

/** Close the WebSocket connection */
export function closeWebSocket() {
  if (socket) {
    socket.close();
    socket = null;
  }
}
