"use client";

import { Compass, ArrowRight } from "lucide-react";

interface RelatedQuestionsProps {
  query?: string;
  onSelectPrompt: (prompt: string) => void;
}

export function RelatedQuestions({ query = "", onSelectPrompt }: RelatedQuestionsProps) {
  // Generate tailored questions if query is present, or clean defaults
  const cleanQ = query.trim();

  let prompts = [
    "How does memory differ from context in LLM architectures?",
    "What are the primary performance bottlenecks and trade-offs?",
    "What are the recommended production deployment best practices?",
  ];

  if (cleanQ) {
    if (/\b(vs|versus|compare|comparison|difference)\b/i.test(cleanQ)) {
      prompts = [
        `How does security and credential management compare in ${cleanQ}?`,
        `What are the performance and latency trade-offs between ${cleanQ}?`,
        `When should developers choose one over the other in production?`,
      ];
    } else {
      prompts = [
        `What are the latest breakthrough algorithms and methodologies for ${cleanQ}?`,
        `What are the most common failure modes and optimization strategies in ${cleanQ}?`,
        `How is ${cleanQ} being applied in modern production systems?`,
      ];
    }
  }

  return (
    <section className="bg-surface-container-low rounded-2xl p-space-lg shadow-md flex flex-col gap-space-md border border-surface-container-high/30 w-full backdrop-blur-md">
      <div className="flex items-center justify-between gap-space-sm">
        <div className="flex items-center gap-space-sm">
          <div className="w-8 h-8 rounded-full bg-secondary/15 text-secondary flex items-center justify-center shrink-0">
            <Compass className="w-4 h-4" />
          </div>
          <div>
            <h2 className="font-title-md text-title-md text-on-surface">
              Related Explorations &amp; Questions
            </h2>
            <p className="font-body-sm text-body-sm text-on-surface-variant">
              Click any prompt to instantly explore follow-up avenues
            </p>
          </div>
        </div>
        <span className="hidden sm:inline-flex px-3 py-1 rounded-full bg-surface-container text-on-surface-variant font-label-mono-sm text-label-mono-sm border border-surface-container-high/30">
          Interactive
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-space-sm">
        {prompts.map((prompt, idx) => (
          <button
            key={idx}
            type="button"
            onClick={() => onSelectPrompt(prompt)}
            className="text-left bg-surface-container hover:bg-surface-container-high rounded-DEFAULT p-space-md transition-all flex items-center justify-between gap-space-sm group border border-surface-container-high/20 hover:border-primary/40 hover:-translate-y-0.5 cursor-pointer shadow-sm"
          >
            <span className="font-body-md text-body-md text-on-surface group-hover:text-primary transition-colors leading-snug">
              {prompt}
            </span>
            <ArrowRight className="w-4 h-4 text-on-surface-variant group-hover:text-primary shrink-0 transition-transform group-hover:translate-x-1" />
          </button>
        ))}
      </div>
    </section>
  );
}
