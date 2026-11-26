/**
 * TypeScript API service layer for communicating with the FastAPI research backend.
 */

export interface TraceEvent {
  step: number;
  node: string;
  tool?: string;
  title: string;
  detail?: string;
  status: "ok" | "warn" | "error";
}

export interface ResearchProgressPayload {
  session_id: string;
  query: string;
  step: number;
  trace: TraceEvent[];
  sub_questions: string[];
  warnings: string[];
  has_final: boolean;
  final_output?: string;
  findings: any[];
  papers?: PaperCitation[];
  metrics: Record<string, any>;
}

export interface ResearchSessionSummary {
  session_id: string;
  user_query: string;
  created_at: string;
  output_format: string;
  status: string;
  finding_count: number;
}

export interface PaperCitation {
  citation_id: number;
  title: string;
  author: string;
  publisher: string;
  url: string;
  formatted_apa?: string;
  formatted_mla?: string;
  sub_question?: string;
}

export interface MemoryRecallHit {
  id: string;
  content: string;
  metadata?: Record<string, any>;
  similarity_score?: number;
}

export interface HealthStatus {
  status: string;
  llm_reachable: boolean;
  llm_message: string;
  chat_model: string;
  provider: string;
  db_path: string;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

export async function checkHealth(demo = false): Promise<HealthStatus> {
  const res = await fetch(`${API_BASE}/api/health?demo=${demo}`);
  if (!res.ok) throw new Error("Health check failed");
  return res.json();
}

export async function startResearch(
  query: string,
  output_format = "brief",
  citation_style = "apa",
  demo = false,
  force_refresh = false
): Promise<{ session_id: string; stream_url: string }> {
  const res = await fetch(`${API_BASE}/api/research`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      query,
      output_format,
      citation_style,
      demo,
      force_refresh,
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Failed to initialize research" }));
    throw new Error(err.detail || "Failed to initialize research");
  }
  return res.json();
}

export async function getResearchHistory(limit = 50): Promise<ResearchSessionSummary[]> {
  const res = await fetch(`${API_BASE}/api/research/history?limit=${limit}`, {
    cache: "no-store",
  });
  if (!res.ok) throw new Error("Failed to fetch research history");
  return res.json();
}

export async function getResearchSession(sessionId: string, style = "apa") {
  const res = await fetch(`${API_BASE}/api/research/${sessionId}?style=${style}`, {
    cache: "no-store",
  });
  if (!res.ok) throw new Error("Failed to fetch research session");
  return res.json();
}

export async function deleteResearchSession(sessionId: string): Promise<boolean> {
  const res = await fetch(`${API_BASE}/api/research/${sessionId}`, {
    method: "DELETE",
  });
  return res.ok;
}

export async function getSessionPapers(sessionId: string): Promise<PaperCitation[]> {
  const res = await fetch(`${API_BASE}/api/research/${sessionId}/papers`, {
    cache: "no-store",
  });
  if (!res.ok) return [];
  return res.json();
}

export async function recallMemory(query: string, top_k = 5, demo = false): Promise<MemoryRecallHit[]> {
  const res = await fetch(
    `${API_BASE}/api/memory/recall?query=${encodeURIComponent(query)}&top_k=${top_k}&demo=${demo}`,
    { cache: "no-store" }
  );
  if (!res.ok) return [];
  return res.json();
}

/**
 * Connect to FastAPI SSE stream and emit events.
 */
export function streamResearchSession({
  sessionId,
  query,
  outputFormat = "brief",
  citationStyle = "apa",
  demo = false,
  forceRefresh = false,
  onToken,
  onProgress,
  onComplete,
  onError,
}: {
  sessionId: string;
  query: string;
  outputFormat?: string;
  citationStyle?: string;
  demo?: boolean;
  forceRefresh?: boolean;
  onToken?: (token: string, accumulated?: string) => void;
  onProgress: (data: ResearchProgressPayload) => void;
  onComplete: (data: { session_id: string; status: string }) => void;
  onError: (error: string) => void;
}): () => void {
  const url = `${API_BASE}/api/research/${sessionId}/stream?query=${encodeURIComponent(
    query
  )}&output_format=${outputFormat}&citation_style=${citationStyle}&demo=${demo}&force_refresh=${forceRefresh}`;

  const eventSource = new EventSource(url);

  eventSource.addEventListener("token", (e) => {
    try {
      const parsed = JSON.parse(e.data);
      if (parsed.token && onToken) {
        onToken(parsed.token, parsed.accumulated);
      }
    } catch (err) {
      console.error("Failed to parse token event", err);
    }
  });

  eventSource.addEventListener("progress", (e) => {
    try {
      const parsed = JSON.parse(e.data);
      onProgress(parsed);
    } catch (err) {
      console.error("Failed to parse progress event", err);
    }
  });

  eventSource.addEventListener("complete", (e) => {
    try {
      const parsed = JSON.parse(e.data);
      onComplete(parsed);
    } catch (err) {
      console.error("Failed to parse complete event", err);
    }
    eventSource.close();
  });

  eventSource.addEventListener("error", (e: any) => {
    try {
      if (e.data) {
        const parsed = JSON.parse(e.data);
        onError(parsed.error || "Streaming error encountered");
      } else {
        onError("Connection to research stream interrupted");
      }
    } catch {
      onError("Connection to research stream interrupted");
    }
    eventSource.close();
  });

  // Return unsubscribe/close function
  return () => {
    eventSource.close();
  };
}
