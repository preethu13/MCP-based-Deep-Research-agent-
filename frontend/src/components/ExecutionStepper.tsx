"use client";

import { TraceEvent } from "@/lib/api";
import { CheckCircle2, Loader2, AlertCircle } from "lucide-react";

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
  const allStages = [
    { id: "planner", label: "Analyzing research question" },
    { id: "researcher", label: "Searching verified literature & sources" },
    { id: "synthesizer", label: "Synthesizing evidence & insights" },
    { id: "formatter", label: "Compiling research report & citations" },
  ];

  // Determine stage progression from real events
  const hasPlanner = trace.some((t) => t.node === "planner" || t.step >= 1) || isStreaming;
  const hasResearcher = trace.some((t) => t.node === "researcher" || t.step >= 2);
  const hasSynthesizer = trace.some((t) => t.node === "synthesizer" || t.step >= 3);
  const hasFormatter = isComplete || trace.some((t) => t.node === "formatter" || t.step >= 4);

  // How many steps have been unlocked/reached so far
  let visibleCount = 0;
  if (isComplete) {
    visibleCount = 4;
  } else if (hasFormatter) {
    visibleCount = 4;
  } else if (hasSynthesizer) {
    visibleCount = 3;
  } else if (hasResearcher) {
    visibleCount = 2;
  } else if (hasPlanner || isStreaming) {
    visibleCount = 1;
  }

  // Only display steps that have actually been reached
  const visibleStages = allStages.slice(0, visibleCount);

  // Progress percentage
  const completedCount = isComplete
    ? 4
    : hasFormatter
    ? 3
    : hasSynthesizer
    ? 2
    : hasResearcher
    ? 1
    : 0;
  const progressPercent = isComplete ? 100 : Math.max(18, (completedCount / 4) * 100 + (isStreaming ? 12 : 0));

  return (
    <div className="w-full rounded-lg bg-surface-container-low p-space-lg text-left shadow-xl border border-surface-container-high/40 relative">
      {/* Header */}
      <div className="flex items-center justify-between mb-space-md">
        <div className="flex items-center gap-space-sm">
          {!isComplete && !error ? (
            <Loader2 className="w-5 h-5 text-primary animate-spin" />
          ) : error ? (
            <AlertCircle className="w-5 h-5 text-error" />
          ) : (
            <CheckCircle2 className="w-5 h-5 text-tertiary" />
          )}
          <span className="font-title-md text-title-md text-on-surface">
            {error
              ? "Research Halted"
              : isComplete
              ? "Research Completed"
              : "Conducting Research..."}
          </span>
          <span className="px-space-sm py-0.5 rounded-full bg-primary/10 text-primary font-label-ui text-label-ui">
            {isComplete ? "Finished" : `Step ${visibleCount} of 4`}
          </span>
        </div>
      </div>

      {/* Gradient Progress Bar */}
      <div className="w-full h-2 bg-surface-container-highest rounded-full overflow-hidden mb-space-lg relative shadow-inner">
        <div
          className="h-full bg-gradient-to-r from-primary via-secondary to-tertiary transition-all duration-500 rounded-full relative"
          style={{ width: `${Math.min(progressPercent, 100)}%` }}
        >
          {!isComplete && isStreaming && (
            <div className="absolute inset-0 bg-white/20 animate-pulse rounded-full" />
          )}
        </div>
      </div>

      {/* Dynamically Revealed Stages (Shown one by one as process continues) */}
      <div className="flex flex-col gap-space-xs font-label-ui text-label-ui">
        {visibleStages.map((stage, idx) => {
          const isDone = isComplete || idx < completedCount;
          const isCurrent = !isComplete && idx === completedCount;

          return (
            <div
              key={stage.id}
              className={`flex items-center gap-space-sm px-space-md py-3 rounded-DEFAULT border transition-all duration-300 animate-in fade-in slide-in-from-top-1 ${
                isDone
                  ? "bg-surface-container/60 border-surface-container-high/40 text-on-surface"
                  : isCurrent
                  ? "bg-surface-container border-primary/50 text-primary font-medium"
                  : "bg-surface-container/20 border-transparent text-outline"
              }`}
            >
              {isDone ? (
                <CheckCircle2 className="w-4 h-4 text-tertiary shrink-0" />
              ) : (
                <Loader2 className="w-4 h-4 text-primary animate-spin shrink-0" />
              )}
              <span className="truncate">{stage.label}</span>
              {isCurrent && (
                <span className="ml-auto text-[11px] font-label-mono-sm text-primary/70 animate-pulse">
                  In progress...
                </span>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
