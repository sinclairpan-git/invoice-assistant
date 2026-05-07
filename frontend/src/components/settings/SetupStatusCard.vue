<template>
  <AppCard>
    <div class="setup-status-card">
      <div>
        <span class="eyebrow">当前公司配置</span>
        <h3>{{ title }}</h3>
        <p>{{ description }}</p>
      </div>
      <div v-if="showAction" class="inline-actions">
        <AppButton
          v-if="error"
          label="重新检测"
          variant="secondary"
          @click="$emit('retryConfig')"
        />
        <AppButton
          v-else-if="config?.setup_status.complete"
          label="回到工作台"
          variant="secondary"
          @click="$emit('openWorkbench')"
        />
        <AppButton v-else label="前往首次配置" @click="$emit('openSetup')" />
      </div>
    </div>
  </AppCard>
</template>

<script setup lang="ts">
import { computed } from "vue";

import type { ActiveConfigPayload } from "../../app/types";
import AppButton from "../../ui-adapter/AppButton.vue";
import AppCard from "../../ui-adapter/AppCard.vue";

const props = defineProps<{
  config?: ActiveConfigPayload | null;
  loading?: boolean;
  error?: string | null;
  showAction?: boolean;
}>();

defineEmits<{
  openSetup: [];
  openWorkbench: [];
  retryConfig: [];
}>();

const title = computed(() => {
  if (props.loading) {
    return "正在确认配置状态";
  }
  if (props.error) {
    return "本地服务未连接";
  }
  return props.config?.setup_status.complete ? "配置已生效" : "首次配置未完成";
});

const description = computed(() => {
  if (props.error) {
    return "当前无法读取配置与批次数据，请先确认后端本地服务正在运行，再重新检测。";
  }
  if (props.loading) {
    return "正在读取税务档案、审核策略和命名规则。";
  }
  if (!props.config?.setup_status.complete) {
    return "完成首次配置后才可上传发票并创建批次。";
  }
  const snapshot = props.config.active_snapshot.tax_profile?.content ?? {};
  const company = String(snapshot.company_name ?? snapshot.buyer_name ?? "公司档案已记录");
  return `${company} 的运行基线已记录。`;
});
</script>
