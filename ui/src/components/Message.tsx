import { Message as MessageType } from "../models/message";

interface Props {
  message: MessageType;
}

export default function Message({ message }: Props) {
  const isUser = message.sender === "user";

  return (
    <div
      className={`max-w-[70%] p-3 my-1 rounded-lg break-words ${
        isUser ? "bg-[#800000] text-white self-end" : "bg-gray-200 text-black self-start"
      }`}
    >
      {message.text}
    </div>
  );
}
