"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ResearchSessionSummary, getResearchHistory, deleteResearchSession } from "@/lib/api";
import { SessionCard } from "@/components/SessionCard";
import { NewTopicModal } from "@/components/NewTopicModal";
import { Plus, Search, Layers, RefreshCw } from "lucide-react";

export default function DashboardPage() {
  const router = useRouter();
  const [sessions, setSessions] = useState<ResearchSessionSummary[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedTag, setSelectedTag] = useState("all");
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  const fetchHistory = () => {
    setIsLoading(true);
    getResearchHistory(60)
      .then((data) => {
        setSessions(data);
        setIsLoading(false);
      })
      .catch(() => setIsLoading(false));
  };

  useEffect(() => {
    fetchHistory();
  }, []);

  const handleDelete = async (sessionId: string) => {
    const ok = await deleteResearchSession(sessionId);
    if (ok) {
      setSessions((prev) => prev.filter((s) => s.session_id !== sessionId));
    }
  };

  const handleCreateTopic = (query: string, format: string) => {
    const params = new URLSearchParams({ q: query, format });
    router.push(`/research?${params.toString()}`);
  };

  // Filter topics by query and format tags
  const filteredSessions = sessions.filter((s) => {
    const matchesSearch =
      s.user_query.toLowerCase().includes(searchQuery.toLowerCase()) ||
      s.session_id.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesTag =
      selectedTag === "all" || s.output_format.toLowerCase() === selectedTag.toLowerCase();
    return matchesSearch && matchesTag;
  });

  return (
    <div className="w-full max-w-7xl mx-auto px-margin-mobile lg:px-margin py-space-xl flex flex-col gap-space-xl">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-space-lg">
        <div className="flex flex-col gap-space-xs max-w-2xl">
          <div className="flex items-center gap-space-sm">
            <span className="font-label-ui text-label-ui text-primary font-medium tracking-wide uppercase">
              Library
            </span>
          </div>
          <h1 className="font-headline-lg text-headline-lg text-on-surface tracking-tight">
            Research Library
          </h1>
          <p className="font-body-md text-body-md text-on-surface-variant">
            Your saved research topics, synthesis briefs, and deep dives.
          </p>
        </div>

        <div className="flex items-center gap-space-sm flex-wrap">
          <button
            onClick={() => setIsModalOpen(true)}
            className="group relative inline-flex items-center gap-space-xs px-space-lg py-2.5 rounded-full bg-primary-container text-on-primary font-title-md text-title-md shadow-lg shadow-primary-container/20 hover:scale-[1.02] active:scale-[0.98] transition-all"
          >
            <Plus className="w-5 h-5 transition-transform group-hover:rotate-90" />
            <span>New Research Topic</span>
          </button>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-space-md p-space-sm rounded-lg bg-surface-container-low border border-surface-container-high/40 shadow-sm">
        <div className="relative flex-1 min-w-[280px]">
          <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 text-outline w-4 h-4" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search research topics, summaries, and notes..."
            className="w-full bg-surface-container pl-10 pr-space-md py-2 rounded-full font-body-md text-body-md text-on-surface placeholder:text-outline focus:outline-none focus:bg-surface-container-high transition-colors"
          />
        </div>

        <div className="flex items-center gap-space-xs overflow-x-auto pb-1 lg:pb-0">
          {[
            { id: "all", label: "All Topics" },
            { id: "brief", label: "Briefs" },
            { id: "report", label: "Deep Dives" },
            { id: "comparison", label: "Comparisons" },
          ].map((tag) => (
            <button
              key={tag.id}
              onClick={() => setSelectedTag(tag.id)}
              className={`px-3.5 py-1.5 rounded-full font-label-ui text-label-ui transition-all ${selectedTag === tag.id
                  ? "bg-surface-container-highest text-on-surface font-semibold"
                  : "bg-surface-container text-on-surface-variant hover:text-on-surface hover:bg-surface-container-high"
                }`}
            >
              {tag.label}
            </button>
          ))}
        </div>
      </div>

      {/* Topics Grid */}
      {isLoading ? (
        <div className="flex items-center justify-center p-16 text-outline">
          <RefreshCw className="w-6 h-6 animate-spin mr-2 text-primary" />
          <span>Loading research library...</span>
        </div>
      ) : filteredSessions.length === 0 ? (
        <div className="flex flex-col items-center justify-center p-16 rounded-lg bg-surface-container-low border border-surface-container-high/40 text-center">
          <Layers className="w-10 h-10 text-outline mb-3" />
          <h3 className="font-headline-sm text-headline-sm text-on-surface">No Research Topics Found</h3>
          <p className="font-body-sm text-body-sm text-on-surface-variant mt-1 max-w-sm">
            {searchQuery
              ? `No topics match "${searchQuery}". Try a different keyword.`
              : "Start your first autonomous research inquiry."}
          </p>
          <button
            onClick={() => setIsModalOpen(true)}
            className="mt-space-md px-space-lg py-2 rounded-full bg-primary text-on-primary font-title-md text-title-md"
          >
            Create Research Topic
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-space-lg">
          {filteredSessions.map((session) => (
            <SessionCard
              key={session.session_id}
              session={session}
              onDelete={handleDelete}
            />
          ))}
        </div>
      )}

      {/* Sync Footer Badge */}
      <div className="relative w-full pt-space-md pb-space-xs">
        <div className="flex flex-col sm:flex-row items-center justify-between gap-space-md p-space-md rounded-lg bg-surface-container-low border border-surface-container-high/30 shadow-sm">
          <div className="flex items-center gap-space-sm">
            <div className="w-2.5 h-2.5 rounded-full bg-tertiary"></div>
            <span className="font-body-sm text-body-sm text-on-surface-variant">
              Workspace synced with local SQLite database ({sessions.length} sessions stored)
            </span>
          </div>
          <div className="flex items-center gap-space-md text-on-surface-variant font-label-ui text-label-ui">
            <span>Private</span>
            <span>·</span>
            <span>Auto-Saved</span>
          </div>
        </div>
      </div>

      {/* New Topic Modal */}
      <NewTopicModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onSubmit={handleCreateTopic}
      />
    </div>
  );
}
