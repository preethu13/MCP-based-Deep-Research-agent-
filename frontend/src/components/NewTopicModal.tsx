"use client";

import { useState } from "react";
import { Sparkles, X } from "lucide-react";

interface NewTopicModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (query: string, format: string) => void;
}

export function NewTopicModal({ isOpen, onClose, onSubmit }: NewTopicModalProps) {
  const [query, setQuery] = useState("");
  const [format, setFormat] = useState("brief");

  if (!isOpen) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;
    onSubmit(query.trim(), format);
    setQuery("");
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-space-md bg-surface-container-lowest/80 backdrop-blur-md">
      <div className="relative w-full max-w-xl p-space-lg rounded-xl bg-surface-container-high border border-surface-container-highest shadow-2xl flex flex-col gap-space-md animate-in fade-in zoom-in-95 duration-150">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-space-xs">
            <Sparkles className="w-5 h-5 text-primary" />
            <h3 className="font-headline-sm text-headline-sm text-on-surface">New Research Topic</h3>
          </div>
          <button
            onClick={onClose}
            className="w-8 h-8 rounded-full flex items-center justify-center text-outline hover:text-on-surface bg-surface-container hover:bg-surface-bright transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="flex flex-col gap-space-md">
          <div className="flex flex-col gap-space-sm">
            <label className="font-label-ui text-label-ui text-on-surface-variant">
              Research Question or In-Depth Topic
            </label>
            <textarea
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="e.g. Compare Redis and Memcached for distributed session caching..."
              rows={3}
              required
              className="w-full bg-surface-container-low p-space-md rounded-lg font-body-md text-body-md text-on-surface placeholder:text-outline focus:outline-none focus:ring-1 focus:ring-primary transition-colors resize-none border border-surface-container-high"
            />
          </div>

          <div className="flex items-center gap-space-xs">
            <span className="font-label-ui text-label-ui text-on-surface-variant mr-2">Format:</span>
            {["brief", "report", "comparison"].map((f) => (
              <button
                key={f}
                type="button"
                onClick={() => setFormat(f)}
                className={`px-3 py-1 rounded-full font-label-ui text-label-ui capitalize border transition-all ${
                  format === f
                    ? "bg-primary text-on-primary border-primary font-medium"
                    : "border-surface-container-high bg-surface-container text-on-surface-variant hover:text-on-surface"
                }`}
              >
                {f}
              </button>
            ))}
          </div>

          <div className="flex items-center justify-end gap-space-sm pt-space-sm border-t border-surface-container-high/40">
            <button
              type="button"
              onClick={onClose}
              className="px-space-lg py-2 rounded-full font-label-ui text-label-ui text-on-surface-variant hover:text-on-surface hover:bg-surface-container transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-space-lg py-2 rounded-full font-title-md text-title-md bg-primary text-on-primary shadow-lg shadow-primary/25 hover:scale-[1.02] active:scale-[0.98] transition-all flex items-center gap-1.5"
            >
              <Sparkles className="w-4 h-4" />
              <span>Begin Research</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
