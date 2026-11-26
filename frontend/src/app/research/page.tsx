"use client";

import { useEffect, useState, useRef, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import {
  TraceEvent,
  PaperCitation,
  startResearch,
  streamResearchSession,
  getResearchSession,
  getSessionPapers,
  getResearchHistory,
} from "@/lib/api";
import { ExecutionStepper } from "@/components/ExecutionStepper";
import { DossierViewer } from "@/components/DossierViewer";
import { PaperExplorer } from "@/components/PaperExplorer";
import { SearchCapsule } from "@/components/SearchCapsule";
import { ArrowLeft, RefreshCw, Sparkles } from "lucide-react";
import Link from "next/link";

function ResearchWorkspaceContent() {
  const searchParams = useSearchParams();
  const router = useRouter();

  const queryParam = searchParams.get("q") || searchParams.get("query") || "";
  const idParam = searchParams.get("id") || "";
  const formatParam = searchParams.get("format") || "brief";
  const styleParam = searchParams.get("style") || "apa";
  const demoParam = searchParams.get("demo") === "true";

  const [activeQuery, setActiveQuery] = useState(queryParam);
  const [sessionId, setSessionId] = useState(idParam);
  const [trace, setTrace] = useState<TraceEvent[]>([]);
  const [finalOutput, setFinalOutput] = useState<string>("");
  const [findings, setFindings] = useState<any[]>([]);
  const [papers, setPapers] = useState<PaperCitation[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [isComplete, setIsComplete] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const cleanupRef = useRef<(() => void) | null>(null);

  // 1. Fresh Idle State: When visiting /research directly without parameters, reset to plain unresearched state
  useEffect(() => {
    if (!idParam && !queryParam) {
      setActiveQuery("");
      setSessionId("");
      setTrace([]);
      setFinalOutput("");
      setFindings([]);
      setPapers([]);
      setIsStreaming(false);
      setIsComplete(false);
      setError(null);
    }
  }, [idParam, queryParam]);

  // 2. Load existing session by ID
  useEffect(() => {
    if (idParam && !queryParam) {
      setSessionId(idParam);
      setIsStreaming(true);
      if (typeof window !== "undefined") {
        sessionStorage.setItem("active_research_session_id", idParam);
        window.dispatchEvent(new Event("active_session_change"));
      }

      getResearchSession(idParam, styleParam)
        .then((session) => {
          setActiveQuery(session.query || "");
          setFinalOutput(session.final_output || "");
          setFindings(session.findings || []);
          setIsComplete(true);
          setIsStreaming(false);
        })
        .catch((err) => {
          setError(`Could not load session: ${err.message}`);
          setIsStreaming(false);
        });

      getSessionPapers(idParam)
        .then((res) => {
          if (res && res.length > 0) setPapers(res);
        })
        .catch(() => {});
    }
  }, [idParam, queryParam, styleParam]);

  // 3. Initiate new live research
  useEffect(() => {
    if (queryParam) {
      setActiveQuery(queryParam);
      setTrace([]);
      setFinalOutput("");
      setFindings([]);
      setPapers([]);
      setError(null);
      setIsComplete(false);
      setIsStreaming(true);

      let activeSessionId = idParam;

      const launch = async () => {
        try {
          if (!activeSessionId) {
            const initRes = await startResearch(queryParam, formatParam, styleParam, demoParam);
            activeSessionId = initRes.session_id;
            setSessionId(activeSessionId);
            if (typeof window !== "undefined") {
              sessionStorage.setItem("active_research_session_id", activeSessionId);
              window.dispatchEvent(new Event("active_session_change"));
            }
          }

          cleanupRef.current = streamResearchSession({
            sessionId: activeSessionId,
            query: queryParam,
            outputFormat: formatParam,
            citationStyle: styleParam,
            demo: demoParam,
            onToken: (tok) => {
              setFinalOutput((prev) => (prev ? prev + tok : tok));
            },
            onProgress: (data) => {
              if (data.trace && data.trace.length > 0) {
                setTrace(data.trace);
              }
              if (data.findings && data.findings.length > 0) {
                setFindings(data.findings);
              }
              if (data.papers && data.papers.length > 0) {
                setPapers(data.papers);
              }
              if (data.final_output) {
                setFinalOutput(data.final_output);
              }
            },
            onComplete: () => {
              setIsStreaming(false);
              setIsComplete(true);
              if (activeSessionId) {
                getSessionPapers(activeSessionId).then((res) => {
                  if (res && res.length > 0) setPapers(res);
                });
                router.replace(`/research?id=${activeSessionId}`);
              }
            },
            onError: (err) => {
              setError(err);
              setIsStreaming(false);
            },
          });
        } catch (err: any) {
          setError(err.message || "Failed to start research");
          setIsStreaming(false);
        }
      };

      launch();

      return () => {
        if (cleanupRef.current) {
          cleanupRef.current();
        }
      };
    }
  }, [queryParam, formatParam, styleParam, demoParam, idParam, router]);

  const handleNewSearch = (newQuery: string, format: string, style: string, demo: boolean) => {
    const params = new URLSearchParams({
      q: newQuery,
      format,
      style,
      demo: demo ? "true" : "false",
    });
    router.push(`/research?${params.toString()}`);
  };

  const hasActiveContent = isStreaming || isComplete || Boolean(finalOutput) || Boolean(activeQuery);

  return (
    <div className="w-full max-w-7xl mx-auto px-margin-mobile lg:px-margin py-space-xl flex flex-col gap-space-xl">
      {/* 1. Top Search Capsule for Follow-ups or New Questions */}
      <div className="w-full max-w-3xl mx-auto">
        <SearchCapsule
          initialQuery=""
          onSearch={handleNewSearch}
          isLoading={isStreaming}
        />
      </div>

      {hasActiveContent ? (
        <>
          {/* 2. Topic Header Banner */}
          <section className="flex flex-col lg:flex-row lg:items-end justify-between gap-space-lg pt-space-sm border-b border-surface-container-high/30 pb-space-lg">
            <div className="flex flex-col gap-space-xs max-w-3xl">
              <div className="flex items-center gap-space-sm flex-wrap">
                <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-secondary-container/60 text-secondary-fixed font-label-ui text-label-ui">
                  <span className="w-1.5 h-1.5 rounded-full bg-secondary"></span>
                  {formatParam.toUpperCase()}
                </span>
              </div>

              <h1 className="font-headline-lg text-headline-lg text-on-surface tracking-tight mt-1">
                {activeQuery || "Research Workspace"}
              </h1>
            </div>

            <div className="flex items-center gap-space-xs">
              <Link
                href="/dashboard"
                className="px-space-md py-2 rounded-full bg-surface-container hover:bg-surface-container-high text-on-surface font-label-ui text-label-ui flex items-center gap-space-xs transition-colors border border-surface-container-high"
              >
                <ArrowLeft className="w-4 h-4" />
                <span>All Sessions</span>
              </Link>
            </div>
          </section>

          {/* 3. Main Two-Column Workspace Layout */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-gutter items-start">
            {/* Left Column (8 cols): Progress Stepper + Dossier View */}
            <div className="lg:col-span-8 flex flex-col gap-space-lg">
              <ExecutionStepper
                trace={trace}
                isStreaming={isStreaming}
                isComplete={isComplete}
                error={error}
              />

              <DossierViewer
                markdown={finalOutput}
                sessionId={sessionId}
                query={activeQuery}
                findings={findings}
                isStreaming={isStreaming && !isComplete}
              />
            </div>

            {/* Right Column (4 cols): Paper Explorer */}
            <div className="lg:col-span-4 flex flex-col gap-space-md">
              <PaperExplorer papers={papers} />
            </div>
          </div>
        </>
      ) : (
        /* Clean Idle State (When no query or session exists yet) */
        <div className="flex flex-col items-center justify-center p-space-xl rounded-xl bg-surface-container-low border border-surface-container-high/40 text-center my-space-lg">
          <div className="w-12 h-12 rounded-full bg-primary/10 text-primary flex items-center justify-center mb-space-md shadow-sm">
            <Sparkles className="w-6 h-6" />
          </div>
          <h2 className="font-headline-md text-headline-md text-on-surface">
            Ready for Deep Research
          </h2>
          <p className="font-body-md text-body-md text-on-surface-variant max-w-lg mt-space-xs leading-relaxed">
            Enter any topic or question in the search bar above to begin autonomous literature search, evidence synthesis, and citation generation.
          </p>

          <div className="flex items-center justify-center gap-space-xs flex-wrap mt-space-lg">
            <span className="font-label-ui text-label-ui text-outline mr-1">Try researching:</span>
            {[
              "Compare Redis and Memcached for session caching",
              "Attention mechanisms vs State Space Models",
              "KV cache compression and context rot in LLMs",
            ].map((suggestion, i) => (
              <button
                key={i}
                onClick={() => handleNewSearch(suggestion, "brief", "apa", false)}
                className="px-3.5 py-1.5 rounded-full bg-surface-container hover:bg-surface-container-high text-on-surface-variant hover:text-on-surface border border-surface-container-high/40 text-[12px] font-label-ui transition-all"
              >
                {suggestion}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default function ResearchWorkspacePage() {
  return (
    <Suspense
      fallback={
        <div className="flex items-center justify-center p-20 text-outline">
          <RefreshCw className="w-6 h-6 animate-spin mr-2 text-primary" />
          <span>Loading research workspace...</span>
        </div>
      }
    >
      <ResearchWorkspaceContent />
    </Suspense>
  );
}
