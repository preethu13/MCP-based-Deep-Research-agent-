"use client";

import { TraceEvent } from "@/lib/api";
import { useState } from "react";
import { CheckCircle2, ChevronDown, Loader2 } from "lucide-react";

interface ExecutionStepperProps {
  trace: TraceEvent[];
  isStreaming?: boolean;
  isComplete?: boolean;
  error?: string | null;
}

export function ExecutionStepper({
  trace,
  isStreaming = false,
  isComplete = false,
  error,
}: ExecutionStepperProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  const stages = [
    { id: "planner", label: "Analyzing research question", detail: "Decomposing query into verified angles" },
    { id: "researcher", label: "Searching verified literature & sources", detail: "Querying OpenAlex & Web literature" },
    { id: "synthesizer", label: "Synthesizing evidence & insights", detail: "Extracting citations & grounded findings" },
    { id: "formatter", label: "Compiling research report & citations", detail: "Formatting dossier & references" },
  ];

  const hasPlanner = trace.some((t) => t.node === "planner") || isStreaming;
  const hasResearcher = trace.some((t) => t.node === "researcher");
  const hasSynthesizer = trace.some((t) => t.node === "synthesizer");
  const hasFormatter = trace.some((t) => t.node === "formatter") || isComplete;

  const completedCount = isComplete
    ? 4
    : hasFormatter
    ? 3
    : hasSynthesizer
    ? 2
    : hasResearcher
    ? 1
    : 0;
  const currentStep = isComplete ? 4 : Math.min(completedCount + 1, 4);

  // Active status labels
  let activeLabel = "Research Workspace Ready";
  let activeDetail = "Awaiting research query";
  let percentLabel = "0%";
  let percentNumber = 0;

  if (error) {
    activeLabel = "Research Halted";
    activeDetail = error;
    percentLabel = "Halted";
    percentNumber = 100;
  } else if (isComplete) {
    activeLabel = "Synthesis Complete";
    activeDetail = "All milestones verified & synthesized";
    percentLabel = "100%";
    percentNumber = 100;
  } else if (hasFormatter) {
    activeLabel = "Compiling Report";
    activeDetail = "Streaming final dossier & citations";
    percentLabel = "92%";
    percentNumber = 92;
  } else if (hasSynthesizer) {
    activeLabel = "Synthesizing Evidence";
    activeDetail = "Synthesizing claims from retrieved sources";
    percentLabel = "75%";
    percentNumber = 75;
  } else if (hasResearcher) {
    activeLabel = "Retrieving Literature";
    activeDetail = "Querying academic papers and web evidence";
    percentLabel = "45%";
    percentNumber = 45;
  } else if (hasPlanner || isStreaming) {
    activeLabel = "Analyzing Query";
    activeDetail = "Decomposing research topic";
    percentLabel = "20%";
    percentNumber = 20;
  }

  return (
    <section className="bg-surface-container-low/70 backdrop-blur-md rounded-DEFAULT shadow-sm border border-surface-container-high/30 flex flex-col gap-space-sm transition-all py-2.5 px-space-md w-full">
      <div className="flex flex-col gap-space-xs w-full">
        {/* Status Line */}
        <div className="flex items-center justify-between gap-space-sm">
          <div className="flex items-center gap-space-xs min-w-0">
            <div className="w-2 h-2 rounded-full bg-primary relative shrink-0">
              {!isComplete && isStreaming && (
                <span className="animate-ping absolute inset-0 rounded-full bg-primary opacity-75"></span>
              )}
            </div>
            <span className="font-label-ui text-label-ui text-on-surface font-semibold truncate">
              {activeLabel}
            </span>
            <span className="text-on-surface-variant font-label-mono-sm text-label-mono-sm">·</span>
            <span className="font-body-sm text-body-sm text-on-surface-variant truncate">
              {activeDetail}
            </span>
          </div>

          <div className="flex items-center gap-space-sm shrink-0">
            <span className="font-label-mono-sm text-label-mono-sm text-primary font-semibold">
              Step {currentStep} of 4
            </span>
            <span className="px-2 py-0.5 rounded-full bg-primary/15 border border-primary/30 text-primary font-label-mono-sm text-label-mono-sm">
              {percentLabel}
            </span>
            <button
              onClick={() => setIsExpanded(!isExpanded)}
              title="Toggle milestone events"
              className="p-1 rounded-full hover:bg-surface-container text-on-surface-variant hover:text-on-surface transition-colors"
            >
              <ChevronDown
                className={`w-3.5 h-3.5 transition-transform duration-200 ${
                  isExpanded ? "rotate-180" : ""
                }`}
              />
            </button>
          </div>
        </div>

        {/* Thin Glowing Gradient Progress Bar (h-1.5) with Active Shimmer Animation */}
        <div className="w-full h-1.5 rounded-full bg-surface-container-high overflow-hidden relative">
          <div
            className="h-full rounded-full bg-gradient-to-r from-primary via-secondary to-tertiary transition-all duration-500 shadow-[0_0_16px_0px_rgba(192,193,255,0.8)] relative overflow-hidden"
            style={{ width: `${percentNumber}%` }}
          >
            {!isComplete && isStreaming && (
              <>
                <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/40 to-transparent animate-pulse" />
                <div
                  className="absolute inset-0 w-full h-full -translate-x-full animate-shimmer"
                  style={{
                    background:
                      "linear-gradient(90deg, transparent 0%, rgba(255,255,255,0.45) 50%, transparent 100%)",
                  }}
                />
              </>
            )}
          </div>
        </div>
      </div>

      {/* Expandable detailed milestone breakdown */}
      {isExpanded && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2 pt-2 border-t border-surface-container-high/30 mt-1">
          {stages.map((stage, idx) => {
            const isDone = isComplete || idx < completedCount;
            const isCurrent = !isComplete && idx === completedCount;
            return (
              <div
                key={stage.id}
                className={`p-2.5 rounded-lg border text-xs flex items-center gap-2 transition-all ${
                  isDone
                    ? "bg-surface-container/60 border-surface-container-high/40 text-on-surface"
                    : isCurrent
                    ? "bg-surface-container border-primary/50 text-primary font-medium"
                    : "bg-surface-container/20 border-transparent text-outline"
                }`}
              >
                {isDone ? (
                  <CheckCircle2 className="w-3.5 h-3.5 text-tertiary shrink-0" />
                ) : (
                  <Loader2
                    className={`w-3.5 h-3.5 shrink-0 ${
                      isCurrent ? "animate-spin text-primary" : "text-outline"
                    }`}
                  />
                )}
                <span className="truncate">{stage.label}</span>
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}
