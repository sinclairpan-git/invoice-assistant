import type {
  ActiveConfigPayload,
  Batch,
  BatchInvoiceListing,
  BatchRetryResult,
  CurrentActor,
  InitialSetupPayload,
  InvoiceDetail,
  InvoiceRetryResult,
  InvoiceSummary,
  ReviewAction,
  RuleKind,
  RuleVersion,
} from "./types";


export class ApiError extends Error {
  status: number;
  detail: string;

  constructor(status: number, detail: string) {
    super(detail);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

async function readErrorDetail(response: Response): Promise<string> {
  try {
    const payload = (await response.json()) as { detail?: string };
    return payload.detail ?? `请求失败（${response.status}）`;
  } catch {
    return `请求失败（${response.status}）`;
  }
}

async function requestJson<T>(input: string, init?: RequestInit): Promise<T> {
  const response = await fetch(input, init);
  if (!response.ok) {
    throw new ApiError(response.status, await readErrorDetail(response));
  }
  return (await response.json()) as T;
}

export function getErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    return error.detail;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return "请求未完成";
}

export async function listBatches(): Promise<Batch[]> {
  const payload = await requestJson<{ items: Batch[] }>("/api/batches");
  return payload.items;
}

export async function getBatch(batchId: string): Promise<Batch> {
  const payload = await requestJson<{ item: Batch }>(`/api/batches/${batchId}`);
  return payload.item;
}

export async function getCurrentActor(): Promise<CurrentActor> {
  const payload = await requestJson<{ item: CurrentActor }>("/api/me");
  return payload.item;
}

export async function createBatch(params: {
  batchNo?: string;
  files: File[];
}): Promise<Batch> {
  const formData = new FormData();
  if (params.batchNo) {
    formData.append("batch_no", params.batchNo);
  }
  params.files.forEach((file) => {
    formData.append("files", file);
  });
  const payload = await requestJson<{ item: Batch }>("/api/batches", {
    method: "POST",
    body: formData,
  });
  return payload.item;
}

export async function listBatchInvoices(batchId: string, displayStatus?: string): Promise<BatchInvoiceListing> {
  const query = displayStatus ? `?display_status=${encodeURIComponent(displayStatus)}` : "";
  return requestJson<BatchInvoiceListing>(`/api/batches/${batchId}/invoices${query}`);
}

export async function getInvoiceDetail(invoiceId: string): Promise<InvoiceDetail> {
  const payload = await requestJson<{ item: InvoiceDetail }>(`/api/invoices/${invoiceId}`);
  return payload.item;
}

export function getInvoicePreviewUrl(invoiceId: string): string {
  return `/api/invoices/${invoiceId}/preview`;
}

export async function createReviewAction(params: {
  invoiceId: string;
  reviewAction: string;
  reviewNote?: string;
}): Promise<{ item: ReviewAction; invoice: InvoiceSummary }> {
  return requestJson<{ item: ReviewAction; invoice: InvoiceSummary }>(
    `/api/invoices/${params.invoiceId}/review-actions`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        review_action: params.reviewAction,
        review_note: params.reviewNote || undefined,
      }),
    },
  );
}

export async function createBatchRetry(params: {
  batchId: string;
}): Promise<BatchRetryResult> {
  const payload = await requestJson<{ item: BatchRetryResult }>(`/api/batches/${params.batchId}/retry-failures`, {
    method: "POST",
  });
  return payload.item;
}

export async function createInvoiceRetry(params: {
  invoiceId: string;
}): Promise<InvoiceRetryResult> {
  const payload = await requestJson<{ item: InvoiceRetryResult }>(`/api/invoices/${params.invoiceId}/retry`, {
    method: "POST",
  });
  return payload.item;
}

export async function getActiveConfig(): Promise<ActiveConfigPayload> {
  const payload = await requestJson<ActiveConfigPayload>("/api/config");
  return payload;
}

export async function listRuleVersions(kind: RuleKind): Promise<RuleVersion[]> {
  const payload = await requestJson<{ items: RuleVersion[] }>(`/api/config/${kind}/versions`);
  return payload.items;
}

export async function createRuleVersion(params: {
  kind: RuleKind;
  content: Record<string, unknown>;
  changeSummary: string;
  changeReason: string;
  activate?: boolean;
}): Promise<RuleVersion> {
  const payload = await requestJson<{ item: RuleVersion }>(`/api/config/${params.kind}/versions`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      content: params.content,
      change_summary: params.changeSummary,
      change_reason: params.changeReason,
      activate: params.activate ?? true,
    }),
  });
  return payload.item;
}

export async function createInitialSetup(params: {
  taxProfile: Record<string, unknown>;
  businessRules: Record<string, unknown>;
  namingRules: Record<string, unknown>;
  changeSummary: string;
  changeReason: string;
}): Promise<InitialSetupPayload> {
  return requestJson<InitialSetupPayload>("/api/config/setup", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      tax_profile: params.taxProfile,
      business_rules: params.businessRules,
      naming_rules: params.namingRules,
      change_summary: params.changeSummary,
      change_reason: params.changeReason,
    }),
  });
}

export async function createExport(params: {
  batchId: string;
  exportType: string;
}): Promise<{
  job_id?: string;
  export_type: string;
  status: string;
  output_path: string;
  summary: Record<string, unknown>;
}> {
  const payload = await requestJson<{
    item: {
      job_id?: string;
      export_type: string;
      status: string;
      output_path: string;
      summary: Record<string, unknown>;
    };
  }>(`/api/batches/${params.batchId}/exports`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      export_type: params.exportType,
    }),
  });
  return payload.item;
}
