import { useEffect, useRef } from "react";
import MessageBubble from "./MessageBubble";

const TypingIndicator = () => (
  <div className="mb-3 flex justify-start">
    <div className="rounded-2xl rounded-bl-sm bg-white px-4 py-3 shadow-sm">
      <div className="flex items-center gap-1">
        <span className="h-2 w-2 animate-bounce rounded-full bg-gray-400 [animation-delay:-0.3s]" />
        <span className="h-2 w-2 animate-bounce rounded-full bg-gray-400 [animation-delay:-0.15s]" />
        <span className="h-2 w-2 animate-bounce rounded-full bg-gray-400" />
      </div>
    </div>
  </div>
);

const ChatWindow = ({ messages, loading }) => {
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  return (
    <div className="h-full overflow-y-auto px-3 py-4 sm:px-6">
      {messages.map((message) => (
        <MessageBubble
          key={message.id}
          role={message.role}
          text={message.text}
          sources={message.sources}
          escalate={message.escalate}
          language={message.language}
          confidence={message.confidence}
        />
      ))}
      {loading && <TypingIndicator />}
      <div ref={bottomRef} />
    </div>
  );
};

export default ChatWindow;
