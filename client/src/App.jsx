import React, { useState, useEffect, useRef } from 'react';
import {
  MessageSquare,
  Send,
  AlertTriangle,
  ShieldAlert,
  UserCheck,
  RefreshCw,
  Layers,
  Sparkles,
  CheckCircle,
  Clock,
  Trash2,
  Package,
  TrendingUp
} from 'lucide-react';

// Custom session ID helper
const getOrGenerateSession = () => {
  let sessionId = localStorage.getItem('pg_session_id');
  if (!sessionId) {
    sessionId = 'session_' + Math.random().toString(36).substring(2, 15);
    localStorage.setItem('pg_session_id', sessionId);
  }
  return sessionId;
};

function App() {
  const [activeTab, setActiveTab] = useState('chat'); // 'chat' | 'dashboard'
  const [sessionId, setSessionId] = useState('');
  const [messages, setMessages] = useState([]);
  const [inputText, setInputText] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [progressSteps, setProgressSteps] = useState([]);
  const [activeAgent, setActiveAgent] = useState(null);
  const [isEscalated, setIsEscalated] = useState(false);
  const [tickets, setTickets] = useState([]);
  const [dashboardLoading, setDashboardLoading] = useState(false);

  const messagesEndRef = useRef(null);

  // Initialize Session & History
  useEffect(() => {
    const sId = getOrGenerateSession();
    setSessionId(sId);
    loadChatHistory(sId);
  }, []);

  // Scroll to bottom on message updates
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, progressSteps]);

  // Load chat history from SQLite
  const loadChatHistory = async (sId) => {
    try {
      const res = await fetch('/api/history', {
        headers: { 'X-Session-ID': sId }
      });
      if (res.ok) {
        const data = await res.json();
        setMessages(data.history || []);

        // Infer escalation status from history messages
        const hasEscalated = data.history.some(msg =>
          msg.role === 'assistant' &&
          (msg.content.includes('human support representative') ||
            msg.content.includes('human follow-up'))
        );
        setIsEscalated(hasEscalated);
      }
    } catch (err) {
      console.error("Failed to load chat history:", err);
    }
  };

  // Load tickets for admin dashboard
  const fetchTickets = async () => {
    setDashboardLoading(true);
    try {
      const res = await fetch('/api/tickets');
      if (res.ok) {
        const data = await res.json();
        setTickets(data.tickets || []);
      }
    } catch (err) {
      console.error("Failed to fetch tickets:", err);
    } finally {
      setDashboardLoading(false);
    }
  };

  useEffect(() => {
    if (activeTab === 'dashboard') {
      fetchTickets();
    }
  }, [activeTab]);

  // Clear Session & Start Fresh
  const handleResetSession = () => {
    const newId = 'session_' + Math.random().toString(36).substring(2, 15);
    localStorage.setItem('pg_session_id', newId);
    setSessionId(newId);
    setMessages([]);
    setProgressSteps([]);
    setActiveAgent(null);
    setIsEscalated(false);
  };

  // Clear entire DB (demotesting helper)
  const handleClearDatabase = async () => {
    if (window.confirm("Are you sure you want to delete all messages and tickets in the database?")) {
      try {
        const res = await fetch('/api/tickets/clear', { method: 'POST' });
        if (res.ok) {
          handleResetSession();
          if (activeTab === 'dashboard') {
            fetchTickets();
          }
          alert("Database wiped successfully!");
        }
      } catch (err) {
        alert("Wipe failed: " + err.message);
      }
    }
  };

  // Send message using SSE Stream reader
  const handleSendMessage = async (textToSend) => {
    const msg = textToSend || inputText;
    if (!msg.trim() || isLoading) return;

    setInputText('');
    setIsLoading(true);
    setProgressSteps([]);
    setActiveAgent(null);

    // Append user message locally
    const updatedMessages = [...messages, { role: 'user', content: msg }];
    setMessages(updatedMessages);

    // Placeholder for streaming reply
    const assistantMessageIndex = updatedMessages.length;
    setMessages(prev => [...prev, { role: 'assistant', content: '' }]);

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Session-ID': sessionId
        },
        body: JSON.stringify({ message: msg })
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      // Stream Reader Setup
      const reader = response.body.getReader();
      const decoder = new TextDecoder("utf-8");
      let buffer = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop(); // Hold incomplete line in buffer

        for (const line of lines) {
          if (line.trim()) {
            try {
              const event = JSON.parse(line);

              if (event.type === 'progress') {
                setProgressSteps(prev => {
                  // Avoid duplicates
                  if (prev.some(p => p.message === event.message)) return prev;
                  return [...prev, event];
                });
                setActiveAgent(event.agent);
              }
              else if (event.type === 'chunk') {
                setMessages(prev => {
                  // Build a brand-new message object instead of mutating the
                  // existing one in place. React 18 StrictMode intentionally
                  // calls this updater function twice in development to catch
                  // exactly this class of bug: if we mutated the shared object,
                  // the second call would see the first call's mutation already
                  // applied and append the chunk again on top of it, doubling
                  // every word. Returning a fresh object each time means both
                  // calls independently compute the same correct result from
                  // the same untouched `prev`, so the double-invoke is harmless.
                  const updatedContent = prev[assistantMessageIndex].content + event.text;

                  // Check if this text escalates
                  if (updatedContent.includes('human support representative') ||
                    updatedContent.includes('human follow-up')) {
                    setIsEscalated(true);
                  }

                  return prev.map((m, idx) =>
                    idx === assistantMessageIndex ? { ...m, content: updatedContent } : m
                  );
                });
              }
            } catch (err) {
              console.warn("Could not parse line chunk:", line, err);
            }
          }
        }
      }
    } catch (err) {
      console.error("Error streaming chat:", err);
      setMessages(prev =>
        prev.map((m, idx) =>
          idx === assistantMessageIndex
            ? { ...m, content: "I'm sorry, I encountered a communication error with our support system. Please try again." }
            : m
        )
      );
    } finally {
      setIsLoading(false);
      setActiveAgent(null);
    }
  };

  const samplePrompts = [
    { title: "Grounded Query", text: "What are the ingredients in Tide Hygienic Clean?", badge: "Product Fact" },
    { title: "Product Recommendation", text: "I have sensitive skin. Which moisturizer should I use?", badge: "skincare" },
    { title: "Serious Safety Exposure", text: "Help, my baby swallowed some detergent!", badge: "CRITICAL Safety" },
    { title: "Angry Customer Suit", text: "This razor is garbage! I will sue your company!", badge: "Escalation" }
  ];

  return (
    <div className="flex flex-col min-h-screen">
      {/* Premium Header */}
      <header className="glass-panel border-b border-white/5 px-6 py-4 flex items-center justify-between sticky top-0 z-50 rounded-none bg-slate-900/80">
        <div className="flex items-center gap-3">
          <div className="bg-gradient-to-r from-blue-600 to-cyan-500 p-2.5 rounded-xl shadow-lg shadow-blue-500/20">
            <Layers className="h-6 w-6 text-white" />
          </div>
          <div>
            <h1 className="text-xl font-bold bg-gradient-to-r from-white via-slate-200 to-slate-400 bg-clip-text text-transparent">
              P&G Multi-Agent Assistant
            </h1>
            <p className="text-xs text-var-text-muted text-gray-400 font-medium">Customer Support System</p>
          </div>
        </div>

        <div className="flex items-center gap-4">
          {/* Navigation Tabs */}
          <div className="flex bg-slate-950/60 p-1.5 rounded-xl border border-white/5">
            <button
              onClick={() => setActiveTab('chat')}
              className={`px-4 py-2 rounded-lg font-medium text-sm transition-all duration-200 flex items-center gap-2 ${activeTab === 'chat'
                  ? 'bg-blue-600 text-white shadow-md'
                  : 'text-gray-400 hover:text-white'
                }`}
            >
              <MessageSquare className="h-4 w-4" />
              Chat Assistant
            </button>
            <button
              onClick={() => setActiveTab('dashboard')}
              className={`px-4 py-2 rounded-lg font-medium text-sm transition-all duration-200 flex items-center gap-2 ${activeTab === 'dashboard'
                  ? 'bg-blue-600 text-white shadow-md'
                  : 'text-gray-400 hover:text-white'
                }`}
            >
              <AlertTriangle className="h-4 w-4" />
              Support Dashboard
            </button>
          </div>

          {/* Wipe DB Helper */}
          <button
            onClick={handleClearDatabase}
            title="Reset DB"
            className="p-2.5 rounded-xl border border-red-500/20 text-red-400 hover:bg-red-500/10 transition-all duration-200 flex items-center justify-center"
          >
            <Trash2 className="h-4 w-4" />
          </button>
        </div>
      </header>

      {/* Main Container */}
      <main className="flex-1 bg-slate-950 flex flex-col items-center justify-center p-4">
        {activeTab === 'chat' ? (
          <div className="chat-container w-full max-w-6xl flex gap-6">
            {/* Left Sidebar: Quick Prompts & Brand Catalog */}
            <div className="w-80 flex flex-col gap-6 max-h-[calc(100vh-140px)] overflow-y-auto hidden md:flex">
              {/* Session Control */}
              <div className="glass-panel p-5 flex flex-col gap-3">
                <h3 className="text-sm font-semibold text-gray-300 flex items-center justify-between">
                  Current Session
                  <button
                    onClick={handleResetSession}
                    className="p-1 rounded hover:bg-white/5 text-gray-400 hover:text-white transition-colors duration-200"
                    title="New Session"
                  >
                    <RefreshCw className="h-3.5 w-3.5" />
                  </button>
                </h3>
                <code className="text-xs text-cyan-400 bg-black/30 p-2.5 rounded-lg border border-white/5 select-all break-all">
                  {sessionId}
                </code>
              </div>

              {/* Sample Prompts */}
              <div className="glass-panel p-5 flex flex-col gap-4">
                <div>
                  <h3 className="text-sm font-semibold text-gray-300">Test Scenarios</h3>
                  <p className="text-xs text-gray-500 mt-1">Select a sample input to test agent reasoning</p>
                </div>
                <div className="flex flex-col gap-2">
                  {samplePrompts.map((p, idx) => (
                    <button
                      key={idx}
                      onClick={() => handleSendMessage(p.text)}
                      disabled={isLoading}
                      className="text-left p-3 rounded-xl border border-white/5 bg-slate-900/30 hover:bg-blue-600/10 hover:border-blue-500/30 transition-all duration-200 group disabled:opacity-50"
                    >
                      <div className="flex items-center justify-between gap-2">
                        <span className="text-[10px] uppercase font-bold text-blue-400 tracking-wider">{p.badge}</span>
                        <Sparkles className="h-3 w-3 text-gray-600 group-hover:text-blue-400 transition-colors" />
                      </div>
                      <p className="text-xs text-gray-300 mt-1.5 group-hover:text-white line-clamp-2">{p.text}</p>
                    </button>
                  ))}
                </div>
              </div>

              {/* Brand Catalog */}
              <div className="glass-panel p-5 flex flex-col gap-4">
                <h3 className="text-sm font-semibold text-gray-300 flex items-center gap-2">
                  <Package className="h-4 w-4 text-cyan-400" />
                  Knowledge Base Catalog
                </h3>
                <div className="flex flex-col gap-2.5">
                  {['Tide', 'Pampers', 'Olay', 'Gillette'].map((brand) => (
                    <div key={brand} className="p-3 bg-slate-900/40 border border-white/5 rounded-xl flex items-center justify-between">
                      <span className="text-xs font-semibold text-gray-300">{brand} Products</span>
                      <span className="text-[10px] bg-slate-950 px-2 py-0.5 rounded text-gray-500 border border-white/5">Verified</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Central Chat Interface */}
            <div className="flex-1 glass-panel flex flex-col overflow-hidden max-h-[calc(100vh-140px)] relative">
              {/* Escalated Status Header */}
              {isEscalated && (
                <div className="bg-red-500/10 border-b border-red-500/20 px-5 py-3 flex items-center gap-3 animate-pulse-slow">
                  <ShieldAlert className="h-5 w-5 text-red-500 shrink-0" />
                  <div className="flex-1">
                    <p className="text-xs font-semibold text-red-200">Conversation Escalated to Human Agent</p>
                    <p className="text-[10px] text-red-400">A support agent is reviewing this session logs for follow-up.</p>
                  </div>
                  <span className="text-[10px] font-bold bg-red-500 text-white px-2 py-0.5 rounded-full uppercase tracking-wider">Urgent</span>
                </div>
              )}

              {/* Messages Area */}
              <div className="flex-1 overflow-y-auto p-6 flex flex-col gap-6">
                {messages.length === 0 ? (
                  <div className="flex-1 flex flex-col items-center justify-center text-center max-w-md mx-auto my-12">
                    <div className="bg-gradient-to-br from-blue-600 to-cyan-500 p-4 rounded-full shadow-lg shadow-blue-500/20 mb-4">
                      <MessageSquare className="h-10 w-10 text-white" />
                    </div>
                    <h3 className="text-lg font-bold text-gray-100">Welcome to P&G Customer Support</h3>
                    <p className="text-xs text-gray-400 mt-2">
                      I can help you with product ingredients, safe usage guidelines, skincare recommendations, and laundry questions. If you report safety concerns, I will immediately flag this for human assistance.
                    </p>
                  </div>
                ) : (
                  messages.map((m, idx) => (
                    <div
                      key={idx}
                      className={`flex gap-3 max-w-[85%] ${m.role === 'user' ? 'self-end flex-row-reverse' : 'self-start'}`}
                    >
                      <div className={`h-9 w-9 rounded-xl flex items-center justify-center shrink-0 shadow ${m.role === 'user'
                          ? 'bg-blue-600 text-white'
                          : 'bg-slate-900 border border-white/10 text-cyan-400'
                        }`}>
                        {m.role === 'user' ? <UserCheck className="h-4 w-4" /> : <Layers className="h-4 w-4" />}
                      </div>

                      <div className="flex flex-col gap-1.5">
                        <div className={`p-4 rounded-2xl leading-relaxed text-sm ${m.role === 'user'
                            ? 'bg-blue-600 text-white rounded-tr-none'
                            : 'glass-panel rounded-tl-none bg-slate-900/60'
                          }`}>
                          {m.content || (isLoading && idx === messages.length - 1 ? (
                            <span className="flex items-center gap-1">
                              <span className="h-2 w-2 bg-blue-500 rounded-full animate-bounce"></span>
                              <span className="h-2 w-2 bg-blue-500 rounded-full animate-bounce [animation-delay:0.2s]"></span>
                              <span className="h-2 w-2 bg-blue-500 rounded-full animate-bounce [animation-delay:0.4s]"></span>
                            </span>
                          ) : '')}
                        </div>
                        <span className="text-[10px] text-gray-500 px-1">
                          {m.role === 'user' ? 'Customer' : 'AI Assistant'}
                        </span>
                      </div>
                    </div>
                  ))
                )}

                {/* Agent Thinking Progress (Only during active loading) */}
                {isLoading && progressSteps.length > 0 && (
                  <div className="self-start flex gap-3 max-w-[85%] animate-fade-in">
                    <div className="h-9 w-9 rounded-xl flex items-center justify-center bg-slate-900 border border-blue-500/30 text-blue-400 shrink-0">
                      <Layers className="h-4 w-4 animate-spin" />
                    </div>
                    <div className="flex flex-col gap-2">
                      <div className="p-4 rounded-2xl rounded-tl-none glass-panel border border-blue-500/20 bg-slate-900/40 w-full min-w-[280px]">
                        <h4 className="text-xs font-bold text-blue-400 mb-2 flex items-center gap-2">
                          Multi-Agent Scanning Pipeline
                        </h4>
                        <div className="flex flex-col gap-2">
                          {progressSteps.map((step, idx) => (
                            <div key={idx} className="flex items-start gap-2.5 text-xs text-gray-300">
                              <CheckCircle className="h-3.5 w-3.5 text-green-400 shrink-0 mt-0.5" />
                              <div className="flex-1">
                                <span className="font-bold text-gray-400">[{step.agent}]</span> {step.message}
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                <div ref={messagesEndRef} />
              </div>

              {/* Chat Input Field */}
              <div className="p-4 border-t border-white/5 bg-slate-950/80">
                <form
                  onSubmit={(e) => { e.preventDefault(); handleSendMessage(); }}
                  className="flex gap-2.5"
                >
                  <input
                    type="text"
                    value={inputText}
                    onChange={(e) => setInputText(e.target.value)}
                    placeholder="Describe your product question or safety concern..."
                    disabled={isLoading}
                    className="flex-1 bg-slate-900 border border-white/5 rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-blue-500/50 transition-colors disabled:opacity-50"
                  />
                  <button
                    type="submit"
                    disabled={isLoading || !inputText.trim()}
                    className="bg-blue-600 hover:bg-blue-500 text-white p-3.5 rounded-xl transition-colors disabled:opacity-50 flex items-center justify-center shrink-0 shadow-lg shadow-blue-500/10"
                  >
                    <Send className="h-4 w-4" />
                  </button>
                </form>
              </div>
            </div>
          </div>
        ) : (
          /* Support Ticket Dashboard (For testing handoff) */
          <div className="w-full max-w-6xl glass-panel p-6 flex flex-col gap-6 animate-fade-in min-h-[500px]">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-xl font-bold flex items-center gap-2 text-white">
                  <ShieldAlert className="h-5 w-5 text-red-500" />
                  Human Agent Support Dashboard
                </h2>
                <p className="text-xs text-gray-400 mt-1">
                  Step 6: Real-time logs of customer conversations escalated due to safety warnings or emotional tone checks.
                </p>
              </div>
              <button
                onClick={fetchTickets}
                disabled={dashboardLoading}
                className="flex items-center gap-2 text-xs font-semibold bg-slate-900 border border-white/5 hover:bg-white/5 px-3 py-2 rounded-xl transition-all duration-200"
              >
                <RefreshCw className={`h-3 w-3 ${dashboardLoading ? 'animate-spin' : ''}`} />
                Refresh
              </button>
            </div>

            {tickets.length === 0 ? (
              <div className="flex-1 flex flex-col items-center justify-center text-center p-12 bg-slate-900/20 border border-white/5 rounded-2xl">
                <CheckCircle className="h-10 w-10 text-green-500 mb-3" />
                <h3 className="text-sm font-bold text-gray-300">Queue is Clear</h3>
                <p className="text-xs text-gray-500 mt-1">No human support follow-ups or safety tickets currently pending.</p>
              </div>
            ) : (
              <div className="overflow-x-auto rounded-xl border border-white/5">
                <table className="w-full text-left border-collapse text-xs">
                  <thead>
                    <tr className="bg-slate-950/80 text-gray-400 border-b border-white/5">
                      <th className="p-4 font-bold">Ticket ID</th>
                      <th className="p-4 font-bold">Session ID</th>
                      <th className="p-4 font-bold">Flagged Reason</th>
                      <th className="p-4 font-bold">Tone</th>
                      <th className="p-4 font-bold">Urgency</th>
                      <th className="p-4 font-bold">Customer Message</th>
                      <th className="p-4 font-bold flex items-center gap-1"><Clock className="h-3.5 w-3.5" /> Logged At</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/5 bg-slate-900/10">
                    {tickets.map((t) => (
                      <tr key={t.ticket_id} className="hover:bg-white/5 transition-colors duration-150">
                        <td className="p-4 font-bold text-cyan-400">#00{t.ticket_id}</td>
                        <td className="p-4 text-gray-400 select-all font-mono break-all">{t.session_id}</td>
                        <td className="p-4">
                          <span className="font-medium text-gray-200">{t.reason}</span>
                        </td>
                        <td className="p-4">
                          <span className={`px-2 py-0.5 rounded text-[10px] uppercase font-bold tracking-wider ${t.tone === 'furious'
                              ? 'bg-red-500/20 text-red-300'
                              : t.tone === 'annoyed'
                                ? 'bg-amber-500/20 text-amber-300'
                                : 'bg-gray-500/20 text-gray-300'
                            }`}>
                            {t.tone}
                          </span>
                        </td>
                        <td className="p-4">
                          <span className={`px-2.5 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider ${t.urgency === 'high'
                              ? 'bg-red-500 text-white shadow-lg shadow-red-500/20'
                              : 'bg-amber-500 text-slate-950 font-bold'
                            }`}>
                            {t.urgency}
                          </span>
                        </td>
                        <td className="p-4 text-gray-300 max-w-[240px] truncate" title={t.user_message}>
                          {t.user_message}
                        </td>
                        <td className="p-4 text-gray-500">{t.timestamp}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}

export default App;