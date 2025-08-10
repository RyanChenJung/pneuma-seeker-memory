import { MessageFormat } from "../models/message";

interface Props {
  message: MessageFormat;
}

export default function Message({ message }: Props) {
  const isUser = message.sender === "user";
  const isLog = message.sender === "log";

  return (
    <div
      className={`max-w-[70%] p-3 my-1 break-words ${
        isLog
          ? "font-mono text-sm italic text-gray-500 bg-gray-100 rounded-sm self-start"
          : isUser
          ? "bg-[#800000] text-white rounded-lg self-end"
          : "bg-gray-200 text-black rounded-lg self-start"
      }`}
    >
      {message.text}
    </div>
  );
}
