import { Button, Empty, Progress, Space, Tag, Typography } from "antd";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import { getErrorMessage, listBatches } from "../app/api";
import type { Batch } from "../app/types";
import { BatchList } from "../components/batch/BatchList";
import { UploadPanel } from "../components/batch/UploadPanel";
import { AsyncBoundary } from "../components/common/AsyncBoundary";
import { SectionHeader } from "../components/common/SectionHeader";


interface BatchListState {
  loading: boolean;
  error: string | null;
  items: Batch[];
}

export function BatchWorkbench() {
  const navigate = useNavigate();
  const [state, setState] = useState<BatchListState>({
    loading: true,
    error: null,
    items: [],
  });

  const loadBatches = useCallback(async () => {
    setState((current) => ({
      ...current,
      loading: true,
      error: null,
    }));
    try {
      const items = await listBatches();
      setState({
        loading: false,
        error: null,
        items,
      });
    } catch (error) {
      setState((current) => ({
        ...current,
        loading: false,
        error: getErrorMessage(error),
      }));
    }
  }, []);

  useEffect(() => {
    void loadBatches();
  }, [loadBatches]);

  const activeBatch = useMemo(() => {
    return state.items.find((item) => {
      const stageCode = item.progress?.stage_code;
      return stageCode === "processing" || stageCode === "queued";
    }) ?? null;
  }, [state.items]);

  useEffect(() => {
    if (!activeBatch) {
      return undefined;
    }
    const intervalId = window.setInterval(() => {
      void loadBatches();
    }, 5000);
    return () => window.clearInterval(intervalId);
  }, [activeBatch, loadBatches]);

  return (
    <div className="page-stack">
      <UploadPanel
        onCreated={(batch) => {
          void loadBatches();
          navigate(`/results/${batch.id}`);
        }}
      />

      <section className="workspace-block">
        <SectionHeader
          title="批次进度"
          subtitle="最近一次仍在运行的批次会在这里持续刷新"
          actions={
            <Button onClick={() => void loadBatches()} loading={state.loading}>
              刷新
            </Button>
          }
        />
        {activeBatch ? (
          <div className="active-batch-strip">
            <div>
              <Typography.Title level={5}>{activeBatch.batch_no}</Typography.Title>
              <Space wrap>
                <Tag color={activeBatch.progress?.stage_code === "completed" ? "green" : "gold"}>
                  {activeBatch.progress?.stage_text || "等待处理"}
                </Tag>
                <Typography.Text type="secondary">{`处理中 ${activeBatch.processing_files}`}</Typography.Text>
                <Typography.Text type="secondary">{`失败 ${activeBatch.failed_files}`}</Typography.Text>
              </Space>
            </div>
            <div className="active-batch-metrics">
              <div>
                <Typography.Text type="secondary">系统建议通过</Typography.Text>
                <Typography.Title level={4}>{activeBatch.suggested_pass_count}</Typography.Title>
              </div>
              <div>
                <Typography.Text type="secondary">系统建议通过金额</Typography.Text>
                <Typography.Title level={4}>{activeBatch.suggested_pass_total_amount}</Typography.Title>
              </div>
            </div>
            <Progress
              percent={activeBatch.progress?.progress_percent ?? 0}
              showInfo
              strokeColor="#118a62"
              trailColor="#dde5da"
            />
          </div>
        ) : (
          <Empty description="当前没有活跃批次" />
        )}
      </section>

      <section className="workspace-block">
        <SectionHeader title="最近批次" subtitle="展示文件数、失败数和系统建议通过金额" />
        <AsyncBoundary loading={state.loading} error={state.error} empty={state.items.length === 0} emptyDescription="还没有批次记录">
          <BatchList batches={state.items} onOpenResults={(batchId) => navigate(`/results/${batchId}`)} />
        </AsyncBoundary>
      </section>
    </div>
  );
}
