<template>
  <Button
    :label="label"
    :severity="severity"
    :outlined="variant === 'secondary'"
    :text="variant === 'ghost'"
    :loading="loading"
    :disabled="disabled"
    @click="$emit('click')"
  />
</template>

<script setup lang="ts">
import Button from "primevue/button";

defineProps<{
  label: string;
  variant?: "primary" | "secondary" | "ghost" | "danger";
  loading?: boolean;
  disabled?: boolean;
  severity?: "secondary" | "success" | "info" | "warn" | "danger";
}>();

defineEmits<{
  click: [];
}>();
</script>
