import { App, Button, Progress, Select, Space, Statistic, Tag, Typography } from "../app/antd";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { createBatchRetry, downloadBatchFile, getBatch, getErrorMessage, listBatchInvoices, listBatches } from "../app/api";
import type { Batch, BatchInvoiceListing } from "../app/types";
import { AsyncBoundary } from "../components/common/AsyncBoundary";
import { SectionHeader } from "../components/common/SectionHeader";
import { InvoiceDrawer } from "../components/results/InvoiceDrawer";
import { ResultTable } from "../components/results/ResultTable";
import {
  RESULT_FILTER_OPTIONS,
  type ResultFilterValue,
  getResultFilterCount,
  toDisplayStatusFilter,
} from "../components/results/resultPresentation";


const ACTIVE_BATCH_STAGE_CODES = new Set([
  "queued",
  "processing",
  "recovering",
  "text_extraction",
  "ocr_processing",
  "classification",
  "duplicate_check",
  "finalization",
]);
const ATTACHMENT_STATUS_LABELS: Record<string, string> = {
  pending_match: "待匹配",
  matched: "已匹配",
  consumed: "已消费",
  ambiguous: "匹配歧义",
  unmatched: "未匹配",
  parse_failed: "解析失败",
};

interface InvoiceState {
  loading: boolean;
  error: string | null;
  data: BatchInvoiceListing | null;
}

function isActiveBatch(batch: Batch | null | undefined) {
  if (!batch) {
    return false;
  }
  const stageCode = batch.progress?.stage_code;
  if (stageCode && ACTIVE_BATCH_STAGE_CODES.has(stageCode)) {
    return true;
  }
  return batch.status === "queued" || batch.status === "processing";
}

async function saveBlobToUserFile(params: {
  blob: Blob;
  filename: string;
  contentType: string;
}) {
  const pickerWindow = window as Window & {
    showSaveFilePicker?: (options?: Record<string, unknown>) => Promise<{
      createWritable: () => Promise<{
        write: (data: Blob) => Promise<void>;
        close: () => Promise<void>;
      }>;
    }>;
  };

  if (typeof pickerWindow.showSaveFilePicker === "function") {
    const extension = params.filename.includes(".") ? `.${params.filename.split(".").pop()}` : "";
    const handle = await pickerWindow.showSaveFilePicker({
      suggestedName: params.filename,
      types: [
        {
          description: params.contentType,
          accept: {
            [params.contentType]: extension ? [extension] : [],
          },
        },
      ],
    });
    const writable = await handle.createWritable();
    await writable.write(params.blob);
    await writable.close();
    return;
  }

  const objectUrl = URL.createObjectURL(params.blob);
  const anchor = document.createElement("a");
  anchor.href = objectUrl;
  anchor.download = params.filename;
  anchor.click();
  URL.revokeObjectURL(objectUrl);
}

export function BatchResults() {
  const { message } = App.useApp();
  const navigate = useNavigate();
  const { batchId } = useParams();
  const [batches, setBatches] = useState<Batch[]>([]);
  const [batchesLoading, setBatchesLoading] = useState(true);
  const [batchesError, setBatchesError] = useState<string | null>(null);
  const [selectedFilter, setSelectedFilter] = useState<ResultFilterValue>("all");
  const [selectedInvoiceId, setSelectedInvoiceId] = useState<string | null>(null);
  const [selectedRowKeys, setSelectedRowKeys] = useState<string[]>([]);
  const [batchDetail, setBatchDetail] = useState<Batch | null>(null);
  const [invoiceState, setInvoiceState] = useState<InvoiceState>({
    loading: false,
    error: null,
    data: null,
  });
  const [savingAction, setSavingAction] = useState<string | null>(null);

  const loadBatches = useCallback(async () => {
    setBatchesLoading(true);
    setBatchesError(null);
    try {
      const items = await listBatches();
      setBatches(items);
    } catch (error) {
      setBatchesError(getErrorMessage(error));
    } finally {
      setBatchesLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadBatches();
  }, [loadBatches]);

  const resolvedBatchId = useMemo(() => {
    if (batchId) {
      return batchId;
    }
    return batches[0]?.id;
  }, [batchId, batches]);

  useEffect(() => {
    if (!batchId && batches.length > 0) {
      navigate(`/results/${batches[0].id}`, { replace: true });
    }
  }, [batchId, batches, navigate]);

  useEffect(() => {
    if (batchId && batches.length > 0 && !batches.some((item) => item.id === batchId)) {
      navigate(`/results/${batches[0].id}`, { replace: true });
    }
  }, [batchId, batches, navigate]);

  const loadResults = useCallback(
    async (nextBatchId: string, nextFilter: ResultFilterValue, options?: { silent?: boolean }) => {
      const silent = options?.silent === true;
      setInvoiceState((current) => ({
        loading: silent ? current.data === null : true,
        error: silent && current.data ? null : current.error,
        data: current.data,
      }));
      try {
        const [detail, listing] = await Promise.all([
          getBatch(nextBatchId),
          listBatchInvoices(nextBatchId, toDisplayStatusFilter(nextFilter)),
        ]);
        setBatchDetail(detail);
        setInvoiceState({
          loading: false,
          error: null,
          data: listing,
        });
      } catch (error) {
        const messageText = getErrorMessage(error);
        setInvoiceState((current) => ({
          loading: false,
          error: current.data && silent ? null : messageText,
          data: current.data && silent ? current.data : null,
        }));
      }
    },
    [],
  );

  useEffect(() => {
    if (resolvedBatchId) {
      void loadResults(resolvedBatchId, selectedFilter);
    }
  }, [loadResults, resolvedBatchId, selectedFilter]);

  useEffect(() => {
    if (!resolvedBatchId || !isActiveBatch(batchDetail)) {
      return undefined;
    }
    const intervalId = window.setInterval(() => {
      void loadBatches();
      void loadResults(resolvedBatchId, selectedFilter, { silent: true });
    }, 2000);
    return () => window.clearInterval(intervalId);
  }, [batchDetail, loadBatches, loadResults, resolvedBatchId, selectedFilter]);

  useEffect(() => {
    const visibleIds = new Set(invoiceState.data?.items.map((item) => item.id) ?? []);
    setSelectedRowKeys((current) => current.filter((item) => visibleIds.has(item)));
  }, [invoiceState.data?.items]);

  const counts = invoiceState.data?.status_counts ?? {};
  const recentFailures = batchDetail?.progress?.recent_failures ?? [];
  const retryableFailures = recentFailures.filter((item) => item.retryable !== false);
  const failedCount = getResultFilterCount(counts, "needs_retry") || batchDetail?.failed_files || 0;
  const attachmentStatusEntries = Object.entries(batchDetail?.attachment_status_counts ?? {}).filter(([, count]) => count > 0);
  const currentResultCount = invoiceState.data?.items.length ?? 0;

  const handleDownload = useCallback(
    async (params: {
      key: string;
      downloadFormat: "zip" | "excel_manifest";
      selectionMode: "all" | "filtered" | "selected";
      requireSelection?: boolean;
    }) => {
      if (!resolvedBatchId) {
        return;
      }
      if (params.requireSelection && selectedRowKeys.length === 0) {
        message.warning("请先勾选要另存的发票。");
        return;
      }

      setSavingAction(params.key);
      try {
        const result = await downloadBatchFile({
          batchId: resolvedBatchId,
          downloadFormat: params.downloadFormat,
          selectionMode: params.selectionMode,
          displayStatus:
            params.selectionMode === "filtered" ? toDisplayStatusFilter(selectedFilter) : undefined,
          invoiceIds: params.selectionMode === "selected" ? selectedRowKeys : undefined,
        });
        await saveBlobToUserFile(result);
        message.success(`已准备保存 ${result.filename}`);
      } catch (error) {
        if (error instanceof DOMException && error.name === "AbortError") {
          message.info("已取消另存为。");
        } else {
          message.error(getErrorMessage(error));
        }
      } finally {
        setSavingAction(null);
      }
    },
    [message, resolvedBatchId, selectedFilter, selectedRowKeys],
  );

  return (
    <div className="page-stack">
      <section className="workspace-block">
        <SectionHeader
          title="批次结果"
          subtitle="按财务动作查看当前批次；系统处理中会自动刷新，确认无误后再另存为。"
          actions={
            <Space wrap>
              <Select
                className="batch-selector"
                value={resolvedBatchId}
                options={batches.map((item) => ({ label: item.batch_no, value: item.id }))}
                loading={batchesLoading}
                onChange={(value) => navigate(`/results/${value}`)}
              />
              <Select value={selectedFilter} options={RESULT_FILTER_OPTIONS} onChange={setSelectedFilter} />
              <Button onClick={() => resolvedBatchId && void loadResults(resolvedBatchId, selectedFilter)} disabled={!resolvedBatchId}>
                刷新
              </Button>
            </Space>
          }
        />

        <AsyncBoundary loading={batchesLoading} error={batchesError}>
          {batchDetail && invoiceState.data ? (
            <div className="results-overview">
              {isActiveBatch(batchDetail) ? (
                <div className="active-batch-strip">
                  <Space wrap>
                    <Tag color="blue">{batchDetail.progress?.stage_text || "处理中"}</Tag>
                    <Typography.Text type="secondary">{`已完成 ${batchDetail.completed_files}/${batchDetail.total_files}`}</Typography.Text>
                    <Typography.Text type="secondary">{`失败 ${batchDetail.failed_files}`}</Typography.Text>
                  </Space>
                  <Progress
                    percent={batchDetail.progress?.progress_percent ?? 0}
                    status="active"
                    strokeColor="#118a62"
                    trailColor="#dde5da"
                  />
                </div>
              ) : null}

              <div className="metric-row">
                <Statistic title="建议通过数量" value={invoiceState.data.batch_summary.count} />
                <Statistic title="建议通过金额" value={invoiceState.data.batch_summary.total_amount} />
                <Statistic title="当前结果数量" value={currentResultCount} />
                <Statistic title="当前结果对应金额" value={invoiceState.data.filtered_summary.total_amount} />
              </div>

              <Space wrap className="status-strip">
                {RESULT_FILTER_OPTIONS.filter((item) => item.value !== "all").map((item) => (
                  <Tag key={item.value}>{`${item.label} ${getResultFilterCount(counts, item.value as Exclude<ResultFilterValue, "all">)}`}</Tag>
                ))}
              </Space>

              {batchDetail.attachment_file_count > 0 ? (
                <Space wrap className="status-strip">
                  <Typography.Text strong>{`清单附件 ${batchDetail.attachment_file_count}`}</Typography.Text>
                  {attachmentStatusEntries.map(([status, count]) => (
                    <Tag key={status}>{`${ATTACHMENT_STATUS_LABELS[status] ?? status} ${count}`}</Tag>
                  ))}
                </Space>
              ) : null}

              {failedCount > 0 ? (
                <Space direction="vertical" size={8} className="full-width">
                  <Space wrap>
                    <Typography.Text strong>补充或重试建议</Typography.Text>
                    <Typography.Text type="secondary">{`需补充/重试 ${failedCount} 张`}</Typography.Text>
                    <Button
                      onClick={async () => {
                        if (!resolvedBatchId) {
                          return;
                        }
                        try {
                          const result = await createBatchRetry({ batchId: resolvedBatchId });
                          message.success(`已重新入队 ${result.retried_invoice_ids.length} 张待补充发票`);
                          await loadResults(resolvedBatchId, selectedFilter);
                          await loadBatches();
                        } catch (error) {
                          message.error(getErrorMessage(error));
                        }
                      }}
                      disabled={recentFailures.length > 0 && retryableFailures.length === 0}
                    >
                      重新处理待补充发票
                    </Button>
                  </Space>
                  {recentFailures.slice(0, 3).map((failure) => (
                    <Space key={failure.invoice_id} wrap>
                      <Typography.Text>{failure.original_filename}</Typography.Text>
                      {failure.error_code ? <Tag color="red">{failure.error_code}</Tag> : null}
                      <Typography.Text type="secondary">{failure.failure_reason || "处理失败"}</Typography.Text>
                    </Space>
                  ))}
                </Space>
              ) : null}

              <Space wrap>
                <Button
                  type="primary"
                  onClick={() =>
                    void handleDownload({
                      key: "filtered-zip",
                      downloadFormat: "zip",
                      selectionMode: selectedFilter === "all" ? "all" : "filtered",
                    })
                  }
                  loading={savingAction === "filtered-zip"}
                  disabled={!resolvedBatchId || isActiveBatch(batchDetail)}
                >
                  另存为当前结果 ZIP
                </Button>
                <Button
                  onClick={() =>
                    void handleDownload({
                      key: "selected-zip",
                      downloadFormat: "zip",
                      selectionMode: "selected",
                      requireSelection: true,
                    })
                  }
                  loading={savingAction === "selected-zip"}
                  disabled={!resolvedBatchId || selectedRowKeys.length === 0 || isActiveBatch(batchDetail)}
                >
                  另存为勾选发票 ZIP
                </Button>
                <Button
                  onClick={() =>
                    void handleDownload({
                      key: "manifest",
                      downloadFormat: "excel_manifest",
                      selectionMode: selectedFilter === "all" ? "all" : "filtered",
                    })
                  }
                  loading={savingAction === "manifest"}
                  disabled={!resolvedBatchId || isActiveBatch(batchDetail)}
                >
                  另存为当前结果台账
                </Button>
              </Space>
            </div>
          ) : null}
        </AsyncBoundary>
      </section>

      <section className="workspace-block">
        <SectionHeader
          title="发票明细"
          subtitle="处理中会自动刷新；先查看结论和人工确认状态，再决定是否另存。"
          actions={
            <Typography.Text type="secondary">
              {selectedRowKeys.length > 0 ? `已勾选 ${selectedRowKeys.length} 张` : "未勾选发票"}
            </Typography.Text>
          }
        />
        <AsyncBoundary
          loading={invoiceState.loading}
          error={invoiceState.error}
          empty={(invoiceState.data?.items.length ?? 0) === 0}
          emptyDescription="当前筛选下没有发票"
        >
          {invoiceState.data ? (
            <ResultTable
              invoices={invoiceState.data.items}
              onInspect={(invoiceId) => setSelectedInvoiceId(invoiceId)}
              selectedRowKeys={selectedRowKeys}
              onSelectionChange={setSelectedRowKeys}
            />
          ) : null}
        </AsyncBoundary>
      </section>

      <InvoiceDrawer
        invoiceId={selectedInvoiceId}
        open={Boolean(selectedInvoiceId)}
        onClose={() => setSelectedInvoiceId(null)}
        onChanged={async () => {
          if (resolvedBatchId) {
            await loadResults(resolvedBatchId, selectedFilter);
            await loadBatches();
          }
        }}
      />
    </div>
  );
}
