import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import type {
  Finding,
  SpecifyResponse,
  TraceEntry,
} from "../types/specsmith";

export function findingKey(finding: Finding, index: number): string {
  if (finding.kind === "rule") {
    return `rule:${index}:${finding.rule_id}:${finding.target_field ?? ""}`;
  }
  return `critique:${index}:${finding.critique_prompt_id}:${finding.target_field ?? ""}`;
}

export function buildLinkMap(
  response: Pick<SpecifyResponse, "spec" | "trace">,
): Map<string, string> {
  const map = new Map<string, string>();
  const entries = response.trace?.entries ?? [];
  const findings = response.spec?.findings ?? [];

  findings.forEach((finding, idx) => {
    let entry: TraceEntry | undefined;
    if (finding.kind === "critique") {
      entry = entries.find((e) =>
        e.prompts.some((p) => p.prompt_id === finding.critique_prompt_id),
      );
    } else {
      const node = finding.produced_by_node;
      if (node) entry = entries.find((e) => e.node === node);
    }
    if (entry) map.set(findingKey(finding, idx), entry.entry_id);
  });

  return map;
}

type LinkState = {
  linkMap: Map<string, string>;
  hoveredFinding: string | null;
  hoveredEntry: string | null;
  pinnedFinding: string | null;
  pinnedEntry: string | null;
  setHoveredFinding: (key: string | null) => void;
  setHoveredEntry: (entryId: string | null) => void;
  togglePinnedFinding: (key: string) => void;
  togglePinnedEntry: (entryId: string) => void;
  clearPinned: () => void;
  /** Returns the trace entry id that this finding links to, if any. */
  entryForFinding: (key: string) => string | undefined;
  /** Returns true if this finding should currently appear linked. */
  findingIsLinked: (key: string) => boolean;
  /** Returns true if this entry should currently appear linked. */
  entryIsLinked: (entryId: string) => boolean;
  /** How many findings are linked to a given trace entry. */
  findingCountForEntry: (entryId: string) => number;
};

const LinkContext = createContext<LinkState | null>(null);

export function LinkProvider({
  response,
  children,
}: {
  response: Pick<SpecifyResponse, "spec" | "trace"> | null;
  children: ReactNode;
}) {
  const linkMap = useMemo(
    () => (response ? buildLinkMap(response) : new Map<string, string>()),
    [response],
  );

  const [hoveredFinding, setHoveredFinding] = useState<string | null>(null);
  const [hoveredEntry, setHoveredEntry] = useState<string | null>(null);
  const [pinnedFinding, setPinnedFinding] = useState<string | null>(null);
  const [pinnedEntry, setPinnedEntry] = useState<string | null>(null);

  useEffect(() => {
    setHoveredFinding(null);
    setHoveredEntry(null);
    setPinnedFinding(null);
    setPinnedEntry(null);
  }, [response]);

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") {
        setPinnedFinding(null);
        setPinnedEntry(null);
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const togglePinnedFinding = useCallback((key: string) => {
    setPinnedFinding((prev) => (prev === key ? null : key));
    setPinnedEntry(null);
  }, []);

  const togglePinnedEntry = useCallback((entryId: string) => {
    setPinnedEntry((prev) => (prev === entryId ? null : entryId));
    setPinnedFinding(null);
  }, []);

  const clearPinned = useCallback(() => {
    setPinnedFinding(null);
    setPinnedEntry(null);
  }, []);

  const entryForFinding = useCallback(
    (key: string) => linkMap.get(key),
    [linkMap],
  );

  const reverseMap = useMemo(() => {
    const m = new Map<string, Set<string>>();
    for (const [findingKey_, entryId] of linkMap.entries()) {
      const set = m.get(entryId) ?? new Set<string>();
      set.add(findingKey_);
      m.set(entryId, set);
    }
    return m;
  }, [linkMap]);

  const findingIsLinked = useCallback(
    (key: string) => {
      if (pinnedFinding === key) return true;
      if (hoveredFinding === key) return true;
      const entryId = linkMap.get(key);
      if (!entryId) return false;
      if (pinnedEntry === entryId) return true;
      if (hoveredEntry === entryId) return true;
      return false;
    },
    [hoveredEntry, hoveredFinding, linkMap, pinnedEntry, pinnedFinding],
  );

  const entryIsLinked = useCallback(
    (entryId: string) => {
      if (pinnedEntry === entryId) return true;
      if (hoveredEntry === entryId) return true;
      const findings = reverseMap.get(entryId);
      if (!findings) return false;
      if (pinnedFinding && findings.has(pinnedFinding)) return true;
      if (hoveredFinding && findings.has(hoveredFinding)) return true;
      return false;
    },
    [hoveredEntry, hoveredFinding, pinnedEntry, pinnedFinding, reverseMap],
  );

  const findingCountForEntry = useCallback(
    (entryId: string) => reverseMap.get(entryId)?.size ?? 0,
    [reverseMap],
  );

  const value: LinkState = {
    linkMap,
    hoveredFinding,
    hoveredEntry,
    pinnedFinding,
    pinnedEntry,
    setHoveredFinding,
    setHoveredEntry,
    togglePinnedFinding,
    togglePinnedEntry,
    clearPinned,
    entryForFinding,
    findingIsLinked,
    entryIsLinked,
    findingCountForEntry,
  };

  return <LinkContext.Provider value={value}>{children}</LinkContext.Provider>;
}

export function useLink(): LinkState {
  const ctx = useContext(LinkContext);
  if (!ctx) throw new Error("useLink must be used inside LinkProvider");
  return ctx;
}
