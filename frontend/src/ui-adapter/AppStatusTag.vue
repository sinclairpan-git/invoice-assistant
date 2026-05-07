<template>
  <Tag :severity="severity" :value="label" :aria-label="label" />
</template>

<script setup lang="ts">
import Tag from "primevue/tag";

defineProps<{
  label: string;
  severity?: "success" | "info" | "warn" | "danger" | "secondary" | "contrast";
}>();
</script>
