"use client";

import { FormEvent, useState } from "react";
import { ArrowUp, Maximize2, Mic, Paperclip } from "lucide-react";

export function AssistantPanel() {
  const [draft, setDraft] = useState("");
  const [reply, setReply] = useState<string | null>(null);

  function submit(event: FormEvent) {
    event.preventDefault();
    const text = draft.trim();
    if (!text) return;
    setReply("Volume is up 24.4% versus last period. Airtel Money still carries most successful payments.");
    setDraft("");
  }

  return (
    <article className="flex h-full min-h-[260px] flex-col rounded-3xl bg-white/85 p-5 shadow-[0_12px_40px_-28px_rgb(15_23_42_/_0.45)] backdrop-blur dark:bg-slate-900/70">
      <div className="flex items-center justify-between">
        <p className="text-sm font-semibold text-text">AI Assistant</p>
        <Maximize2 className="h-4 w-4 text-text-subtle" />
      </div>
      <div className="flex flex-1 flex-col items-center justify-center py-4">
        <div className="pompo-orb h-24 w-24 rounded-full" aria-hidden="true" />
        {reply ? <p className="mt-4 max-w-xs text-center text-sm text-text-muted">{reply}</p> : null}
      </div>
      <form onSubmit={submit} className="flex items-center gap-2 rounded-full bg-surface-inset px-3 py-2">
        <Paperclip className="h-4 w-4 text-text-subtle" />
        <input
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          placeholder="Ask me anything..."
          aria-label="Ask the assistant"
          className="min-w-0 flex-1 bg-transparent text-sm outline-none placeholder:text-text-subtle"
        />
        <Mic className="h-4 w-4 text-text-subtle" />
        <button
          type="submit"
          aria-label="Send"
          className="flex h-8 w-8 items-center justify-center rounded-full bg-primary text-primary-foreground transition hover:scale-105"
        >
          <ArrowUp className="h-4 w-4" />
        </button>
      </form>
    </article>
  );
}
