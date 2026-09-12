import { createFileRoute } from '@tanstack/react-router';
import { CheckCircle2, ClipboardCheck, ExternalLink, ShieldCheck } from 'lucide-react';
import { useState } from 'react';
import { Shell } from '@/components/shell';

export const Route = createFileRoute('/tac-vu-ngoai')({ component: RemoteJobs });

const SNAPSHOT = {
  bytes: 174507,
  sha256: 'e18a2650dcf3d52646f8e6fd50091d88e2e3d6515b228d049485f6d06cea4c10',
  counts: { evidence: 9, products: 24, knowledge: 114 },
} as const;

const RUNS = [
  {
    platform: 'Google Colab',
    title: 'Snapshot thật đã kiểm định',
    status: 'SNAPSHOT_QA_PASS',
    receiptSha256: '717113272ebac8612d196c645762f821fa66382423124d4908a60c76c5eab306',
    notebookUrl: 'https://colab.research.google.com/drive/18SdgyxI8lqTqxWqL4bknkbVcje6--mjN',
    interpreter: 'Python 3.13.15',
  },
  {
    platform: 'Kaggle',
    title: 'Private notebook đã kiểm định',
    status: 'SNAPSHOT_QA_PASS',
    receiptSha256: 'daa48b45830563a9ad03343bcdce1638fa40d6bd5887a19e811188877e4d9117',
    notebookUrl: 'https://www.kaggle.com/code/nguyeble/thbison-snapshot-qa-no-write-7979a60',
    interpreter: 'Python 3.12.13',
  },
] as const;

function RemoteJobs() {
  const [platform, setPlatform] = useState<'kaggle' | 'colab'>('kaggle');
  const [notice, setNotice] = useState('');
  const root = platform === 'kaggle' ? '/kaggle/input' : '/content';
  const outputRoot = platform === 'kaggle' ? '/kaggle/working' : '/content';
  const input = platform === 'kaggle'
    ? '/kaggle/input/datasets/nguyeble/thbison-private-snapshot-qa-20260912/notion-content-os-snapshot.json'
    : '/content/notion-content-os-snapshot.json';
  const command = `# NO_WRITE: kiểm tra snapshot, không tạo bài và không kết nối dịch vụ thật
from pathlib import Path
import subprocess, sys, uuid
workers = list(Path('${root}').rglob('snapshot_worker.py'))
assert len(workers) == 1, 'PINNED_WORKER_NOT_UNIQUE'
subprocess.run([sys.executable, str(workers[0]),
    '--input', '${input}',
    '--sha256', '${SNAPSHOT.sha256}',
    '--output', '${outputRoot}/snapshot-qa-' + uuid.uuid4().hex], check=True)`;

  return <Shell>
    <div className="flex flex-wrap items-start justify-between gap-4">
      <div>
        <p className="text-xs font-semibold uppercase tracking-wide text-muted">Hosted compute · NO_WRITE</p>
        <h1 className="mt-1 font-display text-3xl font-semibold tracking-tight">Tác vụ Kaggle / Colab</h1>
        <p className="mt-2 max-w-3xl text-sm text-muted">VPS giữ dashboard và biên nhận. Notebook chỉ xử lý gói đầu vào đã khóa checksum; không kết nối database hoặc thay đổi trạng thái duyệt.</p>
      </div>
      <span className="inline-flex min-h-9 items-center gap-2 rounded-full bg-ok-bg px-3 text-xs font-medium text-ok"><ShieldCheck className="size-4" aria-hidden /> Không ghi dữ liệu</span>
    </div>

    <section className="mt-6 grid gap-4 lg:grid-cols-2" aria-labelledby="run-status-title">
      <h2 id="run-status-title" className="sr-only">Trạng thái môi trường chạy</h2>
      {RUNS.map((run) => <article key={run.platform} className="rounded-lg border border-line bg-panel p-5">
        <div className="flex items-start justify-between gap-3">
          <div><p className="text-sm font-medium text-muted">{run.platform}</p><h3 className="mt-1 text-lg font-semibold">{run.title}</h3></div>
          <span className="inline-flex items-center gap-2 rounded-full bg-ok-bg px-3 py-1 text-xs font-medium text-ok"><CheckCircle2 className="size-4" aria-hidden /> PASS</span>
        </div>
        <dl className="mt-4 grid grid-cols-2 gap-3 text-sm">
          <div><dt className="text-muted">Kết quả</dt><dd className="mt-1 font-mono text-xs">{run.status}</dd></div>
          <div><dt className="text-muted">Runtime</dt><dd className="mt-1">{run.interpreter}</dd></div>
          <div className="col-span-2"><dt className="text-muted">Receipt SHA-256</dt><dd className="mt-1 break-all font-mono text-xs">{run.receiptSha256}</dd></div>
        </dl>
        <a className="mt-4 inline-flex min-h-11 items-center gap-2 rounded border border-line px-4 text-sm font-medium" href={run.notebookUrl} target="_blank" rel="noreferrer">Mở notebook riêng tư <ExternalLink className="size-4" aria-hidden /></a>
      </article>)}
    </section>

    <section className="mt-6 rounded-lg border border-line bg-panel p-5">
      <h2 className="text-xl font-semibold">Gói đầu vào đã khóa</h2>
      <div className="mt-4 grid gap-3 sm:grid-cols-4">
        <div className="rounded bg-raised p-3"><p className="text-xs text-muted">Dung lượng</p><p className="mt-1 font-mono text-sm">{SNAPSHOT.bytes.toLocaleString('vi-VN')} bytes</p></div>
        <div className="rounded bg-raised p-3"><p className="text-xs text-muted">Evidence</p><p className="mt-1 text-xl font-semibold">{SNAPSHOT.counts.evidence}</p></div>
        <div className="rounded bg-raised p-3"><p className="text-xs text-muted">Products</p><p className="mt-1 text-xl font-semibold">{SNAPSHOT.counts.products}</p></div>
        <div className="rounded bg-raised p-3"><p className="text-xs text-muted">Knowledge</p><p className="mt-1 text-xl font-semibold">{SNAPSHOT.counts.knowledge}</p></div>
      </div>
      <p className="mt-3 break-all font-mono text-xs text-muted">SHA-256 {SNAPSHOT.sha256}</p>
    </section>

    <section className="mt-6 rounded-lg border border-line bg-panel p-5">
      <h2 className="text-xl font-semibold">Lệnh vận hành an toàn</h2>
      <p className="mt-2 text-sm text-muted">Kiểm tra metadata, ID và số lượng. Không sinh bài, train model hoặc crawl dữ liệu.</p>
      <label htmlFor="platform" className="mt-5 block font-medium">Môi trường</label>
      <select id="platform" value={platform} onChange={e => { setPlatform(e.target.value as 'kaggle' | 'colab'); setNotice(''); }} className="mt-2 min-h-11 rounded border border-line bg-paper px-3">
        <option value="kaggle">Kaggle · private notebook, Internet OFF</option>
        <option value="colab">Google Colab · private notebook</option>
      </select>
      <p className="mt-4 text-sm">Worker phải xuất hiện đúng một lần dưới <code className="break-all">{root}</code>; snapshot ở <code className="break-all">{input}</code>.</p>
      <pre className="mt-4 overflow-x-auto rounded bg-paper p-4 text-sm"><code>{command}</code></pre>
      <button className="mt-3 inline-flex min-h-11 items-center gap-2 rounded bg-steel px-4 text-steel-fg" onClick={async () => { try { await navigator.clipboard.writeText(command); setNotice('Đã sao chép lệnh.'); } catch { setNotice('Không truy cập được clipboard; chọn và sao chép lệnh trong khung.'); } }}><ClipboardCheck className="size-4" aria-hidden /> Sao chép lệnh</button>
      <p role="status" className="mt-2 min-h-5 text-sm">{notice}</p>
      <p className="mt-2 text-sm text-muted">Kết quả hợp lệ gồm receipt.json và sha256.json trong thư mục output mới. Lỗi checksum phải dừng trước khi tạo output.</p>
    </section>

    <section className="mt-6 rounded-lg border border-line bg-panel p-5">
      <h2 className="text-xl font-semibold">Cổng Knowledge · để dành cho model riêng</h2>
      <p className="mt-2">Dashboard hiện chỉ giữ interface tích hợp. Không tự đưa 114 Knowledge Items vào bộ sinh bài và không thay đổi HOLD/REVIEW_REQUIRED.</p>
      <p className="mt-3 text-sm text-muted">Khi model chất lượng được gắn sau, output vẫn phải qua kiểm chứng nguồn, preview và phê duyệt thủ công trước khi có quyền xuất bản.</p>
    </section>
  </Shell>;
}
