"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { apiGet } from "../../lib/api";

type Row = {
  id: string; verdict: string; strategy?: string; universe?: string; timeframe?: string; reasons?: string[];
  oos: { years: number; cagr: number; sharpe: number; max_dd: number } | null;
};
type Registry = { updated: string; accepted: string[]; rows: Row[] };

const pct = (x?: number | null) => (x == null ? "—" : `${(x * 100).toFixed(1)}%`);
const VERDICT_CLASS: Record<string, string> = { ACCEPT: "up", WATCH: "dim", REJECT: "down", DEGRADED: "down" };

// Research lab view: the decision registry (bots act only on ACCEPT) and the study reports.
export default function LabWidget() {
  const [tab, setTab] = useState<"registry" | string>("registry");
  const [only, setOnly] = useState<"all" | "ACCEPT" | "WATCH">("all");
  const reg = useQuery({ queryKey: ["lab-registry"], queryFn: () => apiGet<Registry>("/api/lab/registry"), refetchInterval: 60_000 });
  const reports = useQuery({ queryKey: ["lab-reports"], queryFn: () => apiGet<string[]>("/api/lab/reports") });
  const md = useQuery({
    queryKey: ["lab-report", tab],
    enabled: tab !== "registry",
    queryFn: async () => (await fetch(`/api/lab/reports/${tab}`)).text(),
  });

  return (
    <div className="flex flex-col h-full">
      <div className="flex flex-wrap gap-1 p-1">
        <button className={`term-btn ${tab === "registry" ? "active" : ""}`} onClick={() => setTab("registry")}>KARARLAR</button>
        {(reports.data ?? []).map((r) => (
          <button key={r} className={`term-btn ${tab === r ? "active" : ""}`} onClick={() => setTab(r)}>{r.toUpperCase()}</button>
        ))}
      </div>
      {tab === "registry" ? (
        reg.error ? <div className="p-2 down">Error: {(reg.error as Error).message}</div> :
        !reg.data ? <div className="p-2 dim">Loading lab registry…</div> : (
          <div className="overflow-auto">
            <div className="flex gap-1 p-1 items-center">
              {(["all", "ACCEPT", "WATCH"] as const).map((v) => (
                <button key={v} className={`term-btn ${only === v ? "active" : ""}`} onClick={() => setOnly(v)}>{v}</button>
              ))}
              <span className="dim ml-2">ACCEPT: {reg.data.accepted.join(", ") || "—"} · {reg.data.updated?.slice(0, 10)}</span>
            </div>
            <table className="w-full text-xs">
              <thead><tr className="dim"><th>ID</th><th>Karar</th><th>Strateji</th><th>Evren</th><th>TF</th><th>OOS yıl</th><th>Yıllık</th><th>Sharpe</th><th>Maks DD</th></tr></thead>
              <tbody>
                {reg.data.rows.filter((r) => only === "all" || r.verdict === only).map((r) => (
                  <tr key={r.id} title={(r.reasons ?? []).join("\n")}>
                    <td>{r.id}</td><td className={VERDICT_CLASS[r.verdict] ?? ""}>{r.verdict}</td><td>{r.strategy}</td>
                    <td>{r.universe}</td><td>{r.timeframe}</td><td>{r.oos?.years?.toFixed(1) ?? "—"}</td>
                    <td>{pct(r.oos?.cagr)}</td><td>{r.oos?.sharpe?.toFixed(2) ?? "—"}</td><td>{pct(r.oos?.max_dd)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )
      ) : (
        <pre className="p-2 text-xs whitespace-pre-wrap overflow-auto">{md.data ?? "Loading…"}</pre>
      )}
    </div>
  );
}
