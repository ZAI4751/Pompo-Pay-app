"use client";

import { FormEvent, useState } from "react";
import { ArrowUp, Mic, Search, Sparkles, TrendingUp } from "lucide-react";
import { TransactionRow } from "./TransactionRow";
import type { ChatMessage, WalletTxn } from "@/lib/experience/data";
import { cn } from "@/lib/utils/cn";

const suggestions = [
  { id: "hist", label: "View Transaction History", icon: Search },
  { id: "analyze", label: "Analyze Money", icon: TrendingUp },
];

export function WalletAssistant({
  messages,
  txns,
  onSend,
  onSuggestion,
}: {
  messages: ChatMessage[];
  txns: WalletTxn[];
  onSend: (text: string) => void;
  onSuggestion: (id: string) => void;
}) {
  const [draft, setDraft] = useState("");

  function submit(event: FormEvent) {
    event.preventDefault();
    const text = draft.trim();
    if (!text) return;
    onSend(text);
    setDraft("");
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col px-4 pb-2 pt-3">
      <div className="mb-3 flex items-center gap-2 px-1">
        <Sparkles className="h-4 w-4 text-primary" />
        <h1 className="text-base font-semibold text-text">Assistant</h1>
      </div>
      <div className="flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto pr-1 scrollbar-thin">
        {messages.map((message) => {
          const txn = message.txnId ? txns.find((row) => row.id === message.txnId) : undefined;
          const mine = message.role === "user";
          return (
            <div key={message.id} className={cn("flex flex-col gap-2", mine ? "items-end" : "items-start")}>
              <div
                className={cn(
                  "max-w-[88%] rounded-3xl px-4 py-3 text-sm leading-relaxed",
                  mine
                    ? "rounded-br-md bg-white/55 text-text backdrop-blur dark:bg-slate-800/70"
                    : "rounded-bl-md bg-white text-text shadow-sm dark:bg-slate-900/80",
                )}
              >
                {message.body}
              </div>
              {txn ? (
                <div className="w-[88%] rounded-3xl bg-white p-2 shadow-sm dark:bg-slate-900/80">
                  <TransactionRow txn={txn} />
                </div>
              ) : null}
            </div>
          );
        })}
        <div className="flex gap-2 overflow-x-auto pb-1">
          {suggestions.map((item) => {
            const Icon = item.icon;
            return (
              <button
                key={item.id}
                type="button"
                onClick={() => onSuggestion(item.id)}
                className="inline-flex shrink-0 items-center gap-1.5 rounded-full bg-white px-3 py-2 text-xs font-semibold text-text shadow-sm transition hover:scale-105 dark:bg-slate-900"
              >
                <Icon className="h-3.5 w-3.5 text-primary" />
                {item.label}
              </button>
            );
          })}
        </div>
      </div>
      <form onSubmit={submit} className="mt-3 flex items-center gap-2 rounded-full bg-white px-3 py-2 shadow-sm dark:bg-slate-900">
        <Mic className="h-4 w-4 text-text-subtle" aria-hidden="true" />
        <input
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          placeholder="Ask Anything..."
          aria-label="Ask the assistant"
          className="min-w-0 flex-1 bg-transparent text-sm text-text outline-none placeholder:text-text-subtle"
        />
        <button
          type="submit"
          aria-label="Send message"
          className="flex h-8 w-8 items-center justify-center rounded-full bg-primary text-primary-foreground transition hover:scale-105"
        >
          <ArrowUp className="h-4 w-4" />
        </button>
      </form>
    </div>
  );
}
