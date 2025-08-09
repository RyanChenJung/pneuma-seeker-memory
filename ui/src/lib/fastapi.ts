// lib/fastapi.ts

const BASE_URL = "localhost:8000"; // Change to your FastAPI URL

// GET /state
export async function getState() {
    const res = await fetch(`http://${BASE_URL}/state`, {
        cache: 'no-store'  // This is equivalent to getServerSideProps behavior
    });
    if (!res.ok) throw new Error("Failed to fetch state");
    return res.json();
}

// POST /chat
export async function sendChat(message: string) {
    const res = await fetch(`http://${BASE_URL}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message }),
    });
    if (!res.ok) throw new Error("Failed to send chat");
    return res.json();
}

const socket = new WebSocket(`ws://${BASE_URL}/ws`);

export function sendPrompt(prompt: string) {
    socket.send(prompt)
}

socket.onmessage = (event) => {
    console.log("Received update:", event.data);
};

// Send message to backend
socket.send("Hello from client");
