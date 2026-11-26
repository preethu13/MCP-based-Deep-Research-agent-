"use client";

import { PaperCitation } from "@/lib/api";
import { ExternalLink, BookOpen, Layers } from "lucide-react";

interface PaperExplorerProps {
  papers: PaperCitation[];
}

export function PaperExplorer({ papers }: PaperExplorerProps) {
  if (!papers || papers.length === 0) {
    return (
      <div className="p-space-lg rounded-lg bg-surface-container-low border border-surface-container-high/40 text-center">
        <BookOpen className="w-6 h-6 text-outline mx-auto mb-2" />
        <div className="font-title-md text-title-md text-on-surface">No Papers Logged</div>
        <div className="font-body-sm text-body-sm text-on-surface-variant mt-1">
          Academic sources discovered during research will appear here.
        </div>
      </div>
    );
  }

  return (
    <div className="p-space-lg rounded-lg bg-surface-container-low border border-surface-container-high/40 shadow-sm flex flex-col gap-space-md">
      <div className="flex items-center justify-between border-b border-surface-container-high/30 pb-2">
        <div className="flex items-center gap-2">
          <Layers className="w-4 h-4 text-tertiary" />
          <span className="font-title-md text-title-md text-on-surface">Sources & Reading</span>
        </div>
        <span className="px-space-sm py-0.5 rounded-full bg-surface-container font-label-ui text-label-ui text-outline">
          {papers.length} references
        </span>
      </div>

      <div className="space-y-space-sm max-h-[540px] overflow-y-auto pr-1">
        {papers.map((paper, idx) => (
          <a
            key={idx}
            href={paper.url}
            target="_blank"
            rel="noopener noreferrer"
            className="block p-space-sm rounded-DEFAULT bg-surface-container hover:bg-surface-container-high border border-surface-container-high/40 transition-colors group"
          >
            <div className="flex items-center justify-between font-label-ui text-label-ui text-tertiary mb-1">
              <span className="truncate pr-2 font-medium">{paper.title}</span>
              <ExternalLink className="w-3.5 h-3.5 group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-transform shrink-0" />
            </div>

            <div className="text-[12px] text-on-surface-variant line-clamp-1">
              {paper.author || "Unknown authors"} · {paper.publisher}
            </div>

            {paper.formatted_apa && (
              <div className="mt-2 pt-2 border-t border-surface-container-high/40 text-[11px] font-label-mono-sm text-outline line-clamp-2">
                {paper.formatted_apa}
              </div>
            )}
          </a>
        ))}
      </div>
    </div>
  );
}
