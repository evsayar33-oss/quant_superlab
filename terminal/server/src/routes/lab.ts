import { Router } from "express";
import { readFile, readdir } from "node:fs/promises";
import path from "node:path";

// Read-only bridge to the research lab in the same repo (quant_superlab root).
// Bots act only on verdict ACCEPT in decisions/registry.json; this route only SHOWS it.
const ROOT = process.env.LAB_ROOT ?? path.resolve(process.cwd(), "..", "..");
const DEC = path.join(ROOT, "decisions");
const REPORTS: Record<string, string> = {
  synthesis: "synthesis/report.md",
  assetbook: "assetbook/report.md",
  persistence: "assetbook/persistence.md",
  coreassets: "coreassets/report.md",
  mlbook: "mlbook/report.md",
  mega: "mega/report.md",
  watch: "watch/OZET.md",
};

export const labRouter = Router();

labRouter.get("/registry", async (_req, res) => {
  try {
    const reg = JSON.parse(await readFile(path.join(DEC, "registry.json"), "utf8"));
    const rows = Object.entries(reg.hypotheses ?? {}).map(([id, h]: [string, any]) => ({
      id, verdict: h.verdict, strategy: h.strategy, universe: h.universe, timeframe: h.timeframe,
      reasons: h.reasons, oos: h.oos ? { years: h.oos.years, cagr: h.oos.cagr, sharpe: h.oos.sharpe, max_dd: h.oos.max_dd } : null,
      live: h.live ?? null,
    }));
    res.json({ updated: reg.updated, accepted: rows.filter((r) => r.verdict === "ACCEPT").map((r) => r.id), rows });
  } catch (e) {
    res.status(404).json({ error: "registry not found", detail: String(e) });
  }
});

labRouter.get("/reports", (_req, res) => res.json(Object.keys(REPORTS)));

labRouter.get("/reports/:name", async (req, res) => {
  const rel = REPORTS[req.params.name];
  if (!rel) return res.status(404).json({ error: "unknown report" });
  try {
    res.type("text/markdown").send(await readFile(path.join(DEC, rel), "utf8"));
  } catch {
    res.status(404).json({ error: "report not generated yet" });
  }
});

labRouter.get("/live", async (_req, res) => {
  try {
    const files = (await readdir(path.join(DEC, "live"))).filter((f) => f.endsWith(".csv"));
    const out: Record<string, string[]> = {};
    for (const f of files) {
      const lines = (await readFile(path.join(DEC, "live", f), "utf8")).trim().split("\n");
      out[f.replace(".csv", "")] = lines.slice(-30);
    }
    res.json(out);
  } catch {
    res.json({});
  }
});
