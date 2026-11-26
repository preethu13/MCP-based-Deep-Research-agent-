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
} from "@/lib/api";
import { ExecutionStepper } from "@/components/ExecutionStepper";
import { DossierViewer } from "@/components/DossierViewer";
import { SearchCapsule } from "@/components/SearchCapsule";
import { RelatedQuestions } from "@/components/RelatedQuestions";
import {
  Download,
  Share2,
  FileText,
  Code,
  RefreshCw,
} from "lucide-react";

function ResearchWorkspaceContent() {
  const searchParams = useSearchParams();
  const router = useRouter();

  const queryParam = searchParams.get("q") || searchParams.get("query") || "";
  const idParam = searchParams.get("id") || "";
  const formatParam = searchParams.get("format") || "brief";
  const styleParam = searchParams.get("style") || "apa";
  const demoParam = searchParams.get("demo") === "true";

  const defaultTopic = "How AI Models Maintain Context Over Long Conversations";

  const [activeQuery, setActiveQuery] = useState(queryParam || defaultTopic);
  const [sessionId, setSessionId] = useState(idParam);
  const [trace, setTrace] = useState<TraceEvent[]>([]);
  const [finalOutput, setFinalOutput] = useState<string>("");
  const [findings, setFindings] = useState<any[]>([]);
  const [papers, setPapers] = useState<PaperCitation[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [isComplete, setIsComplete] = useState(Boolean(idParam));
  const [error, setError] = useState<string | null>(null);

  // Button feedback states
  const [notesDownloaded, setNotesDownloaded] = useState(false);
  const [linkCopied, setLinkCopied] = useState(false);

  const cleanupRef = useRef<(() => void) | null>(null);

  // 1. Initial / Idle state
  useEffect(() => {
    if (!idParam && !queryParam) {
      setActiveQuery(defaultTopic);
      setIsComplete(true);
      setIsStreaming(false);
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
          if (session.query) setActiveQuery(session.query);
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

  const handleNewSearch = (newQuery: string, format = "brief", style = "apa", demo = false) => {
    const params = new URLSearchParams({
      q: newQuery,
      format,
      style,
      demo: demo ? "true" : "false",
    });
    router.push(`/research?${params.toString()}`);
  };

  // Action Button Handlers
  const handleDownloadNotes = () => {
    const content = finalOutput || `# Research Notes — ${activeQuery}\n\n*Generated by Stitch MCP*\n`;
    const blob = new Blob([content], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${sessionId || "research"}-notes.md`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
    setNotesDownloaded(true);
    setTimeout(() => setNotesDownloaded(false), 2000);
  };

  const handleShare = () => {
    if (typeof window !== "undefined") {
      navigator.clipboard.writeText(window.location.href);
      setLinkCopied(true);
      setTimeout(() => setLinkCopied(false), 2000);
    }
  };

  const handleExportPdf = () => {
    if (typeof window !== "undefined") {
      window.print();
    }
  };

  const handleExportMarkdown = () => {
    const content = finalOutput || `# ${activeQuery}\n\n*Comprehensive Grounded Report*\n`;
    const blob = new Blob([content], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${sessionId || "research-report"}.md`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="w-full max-w-7xl mx-auto px-margin-mobile lg:px-margin py-space-xl flex flex-col gap-space-xl">
      {/* 1. Floating Glassmorphic Pill Search Bar */}
      <SearchCapsule
        initialQuery=""
        onSearch={handleNewSearch}
        isLoading={isStreaming}
        placeholder="Ask a follow-up question or start a new topic..."
      />

      {/* 2. Active Research Topic Header & Tactile Action Row */}
      <section className="flex flex-col lg:flex-row lg:items-end justify-between gap-space-lg pt-space-sm border-b border-surface-container-high/30 pb-space-lg">
        <div className="flex flex-col gap-space-sm max-w-3xl">
          <div className="flex items-center gap-space-sm">
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-secondary-container/60 text-on-secondary-container font-label-ui text-label-ui border border-secondary/20">
              <span className="w-1.5 h-1.5 rounded-full bg-tertiary animate-pulse" />
              Deep Dive
            </span>
            <span className="font-body-sm text-body-sm text-on-surface-variant">
              Active Research Workspace
            </span>
            {sessionId && (
              <span className="font-label-mono-sm text-[11px] text-outline">
                · {sessionId}
              </span>
            )}
          </div>

          <h1 className="font-headline-lg text-headline-lg text-on-surface tracking-tight">
            {activeQuery}
          </h1>
        </div>

        {/* Tactile Action Pill Buttons with neon hover glows and micro-interactions */}
        <div className="flex items-center gap-space-sm shrink-0 flex-wrap">
          {/* Download Notes */}
          <button
            onClick={handleDownloadNotes}
            type="button"
            title="Download Markdown notes"
            className="group px-space-md py-2 rounded-full bg-surface-container hover:bg-surface-container-high text-on-surface font-label-ui text-label-ui flex items-center gap-space-xs transition-all duration-200 border border-surface-container-high/40 hover:border-primary/50 shadow-sm hover:shadow-[0_0_20px_-4px_rgba(192,193,255,0.35)] hover:-translate-y-0.5 active:scale-95 cursor-pointer"
          >
            <Download className="w-4 h-4 text-primary transition-transform duration-200 group-hover:-translate-y-0.5 group-hover:scale-110" />
            <span className="transition-colors group-hover:text-primary">
              {notesDownloaded ? "Notes Saved" : "Download Notes"}
            </span>
          </button>

          {/* Share */}
          <button
            onClick={handleShare}
            type="button"
            title="Copy link to workspace"
            className="group px-space-md py-2 rounded-full bg-surface-container hover:bg-surface-container-high text-on-surface font-label-ui text-label-ui flex items-center gap-space-xs transition-all duration-200 border border-surface-container-high/40 hover:border-tertiary/50 shadow-sm hover:shadow-[0_0_20px_-4px_rgba(123,208,255,0.35)] hover:-translate-y-0.5 active:scale-95 cursor-pointer"
          >
            <Share2 className="w-4 h-4 text-tertiary transition-transform duration-200 group-hover:scale-110 group-hover:rotate-12" />
            <span className="transition-colors group-hover:text-tertiary">
              {linkCopied ? "Link Copied" : "Share"}
            </span>
          </button>

          {/* Export PDF */}
          <button
            onClick={handleExportPdf}
            type="button"
            title="Export formatted PDF report"
            className="group px-space-md py-2 rounded-full bg-surface-container hover:bg-surface-container-high text-on-surface font-label-ui text-label-ui flex items-center gap-space-xs transition-all duration-200 border border-surface-container-high/40 hover:border-primary/50 shadow-sm hover:shadow-[0_0_20px_-4px_rgba(192,193,255,0.35)] hover:-translate-y-0.5 active:scale-95 cursor-pointer"
          >
            <FileText className="w-4 h-4 text-primary transition-transform duration-200 group-hover:scale-110 group-hover:-rotate-6" />
            <span className="transition-colors group-hover:text-primary">
              Export PDF
            </span>
          </button>

          {/* Export Markdown */}
          <button
            onClick={handleExportMarkdown}
            type="button"
            title="Export raw Markdown documentation"
            className="group px-space-md py-2 rounded-full bg-surface-container hover:bg-surface-container-high text-on-surface font-label-ui text-label-ui flex items-center gap-space-xs transition-all duration-200 border border-surface-container-high/40 hover:border-secondary/50 shadow-sm hover:shadow-[0_0_20px_-4px_rgba(208,188,255,0.35)] hover:-translate-y-0.5 active:scale-95 cursor-pointer"
          >
            <Code className="w-4 h-4 text-secondary transition-transform duration-200 group-hover:scale-110 group-hover:translate-x-0.5" />
            <span className="transition-colors group-hover:text-secondary">
              Export Markdown
            </span>
          </button>
        </div>
      </section>

      {/* 3. Status Strip: Thin (h-1.5) Glowing Gradient Progress Bar */}
      <ExecutionStepper
        trace={trace}
        isStreaming={isStreaming}
        isComplete={isComplete}
        error={error}
      />

      {/* 4. The Dossier: Comprehensive Grounded Report */}
      <div className="w-full">
        <DossierViewer
          markdown={finalOutput}
          sessionId={sessionId}
          query={activeQuery}
          findings={findings}
          isStreaming={isStreaming}
        />
      </div>

      {/* 5. Related Explorations & Questions Section below the Dossier */}
      <RelatedQuestions
        query={activeQuery}
        onSelectPrompt={(prompt) => handleNewSearch(prompt, "brief", "apa", false)}
      />
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
