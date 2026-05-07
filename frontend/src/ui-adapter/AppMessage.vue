<template>
  <Message :severity="severity" :closable="false">
    <slot />
  </Message>
</template>

<script setup lang="ts">
import Message from "primevue/message";

defineProps<{
  severity: "success" | "info" | "warn" | "error" | "secondary" | "contrast";
}>();
</script>
