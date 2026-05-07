<template>
  <ProgressBar :value="value" :show-value="showValue" />
</template>

<script setup lang="ts">
import ProgressBar from "primevue/progressbar";

withDefaults(
  defineProps<{
    value: number;
    showValue?: boolean;
  }>(),
  {
    showValue: true,
  },
);
</script>
