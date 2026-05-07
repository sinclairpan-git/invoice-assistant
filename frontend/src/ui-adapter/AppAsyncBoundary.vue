<template>
  <div v-if="loading" class="state-panel">
    <ProgressSpinner aria-label="加载中" />
    <span>正在加载…</span>
  </div>
  <Message v-else-if="error" severity="error" :closable="false">{{ error }}</Message>
  <div v-else-if="empty" class="state-panel muted">{{ emptyDescription || "暂无数据" }}</div>
  <slot v-else />
</template>

<script setup lang="ts">
import Message from "primevue/message";
import ProgressSpinner from "primevue/progressspinner";

defineProps<{
  loading?: boolean;
  error?: string | null;
  empty?: boolean;
  emptyDescription?: string;
}>();
</script>
