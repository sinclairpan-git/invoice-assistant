<template>
  <div class="page-stack">
    <AppCard>
      <AppSectionHeader title="批次结果" subtitle="按财务动作查看当前批次；系统处理中会静默刷新。">
        <template #actions>
          <div class="toolbar">
            <select v-model="resolvedBatchId" aria-label="选择批次" @change="goBatch">
              <option v-for="batch in batches" :key="batch.id" :value="batch.id">{{ batch.batch_no }}</option>
            </select>
            <select v-model="selectedBucket" aria-label="结果分组">
              <option v-for="bucket in RESULT_BUCKETS" :key="bucket.value" :value="bucket.value">
                {{ bucket.label }}
              </option>
            </select>
            <AppButton label="刷新" variant="secondary" :disabled="!resolvedBatchId" @click="refreshCurrent" />
          </div>
        </template>
      </AppSectionHeader>
      <AppAsyncBoundary :loading="batchesLoading" :error="batchesError">
        <div v-if="batchDetail && invoiceState.data" class="results-overview">
          <div v-if="isActiveBatch(batchDetail)" class="active-batch-strip">
            <div class="status-row">
              <AppStatusTag :label="batchDetail.progress?.stage_text || '处理中'" severity="info" />
              <span class="muted">已完成 {{ batchDetail.completed_files }}/{{ batchDetail.total_files }}</span>
              <span class="muted">失败 {{ batchDetail.failed_files }}</span>
            </div>
            <AppProgress :value="batchDetail.progress?.progress_percent ?? 0" />
          </div>

          <div class="metric-row">
            <div><span>建议通过数量</span><strong>{{ invoiceState.data.batch_summary.count }}</strong></div>
            <div><span>建议通过金额</span><strong>{{ invoiceState.data.batch_summary.total_amount }}</strong></div>
            <div><span>当前结果数量</span><strong>{{ invoiceState.data.items.length }}</strong></div>
            <div><span>当前结果金额</span><strong>{{ invoiceState.data.filtered_summary.total_amount }}</strong></div>
          </div>

          <div class="bucket-strip">
            <button
              v-for="bucket in RESULT_BUCKETS"
              :key="bucket.value"
              type="button"
              :class="{ active: selectedBucket === bucket.value }"
              @click="selectedBucket = bucket.value"
            >
              <span>{{ bucket.label }}</span>
              <strong>{{ bucket.value === 'all' ? invoiceState.data.items.length : getBucketCount(invoiceState.data.status_counts, bucket.value) }}</strong>
            </button>
          </div>

          <div class="inline-actions">
            <AppButton
              label="另存为当前结果 ZIP"
              :loading="savingAction === 'filtered-zip'"
              :disabled="!resolvedBatchId || isActiveBatch(batchDetail)"
              @click="download('filtered-zip', 'zip', selectedBucket === 'all' ? 'all' : 'filtered')"
            />
            <AppButton
              label="另存为勾选发票 ZIP"
              variant="secondary"
              :loading="savingAction === 'selected-zip'"
              :disabled="!resolvedBatchId || selectedRowKeys.length === 0 || isActiveBatch(batchDetail)"
              @click="download('selected-zip', 'zip', 'selected', true)"
            />
            <AppButton
              label="另存为当前结果台账"
              variant="secondary"
              :loading="savingAction === 'manifest'"
              :disabled="!resolvedBatchId || isActiveBatch(batchDetail)"
              @click="download('manifest', 'excel_manifest', selectedBucket === 'all' ? 'all' : 'filtered')"
            />
          </div>
          <p v-if="notice" class="form-notice">{{ notice }}</p>
        </div>
      </AppAsyncBoundary>
    </AppCard>

    <AppCard>
      <AppSectionHeader title="发票明细" subtitle="先查看结论和人工确认状态，再决定是否另存。">
        <template #actions>
          <span class="muted">{{ selectedRowKeys.length ? `已勾选 ${selectedRowKeys.length} 张` : "未勾选发票" }}</span>
        </template>
      </AppSectionHeader>
      <AppAsyncBoundary
        :loading="invoiceState.loading"
        :error="invoiceState.error"
        :empty="(invoiceState.data?.items.length ?? 0) === 0"
        empty-description="当前筛选下没有发票"
      >
        <ResultTable
          v-if="invoiceState.data"
          :invoices="invoiceState.data.items"
          :selected-row-keys="selectedRowKeys"
          @inspect="selectedInvoiceId = $event"
          @selection-change="selectedRowKeys = $event"
        />
      </AppAsyncBoundary>
    </AppCard>

    <InvoiceDrawer
      :invoice-id="selectedInvoiceId"
      :open="Boolean(selectedInvoiceId)"
      @close="selectedInvoiceId = null"
      @changed="refreshCurrent"
    />
  </div>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, reactive, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";

import { downloadBatchFile, getBatch, getErrorMessage, listBatchInvoices, listBatches } from "../app/api";
import type { Batch, BatchInvoiceListing } from "../app/types";
import InvoiceDrawer from "../components/results/InvoiceDrawer.vue";
import ResultTable from "../components/results/ResultTable.vue";
import {
  RESULT_BUCKETS,
  type ResultBucket,
  getBucketCount,
  isActiveBatch,
  toDisplayStatusFilter,
} from "../domain/presentation";
import AppAsyncBoundary from "../ui-adapter/AppAsyncBoundary.vue";
import AppButton from "../ui-adapter/AppButton.vue";
import AppCard from "../ui-adapter/AppCard.vue";
import AppProgress from "../ui-adapter/AppProgress.vue";
import AppSectionHeader from "../ui-adapter/AppSectionHeader.vue";
import AppStatusTag from "../ui-adapter/AppStatusTag.vue";

const route = useRoute();
const router = useRouter();
const batches = ref<Batch[]>([]);
const batchesLoading = ref(true);
const batchesError = ref<string | null>(null);
const resolvedBatchId = ref<string>("");
const selectedBucket = ref<ResultBucket>("all");
const selectedRowKeys = ref<string[]>([]);
const selectedInvoiceId = ref<string | null>(null);
const batchDetail = ref<Batch | null>(null);
const savingAction = ref<string | null>(null);
const notice = ref("");
const invoiceState = reactive<{ loading: boolean; error: string | null; data: BatchInvoiceListing | null }>({
  loading: false,
  error: null,
  data: null,
});
let intervalId: number | undefined;

async function loadBatches() {
  batchesLoading.value = true;
  batchesError.value = null;
  try {
    batches.value = await listBatches();
    const routeBatchId = typeof route.params.batchId === "string" ? route.params.batchId : "";
    resolvedBatchId.value = routeBatchId && batches.value.some((batch) => batch.id === routeBatchId)
      ? routeBatchId
      : batches.value[0]?.id ?? "";
    if (!routeBatchId && resolvedBatchId.value) {
      await router.replace(`/results/${resolvedBatchId.value}`);
    }
  } catch (error) {
    batchesError.value = getErrorMessage(error);
  } finally {
    batchesLoading.value = false;
  }
}

async function loadResults(batchId: string, bucket: ResultBucket, silent = false) {
  invoiceState.loading = silent ? invoiceState.data === null : true;
  invoiceState.error = null;
  try {
    const [detail, listing] = await Promise.all([
      getBatch(batchId),
      listBatchInvoices(batchId, toDisplayStatusFilter(bucket)),
    ]);
    batchDetail.value = detail;
    invoiceState.data = listing;
  } catch (error) {
    invoiceState.error = getErrorMessage(error);
    if (!silent) {
      invoiceState.data = null;
    }
  } finally {
    invoiceState.loading = false;
  }
}

function goBatch() {
  if (resolvedBatchId.value) {
    void router.push(`/results/${resolvedBatchId.value}`);
  }
}

function refreshCurrent() {
  if (resolvedBatchId.value) {
    void loadResults(resolvedBatchId.value, selectedBucket.value);
    void loadBatches();
  }
}

async function download(key: string, format: "zip" | "excel_manifest", mode: "all" | "filtered" | "selected", requireSelection = false) {
  if (!resolvedBatchId.value) {
    return;
  }
  if (requireSelection && selectedRowKeys.value.length === 0) {
    notice.value = "请先勾选要另存的发票。";
    return;
  }
  savingAction.value = key;
  try {
    const result = await downloadBatchFile({
      batchId: resolvedBatchId.value,
      downloadFormat: format,
      selectionMode: mode,
      displayStatus: mode === "filtered" ? toDisplayStatusFilter(selectedBucket.value) : undefined,
      invoiceIds: mode === "selected" ? selectedRowKeys.value : undefined,
    });
    const objectUrl = URL.createObjectURL(result.blob);
    const anchor = document.createElement("a");
    anchor.href = objectUrl;
    anchor.download = result.filename;
    anchor.click();
    URL.revokeObjectURL(objectUrl);
    notice.value = `已准备保存 ${result.filename}`;
  } catch (error) {
    notice.value = getErrorMessage(error);
  } finally {
    savingAction.value = null;
  }
}

watch(
  () => [resolvedBatchId.value, selectedBucket.value] as const,
  ([batchId, bucket]) => {
    selectedRowKeys.value = [];
    if (batchId) {
      void loadResults(batchId, bucket);
    }
  },
);

watch(batchDetail, (detail) => {
  if (intervalId) {
    window.clearInterval(intervalId);
    intervalId = undefined;
  }
  if (isActiveBatch(detail) && resolvedBatchId.value) {
    intervalId = window.setInterval(() => {
      void loadBatches();
      void loadResults(resolvedBatchId.value, selectedBucket.value, true);
    }, 2000);
  }
});

onMounted(() => void loadBatches());
onUnmounted(() => {
  if (intervalId) {
    window.clearInterval(intervalId);
  }
});
</script>
