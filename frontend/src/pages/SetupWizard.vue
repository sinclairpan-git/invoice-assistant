<template>
  <div class="page-stack">
    <AppCard>
      <AppSectionHeader
        :title="setupAlreadyComplete ? '配置调整' : '首次配置向导'"
        :subtitle="setupAlreadyComplete ? '继续按字段调整税务档案、审核策略和命名规则。' : '按顺序补齐税务档案、业务规则模板和命名规则。'"
      />
      <AppAsyncBoundary :loading="loading" :error="error">
        <ConfigFieldEditor
          :mode="setupAlreadyComplete ? 'settings_edit' : 'first_setup'"
          :initial-draft="initialDraft"
          :templates="templates"
          :saving="saving"
          @submit="submitSetup"
        />
      </AppAsyncBoundary>
    </AppCard>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";

import { createInitialSetup, getActiveConfig, getErrorMessage } from "../app/api";
import type { ActiveConfigPayload } from "../app/types";
import ConfigFieldEditor from "../components/settings/ConfigFieldEditor.vue";
import { buildConfigFieldDraft, type ConfigFieldDraft } from "../domain/configDraft";
import AppAsyncBoundary from "../ui-adapter/AppAsyncBoundary.vue";
import AppCard from "../ui-adapter/AppCard.vue";
import AppSectionHeader from "../ui-adapter/AppSectionHeader.vue";

const router = useRouter();
const config = ref<ActiveConfigPayload | null>(null);
const loading = ref(true);
const saving = ref(false);
const error = ref<string | null>(null);

const templates = computed(() => Object.values(config.value?.setup_status.default_business_rule_templates ?? {}));
const initialDraft = computed(() => buildConfigFieldDraft(config.value, templates.value));
const setupAlreadyComplete = computed(() => config.value?.setup_status.complete ?? false);

async function loadConfig() {
  loading.value = true;
  try {
    config.value = await getActiveConfig();
    error.value = null;
  } catch (loadError) {
    error.value = getErrorMessage(loadError);
  } finally {
    loading.value = false;
  }
}

async function submitSetup(draft: ConfigFieldDraft) {
  const selectedTemplate = templates.value.find((item) => item.template_name === draft.businessRules.templateName);
  if (!selectedTemplate) {
    error.value = "请先选择业务规则模板。";
    return;
  }
  saving.value = true;
  try {
    await createInitialSetup({
      taxProfile: {
        company_name: draft.taxProfile.enterpriseName,
        taxpayer_id: draft.taxProfile.taxpayerId,
        address_phone: draft.taxProfile.addressPhone,
        bank_account: draft.taxProfile.bankAccount,
      },
      businessRules: { ...selectedTemplate },
      namingRules: { pattern: draft.namingRule.pattern },
      changeSummary: setupAlreadyComplete.value ? "字段化调整当前配置" : "首次配置",
      changeReason: setupAlreadyComplete.value ? "配置中心字段表单调整" : "首次配置向导",
    });
    await router.push(setupAlreadyComplete.value ? "/settings" : "/");
  } catch (submitError) {
    error.value = getErrorMessage(submitError);
  } finally {
    saving.value = false;
  }
}

onMounted(() => void loadConfig());
</script>
