<template>
  <div class="responsive-table">
    <table>
      <thead>
        <tr>
          <th><input aria-label="全选当前页" type="checkbox" :checked="allSelected" @change="toggleAll" /></th>
          <th>原文件名</th>
          <th>建议新文件名</th>
          <th>金额</th>
          <th>购方信息</th>
          <th>处理结论</th>
          <th>人工确认</th>
          <th class="right">操作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="invoice in invoices" :key="invoice.id">
          <td>
            <input
              :aria-label="`选择 ${invoice.original_filename}`"
              type="checkbox"
              :checked="selectedRowKeys.includes(invoice.id)"
              @change="toggleOne(invoice.id)"
            />
          </td>
          <td class="filename-cell">{{ invoice.original_filename }}</td>
          <td>{{ displayRenamed(invoice) }}</td>
          <td>{{ invoice.invoice_amount || "--" }}</td>
          <td>
            <strong>{{ displayBuyer(invoice).title }}</strong>
            <span class="table-subtext">{{ displayBuyer(invoice).subtitle }}</span>
          </td>
          <td>
            <AppStatusTag
              :label="getStatusLabel(getResultBucket(invoice))"
              :severity="getStatusSeverity(getResultBucket(invoice))"
            />
          </td>
          <td>{{ getReviewLabel(invoice) }}</td>
          <td class="right"><AppButton label="查看详情" variant="ghost" @click="$emit('inspect', invoice.id)" /></td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";

import type { InvoiceSummary } from "../../app/types";
import {
  getResultBucket,
  getReviewLabel,
  getStatusLabel,
  getStatusSeverity,
  isInvoiceFailed,
  isInvoiceProcessing,
} from "../../domain/presentation";
import AppButton from "../../ui-adapter/AppButton.vue";
import AppStatusTag from "../../ui-adapter/AppStatusTag.vue";

const props = withDefaults(
  defineProps<{
    invoices: InvoiceSummary[];
    selectedRowKeys?: string[];
  }>(),
  {
    selectedRowKeys: () => [],
  },
);

const emit = defineEmits<{
  inspect: [invoiceId: string];
  selectionChange: [invoiceIds: string[]];
}>();

const allSelected = computed(() => props.invoices.length > 0 && props.invoices.every((invoice) => props.selectedRowKeys.includes(invoice.id)));

function toggleAll(event: Event) {
  const checked = (event.target as HTMLInputElement).checked;
  emit("selectionChange", checked ? props.invoices.map((invoice) => invoice.id) : []);
}

function toggleOne(invoiceId: string) {
  const selected = new Set(props.selectedRowKeys);
  if (selected.has(invoiceId)) {
    selected.delete(invoiceId);
  } else {
    selected.add(invoiceId);
  }
  emit("selectionChange", Array.from(selected));
}

function displayRenamed(invoice: InvoiceSummary) {
  if (isInvoiceProcessing(invoice.processing_status)) {
    return "处理中";
  }
  if (isInvoiceFailed(invoice.processing_status)) {
    return "待补充后再生成";
  }
  return invoice.renamed_filename || "未重命名";
}

function displayBuyer(invoice: InvoiceSummary) {
  if (isInvoiceProcessing(invoice.processing_status)) {
    return { title: "处理中", subtitle: "等待识别" };
  }
  if (isInvoiceFailed(invoice.processing_status)) {
    return { title: "需补充或重试", subtitle: invoice.failure_reason || "当前票据尚未完成识别" };
  }
  return {
    title: invoice.buyer_name || "未识别",
    subtitle: invoice.buyer_tax_no || "税号缺失",
  };
}
</script>
