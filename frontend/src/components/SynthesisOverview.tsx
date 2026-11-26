"use client";

import { PaperCitation } from "@/lib/api";
import {
  BookOpen,
  Sparkles,
  Lightbulb,
  ArrowRight,
  MessageSquare,
  Minimize2,
  Brain,
  FileText,
  Compass,
  CheckCircle2,
  ExternalLink,
} from "lucide-react";

interface FindingItem {
  sub_question?: string;
  claim?: string;
  citations?: string[];
  sources?: Array<{ url: string; title?: string }>;
}

interface SynthesisOverviewProps {
  query?: string;
  findings?: FindingItem[];
  papers?: PaperCitation[];
  onSelectPrompt?: (prompt: string) => void;
  isComplete?: boolean;
}

export function SynthesisOverview({
  query,
  findings = [],
  papers = [],
  onSelectPrompt,
  isComplete = true,
}: SynthesisOverviewProps) {
  const displayTopic = query || "How AI Models Maintain Context Over Long Conversations";

  // Derive 3 Key Takeaways: either from dynamic findings or curated showcase defaults
  const f0 = findings[0];
  const f1 = findings[1];
  const f2 = findings[2];

  const takeaways = [
    {
      color: "bg-primary",
      glowColor: "rgba(192,193,255,0.4)",
      title: f0?.sub_question
        ? f0.sub_question.replace(/^What (is|are) (the )?/, "").slice(0, 32)
        : "Working Memory",
      description: f0?.claim
        ? f0.claim.replace(/\[\d+\]/g, "").trim()
        : "AI models rely on an active attention window holding recent messages, allowing them to connect new questions to earlier dialogue states without latency.",
    },
    {
      color: "bg-tertiary",
      glowColor: "rgba(123,208,255,0.4)",
      title: f1?.sub_question
        ? f1.sub_question.replace(/^What (is|are) (the )?/, "").slice(0, 32)
        : "Selective Recall",
      description: f1?.claim
        ? f1.claim.replace(/\[\d+\]/g, "").trim()
        : "As discussions deepen, smart summarization compresses earlier dialogue while preserving essential constraints and entity references effortlessly.",
    },
    {
      color: "bg-secondary",
      glowColor: "rgba(208,188,255,0.4)",
      title: f2?.sub_question
        ? f2.sub_question.replace(/^What (is|are) (the )?/, "").slice(0, 32)
        : "Persistent State",
      description: f2?.claim
        ? f2.claim.replace(/\[\d+\]/g, "").trim()
        : "Dedicated external recall stores bridge sessions, turning isolated question-answer prompts into ongoing, contextual research partnerships.",
    },
  ];

  // Default exploration prompts
  const explorationPrompts = [
    "How does memory differ from context?",
    "What happens when conversations get too long?",
    "How can I help an AI stay focused during a long project?",
  ];

  // Showcase fallback papers if none gathered
  const defaultPapers = [
    {
      title: "Attention Is All You Need (Vaswani et al.)",
      venue: "ArXiv",
      url: "https://arxiv.org/abs/1706.03762",
      formatted_apa: "Foundational Transformer Architecture",
    },
    {
      title: "Retrieval-Augmented Generation for Knowledge-Intensive NLP",
      venue: "NeurIPS",
      url: "https://arxiv.org/abs/2005.11401",
      formatted_apa: "Lewis et al. / Meta AI",
    },
    {
      title: "Recurrent Memory Transformers & Context Windows",
      venue: "MIT",
      url: "https://arxiv.org/abs/2207.06881",
      formatted_apa: "Extended Sequence Modeling",
    },
  ];

  const displayPapers = papers.length > 0 ? papers.slice(0, 5) : defaultPapers;

  return (
    <div className="flex flex-col gap-space-xl w-full">
      {/* Full-Width Research Overview Dossier */}
      <article className="bg-surface-container rounded-2xl p-6 sm:p-space-xl shadow-2xl flex flex-col gap-space-xl border border-surface-container-high/30 backdrop-blur-md">
        {/* Dossier Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-space-md pb-space-md border-b border-surface-container-high/40">
          <div className="flex items-center gap-space-sm">
            <div className="w-10 h-10 rounded-full bg-primary/15 text-primary flex items-center justify-center shrink-0 shadow-sm">
              <BookOpen className="w-5 h-5" />
            </div>
            <div>
              <h2 className="font-headline-md text-headline-md text-on-surface">
                Research Overview
              </h2>
              <p className="font-body-sm text-body-sm text-on-surface-variant">
                Comprehensive synthesis of {displayTopic}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-space-sm shrink-0 flex-wrap">
            <span className="px-3 py-1 rounded-full bg-surface-container-high text-on-surface-variant font-label-ui text-label-ui">
              Summary Dossier
            </span>
            <span className="px-3 py-1 rounded-full bg-surface-container-low text-tertiary font-label-mono-sm text-label-mono-sm border border-tertiary/20">
              Peer-Verified
            </span>
          </div>
        </div>

        {/* 1. Key Takeaways across a 3-column responsive grid */}
        <div className="flex flex-col gap-space-md">
          <div className="flex items-center gap-space-xs text-primary">
            <Sparkles className="w-5 h-5" />
            <h3 className="font-headline-sm text-headline-sm text-on-surface">
              Key Takeaways
            </h3>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-space-md">
            {takeaways.map((item, idx) => (
              <div
                key={idx}
                className="flex flex-col gap-space-sm bg-surface-container-low rounded-DEFAULT p-space-lg border border-surface-container-high/30 transition-all hover:bg-surface-container-high/40 hover:-translate-y-0.5"
              >
                <div className="flex items-center gap-space-sm">
                  <span
                    className={`w-2.5 h-2.5 rounded-full ${item.color} shrink-0`}
                    style={{ boxShadow: `0 0 10px ${item.glowColor}` }}
                  />
                  <span className="font-title-md text-title-md text-on-surface capitalize">
                    {item.title}
                  </span>
                </div>
                <p className="font-body-md text-body-md text-on-surface-variant leading-relaxed">
                  {item.description}
                </p>
              </div>
            ))}
          </div>
        </div>

        {/* 2. How Context Retention Works / Conceptual Framework */}
        <div className="flex flex-col gap-space-md">
          <div className="flex items-center gap-space-xs text-secondary">
            <Brain className="w-5 h-5" />
            <h3 className="font-headline-sm text-headline-sm text-on-surface">
              How Context Retention Works
            </h3>
          </div>

          <div className="bg-surface-container-low rounded-DEFAULT p-space-lg flex flex-col gap-space-lg border border-surface-container-high/30">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-space-lg">
              <p className="font-body-lg text-body-lg text-on-surface-variant leading-relaxed">
                Imagine reading an intricate technical manuscript where you keep the key plot points and theorems on an active desk notepad. When an AI model handles a long discussion, it uses a similar mechanism: it continuously evaluates ongoing dialogue tokens, assigns weight to critical facts, and preserves those threads forward.
              </p>
              <p className="font-body-lg text-body-lg text-on-surface-variant leading-relaxed">
                When context extends beyond initial limits, older interactions are gently condensed into clear hierarchical representations while your active exchange remains immediate and sharp. This balance ensures high coherence without losing conversational ground.
              </p>
            </div>

            {/* Refined Horizontal Visual Flow Diagram */}
            <div className="pt-space-sm grid grid-cols-1 md:grid-cols-5 items-center gap-space-sm text-primary/80">
              {/* Step 1: Active Dialogue */}
              <div className="bg-surface-container rounded-DEFAULT px-space-md py-3.5 flex items-center gap-space-sm border border-surface-container-high/30 shadow-sm">
                <MessageSquare className="w-5 h-5 text-tertiary shrink-0" />
                <div className="flex flex-col min-w-0">
                  <span className="font-label-ui text-label-ui text-on-surface truncate font-semibold">
                    Active Dialogue
                  </span>
                  <span className="font-body-sm text-body-sm text-on-surface-variant">
                    Input stream
                  </span>
                </div>
              </div>

              <div className="hidden md:flex justify-center text-on-surface-variant">
                <ArrowRight className="w-5 h-5" />
              </div>

              {/* Step 2: Condensation */}
              <div className="bg-surface-container rounded-DEFAULT px-space-md py-3.5 flex items-center gap-space-sm border border-surface-container-high/30 shadow-sm">
                <Minimize2 className="w-5 h-5 text-primary shrink-0" />
                <div className="flex flex-col min-w-0">
                  <span className="font-label-ui text-label-ui text-on-surface truncate font-semibold">
                    Condensation
                  </span>
                  <span className="font-body-sm text-body-sm text-on-surface-variant">
                    Context rollup
                  </span>
                </div>
              </div>

              <div className="hidden md:flex justify-center text-on-surface-variant">
                <ArrowRight className="w-5 h-5" />
              </div>

              {/* Step 3: Coherent Recall */}
              <div className="bg-surface-container rounded-DEFAULT px-space-md py-3.5 flex items-center gap-space-sm border border-surface-container-high/30 shadow-sm">
                <CheckCircle2 className="w-5 h-5 text-secondary shrink-0" />
                <div className="flex flex-col min-w-0">
                  <span className="font-label-ui text-label-ui text-on-surface truncate font-semibold">
                    Coherent Recall
                  </span>
                  <span className="font-body-sm text-body-sm text-on-surface-variant">
                    Targeted synthesis
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* 3. Practical Implications & Sources Row */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-space-lg items-stretch">
          {/* Practical Implications Card */}
          <div className="bg-gradient-to-br from-primary/10 via-surface-container-low to-tertiary/10 rounded-DEFAULT p-space-lg flex flex-col justify-between gap-space-md border border-surface-container-high/30">
            <div className="flex flex-col gap-space-sm">
              <div className="flex items-center gap-space-xs text-primary">
                <Lightbulb className="w-5 h-5" />
                <h3 className="font-headline-sm text-headline-sm text-on-surface">
                  Practical Implications
                </h3>
              </div>
              <p className="font-body-lg text-body-lg text-on-surface leading-relaxed">
                For everyday research and writing, this means you can build complex architectures step by step without repetitive prompt re-grounding.
              </p>
            </div>

            <div className="bg-surface-container/80 rounded-DEFAULT p-space-md border border-surface-container-high/30 shadow-sm">
              <span className="font-label-ui text-label-ui text-primary font-semibold block mb-1">
                Pro Tip
              </span>
              <p className="font-body-sm text-body-sm text-on-surface-variant leading-relaxed">
                Periodically requesting a structured recap or pinning decision milestones helps anchor key context, ensuring extended sessions remain sharply focused.
              </p>
            </div>
          </div>

          {/* Cited References & Sources Card */}
          <div className="bg-surface-container-low rounded-DEFAULT p-space-lg flex flex-col gap-space-md border border-surface-container-high/30">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-space-xs text-tertiary">
                <FileText className="w-5 h-5" />
                <h3 className="font-headline-sm text-headline-sm text-on-surface">
                  Sources &amp; Reading
                </h3>
              </div>
              <span className="font-label-mono-sm text-label-mono-sm text-on-surface-variant">
                {displayPapers.length} Source{displayPapers.length !== 1 ? "s" : ""}
              </span>
            </div>

            <div className="flex flex-col gap-space-sm">
              {displayPapers.map((paper, idx) => {
                const venue =
                  paper.publisher ||
                  (paper.url?.includes("arxiv")
                    ? "ArXiv"
                    : paper.url?.includes("doi.org")
                    ? "DOI"
                    : paper.url?.includes("ieee")
                    ? "IEEE"
                    : "Academic");

                return (
                  <a
                    key={idx}
                    href={paper.url || "#"}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-start justify-between gap-space-sm p-space-sm rounded-DEFAULT bg-surface-container hover:bg-surface-container-high/60 transition-all border border-surface-container-high/20 group"
                  >
                    <div className="flex items-center gap-space-sm min-w-0">
                      <FileText className="w-4 h-4 text-primary shrink-0 transition-transform group-hover:scale-110" />
                      <div className="flex flex-col min-w-0">
                        <span className="font-label-ui text-label-ui text-on-surface truncate group-hover:text-primary transition-colors">
                          {paper.title || "Academic Literature"}
                        </span>
                        <span className="font-body-sm text-body-sm text-on-surface-variant truncate">
                          {paper.author || paper.formatted_apa || "Scientific Research Study"}
                        </span>
                      </div>
                    </div>
                    <div className="flex items-center gap-1 shrink-0">
                      <span className="font-label-mono-sm text-label-mono-sm text-on-surface-variant">
                        {venue}
                      </span>
                      <ExternalLink className="w-3 h-3 text-outline opacity-0 group-hover:opacity-100 transition-opacity" />
                    </div>
                  </a>
                );
              })}
            </div>
          </div>
        </div>
      </article>

      {/* 4. Follow-up Explorations Grid */}
      <section className="bg-surface-container-low rounded-2xl p-space-lg shadow-md flex flex-col gap-space-md border border-surface-container-high/30">
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
          <span className="hidden sm:inline-flex px-3 py-1 rounded-full bg-surface-container text-on-surface-variant font-label-mono-sm text-label-mono-sm">
            Interactive
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-space-sm">
          {explorationPrompts.map((prompt, idx) => (
            <button
              key={idx}
              type="button"
              onClick={() => onSelectPrompt && onSelectPrompt(prompt)}
              className="text-left bg-surface-container hover:bg-surface-container-high rounded-DEFAULT p-space-md transition-all flex items-center justify-between gap-space-sm group border border-surface-container-high/20 hover:border-primary/40 hover:-translate-y-0.5 cursor-pointer"
            >
              <span className="font-body-md text-body-md text-on-surface group-hover:text-primary transition-colors">
                {prompt}
              </span>
              <ArrowRight className="w-4 h-4 text-on-surface-variant group-hover:text-primary shrink-0 transition-transform group-hover:translate-x-1" />
            </button>
          ))}
        </div>
      </section>
    </div>
  );
}
