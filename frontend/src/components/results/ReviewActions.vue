<template>
  <form class="review-actions" @submit.prevent="submit">
    <label>
      人工确认动作
      <select v-model="reviewAction" :disabled="!reviewable || saving">
        <option value="approve">确认通过</option>
        <option value="reject">确认驳回</option>
        <option value="keep_review_required">暂不处理</option>
      </select>
    </label>
    <label>
      确认说明
      <textarea v-model.trim="reviewNote" :disabled="!reviewable || saving" maxlength="200" />
    </label>
    <AppButton label="提交人工确认" :loading="saving" :disabled="!reviewable" @click="submit" />
    <p v-if="!reviewable" class="muted">当前发票不需要人工确认。</p>
    <p v-if="notice" class="form-notice">{{ notice }}</p>
  </form>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";

import { createReviewAction, getErrorMessage } from "../../app/api";
import type { InvoiceSummary } from "../../app/types";
import { getResultBucket, isInvoiceProcessing } from "../../domain/presentation";
import AppButton from "../../ui-adapter/AppButton.vue";

const props = defineProps<{
  invoice: InvoiceSummary;
}>();

const emit = defineEmits<{
  submitted: [invoice: InvoiceSummary];
}>();

const reviewAction = ref("approve");
const reviewNote = ref("");
const saving = ref(false);
const notice = ref("");
const reviewable = computed(() => {
  if (isInvoiceProcessing(props.invoice.processing_status)) {
    return false;
  }
  const bucket = getResultBucket(props.invoice);
  return bucket === "review_required" || bucket === "duplicate_in_batch";
});

async function submit() {
  if (!reviewable.value || saving.value) {
    return;
  }
  saving.value = true;
  notice.value = "";
  try {
    const result = await createReviewAction({
      invoiceId: props.invoice.id,
      reviewAction: reviewAction.value,
      reviewNote: reviewNote.value || undefined,
    });
    notice.value = "人工确认已提交。";
    emit("submitted", result.invoice);
  } catch (error) {
    notice.value = getErrorMessage(error);
  } finally {
    saving.value = false;
  }
}
</script>
