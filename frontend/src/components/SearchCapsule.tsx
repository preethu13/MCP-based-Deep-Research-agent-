"use client";

import { useState } from "react";
import { ArrowRight, Mic, Sparkles } from "lucide-react";

interface SearchCapsuleProps {
  initialQuery?: string;
  onSearch: (query: string, format: string, style: string, demo: boolean) => void;
  isLoading?: boolean;
  placeholder?: string;
}

export function SearchCapsule({
  initialQuery = "",
  onSearch,
  isLoading = false,
  placeholder = "Ask a follow-up question or start a new topic...",
}: SearchCapsuleProps) {
  const [query, setQuery] = useState(initialQuery);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim() || isLoading) return;
    onSearch(query.trim(), "brief", "apa", false);
  };

  return (
    <div className="w-full max-w-3xl mx-auto">
      <form
        onSubmit={handleSubmit}
        className="relative flex items-center gap-space-sm bg-surface-container-high/80 backdrop-blur-xl rounded-full p-2 shadow-2xl border border-white/5 transition-all duration-300 hover:border-primary/30"
      >
        <div className="pl-space-md flex items-center text-primary shrink-0">
          <Sparkles className="w-5 h-5" />
        </div>

        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder={placeholder}
          disabled={isLoading}
          className="w-full bg-transparent text-on-surface placeholder:text-on-surface-variant/70 font-body-md text-body-md focus:outline-none px-space-sm py-2 min-w-0"
        />

        <button
          type="button"
          aria-label="Voice input"
          title="Voice input ready"
          className="w-10 h-10 shrink-0 rounded-full bg-surface-container/80 hover:bg-surface-bright text-on-surface-variant hover:text-on-surface flex items-center justify-center transition-colors"
        >
          <Mic className="w-4 h-4" />
        </button>

        <button
          type="submit"
          disabled={isLoading || !query.trim()}
          className="shrink-0 px-space-lg py-2.5 rounded-full bg-primary hover:bg-primary-fixed text-on-primary font-label-ui text-label-ui shadow-[0_0_24px_-4px_rgba(192,193,255,0.6)] hover:shadow-[0_0_28px_0px_rgba(192,193,255,0.8)] transition-all flex items-center gap-space-xs active:scale-95 disabled:opacity-50 cursor-pointer"
        >
          <span>{isLoading ? "Researching..." : "Research"}</span>
          <ArrowRight className="w-4 h-4" />
        </button>
      </form>
    </div>
  );
}
