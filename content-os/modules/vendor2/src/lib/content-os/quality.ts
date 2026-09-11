import type { ArticlePackage, EvidenceBundle } from "./types";

const NEGATION = /\b(không phải|không|never|not|no longer)\b/i;
const UNIT = /\b(\d+(?:[.,]\d+)?)(?:\s|-)?(kg|tấn|tan|mm|cm|m|tấn lực|ton)\b/i;
const INJECTION = /(ignore (all|previous|system)|upload (api )?keys?|change policy|override safety)/i;
const HTML_INJECTION = /<\s*script|javascript:|onerror\s*=|onload\s*=/i;
const OEM_SHIFT = /\b(hitachi|kito|vital|elephant|ingersoll|yale)\b/i;

export type QualityFinding = {
  code: string;
  block_id?: string;
  message: string;
  blocks_publication: boolean;
};

function numbersIn(text: string): string[] {
  const out: string[] = [];
  const re = new RegExp(UNIT.source, "gi");
  text.replace(re, (m) => {
    out.push(m.toLowerCase().replace(/[\s-]+/g, ""));
    return m;
  });
  return out;
}

export function evaluateArticle(article: ArticlePackage, bundle: EvidenceBundle): QualityFinding[] {
  const findings: QualityFinding[] = [];
  const claims = Object.fromEntries(bundle.claims.map((c) => [c.claim_id, c]));

  for (const block of article.blocks) {
    if (HTML_INJECTION.test(block.text)) {
      findings.push({
        code: "UNSAFE_HTML",
        block_id: block.block_id,
        message: "HTML/script không an toàn trong nội dung.",
        blocks_publication: true,
      });
    }
    if (block.kind === "FACTUAL") {
      const sources = block.claim_ids.map((id) => claims[id]).filter(Boolean);
      const joined = sources.map((c) => `${c.text} ${c.quote}`).join("\n");
      if (NEGATION.test(block.text) && !NEGATION.test(joined)) {
        findings.push({
          code: "NEGATION_MISMATCH",
          block_id: block.block_id,
          message: "Phủ định không có trong nguồn.",
          blocks_publication: true,
        });
      }
      const blockUnits = numbersIn(block.text);
      const srcUnits = numbersIn(joined);
      for (const u of blockUnits) {
        if (!srcUnits.includes(u)) {
          findings.push({
            code: "UNIT_MISMATCH",
            block_id: block.block_id,
            message: `Đơn vị/số liệu ${u} không khớp nguồn.`,
            blocks_publication: true,
          });
        }
      }
      if (OEM_SHIFT.test(block.text) && !OEM_SHIFT.test(joined)) {
        findings.push({
          code: "OEM_SCOPE",
          block_id: block.block_id,
          message: "Không suy OEM khác sang THBISON.",
          blocks_publication: true,
        });
      }
      const lowered = block.text.toLowerCase();
      const srcLow = joined.toLowerCase();
      if (block.claim_ids.length && !sources.some((c) => overlap(lowered, c.text.toLowerCase() + " " + c.quote.toLowerCase()))) {
        if (!srcLow.includes(lowered.slice(0, Math.min(40, lowered.length)))) {
          findings.push({
            code: "ENTAILMENT_WEAK",
            block_id: block.block_id,
            message: "Khối FACTUAL không được nguồn chống đỡ đủ.",
            blocks_publication: true,
          });
        }
      }
    }
    if ((block.kind === "EDITORIAL" || block.kind === "CTA") && looksFactual(block.text) && block.claim_ids.length === 0) {
      findings.push({
        code: "DISGUISED_FACT",
        block_id: block.block_id,
        message: "Khẳng định kỹ thuật không được ngụy trang thành editorial/CTA.",
        blocks_publication: true,
      });
    }
  }

  for (const c of bundle.claims) {
    if (INJECTION.test(c.text) || INJECTION.test(c.quote)) {
      findings.push({
        code: "SOURCE_INJECTION",
        message: "Nguồn chứa chỉ thị công cụ — giữ như dữ liệu, không thi hành.",
        blocks_publication: false,
      });
    }
  }
  return findings;
}

function overlap(a: string, b: string): boolean {
  const words = a.split(/\s+/).filter((w) => w.length > 3);
  if (!words.length) return b.includes(a.slice(0, 24));
  const hits = words.filter((w) => b.includes(w)).length;
  return hits / words.length >= 0.45;
}

function looksFactual(text: string): boolean {
  return UNIT.test(text) || /\b(tải trọng|housing|model|kg|tấn|định mức)\b/i.test(text);
}

export function sanitizeText(text: string): string {
  return text
    .replace(/<\s*script[\s\S]*?>[\s\S]*?<\s*\/\s*script\s*>/gi, "")
    .replace(/[<>]/g, (ch) => (ch === "<" ? "<" : ">"));
}

export function isUntrustedInstruction(text: string): boolean {
  return INJECTION.test(text);
}
