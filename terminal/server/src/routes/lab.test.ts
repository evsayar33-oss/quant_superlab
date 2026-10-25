import { describe, it, expect } from "vitest";
import express from "express";
import { labRouter } from "./lab.js";

async function call(url: string) {
  const app = express();
  app.use("/api/lab", labRouter);
  const srv = app.listen(0);
  const port = (srv.address() as any).port;
  try {
    return await fetch(`http://127.0.0.1:${port}${url}`);
  } finally {
    srv.close();
  }
}

describe("lab bridge", () => {
  it("lists reports and rejects unknown names", async () => {
    expect(await (await call("/api/lab/reports")).json()).toContain("assetbook");
    expect((await call("/api/lab/reports/../../etc/passwd")).status).toBe(404);
  });
});
