<template>
  <div class="page-stack">
    <UploadPanel
      :setup-ready="configState === 'ready'"
      :setup-complete="config?.setup_status.complete === true"
      :setup-error="configState === 'error' ? configError : null"
      @open-setup="router.push('/setup')"
      @created="handleCreated"
    />

    <AppCard>
      <AppSectionHeader title="批次进度" subtitle="最近一次仍在运行的批次会在这里持续刷新">
        <template #actions>
          <AppButton label="刷新" variant="secondary" :loading="batchState.loading" @click="loadBatches" />
        </template>
      </AppSectionHeader>
      <div v-if="activeBatch" class="active-batch-strip">
        <div>
          <h3>{{ activeBatch.batch_no }}</h3>
          <div class="status-row">
            <AppStatusTag :label="activeBatch.progress?.stage_text || '等待处理'" severity="warn" />
            <span class="muted">主票 {{ activeBatch.invoice_file_count }}</span>
            <span class="muted">清单附件 {{ activeBatch.attachment_file_count }}</span>
            <span class="muted">失败 {{ activeBatch.failed_files }}</span>
          </div>
        </div>
        <div class="metric-row">
          <div><span>系统建议通过</span><strong>{{ activeBatch.suggested_pass_count }}</strong></div>
          <div><span>系统建议通过金额</span><strong>{{ activeBatch.suggested_pass_total_amount }}</strong></div>
        </div>
        <AppProgress :value="activeBatch.progress?.progress_percent ?? 0" />
      </div>
      <div v-else class="state-panel muted">当前没有活跃批次</div>
    </AppCard>

    <AppCard>
      <AppSectionHeader title="最近批次" subtitle="展示文件数、失败数和系统建议通过金额" />
      <AppAsyncBoundary
        :loading="batchState.loading"
        :error="batchState.error"
        :empty="recentBatchEmpty"
        :empty-description="recentBatchEmptyDescription"
      >
        <BatchList :batches="batchState.items" @open-results="(batchId) => router.push(`/results/${batchId}`)" />
      </AppAsyncBoundary>
    </AppCard>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, reactive, ref, watch } from "vue";
import { useRouter } from "vue-router";

import { getActiveConfig, getErrorMessage, listBatches } from "../app/api";
import type { ActiveConfigPayload, Batch, ConfigLoadState } from "../app/types";
import BatchList from "../components/batch/BatchList.vue";
import UploadPanel from "../components/batch/UploadPanel.vue";
import { isActiveBatch } from "../domain/presentation";
import AppAsyncBoundary from "../ui-adapter/AppAsyncBoundary.vue";
import AppButton from "../ui-adapter/AppButton.vue";
import AppCard from "../ui-adapter/AppCard.vue";
import AppProgress from "../ui-adapter/AppProgress.vue";
import AppSectionHeader from "../ui-adapter/AppSectionHeader.vue";
import AppStatusTag from "../ui-adapter/AppStatusTag.vue";

const router = useRouter();
const batchState = reactive<{ loading: boolean; error: string | null; items: Batch[] }>({
  loading: true,
  error: null,
  items: [],
});
const config = ref<ActiveConfigPayload | null>(null);
const configState = ref<ConfigLoadState>("loading");
const configError = ref<string | null>(null);
let intervalId: number | undefined;

const activeBatch = computed(() => batchState.items.find((item) => isActiveBatch(item)) ?? null);
const recentBatchEmpty = computed(() => configState.value === "error" || batchState.items.length === 0);
const recentBatchEmptyDescription = computed(() =>
  configState.value === "error" ? "本地服务连接后显示最近批次" : "还没有批次记录",
);

async function loadBatches() {
  if (configState.value !== "ready") {
    batchState.loading = false;
    batchState.error = null;
    batchState.items = [];
    return;
  }
  batchState.loading = true;
  batchState.error = null;
  try {
    batchState.items = await listBatches();
  } catch (error) {
    batchState.error = getErrorMessage(error);
  } finally {
    batchState.loading = false;
  }
}

async function loadConfig() {
  configState.value = "loading";
  try {
    config.value = await getActiveConfig();
    configError.value = null;
    configState.value = "ready";
    if (!config.value.setup_status.complete) {
      void router.push("/setup");
    }
  } catch (error) {
    config.value = null;
    configError.value = getErrorMessage(error);
    configState.value = "error";
  }
}

function handleCreated(batch: Batch) {
  void loadBatches();
  void router.push(`/results/${batch.id}`);
}

watch(activeBatch, (batch) => {
  if (intervalId) {
    window.clearInterval(intervalId);
    intervalId = undefined;
  }
  if (batch) {
    intervalId = window.setInterval(() => void loadBatches(), 5000);
  }
});

onMounted(() => {
  void (async () => {
    await loadConfig();
    await loadBatches();
  })();
});

onUnmounted(() => {
  if (intervalId) {
    window.clearInterval(intervalId);
  }
});
</script>
