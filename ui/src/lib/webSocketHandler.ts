// lib/webSocketHandler.ts

let socket: WebSocket | null = null;
let isConnected = false;
const pendingMessages: string[] = [];

/**
 * Connect to WebSocket backend
 * @param url WebSocket URL including userId and chatId path params
 * @param onMessage Callback for incoming messages
 * @param onOpen Optional callback when connection opens
 */
function connectWebSocket(
  url: string,
  onMessage: (event: MessageEvent) => void,
  onOpen?: () => void
) {
  if (socket && isConnected) {
    // Already connected, just call onOpen if needed
    onOpen && onOpen();
    return;
  }

  socket = new WebSocket(url);

  socket.onopen = () => {
    console.log("WebSocket connected");
    isConnected = true;
    // Send any queued messages
    while (pendingMessages.length > 0) {
      const msg = pendingMessages.shift();
      if (msg) {
        socket!.send(msg);
        console.log("Sent queued message:", msg);
      }
    }
    if (onOpen) onOpen();
  };

  socket.onmessage = (event) => {
    onMessage(event);
  };

  socket.onclose = () => {
    console.log("WebSocket disconnected");
    isConnected = false;
    socket = null;
  };

  socket.onerror = (err) => {
    console.error("WebSocket error:", err);
  };
}

/**
 * Send a prompt message through the WebSocket
 * Will connect automatically if not connected yet
 *
 * @param userId User identifier (used for URL path)
 * @param chatId Chat identifier (used for URL path)
 * @param prompt The prompt message to send
 * @param onMessage Callback to handle incoming messages
 * @param baseUrl The WebSocket server base URL, e.g. 'localhost:8000'
 */
export function sendPrompt(
  userId: string,
  chatId: string,
  prompt: string,
  onMessage: (event: MessageEvent) => void,
  baseUrl = "localhost:8000"
) {
  const wsUrl = `ws://${baseUrl}/ws/${userId}/${chatId}`;
  const message = JSON.stringify({ user_id: userId, chat_id: chatId, prompt });

  if (socket && isConnected && socket.readyState === WebSocket.OPEN) {
    socket.send(message);
  } else {
    // Not connected or connecting
    pendingMessages.push(message);

    connectWebSocket(wsUrl, onMessage, () => {
      // Optionally do something when connection opens (already handled by flush)
    });
  }
}

/** Close the WebSocket connection */
export function closeWebSocket() {
  if (socket) {
    socket.close();
    socket = null;
    isConnected = false;
    pendingMessages.length = 0;
  }
}
