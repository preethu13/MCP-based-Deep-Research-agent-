"use client";

import { useState } from "react";
import { MemoryRecallHit, recallMemory } from "@/lib/api";
import { Search, BrainCircuit, Database } from "lucide-react";

export default function RecallMemoryPage() {
  const [query, setQuery] = useState("");
  const topK = 6;
  const [hits, setHits] = useState<MemoryRecallHit[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;
    setIsLoading(true);
    setHasSearched(true);
    try {
      const results = await recallMemory(query.trim(), topK, false);
      setHits(results);
    } catch (err) {
      console.error("Recall error:", err);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="w-full max-w-7xl mx-auto px-margin-mobile lg:px-margin py-space-xl flex flex-col gap-space-xl">
      {/* Header */}
      <div className="flex flex-col gap-space-xs max-w-2xl">
        <div className="flex items-center gap-space-sm">
          <span className="font-label-ui text-label-ui text-primary font-medium tracking-wide uppercase">
            Vector Store
          </span>
        </div>
        <h1 className="font-headline-lg text-headline-lg text-on-surface tracking-tight">
          Recall Memory
        </h1>
        <p className="font-body-md text-body-md text-on-surface-variant">
          Semantic search across verified claims, embeddings, and findings stored in local memory.
        </p>
      </div>

      {/* Search Input Bar */}
      <div className="p-space-xs rounded-full bg-surface-container-lowest/80 backdrop-blur-2xl shadow-xl border border-surface-container-high/40">
        <form
          onSubmit={handleSearch}
          className="flex flex-col sm:flex-row items-center gap-space-sm px-space-md py-2 bg-surface-container-low/70 rounded-full"
        >
          <div className="pl-space-xs text-primary">
            <BrainCircuit className="w-5 h-5 text-tertiary" />
          </div>

          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search past findings, claims, or concepts (e.g. KV cache, Redis latency)..."
            className="w-full bg-transparent font-body-md text-body-md text-on-surface placeholder:text-outline focus:outline-none px-space-xs tracking-tight"
          />

          <button
            type="submit"
            disabled={isLoading || !query.trim()}
            className="px-space-lg py-2 rounded-full bg-primary text-on-primary font-title-md text-title-md flex items-center gap-space-xs shadow-md shadow-primary/20 hover:scale-[1.02] active:scale-[0.98] transition-all disabled:opacity-50"
          >
            <Search className="w-4 h-4" />
            <span>{isLoading ? "Searching..." : "Recall"}</span>
          </button>
        </form>
      </div>

      {/* Results Section */}
      <div className="flex flex-col gap-space-md">
        <div className="flex items-center justify-between text-outline font-label-ui text-label-ui">
          <span>{hits.length} memories retrieved</span>
          <span className="text-[11px] font-label-mono-sm">ChromaDB + SQLite Hashing Embeddings</span>
        </div>

        {hits.length === 0 ? (
          <div className="p-16 rounded-lg bg-surface-container-low border border-surface-container-high/40 text-center">
            <Database className="w-8 h-8 text-outline mx-auto mb-2" />
            <h3 className="font-headline-sm text-headline-sm text-on-surface">
              {hasSearched ? "No Matching Memories Found" : "Enter a Query to Search Memory"}
            </h3>
            <p className="font-body-sm text-body-sm text-on-surface-variant mt-1">
              {hasSearched
                ? "Try broader terms or verify that previous research sessions completed and saved findings."
                : "Vector similarities will be computed against all past research claims."}
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-space-md">
            {hits.map((hit, idx) => (
              <div
                key={idx}
                className="p-space-lg rounded-lg bg-surface-container-low border border-surface-container-high/40 shadow-sm flex flex-col justify-between gap-space-md hover:bg-surface-container transition-colors"
              >
                <div>
                  <div className="flex items-center justify-between gap-2 mb-2">
                    <span className="px-2.5 py-0.5 rounded-full bg-tertiary-container/20 text-tertiary font-label-mono-sm text-[11px]">
                      sim {hit.similarity_score !== undefined ? hit.similarity_score.toFixed(3) : "1.000"}
                    </span>
                    {hit.metadata?.session_id && (
                      <span className="text-[11px] font-label-mono-sm text-outline">
                        {hit.metadata.session_id}
                      </span>
                    )}
                  </div>

                  <p className="font-body-md text-body-md text-on-surface leading-relaxed">
                    {hit.content}
                  </p>
                </div>

                {hit.metadata && (
                  <div className="pt-2 border-t border-surface-container-high/30 flex items-center justify-between text-[11px] font-label-mono-sm text-outline">
                    <span>{hit.metadata.source || "Grounded Claim"}</span>
                    <span>{hit.metadata.timestamp || "Stored"}</span>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
