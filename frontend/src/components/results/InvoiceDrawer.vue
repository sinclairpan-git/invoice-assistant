<template>
  <div v-if="open" class="drawer-backdrop" role="presentation" @click.self="$emit('close')">
    <aside class="invoice-drawer" role="dialog" aria-modal="true" aria-label="发票详情">
      <div class="drawer-header">
        <h2>发票详情</h2>
        <AppButton label="关闭" variant="secondary" @click="$emit('close')" />
      </div>
      <AppAsyncBoundary :loading="loading" :error="error">
        <div v-if="invoice" class="drawer-body">
          <div class="status-row">
            <AppStatusTag
              :label="getStatusLabel(getResultBucket(invoice))"
              :severity="getStatusSeverity(getResultBucket(invoice))"
            />
            <AppStatusTag :label="getReviewLabel(invoice)" severity="info" />
          </div>

          <div class="detail-grid">
            <div><strong>原文件名</strong><span>{{ invoice.original_filename }}</span></div>
            <div><strong>建议新文件名</strong><span>{{ invoice.renamed_filename || "未重命名" }}</span></div>
            <div><strong>金额</strong><span>{{ invoice.invoice_amount || "--" }}</span></div>
            <div><strong>日期</strong><span>{{ invoice.invoice_date || "--" }}</span></div>
            <div><strong>购方名称</strong><span>{{ invoice.buyer_name || "--" }}</span></div>
            <div><strong>购方税号</strong><span>{{ invoice.buyer_tax_no || "--" }}</span></div>
          </div>

          <div class="tabs">
            <button
              v-for="tab in tabs"
              :key="tab.key"
              type="button"
              :class="{ active: activeTab === tab.key }"
              @click="activeTab = tab.key"
            >
              {{ tab.label }}
            </button>
          </div>

          <section v-if="activeTab === 'preview'" class="tab-panel">
            <AppButton label="打开原始 PDF" variant="secondary" @click="openOriginalPreview" />
            <div class="preview-frame">
              <iframe
                v-if="invoice.preview_path"
                class="pdf-preview"
                :src="getInvoicePreviewUrl(invoice.id)"
                :title="invoice.original_filename"
              />
              <AppMessage v-else severity="warn">当前记录没有可预览的文件路径。</AppMessage>
            </div>
          </section>

          <section v-else-if="activeTab === 'evidence'" class="tab-panel">
            <div class="responsive-table">
              <table>
                <thead>
                  <tr><th>字段</th><th>提取值</th><th>置信度</th><th>来源片段</th></tr>
                </thead>
                <tbody>
                  <tr v-for="field in invoice.extracted_fields" :key="field.id">
                    <td>{{ field.field_name }}</td>
                    <td>{{ field.normalized_value || field.extracted_value || "--" }}</td>
                    <td>{{ field.confidence || "--" }}</td>
                    <td>{{ field.source_fragment || "--" }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </section>

          <section v-else-if="activeTab === 'rules'" class="tab-panel">
            <div class="detail-grid">
              <div><strong>基础校验</strong><span>{{ invoice.basic_compliance_status || "--" }}</span></div>
              <div><strong>业务风险分类</strong><span>{{ invoice.business_compliance_status || "--" }}</span></div>
            </div>
          </section>

          <section v-else-if="activeTab === 'review'" class="tab-panel">
            <ReviewActions :invoice="invoice" @submitted="handleReviewSubmitted" />
            <ul class="audit-list">
              <li v-for="item in invoice.review_actions" :key="item.id">
                <strong>{{ item.review_action }}</strong>
                <span>{{ item.reviewed_by }} · {{ item.reviewed_at }}</span>
                <p v-if="item.review_note">{{ item.review_note }}</p>
              </li>
            </ul>
          </section>

          <section v-else class="tab-panel">
            <div class="detail-grid">
              <div><strong>解析来源</strong><span>{{ invoice.parse_source || "--" }}</span></div>
              <div><strong>失败阶段</strong><span>{{ invoice.last_error_stage || "--" }}</span></div>
              <div><strong>错误码</strong><span>{{ invoice.last_error_code || "--" }}</span></div>
              <div><strong>Provider</strong><span>{{ invoice.provider_diagnostic.provider_name || "--" }}</span></div>
            </div>
          </section>
        </div>
      </AppAsyncBoundary>
    </aside>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from "vue";

import {
  getErrorMessage,
  getInvoiceDetail,
  getInvoiceOriginalPreviewUrl,
  getInvoicePreviewUrl,
} from "../../app/api";
import type { InvoiceDetail, InvoiceSummary } from "../../app/types";
import {
  getResultBucket,
  getReviewLabel,
  getStatusLabel,
  getStatusSeverity,
} from "../../domain/presentation";
import AppAsyncBoundary from "../../ui-adapter/AppAsyncBoundary.vue";
import AppButton from "../../ui-adapter/AppButton.vue";
import AppMessage from "../../ui-adapter/AppMessage.vue";
import AppStatusTag from "../../ui-adapter/AppStatusTag.vue";
import ReviewActions from "./ReviewActions.vue";

const props = defineProps<{
  invoiceId: string | null;
  open: boolean;
}>();

const emit = defineEmits<{
  close: [];
  changed: [];
}>();

const tabs = [
  { key: "preview", label: "PDF 预览" },
  { key: "evidence", label: "识别字段" },
  { key: "rules", label: "校验依据" },
  { key: "review", label: "人工确认" },
  { key: "advanced", label: "高级诊断" },
];
const invoice = ref<InvoiceDetail | null>(null);
const loading = ref(false);
const error = ref<string | null>(null);
const activeTab = ref("preview");

async function loadInvoice() {
  if (!props.invoiceId) {
    invoice.value = null;
    return;
  }
  loading.value = true;
  error.value = null;
  try {
    invoice.value = await getInvoiceDetail(props.invoiceId);
  } catch (loadError) {
    error.value = getErrorMessage(loadError);
  } finally {
    loading.value = false;
  }
}

function openOriginalPreview() {
  if (invoice.value) {
    window.open(getInvoiceOriginalPreviewUrl(invoice.value.id), "_blank", "noopener,noreferrer");
  }
}

async function handleReviewSubmitted(updated: InvoiceSummary) {
  if (invoice.value && invoice.value.id === updated.id) {
    invoice.value = { ...invoice.value, ...updated };
  }
  emit("changed");
  await loadInvoice();
}

watch(
  () => [props.invoiceId, props.open] as const,
  () => {
    if (props.open && props.invoiceId) {
      activeTab.value = "preview";
      void loadInvoice();
    }
  },
);
</script>
