<template>
  <AppCard>
    <AppSectionHeader title="新建批次" subtitle="接收 PDF 发票与清单附件" />
    <div v-if="setupError" class="service-block">
      <strong>本地服务未连接</strong>
      <p>当前无法读取配置状态，上传入口已暂停。请启动后端服务后重新检测。</p>
    </div>
    <AppMessage v-else-if="!setupReady" severity="info">正在检查首次配置状态，上传入口暂不可用。</AppMessage>
    <AppMessage v-else-if="!setupComplete" severity="warn">
      首次配置未完成，完成后才可上传和创建批次。
      <button class="link-button" type="button" @click="$emit('openSetup')">前往首次配置</button>
    </AppMessage>

    <form v-if="!setupError" class="upload-form" @submit.prevent="submit">
      <p class="muted">当前操作者：{{ defaultOperatorName }}</p>
      <label>
        批次号
        <input v-model.trim="batchNo" :disabled="!uploadEnabled" maxlength="60" placeholder="可选，留空则自动生成" />
      </label>
      <label class="drop-zone" :class="{ disabled: !uploadEnabled }">
        <span>拖入 PDF，或点击选择文件</span>
        <input accept=".pdf" :disabled="!uploadEnabled" multiple type="file" @change="readFiles" />
      </label>
      <ul v-if="files.length" class="file-list">
        <li v-for="file in files" :key="file.name">{{ file.name }}</li>
      </ul>
      <div class="inline-actions">
        <AppButton label="创建批次" :loading="submitting" :disabled="!uploadEnabled" @click="submit" />
        <AppButton
          label="清空文件"
          variant="secondary"
          :disabled="!uploadEnabled || submitting || files.length === 0"
          @click="files = []"
        />
      </div>
      <p v-if="notice" class="form-notice">{{ notice }}</p>
    </form>
  </AppCard>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";

import { createBatch, getErrorMessage } from "../../app/api";
import { useOperatorSettings } from "../../app/operator";
import type { Batch } from "../../app/types";
import AppButton from "../../ui-adapter/AppButton.vue";
import AppCard from "../../ui-adapter/AppCard.vue";
import AppMessage from "../../ui-adapter/AppMessage.vue";
import AppSectionHeader from "../../ui-adapter/AppSectionHeader.vue";

const props = withDefaults(
  defineProps<{
    setupReady?: boolean;
    setupComplete?: boolean;
    setupError?: string | null;
  }>(),
  {
    setupReady: true,
    setupComplete: true,
    setupError: null,
  },
);

const emit = defineEmits<{
  created: [batch: Batch];
  openSetup: [];
}>();

const { defaultOperatorName } = useOperatorSettings();
const files = ref<File[]>([]);
const batchNo = ref("");
const submitting = ref(false);
const notice = ref("");
const uploadEnabled = computed(() => props.setupReady && props.setupComplete && !props.setupError);

function readFiles(event: Event) {
  const input = event.target as HTMLInputElement;
  files.value = Array.from(input.files ?? []);
}

async function submit() {
  if (!uploadEnabled.value || submitting.value) {
    return;
  }
  if (files.value.length === 0) {
    notice.value = "请选择至少一个 PDF 文件。";
    return;
  }
  submitting.value = true;
  notice.value = "";
  try {
    const batch = await createBatch({
      batchNo: batchNo.value || undefined,
      files: files.value,
    });
    files.value = [];
    batchNo.value = "";
    notice.value = `批次 ${batch.batch_no} 已创建。`;
    emit("created", batch);
  } catch (error) {
    notice.value = getErrorMessage(error);
  } finally {
    submitting.value = false;
  }
}
</script>
