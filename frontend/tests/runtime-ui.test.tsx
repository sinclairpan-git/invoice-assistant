import { App as AntdApp } from "../src/app/antd";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, RouterProvider, createMemoryRouter } from "react-router-dom";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { AppProviders } from "../src/app/providers";
import { appRoutes } from "../src/app/router";
import { BatchWorkbench } from "../src/pages/BatchWorkbench";
import { BatchResults } from "../src/pages/BatchResults";
import { Settings } from "../src/pages/Settings";
import { SetupWizard } from "../src/pages/SetupWizard";
import { UploadPanel } from "../src/components/batch/UploadPanel";
import { InvoiceDrawer } from "../src/components/results/InvoiceDrawer";
import { ReviewActions } from "../src/components/results/ReviewActions";
import { RuleVersionPanel } from "../src/components/settings/RuleVersionPanel";
import { SetupStatusCard } from "../src/components/settings/SetupStatusCard";


const apiMocks = vi.hoisted(() => ({
  listBatches: vi.fn(),
  getBatch: vi.fn(),
  listBatchInvoices: vi.fn(),
  getInvoiceDetail: vi.fn(),
  createBatchRetry: vi.fn(),
  createInvoiceRetry: vi.fn(),
  downloadBatchFile: vi.fn(),
  createExport: vi.fn(),
  openRuntimePath: vi.fn(),
  createReviewAction: vi.fn(),
  getCurrentActor: vi.fn(),
  getActiveConfig: vi.fn(),
  listRuleVersions: vi.fn(),
  createRuleVersion: vi.fn(),
  createInitialSetup: vi.fn(),
  publishConfigBundle: vi.fn(),
  listConfigBundles: vi.fn(),
  getErrorMessage: vi.fn((error: unknown) => (error instanceof Error ? error.message : "请求失败")),
  getInvoicePreviewUrl: vi.fn((invoiceId: string) => `/api/invoices/${invoiceId}/preview`),
}));

const routerMocks = vi.hoisted(() => ({
  useNavigate: vi.fn(),
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
    downloadBatchFile: apiMocks.downloadBatchFile,
    createExport: apiMocks.createExport,
    openRuntimePath: apiMocks.openRuntimePath,
    createReviewAction: apiMocks.createReviewAction,
    getCurrentActor: apiMocks.getCurrentActor,
    getActiveConfig: apiMocks.getActiveConfig,
    listRuleVersions: apiMocks.listRuleVersions,
    createRuleVersion: apiMocks.createRuleVersion,
    createInitialSetup: apiMocks.createInitialSetup,
    publishConfigBundle: apiMocks.publishConfigBundle,
    listConfigBundles: apiMocks.listConfigBundles,
    getErrorMessage: apiMocks.getErrorMessage,
    getInvoicePreviewUrl: apiMocks.getInvoicePreviewUrl,
  };
});

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>("react-router-dom");
  return {
    ...actual,
    useNavigate: routerMocks.useNavigate,
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
    routerMocks.useNavigate.mockReturnValue(vi.fn());
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
    apiMocks.downloadBatchFile.mockResolvedValue({
      blob: new Blob(["mock export"], {
        type: "application/zip",
      }),
      filename: "mock-export.zip",
      contentType: "application/zip",
    });
    apiMocks.createExport.mockResolvedValue({
      export_type: "excel_manifest",
      status: "completed",
      output_path: "exports/manifest.xlsx",
      summary: {},
    });
    apiMocks.openRuntimePath.mockResolvedValue({
      requested_path: "exports/manifest.xlsx",
      opened_path: "data/exports",
    });
    apiMocks.getCurrentActor.mockResolvedValue({
      actor_id: "trusted-actor-1",
      display_name: "后端可信身份",
      roles: ["config_admin", "reviewer", "exporter"],
    });
    apiMocks.getActiveConfig.mockResolvedValue({
      active_snapshot: {
        tax_profile: {
          id: "tax-v1",
          version_no: "tax-v1",
          content: {
            company_name: "示例科技有限公司",
            buyer_name: "示例科技有限公司",
            buyer_tax_no: "91310000123456789X",
          },
          changed_by: "后端可信身份",
          change_summary: "初始化税务档案",
          change_reason: "首次配置",
        },
        business_rules: {
          id: "rules-v1",
          version_no: "rules-v1",
          content: {
            template_name: "strict_v1",
            display_name: "严格校验",
            minimum_confidence: 0.92,
          },
          changed_by: "后端可信身份",
          change_summary: "初始化业务规则",
          change_reason: "首次配置",
        },
        naming_rules: {
          id: "naming-v1",
          version_no: "naming-v1",
          content: {
            pattern: "{{date}}-{{seller}}-{{amount}}",
          },
          changed_by: "后端可信身份",
          change_summary: "初始化命名规则",
          change_reason: "首次配置",
        },
      },
      active_versions: {
        tax_profile: {
          id: "tax-v1",
          kind: "tax_profile",
          version_no: "tax-v1",
          content: {},
          is_active: true,
          change_summary: "初始化税务档案",
          changed_by: "后端可信身份",
          changed_at: "2026-04-20T10:00:00Z",
          change_reason: "首次配置",
        },
        business_rules: {
          id: "rules-v1",
          kind: "business_rules",
          version_no: "rules-v1",
          content: {},
          is_active: true,
          change_summary: "初始化业务规则",
          changed_by: "后端可信身份",
          changed_at: "2026-04-20T10:01:00Z",
          change_reason: "首次配置",
        },
        naming_rules: {
          id: "naming-v1",
          kind: "naming_rules",
          version_no: "naming-v1",
          content: {},
          is_active: true,
          change_summary: "初始化命名规则",
          changed_by: "后端可信身份",
          changed_at: "2026-04-20T10:02:00Z",
          change_reason: "首次配置",
        },
      },
      setup_status: {
        complete: true,
        default_business_rule_templates: {
          strict_v1: {
            template_name: "strict_v1",
            display_name: "严格校验",
            minimum_confidence: 0.92,
          },
          balanced_v1: {
            template_name: "balanced_v1",
            display_name: "平衡模式",
            minimum_confidence: 0.85,
          },
        },
        missing_required_fields: {
          tax_profile: [],
          business_rules: [],
          naming_rules: [],
        },
      },
    });
    apiMocks.listRuleVersions.mockResolvedValue([]);
    apiMocks.listConfigBundles.mockResolvedValue([
      {
        bundle_version_no: "bundle-20260420-001",
        profile: {
          company_name: "示例科技有限公司",
          taxpayer_id: "91310000123456789X",
        },
        review_policy: {
          template_name: "strict_v1",
          display_name: "严格校验",
        },
        naming_policy: {
          pattern: "{{date}}-{{seller}}-{{amount}}",
        },
        changed_by: "后端可信身份",
        changed_at: "2026-04-20T10:03:00Z",
        change_summary: "初始化配置包",
        change_reason: "首次配置",
        component_versions: {},
      },
    ]);
    apiMocks.createRuleVersion.mockImplementation(async ({ kind, content }: { kind: string; content: Record<string, unknown> }) => ({
      id: `${kind}-new`,
      kind,
      version_no: `${kind}-new`,
      content,
      is_active: true,
      change_summary: "首次配置",
      changed_by: "后端可信身份",
      changed_at: "2026-04-21T09:00:00Z",
      change_reason: "首次配置",
    }));
    apiMocks.createInitialSetup.mockResolvedValue({
      items: {
        tax_profile: {
          id: "tax_profile-new",
          kind: "tax_profile",
          version_no: "tax_profile-new",
          content: {
            company_name: "示例科技有限公司",
            buyer_name: "示例科技有限公司",
            buyer_tax_no: "91310000123456789X",
          },
          is_active: true,
          change_summary: "首次配置",
          changed_by: "后端可信身份",
          changed_at: "2026-04-21T09:00:00Z",
          change_reason: "首次配置",
        },
        business_rules: {
          id: "business_rules-new",
          kind: "business_rules",
          version_no: "business_rules-new",
          content: {
            template_name: "balanced_v1",
            display_name: "平衡模式",
            minimum_confidence: 0.88,
          },
          is_active: true,
          change_summary: "首次配置",
          changed_by: "后端可信身份",
          changed_at: "2026-04-21T09:00:00Z",
          change_reason: "首次配置",
        },
        naming_rules: {
          id: "naming_rules-new",
          kind: "naming_rules",
          version_no: "naming_rules-new",
          content: {
            pattern: "{{date}}-{{buyer}}-{{amount}}",
          },
          is_active: true,
          change_summary: "首次配置",
          changed_by: "后端可信身份",
          changed_at: "2026-04-21T09:00:00Z",
          change_reason: "首次配置",
        },
      },
      setup_status: {
        complete: true,
        default_business_rule_templates: {},
        missing_required_fields: {
          tax_profile: [],
          business_rules: [],
          naming_rules: [],
        },
      },
    });
    apiMocks.publishConfigBundle.mockResolvedValue({
      bundle: {
        bundle_version_no: "bundle-20260425-001",
        profile: {},
        review_policy: {},
        naming_policy: {},
        changed_by: "后端可信身份",
        changed_at: "2026-04-25T10:00:00Z",
        change_summary: "更新配置",
        change_reason: "财务信息变更",
        component_versions: {},
      },
      items: {},
      setup_status: {
        complete: true,
        default_business_rule_templates: {},
        missing_required_fields: {
          tax_profile: [],
          business_rules: [],
          naming_rules: [],
        },
      },
    });
    window.localStorage.setItem("invoice-assistant/default-operator-name", "前端伪造姓名");
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
        invoice_file_count: 1,
        attachment_file_count: 2,
        attachment_status_counts: { consumed: 1, unmatched: 1 },
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
    expect(screen.getByText("清单附件 2")).toBeInTheDocument();
    expect(screen.getByText("已消费 1")).toBeInTheDocument();
    expect(screen.getByText("未匹配 1")).toBeInTheDocument();
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
        invoice_file_count: 3,
        attachment_file_count: 0,
        attachment_status_counts: {},
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
        invoice_file_count: 2,
        attachment_file_count: 1,
        attachment_status_counts: { pending_match: 1 },
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

  it("guides operators to finish setup before creating a batch", async () => {
    let resolveConfig: ((value: unknown) => void) | null = null;
    apiMocks.getActiveConfig.mockImplementation(
      () =>
        new Promise((resolve) => {
          resolveConfig = resolve;
        }),
    );

    const navigateMock = vi.fn();
    routerMocks.useNavigate.mockReturnValue(navigateMock);

    renderWithProviders(<BatchWorkbench />);

    expect(await screen.findByText("正在检查首次配置状态")).toBeInTheDocument();
    expect(screen.getByText("首次配置状态未确认前，上传入口会保持禁用。")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "创建批次" })).toBeDisabled();

    const applyConfig = resolveConfig as ((value: unknown) => void) | null;
    if (!applyConfig) {
      throw new Error("getActiveConfig resolver was not captured");
    }

    applyConfig({
      active_snapshot: {},
      active_versions: {
        tax_profile: {
          id: "tax-draft",
          kind: "tax_profile",
          version_no: "tax-draft",
          content: {},
          is_active: false,
          change_summary: "草稿",
          changed_by: "后端可信身份",
          changed_at: "2026-04-20T10:02:00Z",
          change_reason: "首次配置",
        },
      },
      setup_status: {
        complete: false,
        default_business_rule_templates: {
          strict_v1: {
            template_name: "strict_v1",
            display_name: "严格校验",
            minimum_confidence: 0.92,
          },
        },
        missing_required_fields: {
          tax_profile: ["buyer_name", "buyer_tax_no"],
          business_rules: ["template_name"],
          naming_rules: ["pattern"],
        },
      },
    });

    await waitFor(() => {
      expect(navigateMock).toHaveBeenCalledWith("/setup");
    });
    expect(await screen.findByText("首次配置未完成")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "前往首次配置" })).toBeInTheDocument();
  });

  it("completes the first-run setup wizard through the atomic setup endpoint", async () => {
    const messageSuccess = vi.fn();
    vi.spyOn(AntdApp, "useApp").mockReturnValue({
      message: { success: messageSuccess, error: vi.fn(), warning: vi.fn(), info: vi.fn(), open: vi.fn(), destroy: vi.fn(), loading: vi.fn() },
      notification: {} as never,
      modal: {} as never,
    });

    apiMocks.getActiveConfig.mockResolvedValue({
      active_snapshot: {},
      active_versions: {
        tax_profile: {
          id: "tax-draft",
          kind: "tax_profile",
          version_no: "tax-draft",
          content: {},
          is_active: false,
          change_summary: "草稿",
          changed_by: "后端可信身份",
          changed_at: "2026-04-20T10:02:00Z",
          change_reason: "首次配置",
        },
      },
      setup_status: {
        complete: false,
        default_business_rule_templates: {
          strict_v1: {
            template_name: "strict_v1",
            display_name: "严格校验",
            minimum_confidence: 0.92,
          },
          balanced_v1: {
            template_name: "balanced_v1",
            display_name: "平衡模式",
            minimum_confidence: 0.85,
          },
        },
        missing_required_fields: {
          tax_profile: ["buyer_name", "buyer_tax_no"],
          business_rules: ["template_name"],
          naming_rules: ["pattern"],
        },
      },
    });

    const navigateMock = vi.fn();
    routerMocks.useNavigate.mockReturnValue(navigateMock);

    renderWithProviders(<SetupWizard />);

    expect(await screen.findByText("首次配置向导")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("企业名称"), { target: { value: "示例科技有限公司" } });
    fireEvent.change(screen.getByLabelText("纳税人识别号（税号）"), { target: { value: "91310000123456789X" } });
    fireEvent.change(screen.getByLabelText("地址电话"), { target: { value: "上海市徐汇区示例路 1 号 021-12345678" } });
    fireEvent.change(screen.getByLabelText("开户行及帐号"), { target: { value: "招商银行上海示例支行 1234567890" } });
    fireEvent.click(screen.getByRole("button", { name: "下一步" }));

    expect(await screen.findByText("业务规则模板")).toBeInTheDocument();
    expect(screen.getByText("这一步会影响系统建议、人工确认量和拦截倾向。")).toBeInTheDocument();
    expect(screen.getByText("保守模板：更容易把可疑票据拦下来，误放行更少，但需要人工复核的票会更多。")).toBeInTheDocument();
    expect(screen.getByText("常规模板：更适合日常批量处理，拦截和放行更均衡，人工复核量通常更可控。")).toBeInTheDocument();
    fireEvent.mouseDown(screen.getByLabelText("模板方案"));
    fireEvent.click(await screen.findByText("平衡模式"));
    expect(screen.queryByLabelText("最低置信度阈值")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "下一步" }));

    expect(await screen.findByText("命名规则")).toBeInTheDocument();
    expect(screen.getByText("这一步会影响归档文件名与后续人工检索。")).toBeInTheDocument();
    expect(screen.getByText("当前命名方式：日期-购方-金额")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "下一步" }));

    expect(await screen.findByText("摘要确认")).toBeInTheDocument();
    expect(screen.getAllByText("示例科技有限公司").length).toBeGreaterThan(0);
    expect(screen.getByText(/平衡模式/)).toBeInTheDocument();
    expect(screen.getByText("文件命名方式")).toBeInTheDocument();
    expect(screen.getByText("日期-购方-金额")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "完成配置" }));

    await waitFor(() => {
      expect(apiMocks.createInitialSetup).toHaveBeenCalledTimes(1);
    });
    expect(apiMocks.createInitialSetup).toHaveBeenCalledWith({
      taxProfile: {
        company_name: "示例科技有限公司",
        taxpayer_id: "91310000123456789X",
        address_phone: "上海市徐汇区示例路 1 号 021-12345678",
        bank_account: "招商银行上海示例支行 1234567890",
      },
      businessRules: {
        template_name: "balanced_v1",
        display_name: "平衡模式",
        minimum_confidence: 0.85,
      },
      namingRules: {
        pattern: "{{date}}-{{buyer}}-{{amount}}",
      },
      changeSummary: "首次配置",
      changeReason: "首次配置向导",
    });
    expect(navigateMock).toHaveBeenCalledWith("/");
  });

  it("keeps the setup wizard finance-friendly instead of exposing raw threshold inputs", async () => {
    apiMocks.getActiveConfig.mockResolvedValue({
      active_snapshot: {},
      active_versions: {},
      setup_status: {
        complete: false,
        default_business_rule_templates: {
          regular: {
            template_name: "regular",
            display_name: "常规模板",
            minimum_confidence: 0.75,
          },
        },
        missing_required_fields: {
          tax_profile: ["buyer_name", "buyer_tax_no"],
          business_rules: ["template_name"],
          naming_rules: ["pattern"],
        },
      },
    });

    renderWithProviders(<SetupWizard />);

    expect(await screen.findByText("首次配置向导")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("企业名称"), { target: { value: "示例科技有限公司" } });
    fireEvent.change(screen.getByLabelText("纳税人识别号（税号）"), { target: { value: "91310000123456789X" } });
    fireEvent.change(screen.getByLabelText("地址电话"), { target: { value: "上海市徐汇区示例路 1 号 021-12345678" } });
    fireEvent.change(screen.getByLabelText("开户行及帐号"), { target: { value: "招商银行上海示例支行 1234567890" } });
    fireEvent.click(screen.getByRole("button", { name: "下一步" }));

    expect(await screen.findByText("业务规则模板")).toBeInTheDocument();
    expect(screen.getByText("审核倾向")).toBeInTheDocument();
    expect(screen.queryByLabelText("最低置信度阈值")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "下一步" }));

    expect(await screen.findByText("命名规则")).toBeInTheDocument();
    expect(screen.getByText("当前命名方式：日期-购方-金额")).toBeInTheDocument();
  });

  it("keeps upload blocked and shows config read failure instead of incomplete setup", async () => {
    apiMocks.getActiveConfig.mockRejectedValue(new Error("配置读取失败"));
    const navigateMock = vi.fn();
    routerMocks.useNavigate.mockReturnValue(navigateMock);

    renderWithProviders(<BatchWorkbench />);

    expect(await screen.findByText("配置状态读取失败")).toBeInTheDocument();
    expect(screen.getByText("当前无法确认首次配置是否完成，请先重试配置读取。")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "创建批次" })).toBeDisabled();
    expect(screen.queryByText("首次配置未完成")).not.toBeInTheDocument();
    expect(navigateMock).not.toHaveBeenCalledWith("/setup");
  });

  it("removes editable operator inputs from upload, review, and config forms", async () => {
    const { rerender } = renderWithProviders(<UploadPanel onCreated={vi.fn()} />);
    expect(await screen.findByText("新建批次")).toBeInTheDocument();
    expect(screen.queryByLabelText("操作者")).not.toBeInTheDocument();

    rerender(
      <AppProviders>
        <MemoryRouter>
          <ReviewActions
            invoiceId="invoice-review-1"
            processingStatus="completed"
            systemDecision="review_required"
            duplicateFlag={false}
            reviewStatus="not_reviewed"
            onSubmitted={vi.fn()}
          />
        </MemoryRouter>
      </AppProviders>,
    );
    expect(screen.queryByLabelText("操作者")).not.toBeInTheDocument();

    rerender(
      <AppProviders>
        <MemoryRouter>
          <RuleVersionPanel
            kind="tax_profile"
            title="公司税务档案"
            subtitle="维护购方名称、税号等核验基线"
            activeVersion={undefined}
            versions={[]}
            onUpdated={vi.fn()}
          />
        </MemoryRouter>
      </AppProviders>,
    );
    expect(screen.queryByLabelText("操作者")).not.toBeInTheDocument();
    expect(screen.queryByDisplayValue("前端伪造姓名")).not.toBeInTheDocument();
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
        invoice_file_count: 1,
        attachment_file_count: 2,
        attachment_status_counts: { consumed: 1, unmatched: 1 },
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
      invoice_file_count: 1,
      attachment_file_count: 2,
      attachment_status_counts: { consumed: 1, unmatched: 1 },
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
          basic_compliance_status: "不通过",
          business_compliance_status: "不通过",
          final_decision: "处理失败",
          decision_reasons: ["OCR timed out"],
          suggested_actions: ["修复失败原因后重试"],
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

    expect(await screen.findByText("清单附件 2")).toBeInTheDocument();
    expect(screen.getByText("已消费 1")).toBeInTheDocument();
    expect(screen.getByText("未匹配 1")).toBeInTheDocument();
    const retryButton = await screen.findByRole("button", { name: "重新处理待补充发票" });
    fireEvent.click(retryButton);

    await waitFor(() => {
      expect(apiMocks.createBatchRetry).toHaveBeenCalledWith({ batchId: "batch-1" });
    });
  });

  it("downloads the current manifest through the save picker from batch results", async () => {
    const write = vi.fn().mockResolvedValue(undefined);
    const close = vi.fn().mockResolvedValue(undefined);
    const createWritable = vi.fn().mockResolvedValue({ write, close });
    const showSaveFilePicker = vi.fn().mockResolvedValue({ createWritable });
    vi.stubGlobal("showSaveFilePicker", showSaveFilePicker);

    apiMocks.listBatches.mockResolvedValue([
      {
        id: "batch-export-1",
        batch_no: "BATCH-EXPORT-001",
        created_at: "2026-04-19T09:00:00Z",
        created_by: "tester",
        status: "completed",
        total_files: 2,
        completed_files: 2,
        processing_files: 0,
        failed_files: 0,
        suggested_pass_count: 1,
        suggested_pass_total_amount: "88.00",
        export_manifest_path: null,
        invoice_file_count: 2,
        attachment_file_count: 0,
        attachment_status_counts: {},
      },
    ]);
    apiMocks.getBatch.mockResolvedValue({
      id: "batch-export-1",
      batch_no: "BATCH-EXPORT-001",
      created_at: "2026-04-19T09:00:00Z",
      created_by: "tester",
      status: "completed",
      total_files: 2,
      completed_files: 2,
      processing_files: 0,
      failed_files: 0,
      suggested_pass_count: 1,
      suggested_pass_total_amount: "88.00",
      export_manifest_path: null,
      invoice_file_count: 2,
      attachment_file_count: 0,
      attachment_status_counts: {},
      progress: {
        batch_id: "batch-export-1",
        batch_no: "BATCH-EXPORT-001",
        stage_code: "completed",
        stage_text: "处理完成",
        progress_percent: 100,
        total_files: 2,
        completed_files: 2,
        processing_files: 0,
        failed_files: 0,
        suggested_pass_count: 1,
        suggested_pass_total_amount: "88.00",
        recent_failures: [],
      },
      export_jobs: [],
    });
    apiMocks.listBatchInvoices.mockResolvedValue({
      items: [],
      status_counts: {},
      batch_summary: { count: 1, total_amount: "88.00" },
      filtered_summary: { count: 1, total_amount: "88.00" },
    });
    apiMocks.downloadBatchFile.mockResolvedValue({
      blob: new Blob(["manifest"], {
        type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
      }),
      filename: "BATCH-EXPORT-001.xlsx",
      contentType: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    });

    const router = createMemoryRouter(appRoutes, {
      initialEntries: ["/results/batch-export-1"],
    });

    render(
      <AppProviders>
        <RouterProvider router={router} />
      </AppProviders>,
    );

    expect(await screen.findByText("BATCH-EXPORT-001")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "另存为当前结果台账" }));

    await waitFor(() => {
      expect(apiMocks.downloadBatchFile).toHaveBeenCalledWith({
        batchId: "batch-export-1",
        downloadFormat: "excel_manifest",
        selectionMode: "all",
        displayStatus: undefined,
        invoiceIds: undefined,
      });
    });
    await waitFor(() => {
      expect(showSaveFilePicker).toHaveBeenCalled();
      expect(createWritable).toHaveBeenCalled();
      expect(write).toHaveBeenCalled();
      expect(close).toHaveBeenCalled();
    });
  });

  it("downloads selected invoices as zip from batch results", async () => {
    const createWritable = vi.fn().mockResolvedValue({
      write: vi.fn().mockResolvedValue(undefined),
      close: vi.fn().mockResolvedValue(undefined),
    });
    vi.stubGlobal("showSaveFilePicker", vi.fn().mockResolvedValue({ createWritable }));

    apiMocks.listBatches.mockResolvedValue([
      {
        id: "batch-export-selected-1",
        batch_no: "BATCH-EXPORT-SELECTED-001",
        created_at: "2026-04-19T09:00:00Z",
        created_by: "tester",
        status: "completed",
        total_files: 1,
        completed_files: 1,
        processing_files: 0,
        failed_files: 0,
        suggested_pass_count: 1,
        suggested_pass_total_amount: "66.00",
        export_manifest_path: null,
        invoice_file_count: 1,
        attachment_file_count: 0,
        attachment_status_counts: {},
      },
    ]);
    apiMocks.getBatch.mockResolvedValue({
      id: "batch-export-selected-1",
      batch_no: "BATCH-EXPORT-SELECTED-001",
      created_at: "2026-04-19T09:00:00Z",
      created_by: "tester",
      status: "completed",
      total_files: 1,
      completed_files: 1,
      processing_files: 0,
      failed_files: 0,
      suggested_pass_count: 1,
      suggested_pass_total_amount: "66.00",
      export_manifest_path: null,
      invoice_file_count: 1,
      attachment_file_count: 0,
      attachment_status_counts: {},
      progress: {
        batch_id: "batch-export-selected-1",
        batch_no: "BATCH-EXPORT-SELECTED-001",
        stage_code: "completed",
        stage_text: "处理完成",
        progress_percent: 100,
        total_files: 1,
        completed_files: 1,
        processing_files: 0,
        failed_files: 0,
        suggested_pass_count: 1,
        suggested_pass_total_amount: "66.00",
        recent_failures: [],
      },
      export_jobs: [],
    });
    apiMocks.listBatchInvoices.mockResolvedValue({
      items: [
        {
          id: "invoice-selected-1",
          batch_id: "batch-export-selected-1",
          original_filename: "selected.pdf",
          renamed_filename: "2026-04-19-示例-66.00.pdf",
          storage_path_original: null,
          storage_path_renamed: null,
          invoice_code: null,
          invoice_number: "12345678",
          seller_name: null,
          buyer_name: "示例科技有限公司",
          buyer_tax_no: "91310000123456789X",
          invoice_date: "2026-04-19",
          invoice_amount: "66.00",
          processing_status: "completed",
          system_decision: "suggested_pass",
          review_status: "not_reviewed",
          artifact_status: "renamed",
          duplicate_flag: false,
          duplicate_group_key: null,
          risk_flags: [],
          display_status: "系统建议通过",
          basic_compliance_status: "通过",
          business_compliance_status: "低风险",
          final_decision: "系统建议通过",
          decision_reasons: [],
          suggested_actions: ["可直接归档"],
          problem_count: 0,
          failure_reason: null,
          preview_path: "selected.pdf",
          attachments: [],
        },
      ],
      status_counts: { 系统建议通过: 1 },
      batch_summary: { count: 1, total_amount: "66.00" },
      filtered_summary: { count: 1, total_amount: "66.00" },
    });
    apiMocks.downloadBatchFile.mockResolvedValue({
      blob: new Blob(["zip"], {
        type: "application/zip",
      }),
      filename: "selected.zip",
      contentType: "application/zip",
    });

    const router = createMemoryRouter(appRoutes, {
      initialEntries: ["/results/batch-export-selected-1"],
    });

    render(
      <AppProviders>
        <RouterProvider router={router} />
      </AppProviders>,
    );

    expect(await screen.findByText("selected.pdf")).toBeInTheDocument();

    const checkboxes = screen.getAllByRole("checkbox");
    fireEvent.click(checkboxes[1]);
    fireEvent.click(screen.getByRole("button", { name: "另存为勾选发票 ZIP" }));

    await waitFor(() => {
      expect(apiMocks.downloadBatchFile).toHaveBeenCalledWith({
        batchId: "batch-export-selected-1",
        downloadFormat: "zip",
        selectionMode: "selected",
        displayStatus: undefined,
        invoiceIds: ["invoice-selected-1"],
      });
    });
  });

  it("shows field-based settings summary after setup completes", async () => {
    renderWithProviders(<Settings />);

    expect(await screen.findByText("配置中心")).toBeInTheDocument();
    expect(screen.getByText("当前页已隐藏技术配置 JSON，避免要求财务用户直接编辑系统键名。")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "按字段修改配置" })).toBeInTheDocument();
    expect(screen.getByText("公司税务档案")).toBeInTheDocument();
    expect(screen.queryByText("{{date}}-{{seller}}-{{amount}}")).not.toBeInTheDocument();
    expect(screen.queryByText("0.92")).not.toBeInTheDocument();
    expect(screen.queryByText("高级版本管理")).not.toBeInTheDocument();
  });

  it("edits active settings through the shared field form without leaving settings", async () => {
    const messageSuccess = vi.fn();
    vi.spyOn(AntdApp, "useApp").mockReturnValue({
      message: { success: messageSuccess, error: vi.fn(), warning: vi.fn(), info: vi.fn(), open: vi.fn(), destroy: vi.fn(), loading: vi.fn() },
      notification: {} as never,
      modal: {} as never,
    });
    const navigateMock = vi.fn();
    routerMocks.useNavigate.mockReturnValue(navigateMock);

    renderWithProviders(<Settings />);

    fireEvent.click(await screen.findByRole("button", { name: "按字段修改配置" }));

    expect(await screen.findByText("字段化调整")).toBeInTheDocument();
    expect(screen.getByDisplayValue("示例科技有限公司")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("企业名称"), { target: { value: "更新后的示例科技有限公司" } });
    fireEvent.click(screen.getByRole("button", { name: "下一步" }));
    expect(await screen.findByText("业务规则模板")).toBeInTheDocument();
    fireEvent.click(await screen.findByRole("button", { name: "下一步" }));
    expect(await screen.findByText("命名规则")).toBeInTheDocument();
    fireEvent.click(await screen.findByRole("button", { name: "下一步" }));
    expect(await screen.findByText("摘要确认")).toBeInTheDocument();
    fireEvent.click(await screen.findByRole("button", { name: "保存配置" }));
    expect(await screen.findByText("发布确认")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("变更摘要"), { target: { value: "更新公司税务资料" } });
    fireEvent.change(screen.getByLabelText("变更原因"), { target: { value: "财务信息更新" } });
    fireEvent.click(screen.getByRole("button", { name: "确认发布" }));

    await waitFor(() => {
      expect(apiMocks.publishConfigBundle).toHaveBeenCalledTimes(1);
    });
    expect(apiMocks.publishConfigBundle).toHaveBeenCalledWith({
      profile: {
        company_name: "更新后的示例科技有限公司",
        taxpayer_id: "91310000123456789X",
        address_phone: "",
        bank_account: "",
      },
      reviewPolicy: {
        template_name: "strict_v1",
        display_name: "严格校验",
        minimum_confidence: 0.92,
      },
      namingPolicy: {
        pattern: "{{date}}-{{seller}}-{{amount}}",
      },
      changeSummary: "更新公司税务资料",
      changeReason: "财务信息更新",
    });
    expect(messageSuccess).toHaveBeenCalledWith("配置已发布。");
    expect(navigateMock).not.toHaveBeenCalledWith("/setup");
  });

  it("shows publish confirmation before saving edited settings", async () => {
    const messageSuccess = vi.fn();
    vi.spyOn(AntdApp, "useApp").mockReturnValue({
      message: { success: messageSuccess, error: vi.fn(), warning: vi.fn(), info: vi.fn(), open: vi.fn(), destroy: vi.fn(), loading: vi.fn() },
      notification: {} as never,
      modal: {} as never,
    });

    renderWithProviders(<Settings />);

    fireEvent.click(await screen.findByRole("button", { name: "按字段修改配置" }));
    fireEvent.change(screen.getByLabelText("企业名称"), { target: { value: "更新后的示例科技有限公司" } });
    fireEvent.click(screen.getByRole("button", { name: "下一步" }));
    fireEvent.click(await screen.findByRole("button", { name: "下一步" }));
    fireEvent.click(await screen.findByRole("button", { name: "下一步" }));
    fireEvent.click(await screen.findByRole("button", { name: "保存配置" }));

    expect(await screen.findByText("发布确认")).toBeInTheDocument();
    expect(screen.getByText("影响范围")).toBeInTheDocument();
    expect(screen.getByText("变更原因")).toBeInTheDocument();
    expect(screen.getByText("税务档案、审核策略、文件命名会整体生成新版本并立即生效。")).toBeInTheDocument();
    expect(apiMocks.publishConfigBundle).not.toHaveBeenCalled();

    fireEvent.change(screen.getByLabelText("变更摘要"), { target: { value: "更新公司税务资料" } });
    fireEvent.change(screen.getByLabelText("变更原因"), { target: { value: "财务信息更新" } });
    fireEvent.click(screen.getByRole("button", { name: "确认发布" }));

    await waitFor(() => {
      expect(apiMocks.publishConfigBundle).toHaveBeenCalledWith({
        profile: {
          company_name: "更新后的示例科技有限公司",
          taxpayer_id: "91310000123456789X",
          address_phone: "",
          bank_account: "",
        },
        reviewPolicy: {
          template_name: "strict_v1",
          display_name: "严格校验",
          minimum_confidence: 0.92,
        },
        namingPolicy: {
          pattern: "{{date}}-{{seller}}-{{amount}}",
        },
        changeSummary: "更新公司税务资料",
        changeReason: "财务信息更新",
      });
    });
    expect(messageSuccess).toHaveBeenCalledWith("配置已发布。");
  });

  it("shows config bundle history as a read-only view", async () => {
    renderWithProviders(<Settings />);

    expect(await screen.findByRole("button", { name: "查看历史变更" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "查看历史变更" }));

    expect(await screen.findByText("历史变更")).toBeInTheDocument();
    expect(screen.getByText("bundle-20260420-001")).toBeInTheDocument();
    expect(screen.getByText("初始化配置包")).toBeInTheDocument();
    expect(screen.getByText("首次配置")).toBeInTheDocument();
    expect(screen.getByText("历史版本仅供查阅，不允许直接编辑。")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "编辑该版本" })).not.toBeInTheDocument();
  });

  it("shows completion action and last modified time on setup status card after setup", async () => {
    renderWithProviders(
      <SetupStatusCard
        config={{
          active_snapshot: {
            tax_profile: {
              id: "tax-v1",
              version_no: "tax-v1",
              content: {
                buyer_name: "示例科技有限公司",
                buyer_tax_no: "91310000123456789X",
              },
              changed_by: "后端可信身份",
              change_summary: "初始化税务档案",
              change_reason: "首次配置",
            },
            business_rules: {
              id: "rules-v1",
              version_no: "rules-v1",
              content: {
                template_name: "strict_v1",
                display_name: "严格校验",
                minimum_confidence: 0.92,
              },
              changed_by: "后端可信身份",
              change_summary: "初始化业务规则",
              change_reason: "首次配置",
            },
            naming_rules: {
              id: "naming-v1",
              version_no: "naming-v1",
              content: {
                pattern: "{{date}}-{{seller}}-{{amount}}",
              },
              changed_by: "后端可信身份",
              change_summary: "初始化命名规则",
              change_reason: "首次配置",
            },
          },
          active_versions: {
            tax_profile: {
              id: "tax-v1",
              kind: "tax_profile",
              version_no: "tax-v1",
              content: {},
              is_active: true,
              change_summary: "初始化税务档案",
              changed_by: "后端可信身份",
              changed_at: "2026-04-20T10:00:00Z",
              change_reason: "首次配置",
            },
            business_rules: {
              id: "rules-v1",
              kind: "business_rules",
              version_no: "rules-v1",
              content: {},
              is_active: true,
              change_summary: "初始化业务规则",
              changed_by: "后端可信身份",
              changed_at: "2026-04-20T10:01:00Z",
              change_reason: "首次配置",
            },
            naming_rules: {
              id: "naming-v1",
              kind: "naming_rules",
              version_no: "naming-v1",
              content: {},
              is_active: true,
              change_summary: "初始化命名规则",
              changed_by: "后端可信身份",
              changed_at: "2026-04-20T10:02:00Z",
              change_reason: "首次配置",
            },
          },
          setup_status: {
            complete: true,
            default_business_rule_templates: {},
            missing_required_fields: {
              tax_profile: [],
              business_rules: [],
              naming_rules: [],
            },
          },
        }}
        showAction
        onOpenWorkbench={vi.fn()}
        onOpenSetup={vi.fn()}
      />,
    );

    expect(await screen.findByText("首次配置已完成")).toBeInTheDocument();
    expect(screen.getByText("去处理发票")).toBeInTheDocument();
    expect(screen.getByText("最后修改于 2026-04-20 10:02")).toBeInTheDocument();
  });

  it("keeps invoice diagnostics behind the advanced tab and retries a single failed invoice", async () => {
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
      basic_compliance_status: "不通过",
      business_compliance_status: "不通过",
      final_decision: "处理失败",
      decision_reasons: ["OCR timed out"],
      suggested_actions: ["修复失败原因后重试"],
      problem_count: 1,
      failure_reason: "OCR timed out",
      preview_path: null,
      attachments: [
        {
          id: "attachment-1",
          batch_id: "batch-1",
          original_filename: "broken-销货清单.pdf",
          attachment_status: "parse_failed",
          attachment_status_label: "解析失败",
          matched_invoice_id: null,
          match_reason: "OCR parser timed out while parsing attachment.",
        },
      ],
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

    expect(await screen.findByText("处理结论")).toBeInTheDocument();
    expect(screen.getAllByText("需补充/重试").length).toBeGreaterThan(0);
    expect(screen.getByText("修复失败原因后重试")).toBeInTheDocument();
    expect(screen.getByText("broken-销货清单.pdf")).toBeInTheDocument();
    expect(screen.getByText("解析失败")).toBeInTheDocument();
    expect(screen.getByText("OCR parser timed out while parsing attachment.")).toBeInTheDocument();
    expect(screen.queryByText("rapidocr-onnxruntime")).not.toBeInTheDocument();
    expect(screen.queryByText("ocr_timeout")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("tab", { name: "高级诊断" }));

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
