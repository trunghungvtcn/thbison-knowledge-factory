import http from "node:http";
import { mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";

const root = resolve(import.meta.dirname, "../../modules/vendor1");
process.env.THBISON_ROOT = root;
process.env.THBISON_DATA_DIR ||= mkdtempSync(join(tmpdir(), "thbison-v1-"));
process.env.THBISON_MODE = "MOCK";
process.env.THBISON_CLOCK_NOW ||= "2030-01-01T00:00:00Z";
const { handlePlanningHttp } = await import("../../modules/vendor1/src/planning/http.ts");
const port = Number(process.env.PORT || 18081);

http.createServer(async (req, res) => {
  const chunks = [];
  for await (const chunk of req) chunks.push(chunk);
  const body = chunks.length ? Buffer.concat(chunks) : undefined;
  const headers = new Headers();
  for (const [key, value] of Object.entries(req.headers)) if (value) headers.set(key, Array.isArray(value) ? value.join(",") : value);
  try {
    const response = await handlePlanningHttp(new Request(`http://127.0.0.1:${port}${req.url}`, { method: req.method, headers, body }));
    res.writeHead(response.status, Object.fromEntries(response.headers.entries()));
    res.end(Buffer.from(await response.arrayBuffer()));
  } catch (error) {
    const raw = JSON.stringify({ code: "INTEGRATION_ERROR", message: String(error?.message || error) });
    res.writeHead(500, { "content-type": "application/json", "content-length": Buffer.byteLength(raw) });
    res.end(raw);
  }
}).listen(port, "127.0.0.1", () => console.log(`V1_PLANNING_LISTENING:${port}`));
