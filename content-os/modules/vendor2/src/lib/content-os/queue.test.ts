import assert from "node:assert/strict";
import { test } from "node:test";
import { createDeferredPort, registerProcessor, runProcessor, setQueuePort, getQueue } from "./queue.ts";

test("queue port dispatches without awaiting processor (Vendor 3 contract)", async () => {
  let started = false;
  let finished = false;
  registerProcessor(async () => {
    started = true;
    await new Promise((r) => setTimeout(r, 30));
    finished = true;
  });
  const port = createDeferredPort();
  setQueuePort(port);
  port.dispatch("job-1", "content");
  assert.equal(finished, false);
  await port.drain();
  assert.equal(started, true);
  assert.equal(finished, true);
  assert.equal(getQueue(), port);
});

test("Vendor 3 can replace the port without changing processors", async () => {
  const seen: string[] = [];
  registerProcessor(async (id) => {
    seen.push(id);
  });
  const custom = {
    dispatch(jobId: string) {
      void runProcessor(jobId, "content");
    },
    async drain() {
      /* no-op */
    },
  };
  setQueuePort(custom);
  getQueue().dispatch("job-x", "content");
  await new Promise((r) => setTimeout(r, 10));
  assert.deepEqual(seen, ["job-x"]);
});
