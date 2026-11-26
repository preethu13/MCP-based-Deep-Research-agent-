"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Download, Copy, Check } from "lucide-react";
import { useState } from "react";

interface DossierViewerProps {
  markdown: string;
  sessionId: string;
  query?: string;
  findings?: unknown[];
  isStreaming?: boolean;
}

export function DossierViewer({ markdown, sessionId, isStreaming }: DossierViewerProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(markdown);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownload = () => {
    const blob = new Blob([markdown], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${sessionId || "research"}.md`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  return (
    <article className="bg-surface-container rounded-2xl p-6 sm:p-8 shadow-xl border border-surface-container-high/60 flex flex-col gap-6">
      {/* Dossier Header - Clean, No Icons */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-surface-container-high/40 pb-5">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-xl sm:text-2xl font-bold text-on-surface tracking-tight">
              The Dossier
            </h2>
            {isStreaming && (
              <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-primary/20 text-primary-fixed border border-primary/30 text-[10px] font-mono tracking-wider animate-pulse">
                <span className="w-1.5 h-1.5 rounded-full bg-primary animate-ping" />
                STREAMING
              </span>
            )}
          </div>
          <p className="text-xs sm:text-sm text-on-surface-variant mt-0.5">
            Comprehensive Grounded Report
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleCopy}
            className="px-4 py-1.5 rounded-full bg-surface-container-high hover:bg-surface-bright text-on-surface font-label-ui text-xs flex items-center gap-1.5 transition-colors border border-surface-container-high shadow-sm"
          >
            {copied ? <Check className="w-3.5 h-3.5 text-tertiary" /> : <Copy className="w-3.5 h-3.5" />}
            <span>{copied ? "Copied" : "Copy"}</span>
          </button>

          <button
            onClick={handleDownload}
            className="px-4 py-1.5 rounded-full bg-primary text-on-primary font-title-md text-xs font-semibold flex items-center gap-1.5 shadow-md shadow-primary/20 hover:scale-[1.02] active:scale-[0.98] transition-all"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Download .MD</span>
          </button>
        </div>
      </div>

      {/* Styled Markdown Body with Custom Components */}
      <div className="w-full text-on-surface">
        <ReactMarkdown
          remarkPlugins={[remarkGfm]}
          components={{
            h1: ({ children }) => (
              <h1 className="text-2xl sm:text-3xl font-bold text-on-surface tracking-tight mt-6 mb-3 border-b border-surface-container-high/50 pb-2">
                {children}
              </h1>
            ),
            h2: ({ children }) => (
              <h2 className="text-lg sm:text-xl font-bold text-on-surface tracking-tight mt-6 mb-3 text-primary-fixed">
                {children}
              </h2>
            ),
            h3: ({ children }) => (
              <h3 className="text-base sm:text-lg font-semibold text-tertiary mt-5 mb-2">
                {children}
              </h3>
            ),
            p: ({ children }) => (
              <p className="text-sm sm:text-base text-on-surface/90 leading-relaxed my-3 font-normal">
                {children}
              </p>
            ),
            ul: ({ children }) => (
              <ul className="list-disc list-outside pl-6 space-y-2.5 my-3 text-on-surface/90">
                {children}
              </ul>
            ),
            ol: ({ children }) => (
              <ol className="list-decimal list-outside pl-6 space-y-2.5 my-3 text-on-surface/90">
                {children}
              </ol>
            ),
            li: ({ children }) => (
              <li className="text-sm sm:text-base leading-relaxed pl-1 marker:text-primary">
                {children}
              </li>
            ),
            blockquote: ({ children }) => (
              <blockquote className="border-l-4 border-primary/70 bg-surface-container-low/80 rounded-r-lg px-4 py-3 my-4 text-on-surface-variant italic text-sm sm:text-base leading-relaxed">
                {children}
              </blockquote>
            ),
            a: ({ href, children }) => (
              <a
                href={href}
                target="_blank"
                rel="noopener noreferrer"
                className="text-tertiary hover:text-primary hover:underline font-medium transition-colors"
              >
                {children}
              </a>
            ),
            strong: ({ children }) => (
              <strong className="text-on-surface font-semibold">
                {children}
              </strong>
            ),
            hr: () => <hr className="border-surface-container-high/60 my-6" />,
            table: ({ children }) => (
              <div className="overflow-x-auto my-5 rounded-xl border border-surface-container-high/60 bg-surface-container-low/50">
                <table className="w-full text-left text-sm text-on-surface border-collapse">
                  {children}
                </table>
              </div>
            ),
            th: ({ children }) => (
              <th className="bg-surface-container-highest px-4 py-2.5 font-semibold text-on-surface border-b border-surface-container-high/60 text-xs uppercase tracking-wider">
                {children}
              </th>
            ),
            td: ({ children }) => (
              <td className="px-4 py-2.5 border-b border-surface-container-high/30 text-on-surface/90 text-sm">
                {children}
              </td>
            ),
            code: ({ children }) => (
              <code className="px-1.5 py-0.5 rounded bg-surface-container-highest text-secondary-fixed font-mono text-xs">
                {children}
              </code>
            ),
          }}
        >
          {markdown || "_No report text generated yet._"}
        </ReactMarkdown>
        {isStreaming && markdown && (
          <span className="inline-block w-2 h-4 ml-1 bg-primary animate-pulse align-middle rounded-sm shadow-[0_0_8px_rgba(99,102,241,0.8)]" />
        )}
      </div>
    </article>
  );
}
