"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { SearchCapsule } from "@/components/SearchCapsule";
import { ShieldCheck, Link2, BrainCircuit, Sparkles } from "lucide-react";

export default function HomePage() {
  const router = useRouter();
  const [isStarting, setIsStarting] = useState(false);

  const handleSearch = (query: string, format: string, style: string, demo: boolean) => {
    setIsStarting(true);
    const params = new URLSearchParams({
      q: query,
      format,
      style,
      demo: demo ? "true" : "false",
    });
    router.push(`/research?${params.toString()}`);
  };

  return (
    <div className="flex flex-col w-full relative">
      {/* Ambient Radial Gradient Glow */}
      <div className="absolute -top-12 left-1/2 -translate-x-1/2 w-3/4 max-w-5xl h-96 bg-gradient-to-tr from-secondary-container/25 via-tertiary-container/10 to-transparent blur-[140px] pointer-events-none rounded-full" />

      {/* Hero & Primary Synthesizer Area */}
      <section className="relative w-full max-w-7xl mx-auto px-margin-mobile lg:px-margin pt-14 pb-16 flex flex-col items-center text-center">
        {/* Micro Pill Badge */}
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-surface-container-high/80 border border-surface-container-highest text-primary font-label-mono-sm text-[11px] mb-6 shadow-sm">
          <Sparkles className="w-3.5 h-3.5" />
          <span>Local · Private · $0 per query</span>
        </div>

        {/* Editorial Headline */}
        <h1 className="font-display-lg text-display-lg max-w-4xl tracking-tight text-on-surface">
          Autonomous{" "}
          <span className="bg-gradient-to-r from-primary via-secondary to-tertiary bg-clip-text text-transparent">
            Deep Research
          </span>
        </h1>

        <p className="mt-space-md font-body-lg text-body-lg text-on-surface-variant max-w-2xl tracking-normal leading-relaxed">
          Ask complex questions, explore topics recursively across academic literature and open web, and receive grounded answers backed by verified citations.
        </p>

        {/* Central Floating Search Capsule */}
        <div className="w-full mt-space-xl z-20">
          <SearchCapsule onSearch={handleSearch} isLoading={isStarting} />
        </div>
      </section>

      {/* Quick Example Topics Section */}
      <section className="w-full max-w-5xl mx-auto px-margin-mobile lg:px-margin pb-16">
        <div className="flex items-center justify-center gap-space-xs flex-wrap text-center">
          <span className="font-label-ui text-label-ui text-outline mr-2">Try researching:</span>
          {[
            "Compare Redis and Memcached for session caching",
            "Attention mechanisms vs State Space Models",
            "Context retention and KV cache compression in LLMs",
          ].map((topic, i) => (
            <button
              key={i}
              onClick={() => handleSearch(topic, "brief", "apa", false)}
              className="px-3.5 py-1.5 rounded-full bg-surface-container hover:bg-surface-container-high text-on-surface-variant hover:text-on-surface border border-surface-container-high/40 text-[12px] font-label-ui transition-all"
            >
              {topic}
            </button>
          ))}
        </div>
      </section>

      {/* 3 Glassmorphic Bento Cards */}
      <section className="w-full max-w-7xl mx-auto px-margin-mobile lg:px-margin pb-24">
        <div className="flex flex-col items-center text-center mb-space-xl">
          <h2 className="font-headline-lg text-headline-lg text-on-surface tracking-tight">
            Designed to Be Private and Rigorous
          </h2>
          <p className="font-body-md text-body-md text-on-surface-variant max-w-xl mt-space-xs">
            A research analyst that runs directly on your hardware without subscription costs.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-gutter">
          <div className="p-space-xl rounded-lg bg-surface-container-low border border-surface-container-high/40 shadow-sm flex flex-col justify-between group hover:bg-surface-container transition-all">
            <div>
              <div className="w-12 h-12 rounded-full bg-secondary-container/20 text-secondary flex items-center justify-center mb-space-lg shadow-sm">
                <ShieldCheck className="w-6 h-6" />
              </div>
              <h3 className="font-headline-sm text-headline-sm text-on-surface mb-space-sm">
                100% Local & Private
              </h3>
              <p className="font-body-md text-body-md text-on-surface-variant leading-relaxed">
                Operates with local Ollama models or BYO cloud API. Your research questions and data stay entirely under your control.
              </p>
            </div>
          </div>

          <div className="p-space-xl rounded-lg bg-surface-container-low border border-surface-container-high/40 shadow-sm flex flex-col justify-between group hover:bg-surface-container transition-all">
            <div>
              <div className="w-12 h-12 rounded-full bg-primary-container/20 text-primary flex items-center justify-center mb-space-lg shadow-sm">
                <Link2 className="w-6 h-6" />
              </div>
              <h3 className="font-headline-sm text-headline-sm text-on-surface mb-space-sm">
                Dual-Tier Search MCP
              </h3>
              <p className="font-body-md text-body-md text-on-surface-variant leading-relaxed">
                Connects OpenAlex academic papers and DuckDuckGo web search with relevance guardrails and false-friend filters.
              </p>
            </div>
          </div>

          <div className="p-space-xl rounded-lg bg-surface-container-low border border-surface-container-high/40 shadow-sm flex flex-col justify-between group hover:bg-surface-container transition-all">
            <div>
              <div className="w-12 h-12 rounded-full bg-tertiary-container/20 text-tertiary flex items-center justify-center mb-space-lg shadow-sm">
                <BrainCircuit className="w-6 h-6" />
              </div>
              <h3 className="font-headline-sm text-headline-sm text-on-surface mb-space-sm">
                Semantic Recall Memory
              </h3>
              <p className="font-body-md text-body-md text-on-surface-variant leading-relaxed">
                Stores verified claims and paper findings in ChromaDB and SQLite, compounding knowledge across research inquiries.
              </p>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
