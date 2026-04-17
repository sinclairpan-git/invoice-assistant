import { App, Button, Select, Space, Statistic, Tag, Typography } from "../app/antd";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { createBatchRetry, createExport, getBatch, getErrorMessage, listBatchInvoices, listBatches } from "../app/api";
import { useOperatorSettings } from "../app/operator-settings";
import type { Batch, BatchInvoiceListing } from "../app/types";
import { AsyncBoundary } from "../components/common/AsyncBoundary";
import { SectionHeader } from "../components/common/SectionHeader";
import { InvoiceDrawer } from "../components/results/InvoiceDrawer";
import { ResultTable } from "../components/results/ResultTable";


const FILTER_OPTIONS = ["全部", "系统建议通过", "系统建议驳回", "待复核", "疑似重复", "处理失败"];

interface InvoiceState {
  loading: boolean;
  error: string | null;
  data: BatchInvoiceListing | null;
}

export function BatchResults() {
  const { message } = App.useApp();
  const navigate = useNavigate();
  const { batchId } = useParams();
  const { defaultOperatorName } = useOperatorSettings();
  const [batches, setBatches] = useState<Batch[]>([]);
  const [batchesLoading, setBatchesLoading] = useState(true);
  const [batchesError, setBatchesError] = useState<string | null>(null);
  const [selectedFilter, setSelectedFilter] = useState("全部");
  const [selectedInvoiceId, setSelectedInvoiceId] = useState<string | null>(null);
  const [batchDetail, setBatchDetail] = useState<Batch | null>(null);
  const [invoiceState, setInvoiceState] = useState<InvoiceState>({
    loading: false,
    error: null,
    data: null,
  });

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
    async (nextBatchId: string, nextFilter: string) => {
      setInvoiceState({
        loading: true,
        error: null,
        data: null,
      });
      try {
        const [detail, listing] = await Promise.all([
          getBatch(nextBatchId),
          listBatchInvoices(nextBatchId, nextFilter === "全部" ? undefined : nextFilter),
        ]);
        setBatchDetail(detail);
        setInvoiceState({
          loading: false,
          error: null,
          data: listing,
        });
      } catch (error) {
        setInvoiceState({
          loading: false,
          error: getErrorMessage(error),
          data: null,
        });
      }
    },
    [],
  );

  useEffect(() => {
    if (resolvedBatchId) {
      void loadResults(resolvedBatchId, selectedFilter);
    }
  }, [loadResults, resolvedBatchId, selectedFilter]);

  const counts = invoiceState.data?.status_counts ?? {};
  const recentFailures = batchDetail?.progress?.recent_failures ?? [];
  const retryableFailures = recentFailures.filter((item) => item.retryable !== false);
  const failedCount = counts["处理失败"] ?? batchDetail?.failed_files ?? 0;

  return (
    <div className="page-stack">
      <section className="workspace-block">
        <SectionHeader
          title="批次结果"
          subtitle="按显示状态筛选，并查看当前筛选下的系统建议通过金额"
          actions={
            <Space wrap>
              <Select
                className="batch-selector"
                value={resolvedBatchId}
                options={batches.map((item) => ({ label: item.batch_no, value: item.id }))}
                loading={batchesLoading}
                onChange={(value) => navigate(`/results/${value}`)}
              />
              <Select value={selectedFilter} options={FILTER_OPTIONS.map((item) => ({ label: item, value: item }))} onChange={setSelectedFilter} />
              <Button onClick={() => resolvedBatchId && void loadResults(resolvedBatchId, selectedFilter)} disabled={!resolvedBatchId}>
                刷新
              </Button>
            </Space>
          }
        />

        <AsyncBoundary loading={batchesLoading} error={batchesError}>
          {batchDetail && invoiceState.data ? (
            <div className="results-overview">
              <div className="metric-row">
                <Statistic title="批次系统建议通过金额" value={invoiceState.data.batch_summary.total_amount} />
                <Statistic title="当前筛选系统建议通过金额" value={invoiceState.data.filtered_summary.total_amount} />
                <Statistic title="批次系统建议通过数量" value={invoiceState.data.batch_summary.count} />
                <Statistic title="当前筛选系统建议通过数量" value={invoiceState.data.filtered_summary.count} />
              </div>
              <Space wrap className="status-strip">
                {FILTER_OPTIONS.filter((item) => item !== "全部").map((status) => (
                  <Tag key={status}>{`${status} ${counts[status] ?? 0}`}</Tag>
                ))}
              </Space>
              {failedCount > 0 ? (
                <Space direction="vertical" size={8} className="full-width">
                  <Space wrap>
                    <Typography.Text strong>失败摘要</Typography.Text>
                    <Typography.Text type="secondary">{`失败 ${failedCount} 张`}</Typography.Text>
                    <Button
                      onClick={async () => {
                        if (!resolvedBatchId) {
                          return;
                        }
                        try {
                          const result = await createBatchRetry({ batchId: resolvedBatchId });
                          message.success(`已重新入队 ${result.retried_invoice_ids.length} 张失败票`);
                          await loadResults(resolvedBatchId, selectedFilter);
                          await loadBatches();
                        } catch (error) {
                          message.error(getErrorMessage(error));
                        }
                      }}
                      disabled={recentFailures.length > 0 && retryableFailures.length === 0}
                    >
                      重试失败票
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
                  onClick={async () => {
                    if (!resolvedBatchId) {
                      return;
                    }
                    try {
                      const result = await createExport({
                        batchId: resolvedBatchId,
                        exportType: "suggested_pass_zip",
                        createdBy: defaultOperatorName,
                      });
                      message.success(`已生成 ${result.output_path}`);
                    } catch (error) {
                      message.error(getErrorMessage(error));
                    }
                  }}
                >
                  导出建议通过 ZIP
                </Button>
                <Button
                  onClick={async () => {
                    if (!resolvedBatchId) {
                      return;
                    }
                    try {
                      const result = await createExport({
                        batchId: resolvedBatchId,
                        exportType: "issue_zip",
                        createdBy: defaultOperatorName,
                      });
                      message.success(`已生成 ${result.output_path}`);
                    } catch (error) {
                      message.error(getErrorMessage(error));
                    }
                  }}
                >
                  导出问题票 ZIP
                </Button>
                <Button
                  onClick={async () => {
                    if (!resolvedBatchId) {
                      return;
                    }
                    try {
                      const result = await createExport({
                        batchId: resolvedBatchId,
                        exportType: "excel_manifest",
                        createdBy: defaultOperatorName,
                      });
                      message.success(`已生成 ${result.output_path}`);
                    } catch (error) {
                      message.error(getErrorMessage(error));
                    }
                  }}
                >
                  导出 Excel 台账
                </Button>
              </Space>
            </div>
          ) : null}
        </AsyncBoundary>
      </section>

      <section className="workspace-block">
        <SectionHeader title="发票明细" subtitle="支持查看字段证据、风险依据和人工复核入口" />
        <AsyncBoundary
          loading={invoiceState.loading}
          error={invoiceState.error}
          empty={(invoiceState.data?.items.length ?? 0) === 0}
          emptyDescription="当前筛选下没有票据"
        >
          {invoiceState.data ? (
            <ResultTable invoices={invoiceState.data.items} onInspect={(invoiceId) => setSelectedInvoiceId(invoiceId)} />
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
          }
        }}
      />
    </div>
  );
}
