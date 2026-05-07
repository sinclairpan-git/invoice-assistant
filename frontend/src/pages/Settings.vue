<template>
  <div class="page-stack">
    <AppCard>
      <AppSectionHeader title="当前操作者" subtitle="由后端可信上下文提供，用于复核、导出和配置变更审计" />
      <strong>{{ defaultOperatorName }}</strong>
      <div class="status-row">
        <AppStatusTag v-for="role in currentActor.roles" :key="role" :label="role" severity="info" />
        <span v-if="currentActor.roles.length === 0" class="muted">当前未分配受控角色</span>
      </div>
      <p v-if="actorError" class="form-notice">{{ actorError }}</p>
    </AppCard>

    <AppAsyncBoundary :loading="state.loading" :error="state.error">
      <template v-if="state.config?.setup_status.complete">
        <AppCard>
          <AppSectionHeader
            title="配置中心"
            subtitle="按字段查看当前公司的运行基线；需要修改时，进入字段表单重新填写并保存为新版本。"
          >
            <template #actions>
              <div class="inline-actions">
                <AppButton label="查看历史变更" variant="secondary" @click="openHistory" />
                <AppButton :label="editing ? '返回配置摘要' : '按字段修改配置'" @click="editing = !editing" />
              </div>
            </template>
          </AppSectionHeader>
          <p class="muted">当前页已隐藏技术配置 JSON，避免要求财务用户直接编辑系统键名。</p>
          <p v-if="pageNotice" class="success-notice">{{ pageNotice }}</p>
        </AppCard>

        <AppCard v-if="editing">
          <AppSectionHeader title="字段化调整" subtitle="复用首次配置的字段表单，统一维护税务档案、审核策略和文件命名。" />
          <ConfigFieldEditor
            mode="settings_edit"
            :initial-draft="initialDraft"
            :templates="templates"
            :saving="saving"
            @submit="preparePublish"
          />
          <p v-if="publishNotice" class="info-notice">{{ publishNotice }}</p>
          <p v-if="publishResult" :class="publishResult.type === 'success' ? 'success-notice' : 'form-notice'">
            {{ publishResult.message }}
          </p>
          <form v-if="pendingDraft" ref="publishConfirmRef" class="publish-confirm" @submit.prevent="confirmPublish">
            <h3>发布确认</h3>
            <p>税务档案、审核策略、文件命名会整体生成新版本并立即生效。</p>
            <label>变更摘要<input v-model.trim="changeSummary" required maxlength="80" /></label>
            <label>变更原因<input v-model.trim="changeReason" required maxlength="120" /></label>
            <AppButton label="确认发布配置" :loading="saving" @click="confirmPublish" />
          </form>
        </AppCard>

        <template v-else>
          <AppCard v-if="historyOpen">
            <AppSectionHeader title="历史变更" subtitle="历史版本仅供查阅，不允许直接编辑。" />
            <AppAsyncBoundary :loading="historyLoading" :empty="bundleHistory.length === 0" empty-description="暂无历史变更">
              <ul class="audit-list">
                <li v-for="item in bundleHistory" :key="item.bundle_version_no">
                  <strong>{{ item.bundle_version_no }}</strong>
                  <span>{{ item.change_summary }}</span>
                  <p>{{ item.change_reason }}</p>
                  <span class="muted">{{ item.changed_by }} · {{ item.changed_at }}</span>
                </li>
              </ul>
            </AppAsyncBoundary>
          </AppCard>
          <AppCard>
            <AppSectionHeader title="公司税务档案" subtitle="影响购方抬头、税号匹配和基础校验。" />
            <div class="detail-grid">
              <div><strong>企业名称</strong><span>{{ readString(taxProfile, "company_name", "buyer_name") }}</span></div>
              <div><strong>纳税人识别号</strong><span>{{ readString(taxProfile, "taxpayer_id", "buyer_tax_no") }}</span></div>
              <div><strong>地址电话</strong><span>{{ readString(taxProfile, "address_phone") }}</span></div>
              <div><strong>开户行及帐号</strong><span>{{ readString(taxProfile, "bank_account") }}</span></div>
            </div>
          </AppCard>
          <AppCard>
            <AppSectionHeader title="审核策略" subtitle="影响系统建议和人工确认量。" />
            <div class="detail-grid">
              <div><strong>模板方案</strong><span>{{ readString(businessRules, "display_name", "template_name") }}</span></div>
              <div><strong>文件命名</strong><span>{{ readString(namingRules, "pattern") }}</span></div>
            </div>
          </AppCard>
        </template>
      </template>
      <AppCard v-else>
        <AppSectionHeader title="配置中心" subtitle="请先完成首次配置，后续调整也会继续使用字段表单。" />
        <AppButton label="前往首次配置" @click="router.push('/setup')" />
      </AppCard>
    </AppAsyncBoundary>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, reactive, ref } from "vue";
import { useRouter } from "vue-router";

import { getActiveConfig, getErrorMessage, listConfigBundles, publishConfigBundle } from "../app/api";
import { useOperatorSettings } from "../app/operator";
import type { ActiveConfigPayload, ConfigBundle } from "../app/types";
import ConfigFieldEditor from "../components/settings/ConfigFieldEditor.vue";
import { buildConfigFieldDraft, type ConfigFieldDraft } from "../domain/configDraft";
import AppAsyncBoundary from "../ui-adapter/AppAsyncBoundary.vue";
import AppButton from "../ui-adapter/AppButton.vue";
import AppCard from "../ui-adapter/AppCard.vue";
import AppSectionHeader from "../ui-adapter/AppSectionHeader.vue";
import AppStatusTag from "../ui-adapter/AppStatusTag.vue";

const router = useRouter();
const { currentActor, defaultOperatorName, error: actorError } = useOperatorSettings();
const state = reactive<{ loading: boolean; error: string | null; config: ActiveConfigPayload | null }>({
  loading: true,
  error: null,
  config: null,
});
const editing = ref(false);
const saving = ref(false);
const pendingDraft = ref<ConfigFieldDraft | null>(null);
const historyOpen = ref(false);
const historyLoading = ref(false);
const bundleHistory = ref<ConfigBundle[]>([]);
const changeSummary = ref("字段化调整当前配置");
const changeReason = ref("配置中心字段表单调整");
const publishNotice = ref("");
const publishResult = ref<{ type: "success" | "error"; message: string } | null>(null);
const publishConfirmRef = ref<HTMLFormElement | null>(null);
const pageNotice = ref("");

const templates = computed(() => Object.values(state.config?.setup_status.default_business_rule_templates ?? {}));
const initialDraft = computed(() => buildConfigFieldDraft(state.config, templates.value));
const taxProfile = computed(() => state.config?.active_snapshot.tax_profile?.content ?? {});
const businessRules = computed(() => state.config?.active_snapshot.business_rules?.content ?? {});
const namingRules = computed(() => state.config?.active_snapshot.naming_rules?.content ?? {});

function readString(content: Record<string, unknown>, ...keys: string[]) {
  for (const key of keys) {
    const value = content[key];
    if (typeof value === "string" && value.trim()) {
      return value.trim();
    }
  }
  return "--";
}

async function loadSettings() {
  state.loading = true;
  state.error = null;
  try {
    state.config = await getActiveConfig();
  } catch (error) {
    state.error = getErrorMessage(error);
    state.config = null;
  } finally {
    state.loading = false;
  }
}

async function preparePublish(draft: ConfigFieldDraft) {
  pendingDraft.value = draft;
  changeSummary.value = "字段化调整当前配置";
  changeReason.value = "配置中心字段表单调整";
  publishNotice.value = "发布确认已生成。请确认变更摘要和原因后，再点击“确认发布配置”。";
  publishResult.value = null;
  pageNotice.value = "";
  await nextTick();
  publishConfirmRef.value?.scrollIntoView({ behavior: "smooth", block: "center" });
  publishConfirmRef.value?.querySelector("input")?.focus();
}

async function confirmPublish() {
  if (!pendingDraft.value) {
    return;
  }
  const selectedTemplate = templates.value.find((item) => item.template_name === pendingDraft.value?.businessRules.templateName);
  if (!selectedTemplate) {
    publishResult.value = { type: "error", message: "请先选择业务规则模板。" };
    return;
  }
  saving.value = true;
  publishResult.value = null;
  try {
    await publishConfigBundle({
      profile: {
        company_name: pendingDraft.value.taxProfile.enterpriseName,
        taxpayer_id: pendingDraft.value.taxProfile.taxpayerId,
        address_phone: pendingDraft.value.taxProfile.addressPhone,
        bank_account: pendingDraft.value.taxProfile.bankAccount,
      },
      reviewPolicy: { ...selectedTemplate },
      namingPolicy: { pattern: pendingDraft.value.namingRule.pattern },
      changeSummary: changeSummary.value,
      changeReason: changeReason.value,
    });
    pendingDraft.value = null;
    editing.value = false;
    publishNotice.value = "";
    await loadSettings();
    pageNotice.value = "配置已发布并生效。";
  } catch (error) {
    publishResult.value = { type: "error", message: getErrorMessage(error) };
  } finally {
    saving.value = false;
  }
}

async function openHistory() {
  historyOpen.value = true;
  historyLoading.value = true;
  try {
    bundleHistory.value = await listConfigBundles();
  } finally {
    historyLoading.value = false;
  }
}

onMounted(() => void loadSettings());
</script>
