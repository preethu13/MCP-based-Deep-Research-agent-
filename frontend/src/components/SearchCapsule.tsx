"use client";

import { useState } from "react";
import { ArrowRight, Mic, Sparkles } from "lucide-react";

interface SearchCapsuleProps {
  initialQuery?: string;
  onSearch: (query: string, format: string, style: string, demo: boolean) => void;
  isLoading?: boolean;
}

export function SearchCapsule({ initialQuery = "", onSearch, isLoading = false }: SearchCapsuleProps) {
  const [query, setQuery] = useState(initialQuery);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim() || isLoading) return;
    onSearch(query.trim(), "brief", "apa", false);
  };

  return (
    <div className="w-full max-w-4xl mx-auto flex flex-col items-center">
      {/* Floating Glassmorphic Capsule */}
      <div className="w-full p-space-xs rounded-full bg-surface-container-lowest/80 backdrop-blur-2xl shadow-2xl border border-surface-container-high/40 transition-all duration-300">
        <form
          onSubmit={handleSubmit}
          className="flex flex-col sm:flex-row items-center gap-space-sm px-space-md py-2.5 bg-surface-container-low/70 rounded-full"
        >
          <div className="flex items-center gap-space-sm pl-space-xs">
            <div className="w-9 h-9 rounded-full bg-surface-container flex items-center justify-center text-primary shadow-sm">
              <Sparkles className="w-4 h-4 text-primary" />
            </div>
          </div>

          <div className="flex-1 w-full min-w-0">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="What would you like to research today?"
              disabled={isLoading}
              className="w-full bg-transparent font-body-md text-body-md text-on-surface placeholder:text-outline focus:outline-none px-space-xs tracking-tight"
            />
          </div>

          <div className="flex items-center gap-space-xs flex-wrap sm:flex-nowrap justify-end w-full sm:w-auto pr-space-xs">
            <button
              type="button"
              title="Voice Input (Speech-to-Text ready)"
              className="flex items-center justify-center w-9 h-9 rounded-full bg-surface-container hover:bg-surface-container-high text-on-surface-variant hover:text-on-surface transition-colors"
            >
              <Mic className="w-4 h-4" />
            </button>

            <button
              type="submit"
              disabled={isLoading || !query.trim()}
              className="px-space-lg py-2.5 rounded-full bg-primary-container hover:bg-primary-container/90 text-on-primary font-title-md text-title-md flex items-center gap-space-xs shadow-md shadow-primary-container/25 transition-all active:scale-[0.98] disabled:opacity-50"
            >
              <span>{isLoading ? "Researching..." : "Research"}</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
