import { createFileRoute } from '@tanstack/react-router';
import { Shell } from '@/components/shell';
import { useState } from 'react';

export const Route = createFileRoute('/tac-vu-ngoai')({ component: RemoteJobs });
const HASH = 'e18a2650dcf3d52646f8e6fd50091d88e2e3d6515b228d049485f6d06cea4c10';
function RemoteJobs() {
  const [platform, setPlatform] = useState<'kaggle' | 'colab'>('kaggle');
  const [notice, setNotice] = useState('');
  const root = platform === 'kaggle' ? '/kaggle/working' : '/content';
  const input = platform === 'kaggle' ? '/kaggle/input/thbison-private/notion-content-os-snapshot-20260912.json' : '/content/notion-content-os-snapshot-20260912.json';
  const command = `# Chạy trong một ô notebook; dùng source đã kiểm checksum tại ${root}/thbison\nimport subprocess, sys, uuid\nsubprocess.run([sys.executable, '${root}/thbison/content-os/scripts/snapshot_worker.py',\n    '--input', '${input}',\n    '--sha256', '${HASH}',\n    '--output', '${root}/snapshot-qa-' + uuid.uuid4().hex], check=True)`;
  return <Shell>
    <h1 className="text-3xl font-semibold">Tác vụ Kaggle / Colab</h1>
    <p className="mt-3 text-muted">VPS giữ dashboard và biên nhận. Notebook xử lý gói đầu vào đã khóa checksum; không kết nối database.</p>
    <div className="mt-6 grid gap-4 md:grid-cols-3">
      {['1. Chuẩn bị source và snapshot riêng tư', '2. Chạy notebook NO_WRITE', '3. Đối soát receipt trước khi nhập'].map(t => <div key={t} className="rounded-lg border border-line bg-panel p-5">{t}</div>)}
    </div>
    <section className="mt-6 rounded-lg border border-line bg-panel p-5">
      <h2 className="text-xl font-semibold">Kiểm tra snapshot · sẵn lệnh</h2>
      <p className="mt-2 text-sm text-muted">Kiểm tra metadata, ID và số lượng. Không phải tác vụ sinh bài, train model hay crawl dữ liệu.</p>
      <label htmlFor="platform" className="mt-5 block font-medium">Môi trường</label>
      <select id="platform" value={platform} onChange={e => {setPlatform(e.target.value as 'kaggle' | 'colab'); setNotice('');}} className="mt-2 min-h-11 rounded border border-line bg-paper px-3">
        <option value="kaggle">Kaggle · private notebook, Internet OFF</option><option value="colab">Google Colab · private notebook</option>
      </select>
      <p className="mt-4 text-sm">Đặt source tại <code className="break-all">{root}/thbison</code>. Đặt snapshot tại đường dẫn trong lệnh; không dùng dataset công khai và không chia sẻ notebook chứa dữ liệu thật.</p>
      <pre className="mt-4 overflow-x-auto rounded bg-paper p-4 text-sm"><code>{command}</code></pre>
      <button className="mt-3 min-h-11 rounded bg-steel px-4 text-steel-fg" onClick={async () => {try {await navigator.clipboard.writeText(command); setNotice('Đã sao chép lệnh.');} catch {setNotice('Không truy cập được clipboard; chọn và sao chép lệnh trong khung.');}}}>Sao chép lệnh</button>
      <p role="status" className="mt-2 text-sm">{notice}</p>
      <p className="mt-3 text-sm text-muted">Kết quả: receipt.json và sha256.json trong thư mục output mới. Lỗi checksum sẽ dừng trước khi tạo output. Chưa chạy trên Kaggle/Colab trong lượt triển khai này.</p>
    </section>
    <section className="mt-6 rounded-lg border border-line bg-panel p-5">
      <h2 className="text-xl font-semibold">Sinh bài từ nguồn thật · chưa mở</h2>
      <p className="mt-2">Snapshot hiện là metadata. Cần bổ sung quan hệ Knowledge → Evidence và trích dẫn đã xác minh trước khi nối bộ sinh bài. Không thay thế phần thiếu bằng fixture.</p>
      <p className="mt-3 text-sm text-muted">Không có nút tự khởi chạy từ dashboard, scheduler hoặc tự nhập kết quả vào Notion/CMS. Mọi output phải qua nghiệm thu trước.</p>
    </section>
  </Shell>;
}
