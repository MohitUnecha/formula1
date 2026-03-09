'use client';

import { useState, useRef, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { MessageSquare, X, Send, Loader2, TrendingUp, ArrowUpRight } from 'lucide-react';

// ─── Types ────────────────────────────────────────────────────────────────────

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  suggest_predictions?: boolean;
  prediction_context?: string | null;
  timestamp: Date;
}

interface ChatResponse {
  reply: string;
  suggest_predictions: boolean;
  prediction_context: string | null;
}

// ─── Constants ────────────────────────────────────────────────────────────────

const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

function makeWelcome(): Message {
  return {
    id: 'welcome',
    role: 'assistant',
    content: "IT'S LIGHTS OUT! 🏁 I'm Crofty — your F1 expert. Ask me anything.",
    timestamp: new Date(),
  };
}

const CHIPS = [
  '2000 Australian GP winner?',
  '2025 World Champion?',
  'Who wins next race?',
  'Fastest lap records',
  'Tell me about Hamilton',
];

// ─── Component ────────────────────────────────────────────────────────────────

export function ChatbotPanel() {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>(() => [makeWelcome()]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [unread, setUnread] = useState(0);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  useEffect(() => {
    if (open) {
      setUnread(0);
      setTimeout(() => inputRef.current?.focus(), 120);
    }
  }, [open]);

  const sendMessage = useCallback(
    async (text: string) => {
      const trimmed = text.trim();
      if (!trimmed || loading) return;

      const userMsg: Message = {
        id: `u-${Date.now()}`,
        role: 'user',
        content: trimmed,
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, userMsg]);
      setInput('');
      setLoading(true);

      try {
        const history = messages
          .filter((m) => m.id !== 'welcome')
          .slice(-8)
          .map((m) => ({ role: m.role, content: m.content }));

        const res = await fetch(`${BACKEND_URL}/api/chat`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ message: trimmed, history }),
        });

        if (!res.ok) {
          throw new Error(`Server error ${res.status}`);
        }

        const data: ChatResponse = await res.json();

        const assistantMsg: Message = {
          id: `a-${Date.now()}`,
          role: 'assistant',
          content: data.reply,
          suggest_predictions: data.suggest_predictions,
          prediction_context: data.prediction_context,
          timestamp: new Date(),
        };

        setMessages((prev) => [...prev, assistantMsg]);
        if (!open) setUnread((u) => u + 1);
      } catch {
        setMessages((prev) => [
          ...prev,
          {
            id: `err-${Date.now()}`,
            role: 'assistant',
            content: "Radio check — comms down! 🛑 Try again in a moment.",
            timestamp: new Date(),
          },
        ]);
      } finally {
        setLoading(false);
      }
    },
    [loading, messages, open]
  );

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage(input);
    }
  };

  const fmt = (d: Date) =>
    d.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' });

  const showChips = messages.length === 1 && !loading;

  return (
    <>
      {/* ── Trigger button ── */}
      <button
        onClick={() => setOpen((v) => !v)}
        aria-label="Open Crofty"
        className="fixed bottom-6 right-6 z-50 rounded-2xl bg-[#E10600] hover:bg-[#c00500] shadow-[0_8px_32px_rgba(225,6,0,0.4)] transition-all duration-200 flex items-center justify-center group"
        style={{ width: 52, height: 52 }}
      >
        {open ? (
          <X size={18} className="text-white" />
        ) : (
          <MessageSquare size={18} className="text-white group-hover:scale-110 transition-transform duration-150" strokeWidth={2.5} />
        )}
        {!open && unread > 0 && (
          <span className="absolute -top-1 -right-1 w-4 h-4 bg-white text-[#E10600] text-[9px] font-black rounded-full flex items-center justify-center">
            {unread}
          </span>
        )}
      </button>

      {/* ── Panel ── */}
      <div
        className={`fixed bottom-[74px] right-6 z-50 flex flex-col rounded-2xl border border-white/[0.07] shadow-[0_24px_80px_rgba(0,0,0,0.7)] transition-all duration-200 origin-bottom-right overflow-hidden
          ${open ? 'opacity-100 scale-100 pointer-events-auto' : 'opacity-0 scale-[0.97] pointer-events-none'}`}
        style={{
          width: 360,
          maxWidth: 'calc(100vw - 1.5rem)',
          height: 520,
          background: 'linear-gradient(160deg, #0e1018 0%, #080a10 100%)',
        }}
      >
        {/* Header */}
        <div className="shrink-0 flex items-center justify-between px-5 pt-4 pb-3.5 border-b border-white/[0.05]">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-xl bg-[#E10600] flex items-center justify-center shadow-[0_4px_12px_rgba(225,6,0,0.35)]">
              <span className="text-white text-[13px] font-black tracking-tight leading-none">C</span>
            </div>
            <div>
              <p className="text-white text-[13px] font-bold tracking-wider leading-none mb-[3px]">CROFTY</p>
              <div className="flex items-center gap-1.5">
                <div className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                <p className="text-white/30 text-[10px] font-medium">Sky Sports F1 AI</p>
              </div>
            </div>
          </div>
          <button
            onClick={() => setOpen(false)}
            className="w-7 h-7 rounded-lg flex items-center justify-center text-white/25 hover:text-white/60 hover:bg-white/[0.05] transition-all"
          >
            <X size={14} />
          </button>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4" style={{ scrollbarWidth: 'none' }}>
          {messages.map((msg) => (
            <div key={msg.id} className={`flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'} gap-1`}>
              <div
                className={`max-w-[85%] px-3.5 py-2.5 rounded-2xl text-[13px] leading-[1.6] ${
                  msg.role === 'user'
                    ? 'bg-[#E10600] text-white rounded-tr-[5px]'
                    : 'bg-white/[0.06] text-white/80 rounded-tl-[5px] border border-white/[0.05]'
                }`}
              >
                {msg.content}
              </div>

              {msg.role === 'assistant' && msg.suggest_predictions && (
                <button
                  onClick={() => { router.push('/predictions'); setOpen(false); }}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-white/[0.04] hover:bg-[#E10600]/12 border border-white/[0.06] hover:border-[#E10600]/35 text-white/50 hover:text-white/85 text-[11px] font-medium transition-all duration-200"
                >
                  <TrendingUp size={11} strokeWidth={2.5} />
                  {msg.prediction_context ? `${msg.prediction_context} Predictions` : 'Open Predictions'}
                  <ArrowUpRight size={10} className="opacity-50" />
                </button>
              )}

              <span className="text-white/[0.18] text-[9px] px-0.5" suppressHydrationWarning>
                {fmt(msg.timestamp)}
              </span>
            </div>
          ))}

          {loading && (
            <div className="flex items-start">
              <div className="px-4 py-3 rounded-2xl rounded-tl-[5px] bg-white/[0.06] border border-white/[0.05]">
                <div className="flex items-center gap-1.5">
                  {[0, 150, 300].map((d) => (
                    <div
                      key={d}
                      className="w-1.5 h-1.5 rounded-full bg-[#E10600]/60 animate-bounce"
                      style={{ animationDelay: `${d}ms`, animationDuration: '1s' }}
                    />
                  ))}
                </div>
              </div>
            </div>
          )}

          <div ref={bottomRef} />
        </div>

        {/* Chips — horizontal scroll, no wrap */}
        {showChips && (
          <div
            className="shrink-0 px-4 pb-3 flex gap-2 overflow-x-auto"
            style={{ scrollbarWidth: 'none', WebkitOverflowScrolling: 'touch' } as React.CSSProperties}
          >
            {CHIPS.map((chip) => (
              <button
                key={chip}
                onClick={() => sendMessage(chip)}
                className="shrink-0 px-3 py-1.5 rounded-xl bg-white/[0.04] border border-white/[0.07] hover:border-[#E10600]/40 hover:bg-[#E10600]/08 text-white/45 hover:text-white/80 text-[11px] font-medium transition-all duration-150 whitespace-nowrap"
              >
                {chip}
              </button>
            ))}
          </div>
        )}

        {/* Input */}
        <div className="shrink-0 px-4 pb-4 pt-3 border-t border-white/[0.05]">
          <div className="flex items-end gap-2.5 bg-white/[0.04] rounded-xl border border-white/[0.07] focus-within:border-[#E10600]/35 transition-colors duration-200 px-3.5 py-2.5">
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => {
                setInput(e.target.value);
                e.target.style.height = 'auto';
                e.target.style.height = Math.min(e.target.scrollHeight, 80) + 'px';
              }}
              onKeyDown={handleKeyDown}
              placeholder="Ask Crofty anything…"
              rows={1}
              disabled={loading}
              className="flex-1 bg-transparent text-white/85 text-[13px] placeholder-white/[0.18] resize-none outline-none leading-relaxed"
              style={{ maxHeight: 80, scrollbarWidth: 'none', overflow: 'hidden' }}
            />
            <button
              onClick={() => sendMessage(input)}
              disabled={!input.trim() || loading}
              className="shrink-0 w-7 h-7 mb-0.5 rounded-lg flex items-center justify-center bg-[#E10600] disabled:bg-white/[0.05] text-white disabled:text-white/20 hover:bg-[#c00500] disabled:cursor-not-allowed transition-all duration-150 shadow-[0_2px_10px_rgba(225,6,0,0.25)] disabled:shadow-none"
            >
              {loading
                ? <Loader2 size={13} className="animate-spin" />
                : <Send size={13} strokeWidth={2.5} />
              }
            </button>
          </div>
        </div>
      </div>
    </>
  );
}
