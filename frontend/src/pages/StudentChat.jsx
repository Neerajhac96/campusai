import { useEffect, useMemo, useState } from "react";
import { getChatHistory, sendQuery } from "../api/client";
import ChatWindow from "../components/ChatWindow";
import { useAuth } from "../context/AuthContext";

const QUICK_SUGGESTIONS = [
  "Fees ki last date kya hai?",
  "Attendance minimum kitna chahiye?",
  "Scholarship ke liye kaise apply karein?",
  "Hall ticket kab milega?",
  "What is the exam schedule?",
  "How to apply for hostel?",
];

const StudentChat = () => {
  const { user, logout } = useAuth();
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [historyLoaded, setHistoryLoaded] = useState(false);
  const [showSuggestions, setShowSuggestions] = useState(true);

  const collegeName = useMemo(() => user?.college_name || "Your College", [user]);

  useEffect(() => {
    const loadHistory = async () => {
      try {
        const history = await getChatHistory(1, 20);
        const reconstructed = [];
        [...(history.items || [])].reverse().forEach((entry) => {
          reconstructed.push({
            id: `${entry.id}_q`,
            role: "user",
            text: entry.query_text,
          });
          reconstructed.push({
            id: `${entry.id}_a`,
            role: "bot",
            text: entry.response_text,
            sources: entry.sources,
            escalate: entry.escalated,
            language: entry.language,
            confidence: entry.confidence,
          });
        });
        setMessages(reconstructed);
        setShowSuggestions(reconstructed.length === 0);
      } catch (error) {
        window.alert(error.message);
      } finally {
        setHistoryLoaded(true);
      }
    };
    loadHistory();
  }, []);

  const submitQuery = async (text) => {
    const trimmed = text.trim();
    if (!trimmed || loading) {
      return;
    }
    const userMessage = {
      id: crypto.randomUUID(),
      role: "user",
      text: trimmed,
    };
    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setLoading(true);
    setShowSuggestions(false);

    try {
      const result = await sendQuery(trimmed);
      const botMessage = {
        id: crypto.randomUUID(),
        role: "bot",
        text: result.answer,
        sources: result.sources || [],
        escalate: result.escalate,
        language: result.language,
        confidence: result.confidence,
      };
      setMessages((prev) => [...prev, botMessage]);
    } catch (error) {
      const fallback = {
        id: crypto.randomUUID(),
        role: "bot",
        text: `Sorry, something went wrong: ${error.message}`,
        sources: [],
        escalate: true,
        language: "english",
        confidence: "uncertain",
      };
      setMessages((prev) => [...prev, fallback]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = async (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      await submitQuery(input);
    }
  };

  return (
    <div className="flex h-screen flex-col bg-wa-bg">
      <header className="bg-wa-dark px-4 py-3 text-white shadow">
        <div className="mx-auto flex w-full max-w-4xl items-center justify-between">
          <div>
            <p className="text-lg font-bold">CampusAI</p>
            <p className="text-xs text-emerald-100">{collegeName}</p>
          </div>
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-1 text-xs text-emerald-200">
              <span className="h-2 w-2 rounded-full bg-wa-green" />
              online
            </div>
            <button
              type="button"
              onClick={logout}
              className="rounded-md border border-emerald-100/40 px-3 py-1.5 text-xs font-semibold"
            >
              Logout
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto flex w-full max-w-4xl flex-1 flex-col overflow-hidden">
        <section className="flex-1 overflow-hidden">
          {!historyLoaded ? (
            <div className="flex h-full items-center justify-center text-sm text-gray-500">Loading chat...</div>
          ) : (
            <ChatWindow messages={messages} loading={loading} />
          )}
        </section>

        {showSuggestions && (
          <div className="border-t border-gray-200 bg-white px-3 py-2 sm:px-6">
            <p className="mb-2 text-xs font-medium text-gray-500">Quick questions</p>
            <div className="flex flex-wrap gap-2">
              {QUICK_SUGGESTIONS.map((suggestion) => (
                <button
                  key={suggestion}
                  type="button"
                  onClick={() => submitQuery(suggestion)}
                  className="rounded-full border border-gray-200 bg-gray-50 px-3 py-1.5 text-xs text-gray-700 hover:bg-gray-100"
                >
                  {suggestion}
                </button>
              ))}
            </div>
          </div>
        )}

        <footer className="border-t border-gray-200 bg-white px-3 py-3 sm:px-6">
          <div className="flex items-end gap-2">
            <textarea
              value={input}
              onChange={(event) => setInput(event.target.value)}
              onKeyDown={handleKeyDown}
              rows={2}
              placeholder="Ask anything about fees, attendance, exams, hostel..."
              className="max-h-40 min-h-[52px] flex-1 resize-y rounded-xl border border-gray-300 px-3 py-2 text-sm focus:border-wa-dark focus:outline-none"
            />
            <button
              type="button"
              disabled={loading || !input.trim()}
              onClick={() => submitQuery(input)}
              className="h-[52px] rounded-xl bg-wa-green px-5 text-sm font-semibold text-white disabled:opacity-60"
            >
              Send
            </button>
          </div>
          <p className="mt-1 text-[11px] text-gray-500">Enter to send, Shift+Enter for new line</p>
        </footer>
      </main>
    </div>
  );
};

export default StudentChat;
