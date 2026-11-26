"use client";

import Link from "next/link";
import { ResearchSessionSummary } from "@/lib/api";
import { FolderOpen, Trash2, Calendar, CheckCircle2 } from "lucide-react";

interface SessionCardProps {
  session: ResearchSessionSummary;
  onDelete: (sessionId: string) => void;
}

export function SessionCard({ session, onDelete }: SessionCardProps) {
  const formattedDate = session.created_at
    ? new Date(session.created_at).toLocaleDateString(undefined, {
        month: "short",
        day: "numeric",
        year: "numeric",
      })
    : "Recent";

  return (
    <div className="group relative flex flex-col justify-between p-space-lg rounded-lg bg-surface-container-low hover:bg-surface-container border border-surface-container-high/40 transition-all duration-300 shadow-md hover:shadow-xl">
      <div className="flex flex-col gap-space-md">
        {/* Top Badges */}
        <div className="flex items-start justify-between gap-space-sm">
          <div className="flex flex-wrap items-center gap-1.5">
            <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full font-label-ui text-label-ui bg-secondary-container/30 text-secondary-fixed">
              <span className="w-1.5 h-1.5 rounded-full bg-secondary"></span>
              {session.output_format || "Brief"}
            </span>
            <span className="px-2 py-1 rounded-full font-label-ui text-label-ui bg-surface-container-high text-on-surface-variant">
              {session.finding_count} findings
            </span>
          </div>

          <div className="flex items-center gap-1 px-2 py-1 rounded-full bg-tertiary-container/20 text-tertiary font-label-ui text-label-ui">
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>Ready</span>
          </div>
        </div>

        {/* Content */}
        <div className="flex flex-col gap-space-xs">
          <div className="flex items-center gap-space-xs font-label-ui text-label-ui text-outline">
            <Calendar className="w-3.5 h-3.5" />
            <span>{formattedDate}</span>
          </div>

          <h2 className="font-headline-sm text-headline-sm text-on-surface group-hover:text-primary transition-colors line-clamp-2">
            {session.user_query}
          </h2>
        </div>
      </div>

      {/* Card Actions */}
      <div className="flex items-center justify-between gap-space-sm pt-space-lg mt-space-sm border-t border-surface-container-high/30">
        <div className="flex items-center gap-space-xs">
          <Link
            href={`/research?id=${session.session_id}`}
            className="inline-flex items-center gap-1.5 px-space-md py-1.5 rounded-full bg-primary text-on-primary font-title-md text-title-md shadow-md shadow-primary/20 hover:scale-[1.02] active:scale-[0.98] transition-all"
          >
            <FolderOpen className="w-4 h-4" />
            <span>Open Dossier</span>
          </Link>
        </div>

        <button
          onClick={() => onDelete(session.session_id)}
          className="w-8 h-8 rounded-full flex items-center justify-center text-outline hover:text-error hover:bg-error-container/20 transition-colors"
          title="Delete Research Session"
        >
          <Trash2 className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}
