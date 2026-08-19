import { useMemo, useState } from "react";

const groupConversation = (conversation) => {
  const updated = new Date(conversation.updated_at);
  const now = new Date();
  const startToday = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const startUpdated = new Date(updated.getFullYear(), updated.getMonth(), updated.getDate());
  const diffDays = Math.floor((startToday - startUpdated) / 86400000);

  if (diffDays === 0) return "Today";
  if (diffDays === 1) return "Yesterday";
  if (diffDays <= 7) return "Last 7 Days";
  if (diffDays <= 30) return "Last 30 Days";
  return "Older";
};

const groups = ["Today", "Yesterday", "Last 7 Days", "Last 30 Days", "Older"];

const ConversationList = ({
  conversations,
  activeId,
  onSelect,
  onDelete,
  onNewChat,
  loading = false,
}) => {
  const [search, setSearch] = useState("");

  const grouped = useMemo(() => {
    const query = search.trim().toLowerCase();
    const filtered = conversations.filter((conversation) =>
      (conversation.title || "New Chat").toLowerCase().includes(query)
    );
    return filtered.reduce((acc, conversation) => {
      const group = groupConversation(conversation);
      acc[group] = [...(acc[group] || []), conversation];
      return acc;
    }, {});
  }, [conversations, search]);

  return (
    <div className="flex h-full flex-col bg-[#f7f9f8] text-gray-900 dark:bg-[#111] dark:text-gray-100">
      <div className="flex items-center justify-between border-b border-black/5 px-4 py-3 dark:border-white/10">
        <div>
          <p className="text-lg font-bold text-wa-dark dark:text-white">CampusAI</p>
          <p className="text-[11px] text-gray-500 dark:text-gray-400">College assistant</p>
        </div>
        <button
          type="button"
          onClick={onNewChat}
          className="rounded-lg bg-wa-dark px-3 py-2 text-sm font-semibold text-white"
          title="New chat"
        >
          ✏️ New
        </button>
      </div>

      <div className="px-3 py-3">
        <input
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          placeholder="Search chats..."
          className="w-full rounded-xl border border-gray-200 bg-white px-3 py-2 text-sm outline-none focus:border-wa-dark dark:border-[#333] dark:bg-[#1c1c1c]"
        />
      </div>

      <div className="flex-1 overflow-y-auto px-2 pb-3">
        {loading ? (
          <div className="space-y-2 px-2">
            {[1, 2, 3, 4].map((item) => (
              <div key={item} className="h-12 animate-pulse rounded-xl bg-gray-200 dark:bg-[#222]" />
            ))}
          </div>
        ) : null}

        {!loading &&
          groups.map((group) => {
            const items = grouped[group] || [];
            if (items.length === 0) {
              return null;
            }
            return (
              <section key={group} className="mb-4">
                <p className="px-2 pb-1 text-[11px] font-semibold uppercase tracking-wide text-gray-500">
                  {group}
                </p>
                <div className="space-y-1">
                  {items.map((conversation) => (
                    <div
                      key={conversation.id}
                      className={`group flex items-center gap-2 rounded-xl px-3 py-2 text-sm ${
                        activeId === conversation.id
                          ? "bg-wa-dark text-white"
                          : "hover:bg-white dark:hover:bg-[#1f1f1f]"
                      }`}
                    >
                      <button
                        type="button"
                        onClick={() => onSelect(conversation.id)}
                        className="min-w-0 flex-1 text-left"
                      >
                        <p className="truncate font-semibold">{conversation.title || "New Chat"}</p>
                        <p
                          className={`truncate text-[11px] ${
                            activeId === conversation.id ? "text-white/70" : "text-gray-500"
                          }`}
                        >
                          {conversation.last_message || "No messages yet"}
                        </p>
                      </button>
                      <button
                        type="button"
                        onClick={() => onDelete(conversation.id)}
                        className={`rounded-md px-1.5 py-1 text-xs opacity-0 transition group-hover:opacity-100 ${
                          activeId === conversation.id ? "hover:bg-white/15" : "hover:bg-red-50"
                        }`}
                        title="Delete chat"
                      >
                        🗑️
                      </button>
                    </div>
                  ))}
                </div>
              </section>
            );
          })}

        {!loading && conversations.length === 0 ? (
          <p className="px-4 py-6 text-sm text-gray-500">No conversations yet. Start a new chat.</p>
        ) : null}
      </div>
    </div>
  );
};

export default ConversationList;
