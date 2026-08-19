import DOMPurify from "dompurify";
import { marked } from "marked";
import { useMemo, useState } from "react";

marked.setOptions({
  breaks: true,
  gfm: true,
});

const MessageBubble = ({
  role,
  text,
  content,
  sources = [],
  escalate = false,
  language = "english",
  confidence = "high",
  isLastAssistant = false,
  onRegenerate,
}) => {
  const [copied, setCopied] = useState(false);
  const isUser = role === "user";
  const value = content ?? text ?? "";

  const safeHtml = useMemo(() => {
    if (isUser) {
      return "";
    }
    return DOMPurify.sanitize(marked.parse(value));
  }, [isUser, value]);

  const copyMessage = async () => {
    await navigator.clipboard.writeText(value);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1200);
  };

  return (
    <div className={`group mb-5 flex w-full ${isUser ? "justify-end" : "justify-start"}`}>
      <div className={`flex max-w-[92%] flex-col ${isUser ? "items-end" : "items-start"} md:max-w-[78%]`}>
        <div
          className={`rounded-2xl px-4 py-3 shadow-sm ${
            isUser
              ? "rounded-br-sm bg-wa-user text-gray-900 dark:bg-[#1f5f45] dark:text-white"
              : "rounded-bl-sm bg-white text-gray-900 dark:bg-[#242424] dark:text-gray-100"
          }`}
        >
          {isUser ? (
            <p className="whitespace-pre-wrap text-sm leading-relaxed">{value}</p>
          ) : (
            <div
              className="campusai-markdown text-sm leading-relaxed"
              dangerouslySetInnerHTML={{ __html: safeHtml }}
            />
          )}

          {!isUser && (
            <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-gray-600 dark:text-gray-300">
              <span className="rounded-full bg-gray-100 px-2 py-0.5 dark:bg-[#333]">
                {language === "hindi" ? "🇮🇳 Hindi" : "🇬🇧 English"}
              </span>
              {confidence !== "high" ? (
                <span className="rounded-full bg-amber-50 px-2 py-0.5 font-semibold text-amber-700">
                  {confidence}
                </span>
              ) : null}
            </div>
          )}

          {!isUser && sources?.length > 0 && (
            <div className="mt-3 flex flex-wrap gap-1.5">
              {sources.map((source) => (
                <button
                  key={source}
                  type="button"
                  className="rounded-full border border-gray-200 bg-gray-50 px-2.5 py-1 text-left text-[11px] text-gray-600 hover:bg-gray-100 dark:border-[#3a3a3a] dark:bg-[#1a1a1a] dark:text-gray-300"
                  title="Document preview coming soon"
                >
                  📄 {source}
                </button>
              ))}
            </div>
          )}

          {!isUser && escalate && (
            <div className="mt-2 rounded-md border border-orange-200 bg-orange-50 px-2.5 py-2 text-xs text-orange-700">
              Please verify this with Admin Office before taking action.
            </div>
          )}
        </div>

        {!isUser && (
          <div className="mt-1 flex gap-2 opacity-0 transition group-hover:opacity-100">
            <button
              type="button"
              onClick={copyMessage}
              className="rounded-md px-2 py-1 text-xs font-semibold text-gray-500 hover:bg-white hover:text-wa-dark dark:hover:bg-[#2a2a2a] dark:hover:text-white"
            >
              {copied ? "Copied" : "📋 Copy"}
            </button>
            {isLastAssistant ? (
              <button
                type="button"
                onClick={onRegenerate}
                className="rounded-md px-2 py-1 text-xs font-semibold text-gray-500 hover:bg-white hover:text-wa-dark dark:hover:bg-[#2a2a2a] dark:hover:text-white"
              >
                🔄 Regenerate
              </button>
            ) : null}
          </div>
        )}
      </div>
    </div>
  );
};

export default MessageBubble;
