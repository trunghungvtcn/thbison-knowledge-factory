/**
 * Queue port — Vendor 2 owns job business processors.
 * Vendor 3 owns runtime (worker pool, retries, backoff).
 *
 * HTTP POST job endpoints MUST admit the job as QUEUED and return 202 without
 * awaiting the processor. Vendor 3 replaces `setQueuePort` with their adapter
 * and continues to call the same `registerProcessor` callback.
 */
export type JobKind = "content" | "planning";

export type QueuePort = {
  dispatch(jobId: string, kind: JobKind): void;
  drain(): Promise<void>;
};

export type JobProcessor = (jobId: string, kind: JobKind) => Promise<void>;

let processor: JobProcessor = async () => {
  throw new Error("Job processor not registered");
};

export function registerProcessor(fn: JobProcessor): void {
  processor = fn;
}

export function runProcessor(jobId: string, kind: JobKind): Promise<void> {
  return processor(jobId, kind);
}

export function createDeferredPort(): QueuePort {
  const pending: Promise<void>[] = [];
  return {
    dispatch(jobId, kind) {
      const run = Promise.resolve()
        .then(() => processor(jobId, kind))
        .catch((err) => {
          console.error("content-os.queue", jobId, err);
        });
      pending.push(run);
    },
    async drain() {
      while (pending.length) {
        await Promise.all(pending.splice(0));
      }
    },
  };
}

let port: QueuePort = createDeferredPort();

export function getQueue(): QueuePort {
  return port;
}

/** Vendor 3: swap in Redis/SQS/etc. Do not fork processContentJob/processPlanningJob. */
export function setQueuePort(next: QueuePort): void {
  port = next;
}
