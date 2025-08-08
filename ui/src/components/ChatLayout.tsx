import { useState } from "react";
import { Message as MessageType } from "../models/message";
import StatusPanel from "./StatusPanel";
import ChatArea from "./ChatArea";

export default function ChatLayout() {
    const [messages, setMessages] = useState<MessageType[]>([
        { text: "Hello! How can I help you today?", sender: "assistant" },
    ]);
    const [statusVisible, setStatusVisible] = useState(true);

    const addMessage = (text: string) => {
        setMessages((prev) => [...prev, { text, sender: "user" }]);
        setTimeout(() => {
            setMessages((prev) => [
                ...prev,
                { text: `You said: ${text}`, sender: "assistant" },
            ]);
        }, 1000);
    };

    const toggleStatus = () => setStatusVisible((v) => !v);

    return (
        <div
            className={`border border-gray-300 rounded-lg overflow-hidden shadow-lg h-screen transition-all duration-500 ease-in-out flex
    flex-col md:flex-row
  `}
        >
            <StatusPanel messages={messages} visible={statusVisible} onToggle={toggleStatus} />
            <ChatArea
                messages={messages}
                onSend={addMessage}
                statusVisible={statusVisible}
                onToggle={toggleStatus}
            />
        </div>
    );
}
