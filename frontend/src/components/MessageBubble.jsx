const MessageBubble = ({
  role,
  text,
  sources = [],
  escalate = false,
  language = "english",
  confidence = "high",
}) => {
  const isUser = role === "user";

  return (
    <div className={`flex w-full ${isUser ? "justify-end" : "justify-start"} mb-3`}>
      <div
        className={`max-w-[88%] rounded-2xl px-4 py-3 shadow-sm ${
          isUser ? "bg-wa-user text-gray-900 rounded-br-sm" : "bg-white text-gray-900 rounded-bl-sm"
        }`}
      >
        <p className="whitespace-pre-wrap text-sm leading-relaxed">{text}</p>

        {!isUser && (
          <div className="mt-2 flex items-center gap-2 text-xs text-gray-600">
            <span>{language === "hindi" ? "🇮🇳 Hindi" : "🇬🇧 English"}</span>
            <span className="rounded bg-gray-100 px-2 py-0.5">{confidence}</span>
          </div>
        )}

        {!isUser && sources?.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-1.5">
            {sources.map((source) => (
              <span
                key={source}
                className="rounded-full border border-gray-200 bg-gray-50 px-2.5 py-1 text-[11px] text-gray-600"
              >
                📄 {source}
              </span>
            ))}
          </div>
        )}

        {!isUser && escalate && (
          <div className="mt-2 rounded-md border border-orange-200 bg-orange-50 px-2.5 py-2 text-xs text-orange-700">
            ⚠️ Please verify this with Admin Office before taking action.
          </div>
        )}
      </div>
    </div>
  );
};

export default MessageBubble;
