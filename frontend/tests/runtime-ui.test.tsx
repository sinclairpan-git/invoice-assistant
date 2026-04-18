import { App as AntdApp } from "../src/app/antd";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, RouterProvider, createMemoryRouter } from "react-router-dom";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { AppProviders } from "../src/app/providers";
import { appRoutes } from "../src/app/router";
import { BatchWorkbench } from "../src/pages/BatchWorkbench";
import { BatchResults } from "../src/pages/BatchResults";
import { InvoiceDrawer } from "../src/components/results/InvoiceDrawer";


const apiMocks = vi.hoisted(() => ({
  listBatches: vi.fn(),
  getBatch: vi.fn(),
  listBatchInvoices: vi.fn(),
  getInvoiceDetail: vi.fn(),
  createBatchRetry: vi.fn(),
  createInvoiceRetry: vi.fn(),
  createExport: vi.fn(),
  createReviewAction: vi.fn(),
  getErrorMessage: vi.fn((error: unknown) => (error instanceof Error ? error.message : "请求失败")),
  getInvoicePreviewUrl: vi.fn((invoiceId: string) => `/api/invoices/${invoiceId}/preview`),
}));

vi.mock("../src/app/api", async () => {
  const actual = await vi.importActual<object>("../src/app/api");
  return {
    ...actual,
    listBatches: apiMocks.listBatches,
    getBatch: apiMocks.getBatch,
    listBatchInvoices: apiMocks.listBatchInvoices,
    getInvoiceDetail: apiMocks.getInvoiceDetail,
    createBatchRetry: apiMocks.createBatchRetry,
    createInvoiceRetry: apiMocks.createInvoiceRetry,
    createExport: apiMocks.createExport,
    createReviewAction: apiMocks.createReviewAction,
    getErrorMessage: apiMocks.getErrorMessage,
    getInvoicePreviewUrl: apiMocks.getInvoicePreviewUrl,
  };
});

function renderWithProviders(node: ReactNode) {
  return render(
    <AppProviders>
      <MemoryRouter>{node}</MemoryRouter>
    </AppProviders>,
  );
}

describe("runtime UI", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    apiMocks.listBatches.mockResolvedValue([]);
    apiMocks.getBatch.mockResolvedValue(null);
    apiMocks.listBatchInvoices.mockResolvedValue({
      items: [],
      status_counts: {},
      batch_summary: { count: 0, total_amount: "0.00" },
      filtered_summary: { count: 0, total_amount: "0.00" },
    });
    apiMocks.getInvoiceDetail.mockResolvedValue(null);
    apiMocks.createBatchRetry.mockResolvedValue({ batch_id: "batch-1", retried_invoice_ids: ["invoice-failed"] });
    apiMocks.createInvoiceRetry.mockResolvedValue({ invoice_id: "invoice-failed", batch_id: "batch-1", retried: true });
    apiMocks.createExport.mockResolvedValue({
      export_type: "excel_manifest",
      status: "completed",
      output_path: "exports/manifest.xlsx",
      summary: {},
    });
    vi.stubGlobal("getComputedStyle", () => ({
      getPropertyValue: () => "",
      overflow: "auto",
      overflowX: "auto",
      overflowY: "auto",
    }));
    vi.stubGlobal(
      "matchMedia",
      vi.fn().mockImplementation((query: string) => ({
        matches: false,
        media: query,
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
      })),
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("shows active batch failure diagnostics and retry action on the workbench", async () => {
    apiMocks.listBatches.mockResolvedValue([
      {
        id: "batch-1",
        batch_no: "BATCH-RT-001",
        created_at: "2026-04-18T10:00:00Z",
        created_by: "tester",
        status: "processing",
        total_files: 2,
        completed_files: 1,
        processing_files: 0,
        failed_files: 1,
        suggested_pass_count: 1,
        suggested_pass_total_amount: "100.00",
        export_manifest_path: null,
        progress: {
          batch_id: "batch-1",
          batch_no: "BATCH-RT-001",
          stage_code: "processing",
          stage_text: "OCR 识别中",
          progress_percent: 50,
          total_files: 2,
          completed_files: 1,
          processing_files: 0,
          failed_files: 1,
          suggested_pass_count: 1,
          suggested_pass_total_amount: "100.00",
          recent_failures: [
            {
              invoice_id: "invoice-failed",
              original_filename: "broken.pdf",
              failure_reason: "OCR timed out",
              failure_stage: "ocr_processing",
              error_code: "ocr_timeout",
              retryable: true,
              parse_source: "ocr",
              provider_diagnostic: { provider_name: "rapidocr-onnxruntime" },
            },
          ],
        },
      } as never,
    ]);

    renderWithProviders(<BatchWorkbench />);

    expect((await screen.findAllByText("OCR 识别中")).length).toBeGreaterThan(0);
    expect(screen.getByText("broken.pdf")).toBeInTheDocument();
    expect(screen.getByText("OCR timed out")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "重试失败票" })).toBeInTheDocument();
  });

  it("treats fine-grained runtime stages as active batches on the workbench", async () => {
    apiMocks.listBatches.mockResolvedValue([
      {
        id: "batch-stage-1",
        batch_no: "BATCH-STAGE-001",
        created_at: "2026-04-18T10:05:00Z",
        created_by: "tester",
        status: "processing",
        total_files: 3,
        completed_files: 1,
        processing_files: 2,
        failed_files: 0,
        suggested_pass_count: 1,
        suggested_pass_total_amount: "88.00",
        export_manifest_path: null,
        progress: {
          batch_id: "batch-stage-1",
          batch_no: "BATCH-STAGE-001",
          stage_code: "text_extraction",
          stage_text: "文本抽取中",
          progress_percent: 33.33,
          total_files: 3,
          completed_files: 1,
          processing_files: 2,
          failed_files: 0,
          suggested_pass_count: 1,
          suggested_pass_total_amount: "88.00",
          recent_failures: [],
        },
      } as never,
    ]);

    renderWithProviders(<BatchWorkbench />);

    expect((await screen.findAllByText("BATCH-STAGE-001")).length).toBeGreaterThan(0);
    expect(screen.getAllByText("文本抽取中").length).toBeGreaterThan(0);
    expect(screen.queryByText("当前没有活跃批次")).not.toBeInTheDocument();
  });

  it("keeps recovered queued batches visible on the workbench", async () => {
    apiMocks.listBatches.mockResolvedValue([
      {
        id: "batch-recovery-1",
        batch_no: "BATCH-RECOVERY-UI-001",
        created_at: "2026-04-18T10:08:00Z",
        created_by: "tester",
        status: "processing",
        total_files: 2,
        completed_files: 0,
        processing_files: 2,
        failed_files: 0,
        suggested_pass_count: 0,
        suggested_pass_total_amount: "0.00",
        export_manifest_path: null,
        progress: {
          batch_id: "batch-recovery-1",
          batch_no: "BATCH-RECOVERY-UI-001",
          stage_code: "queued",
          stage_text: "等待处理",
          progress_percent: 0,
          total_files: 2,
          completed_files: 0,
          processing_files: 2,
          failed_files: 0,
          suggested_pass_count: 0,
          suggested_pass_total_amount: "0.00",
          recent_failures: [],
        },
      } as never,
    ]);

    renderWithProviders(<BatchWorkbench />);

    expect((await screen.findAllByText("BATCH-RECOVERY-UI-001")).length).toBeGreaterThan(0);
    expect(screen.getAllByText("等待处理").length).toBeGreaterThan(0);
    expect(screen.queryByText("当前没有活跃批次")).not.toBeInTheDocument();
  });

  it("retries failed invoices from the batch results page", async () => {
    apiMocks.listBatches.mockResolvedValue([
      {
        id: "batch-1",
        batch_no: "BATCH-RT-001",
        created_at: "2026-04-18T10:00:00Z",
        created_by: "tester",
        status: "failed",
        total_files: 2,
        completed_files: 1,
        processing_files: 0,
        failed_files: 1,
        suggested_pass_count: 1,
        suggested_pass_total_amount: "100.00",
        export_manifest_path: null,
      },
    ]);
    apiMocks.getBatch.mockResolvedValue({
      id: "batch-1",
      batch_no: "BATCH-RT-001",
      created_at: "2026-04-18T10:00:00Z",
      created_by: "tester",
      status: "failed",
      total_files: 2,
      completed_files: 1,
      processing_files: 0,
      failed_files: 1,
      suggested_pass_count: 1,
      suggested_pass_total_amount: "100.00",
      export_manifest_path: null,
      progress: {
        batch_id: "batch-1",
        batch_no: "BATCH-RT-001",
        stage_code: "failed",
        stage_text: "批次处理失败",
        progress_percent: 100,
        total_files: 2,
        completed_files: 1,
        processing_files: 0,
        failed_files: 1,
        suggested_pass_count: 1,
        suggested_pass_total_amount: "100.00",
        recent_failures: [
          {
            invoice_id: "invoice-failed",
            original_filename: "broken.pdf",
            failure_reason: "OCR timed out",
          },
        ],
      },
    });
    apiMocks.listBatchInvoices.mockResolvedValue({
      items: [
        {
          id: "invoice-failed",
          batch_id: "batch-1",
          original_filename: "broken.pdf",
          renamed_filename: null,
          storage_path_original: null,
          storage_path_renamed: null,
          invoice_code: null,
          invoice_number: null,
          seller_name: null,
          buyer_name: null,
          buyer_tax_no: null,
          invoice_date: null,
          invoice_amount: null,
          processing_status: "processing_failed",
          system_decision: null,
          review_status: "not_reviewed",
          artifact_status: "original_only",
          duplicate_flag: false,
          duplicate_group_key: null,
          risk_flags: [],
          display_status: "处理失败",
          problem_count: 1,
          failure_reason: "OCR timed out",
          preview_path: null,
        },
      ],
      status_counts: { "处理失败": 1 },
      batch_summary: { count: 0, total_amount: "0.00" },
      filtered_summary: { count: 0, total_amount: "0.00" },
    });

    const router = createMemoryRouter(appRoutes, {
      initialEntries: ["/results/batch-1"],
    });

    render(
      <AppProviders>
        <RouterProvider router={router} />
      </AppProviders>,
    );

    const retryButton = await screen.findByRole("button", { name: "重试失败票" });
    fireEvent.click(retryButton);

    await waitFor(() => {
      expect(apiMocks.createBatchRetry).toHaveBeenCalledWith({ batchId: "batch-1" });
    });
  });

  it("shows invoice diagnostic details and retries a single failed invoice", async () => {
    const onChanged = vi.fn();
    const messageSuccess = vi.fn();
    vi.spyOn(AntdApp, "useApp").mockReturnValue({
      message: { success: messageSuccess, error: vi.fn(), warning: vi.fn(), info: vi.fn(), open: vi.fn(), destroy: vi.fn(), loading: vi.fn() },
      notification: {} as never,
      modal: {} as never,
    });
    apiMocks.getInvoiceDetail.mockResolvedValue({
      id: "invoice-failed",
      batch_id: "batch-1",
      original_filename: "broken.pdf",
      renamed_filename: null,
      storage_path_original: null,
      storage_path_renamed: null,
      invoice_code: null,
      invoice_number: null,
      seller_name: null,
      buyer_name: null,
      buyer_tax_no: null,
      invoice_date: null,
      invoice_amount: null,
      processing_status: "processing_failed",
      system_decision: null,
      review_status: "not_reviewed",
      artifact_status: "original_only",
      duplicate_flag: false,
      duplicate_group_key: null,
      risk_flags: [],
      display_status: "处理失败",
      problem_count: 1,
      failure_reason: "OCR timed out",
      preview_path: null,
      parse_source: "ocr",
      last_error_stage: "ocr_processing",
      last_error_code: "ocr_timeout",
      last_error_message: "OCR timed out",
      retryable: true,
      provider_diagnostic: {
        provider_name: "rapidocr-onnxruntime",
        provider_version: "1.3.24",
        provider_error_code: "ocr_timeout",
      },
      evidence_items: [],
      extracted_fields: [],
      field_checks: [],
      review_actions: [],
    });

    renderWithProviders(
      <InvoiceDrawer invoiceId="invoice-failed" open onClose={() => undefined} onChanged={onChanged} />,
    );

    expect(await screen.findByText("rapidocr-onnxruntime")).toBeInTheDocument();
    expect(screen.getAllByText("ocr_timeout").length).toBeGreaterThan(0);

    fireEvent.click(screen.getByRole("button", { name: "重试当前票" }));

    await waitFor(() => {
      expect(apiMocks.createInvoiceRetry).toHaveBeenCalledWith({ invoiceId: "invoice-failed" });
    });
    await waitFor(() => {
      expect(onChanged).toHaveBeenCalled();
      expect(messageSuccess).toHaveBeenCalled();
    });
  });
});
