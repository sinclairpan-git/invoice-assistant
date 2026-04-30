export type ResultFilterValue =
  | "all"
  | "processing"
  | "suggested_pass"
  | "suggested_reject"
  | "manual_review"
  | "batch_duplicate"
  | "needs_retry";

export const RESULT_FILTER_OPTIONS: Array<{ value: ResultFilterValue; label: string }> = [
  { value: "all", label: "全部" },
  { value: "processing", label: "处理中" },
  { value: "suggested_pass", label: "建议通过" },
  { value: "suggested_reject", label: "建议驳回" },
  { value: "manual_review", label: "待人工确认" },
  { value: "batch_duplicate", label: "本批次重复" },
  { value: "needs_retry", label: "需补充/重试" },
];

const DISPLAY_STATUS_BY_FILTER: Record<Exclude<ResultFilterValue, "all">, string> = {
  processing: "处理中",
  suggested_pass: "系统建议通过",
  suggested_reject: "系统建议驳回",
  manual_review: "待复核",
  batch_duplicate: "疑似重复",
  needs_retry: "处理失败",
};

const DISPLAY_STATUS_LABELS: Record<string, string> = Object.fromEntries(
  RESULT_FILTER_OPTIONS.filter((item) => item.value !== "all").map((item) => [
    DISPLAY_STATUS_BY_FILTER[item.value as Exclude<ResultFilterValue, "all">],
    item.label,
  ]),
);

const TERMINAL_PROCESSING_STATUSES = new Set(["completed", "processing_failed", "failed"]);
const FAILED_PROCESSING_STATUSES = new Set(["processing_failed", "failed"]);

export function toDisplayStatusFilter(value: ResultFilterValue): string | undefined {
  if (value === "all") {
    return undefined;
  }
  return DISPLAY_STATUS_BY_FILTER[value];
}

export function getResultFilterValue(status: string | null | undefined): ResultFilterValue | null {
  if (!status) {
    return null;
  }
  const entry = Object.entries(DISPLAY_STATUS_BY_FILTER).find(([, displayStatus]) => displayStatus === status);
  return (entry?.[0] as ResultFilterValue | undefined) ?? null;
}

export function getResultFilterCount(
  counts: Record<string, number>,
  value: Exclude<ResultFilterValue, "all">,
): number {
  return counts[DISPLAY_STATUS_BY_FILTER[value]] ?? 0;
}

export function getResultStatusLabel(status: string | null | undefined): string {
  if (!status) {
    return "--";
  }
  return DISPLAY_STATUS_LABELS[status] ?? status;
}

export function getResultStatusColor(status: string | null | undefined): string {
  if (!status) {
    return "default";
  }
  if (status === "处理中") {
    return "blue";
  }
  if (status === "系统建议通过") {
    return "green";
  }
  if (status === "系统建议驳回" || status === "处理失败") {
    return "red";
  }
  if (status === "疑似重复") {
    return "volcano";
  }
  return "gold";
}

export function isInvoiceProcessing(processingStatus: string | null | undefined): boolean {
  if (!processingStatus) {
    return true;
  }
  return !TERMINAL_PROCESSING_STATUSES.has(processingStatus);
}

export function isInvoiceFailed(processingStatus: string | null | undefined): boolean {
  if (!processingStatus) {
    return false;
  }
  return FAILED_PROCESSING_STATUSES.has(processingStatus);
}

export function requiresManualReview(params: {
  processingStatus: string | null | undefined;
  systemDecision: string | null | undefined;
  duplicateFlag: boolean;
  reviewStatus: string | null | undefined;
}): boolean {
  if (params.reviewStatus === "manually_approved" || params.reviewStatus === "manually_rejected") {
    return false;
  }
  if (isInvoiceProcessing(params.processingStatus) || isInvoiceFailed(params.processingStatus)) {
    return false;
  }
  return params.duplicateFlag || params.systemDecision === "review_required";
}

export function getReviewStatusLabel(params: {
  processingStatus: string | null | undefined;
  systemDecision: string | null | undefined;
  duplicateFlag: boolean;
  reviewStatus: string | null | undefined;
}): string {
  if (params.reviewStatus === "manually_approved") {
    return "已人工确认通过";
  }
  if (params.reviewStatus === "manually_rejected") {
    return "已人工确认驳回";
  }
  if (requiresManualReview(params)) {
    return "待人工确认";
  }
  return "无需人工确认";
}

export function getReviewStatusColor(params: {
  processingStatus: string | null | undefined;
  systemDecision: string | null | undefined;
  duplicateFlag: boolean;
  reviewStatus: string | null | undefined;
}): string {
  if (params.reviewStatus === "manually_approved") {
    return "green";
  }
  if (params.reviewStatus === "manually_rejected") {
    return "red";
  }
  if (requiresManualReview(params)) {
    return "gold";
  }
  return "default";
}
