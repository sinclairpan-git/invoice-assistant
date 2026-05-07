import type { Batch, InvoiceSummary } from "../app/types";

export type ResultBucket =
  | "all"
  | "suggested_pass"
  | "review_required"
  | "duplicate_in_batch"
  | "needs_retry";

export const RESULT_BUCKETS: Array<{ label: string; value: ResultBucket }> = [
  { label: "全部", value: "all" },
  { label: "建议通过", value: "suggested_pass" },
  { label: "待人工确认", value: "review_required" },
  { label: "本批次重复", value: "duplicate_in_batch" },
  { label: "需补充/重试", value: "needs_retry" },
];

const PROCESSING_CODES = new Set([
  "queued",
  "processing",
  "recovering",
  "text_extraction",
  "ocr_processing",
  "classification",
  "duplicate_check",
  "finalization",
]);

export function isActiveBatch(batch: Batch | null | undefined): boolean {
  if (!batch) {
    return false;
  }
  const stageCode = batch.progress?.stage_code;
  return Boolean(stageCode && PROCESSING_CODES.has(stageCode)) || batch.status === "queued" || batch.status === "processing";
}

export function isInvoiceProcessing(status: string | null | undefined): boolean {
  return Boolean(status && PROCESSING_CODES.has(status));
}

export function isInvoiceFailed(status: string | null | undefined): boolean {
  return status === "failed" || status === "needs_retry";
}

export function toDisplayStatusFilter(bucket: ResultBucket): string | undefined {
  if (bucket === "all") {
    return undefined;
  }
  return bucket;
}

export function getResultBucket(invoice: InvoiceSummary): ResultBucket {
  if (isInvoiceFailed(invoice.processing_status)) {
    return "needs_retry";
  }
  if (invoice.duplicate_flag || invoice.display_status === "duplicate_in_batch") {
    return "duplicate_in_batch";
  }
  if (invoice.system_decision === "review_required" || invoice.display_status === "review_required") {
    return "review_required";
  }
  if (invoice.system_decision === "suggested_pass" || invoice.display_status === "suggested_pass") {
    return "suggested_pass";
  }
  return "all";
}

export function getBucketCount(counts: Record<string, number>, bucket: ResultBucket): number {
  if (bucket === "all") {
    return Object.values(counts).reduce((sum, count) => sum + count, 0);
  }
  return counts[bucket] ?? 0;
}

export function getStatusLabel(status: string | null | undefined): string {
  const labels: Record<string, string> = {
    suggested_pass: "建议通过",
    review_required: "待人工确认",
    duplicate_in_batch: "本批次重复",
    needs_retry: "需补充/重试",
    failed: "处理失败",
    queued: "排队中",
    processing: "处理中",
    completed: "已完成",
  };
  return status ? labels[status] ?? status : "未刷新";
}

export function getStatusSeverity(status: string | null | undefined) {
  if (status === "suggested_pass" || status === "completed" || status === "approved") {
    return "success" as const;
  }
  if (status === "review_required" || status === "duplicate_in_batch" || status === "processing") {
    return "warn" as const;
  }
  if (status === "needs_retry" || status === "failed" || status === "rejected") {
    return "danger" as const;
  }
  return "secondary" as const;
}

export function getReviewLabel(invoice: InvoiceSummary): string {
  if (isInvoiceProcessing(invoice.processing_status)) {
    return "等待识别";
  }
  if (invoice.review_status === "approved") {
    return "已确认通过";
  }
  if (invoice.review_status === "rejected") {
    return "已确认驳回";
  }
  if (getResultBucket(invoice) === "review_required" || getResultBucket(invoice) === "duplicate_in_batch") {
    return "待人工确认";
  }
  return "无需确认";
}
