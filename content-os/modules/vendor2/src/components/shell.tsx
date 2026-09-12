import { Link, useRouterState } from "@tanstack/react-router";
import { CalendarRange, Database, FileText, History, LayoutDashboard, ShieldCheck, ClipboardCheck } from "lucide-react";
import { useEffect, useState } from "react";
import { getSession, setSession } from "@/lib/content-os/workspace.functions";
import { cn } from "@/lib/content-os/cn";

const NAV = [
  { to: "/", label: "Tổng quan", icon: LayoutDashboard },
  { to: "/ke-hoach", label: "Kế hoạch", icon: CalendarRange },
  { to: "/bai-viet", label: "Bài viết", icon: FileText },
  { to: "/nguon-du-lieu", label: "Nguồn dữ liệu", icon: Database },
  { to: "/tac-vu-ngoai", label: "Kaggle / Colab", icon: ClipboardCheck },
  { to: "/lich-su", label: "Lịch sử", icon: History },
  { to: "/nghiem-thu", label: "Nghiệm thu", icon: ClipboardCheck },
];

export function Shell({ children }: { children: React.ReactNode }) {
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  const [session, setLocal] = useState<Awaited<ReturnType<typeof getSession>> | null>(null);

  useEffect(() => {
    void getSession().then(setLocal);
  }, []);

  return (
    <div className="min-h-screen bg-paper">
      <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 bg-steel text-steel-fg px-3 py-2 rounded-sm">
        Bỏ qua điều hướng
      </a>
      <header className="border-b border-line bg-panel">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center gap-3 px-4 py-3">
          <div className="flex items-center gap-3">
            <span className="grid size-9 place-items-center rounded-md bg-steel text-steel-fg text-xs font-semibold tracking-tight">
              TH
            </span>
            <div>
              <p className="text-sm font-semibold leading-tight">THBISON Content OS</p>
              <p className="text-xs text-muted">Pa lăng xích kéo tay · VN · Asia/Bangkok</p>
            </div>
          </div>
          <div className="ml-auto flex flex-wrap items-center gap-2">
            <span className="inline-flex min-h-8 items-center rounded-full bg-warn-bg px-3 text-xs font-medium text-warn">
              MOCK · LIVE tắt
            </span>
            <label className="text-xs text-muted" htmlFor="principal">
              Vai trò mô phỏng
            </label>
            <select
              id="principal"
              className="min-h-11 rounded-sm border border-line bg-panel px-2 text-sm"
              value={session?.principal_id ?? "editor"}
              onChange={(e) => {
                void setSession({ data: { principalId: e.target.value } }).then((p) =>
                  setLocal((s) => (s ? { ...s, ...p } : s)),
                );
              }}
            >
              <option value="editor">Biên tập (được duyệt)</option>
              <option value="reader">Chỉ đọc</option>
              <option value="other">Dự án khác</option>
            </select>
          </div>
        </div>
        <nav className="mx-auto flex max-w-7xl gap-1 overflow-x-auto px-2 pb-2" aria-label="Chính">
          {NAV.map((item) => {
            const active = item.to === "/" ? pathname === "/" : pathname.startsWith(item.to);
            const Icon = item.icon;
            return (
              <Link
                key={item.to}
                to={item.to}
                className={cn(
                  "inline-flex min-h-11 items-center gap-2 rounded-md px-3 text-sm",
                  active ? "bg-steel text-steel-fg" : "text-ink hover:bg-raised",
                )}
              >
                <Icon className="size-4" aria-hidden />
                {item.label}
              </Link>
            );
          })}
        </nav>
      </header>
      <main id="main" className="mx-auto max-w-7xl px-4 py-6">
        {children}
      </main>
    </div>
  );
}

export function StatusPill({ status }: { status: string }) {
  const map: Record<string, string> = {
    PREVIEW_READY: "bg-ok-bg text-ok",
    REVIEW_REQUIRED: "bg-warn-bg text-warn",
    DRAFT: "bg-raised text-ink",
    APPROVED: "bg-ok-bg text-ok",
    REJECTED: "bg-danger-bg text-danger",
    REVOKED: "bg-danger-bg text-danger",
    DRY_RUN: "bg-raised text-ink",
    UNKNOWN: "bg-warn-bg text-warn",
    PUBLISHED: "bg-danger-bg text-danger",
    MOCK: "bg-warn-bg text-warn",
    SUCCEEDED: "bg-ok-bg text-ok",
    FAILED: "bg-danger-bg text-danger",
    QUEUED: "bg-raised text-ink",
  };
  return (
    <span className={cn("inline-flex min-h-8 items-center rounded-full px-3 text-xs font-medium", map[status] ?? "bg-raised")}>
      {status}
    </span>
  );
}

export function ShieldNote() {
  return (
    <p className="flex items-start gap-2 text-xs text-muted">
      <ShieldCheck className="mt-0.5 size-4 shrink-0" aria-hidden />
      Máy chủ cấp quyền duyệt. JSON client không phải phê duyệt. TEST_ONLY không được ghi LIVE.
    </p>
  );
}
