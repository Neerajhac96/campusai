import { useEffect, useMemo, useRef, useState } from "react";
import {
  deleteConversation,
  getConversation,
  getConversations,
  newConversation,
  sendQuery,
  updateConversationTitle,
} from "../api/client";
import ConversationList from "../components/ConversationList";
import MessageBubble from "../components/MessageBubble";
import { useAuth } from "../context/AuthContext";

const suggestions = [
  { title: "What are the attendance rules?", icon: "📚" },
  { title: "Fee structure and payment dates", icon: "💰" },
  { title: "Scholarship eligibility and process", icon: "🎓" },
  { title: "Hostel facilities and rules", icon: "🏠" },
];

const TypingIndicator = () => (
  <div className="mb-5 flex items-center gap-3 text-sm text-gray-500 dark:text-gray-300">
    <div className="flex gap-1 rounded-2xl bg-white px-4 py-3 shadow-sm dark:bg-[#242424]">
      {[0, 1, 2].map((item) => (
        <span
          key={item}
          className="h-2 w-2 animate-bounce rounded-full bg-wa-dark dark:bg-wa-green"
          style={{ animationDelay: `${item * 120}ms` }}
        />
      ))}
    </div>
    <span>CampusAI is thinking...</span>
  </div>
);

const StudentChat = () => {
  const { user, logout } = useAuth();
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);
  const [conversations, setConversations] = useState([]);
  const [activeConversationId, setActiveConversationId] = useState(null);
  const [activeConversation, setActiveConversation] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loadingConversations, setLoadingConversations] = useState(true);
  const [loadingMessages, setLoadingMessages] = useState(false);
  const [sending, setSending] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [error, setError] = useState("");
  const [editingTitle, setEditingTitle] = useState(false);
  const [titleDraft, setTitleDraft] = useState("");
  const [darkMode, setDarkMode] = useState(() => localStorage.getItem("campusai_dark_mode") === "true");

  const collegeName = useMemo(() => user?.college_name || "Your College", [user]);
  const userName = useMemo(() => user?.name || "CampusAI User", [user]);
  const activeTitle = activeConversation?.title || "New Chat";

  useEffect(() => {
    document.documentElement.classList.toggle("dark", darkMode);
    localStorage.setItem("campusai_dark_mode", String(darkMode));
  }, [darkMode]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, sending]);

  useEffect(() => {
    if (!inputRef.current) {
      return;
    }
    inputRef.current.style.height = "auto";
    inputRef.current.style.height = `${Math.min(inputRef.current.scrollHeight, 200)}px`;
  }, [input]);

  const loadConversations = async (selectId = activeConversationId) => {
    setError("");
    setLoadingConversations(true);
    try {
      const data = await getConversations();
      setConversations(data || []);
      const nextId = selectId || data?.[0]?.id || null;
      if (nextId) {
        await loadConversation(nextId);
      } else {
        setActiveConversationId(null);
        setActiveConversation(null);
        setMessages([]);
      }
    } catch (err) {
      setError(err.message || "Unable to load conversations");
    } finally {
      setLoadingConversations(false);
    }
  };

  const loadConversation = async (conversationId) => {
    setLoadingMessages(true);
    setError("");
    try {
      const data = await getConversation(conversationId);
      setActiveConversationId(data.id);
      setActiveConversation(data);
      setTitleDraft(data.title || "New Chat");
      setMessages(data.messages || []);
      setSidebarOpen(false);
    } catch (err) {
      setError(err.message || "Unable to open conversation");
    } finally {
      setLoadingMessages(false);
    }
  };

  useEffect(() => {
    loadConversations(null);
  }, []);

  const handleNewChat = async () => {
    setError("");
    try {
      const conversation = await newConversation();
      setConversations((current) => [conversation, ...current]);
      setActiveConversationId(conversation.id);
      setActiveConversation({ ...conversation, messages: [] });
      setMessages([]);
      setTitleDraft(conversation.title || "New Chat");
      setSidebarOpen(false);
    } catch (err) {
      setError(err.message || "Unable to create a new chat");
    }
  };

  const handleDeleteConversation = async (conversationId) => {
    if (!window.confirm("Delete this chat?")) {
      return;
    }
    try {
      await deleteConversation(conversationId);
      const remaining = conversations.filter((item) => item.id !== conversationId);
      setConversations(remaining);
      if (activeConversationId === conversationId) {
        if (remaining[0]) {
          await loadConversation(remaining[0].id);
        } else {
          setActiveConversationId(null);
          setActiveConversation(null);
          setMessages([]);
        }
      }
    } catch (err) {
      setError(err.message || "Unable to delete chat");
    }
  };

  const saveTitle = async () => {
    const title = titleDraft.trim();
    if (!activeConversationId || !title || title === activeTitle) {
      setEditingTitle(false);
      return;
    }
    try {
      const updated = await updateConversationTitle(activeConversationId, title);
      setActiveConversation((current) => ({ ...current, title: updated.title }));
      setConversations((current) =>
        current.map((item) => (item.id === updated.id ? { ...item, title: updated.title } : item))
      );
    } catch (err) {
      window.alert(err.message);
      setTitleDraft(activeTitle);
    } finally {
      setEditingTitle(false);
    }
  };

  const submitQuery = async (rawText) => {
    const query = rawText.trim();
    if (!query || sending || query.length > 500) {
      return;
    }

    const tempUserMessage = {
      id: crypto.randomUUID(),
      conversation_id: activeConversationId || "pending",
      role: "user",
      content: query,
      sources: [],
      language: "english",
      confidence: "high",
      escalated: false,
      response_time_ms: 0,
      created_at: new Date().toISOString(),
    };

    setMessages((current) => [...current, tempUserMessage]);
    setInput("");
    setSending(true);
    setError("");

    try {
      const result = await sendQuery(query, activeConversationId);
      const assistantMessage = {
        id: result.message_id,
        conversation_id: result.conversation_id,
        role: "assistant",
        content: result.answer,
        sources: result.sources || [],
        language: result.language,
        confidence: result.confidence,
        escalated: result.escalate,
        response_time_ms: result.response_time_ms,
        created_at: new Date().toISOString(),
      };
      setActiveConversationId(result.conversation_id);
      setActiveConversation((current) => ({
        ...(current || {}),
        id: result.conversation_id,
        title: result.conversation_title || current?.title || "New Chat",
      }));
      setTitleDraft(result.conversation_title || "New Chat");
      setMessages((current) => [...current, assistantMessage]);
      await loadConversations(result.conversation_id);
    } catch (err) {
      setMessages((current) => [
        ...current,
        {
          id: crypto.randomUUID(),
          conversation_id: activeConversationId || "error",
          role: "assistant",
          content: `Sorry, something went wrong: ${err.message}`,
          sources: [],
          language: "english",
          confidence: "uncertain",
          escalated: true,
          response_time_ms: 0,
          created_at: new Date().toISOString(),
        },
      ]);
    } finally {
      setSending(false);
    }
  };

  const regenerateLast = () => {
    const lastUser = [...messages].reverse().find((message) => message.role === "user");
    if (lastUser) {
      submitQuery(lastUser.content);
    }
  };

  const handleKeyDown = (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      submitQuery(input);
    }
  };

  const isEmpty = messages.length === 0 && !loadingMessages;
  const lastAssistantId = [...messages].reverse().find((message) => message.role === "assistant")?.id;

  return (
    <div className="flex h-screen overflow-hidden bg-wa-bg text-gray-900 dark:bg-[#1a1a1a] dark:text-gray-100">
      <aside className="hidden h-full w-[260px] shrink-0 flex-col border-r border-black/5 md:flex dark:border-white/10">
        <div className="min-h-0 flex-1">
          <ConversationList
            conversations={conversations}
            activeId={activeConversationId}
            onSelect={loadConversation}
            onDelete={handleDeleteConversation}
            onNewChat={handleNewChat}
            loading={loadingConversations}
          />
        </div>
        <div className="border-t border-black/5 bg-[#f7f9f8] p-4 dark:border-white/10 dark:bg-[#111]">
          <p className="truncate text-sm font-semibold">{userName}</p>
          <p className="truncate text-xs text-gray-500 dark:text-gray-400">{collegeName}</p>
          <button
            type="button"
            onClick={() => logout({ replace: true })}
            className="mt-3 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm font-semibold hover:bg-white dark:border-[#333] dark:hover:bg-[#1f1f1f]"
          >
            Logout
          </button>
        </div>
      </aside>

      {sidebarOpen ? (
        <div className="fixed inset-0 z-40 md:hidden">
          <button
            type="button"
            aria-label="Close sidebar"
            className="absolute inset-0 bg-black/40"
            onClick={() => setSidebarOpen(false)}
          />
          <div className="relative h-full w-[82vw] max-w-[320px]">
            <ConversationList
              conversations={conversations}
              activeId={activeConversationId}
              onSelect={loadConversation}
              onDelete={handleDeleteConversation}
              onNewChat={handleNewChat}
              loading={loadingConversations}
            />
          </div>
        </div>
      ) : null}

      <main className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center justify-between border-b border-black/5 bg-white px-4 py-3 shadow-sm dark:border-white/10 dark:bg-[#202020]">
          <div className="flex min-w-0 items-center gap-3">
            <button
              type="button"
              onClick={() => setSidebarOpen(true)}
              className="rounded-lg border border-gray-200 px-2 py-1.5 text-lg md:hidden dark:border-[#333]"
              aria-label="Open sidebar"
            >
              ☰
            </button>
            <div className="min-w-0">
              {editingTitle ? (
                <input
                  value={titleDraft}
                  onChange={(event) => setTitleDraft(event.target.value)}
                  onBlur={saveTitle}
                  onKeyDown={(event) => {
                    if (event.key === "Enter") saveTitle();
                    if (event.key === "Escape") setEditingTitle(false);
                  }}
                  className="w-full rounded-md border border-gray-300 px-2 py-1 text-lg font-bold outline-none focus:border-wa-dark dark:border-[#333] dark:bg-[#111]"
                  autoFocus
                />
              ) : (
                <button
                  type="button"
                  onClick={() => activeConversationId && setEditingTitle(true)}
                  className="max-w-[58vw] truncate text-left text-lg font-bold text-wa-dark dark:text-white"
                  title="Click to rename"
                >
                  {activeTitle}
                </button>
              )}
              <p className="text-xs text-gray-500 dark:text-gray-400">{collegeName}</p>
            </div>
          </div>
          <button
            type="button"
            onClick={() => setDarkMode((current) => !current)}
            className="rounded-lg border border-gray-200 px-3 py-2 text-sm font-semibold dark:border-[#333]"
          >
            {darkMode ? "☀️" : "🌙"}
          </button>
        </header>

        {error ? (
          <div className="mx-4 mt-4 rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700">
            <p>{error}</p>
            <button type="button" onClick={() => loadConversations(activeConversationId)} className="mt-2 font-semibold">
              Retry
            </button>
          </div>
        ) : null}

        <section className="flex-1 overflow-y-auto px-4 py-6">
          <div className="mx-auto flex min-h-full w-full max-w-3xl flex-col">
            {loadingMessages ? (
              <div className="flex flex-1 items-center justify-center text-sm text-gray-500">Loading messages...</div>
            ) : null}

            {isEmpty ? (
              <div className="flex flex-1 flex-col items-center justify-center text-center">
                <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-wa-dark text-2xl font-bold text-white">
                  CA
                </div>
                <h1 className="text-2xl font-bold text-wa-dark dark:text-white">What would you like to know?</h1>
                <p className="mt-2 max-w-md text-sm text-gray-500 dark:text-gray-400">
                  Ask about fees, attendance, exams, hostel, scholarships, placements, or notices.
                </p>
                <div className="mt-6 grid w-full max-w-2xl gap-3 sm:grid-cols-2">
                  {suggestions.map((suggestion) => (
                    <button
                      key={suggestion.title}
                      type="button"
                      onClick={() => submitQuery(suggestion.title)}
                      className="rounded-2xl border border-gray-200 bg-white p-4 text-left shadow-sm transition hover:-translate-y-0.5 hover:border-wa-dark dark:border-[#333] dark:bg-[#242424]"
                    >
                      <span className="text-2xl">{suggestion.icon}</span>
                      <p className="mt-2 text-sm font-semibold">{suggestion.title}</p>
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              <div>
                {messages.map((message) => (
                  <MessageBubble
                    key={message.id}
                    role={message.role}
                    content={message.content}
                    sources={message.sources}
                    language={message.language}
                    confidence={message.confidence}
                    escalate={message.escalated}
                    isLastAssistant={message.id === lastAssistantId}
                    onRegenerate={regenerateLast}
                  />
                ))}
                {sending ? <TypingIndicator /> : null}
                <div ref={messagesEndRef} />
              </div>
            )}
          </div>
        </section>

        <footer className="border-t border-black/5 bg-white px-4 py-3 dark:border-white/10 dark:bg-[#202020]">
          <div className="mx-auto max-w-3xl">
            <div className="flex items-end gap-2 rounded-2xl border border-gray-200 bg-gray-50 p-2 focus-within:border-wa-dark dark:border-[#333] dark:bg-[#151515]">
              <textarea
                ref={inputRef}
                value={input}
                maxLength={500}
                onChange={(event) => setInput(event.target.value)}
                onKeyDown={handleKeyDown}
                rows={1}
                placeholder="Message CampusAI..."
                className="max-h-[200px] min-h-[44px] flex-1 resize-none bg-transparent px-2 py-2 text-sm outline-none"
              />
              <button
                type="button"
                disabled={sending || !input.trim()}
                onClick={() => submitQuery(input)}
                className="flex h-10 w-10 items-center justify-center rounded-xl bg-wa-dark text-lg font-bold text-white disabled:opacity-40"
                aria-label="Send message"
              >
                ↑
              </button>
            </div>
            <div className="mt-1 flex items-center justify-between text-[11px] text-gray-500 dark:text-gray-400">
              <span>CampusAI may make mistakes. Verify important info.</span>
              <span>{input.length}/500</span>
            </div>
          </div>
        </footer>
      </main>
    </div>
  );
};

export default StudentChat;
