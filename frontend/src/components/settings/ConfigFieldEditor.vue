<template>
  <div class="field-flow">
    <div class="stepper" aria-label="配置步骤">
      <button
        v-for="(step, index) in steps"
        :key="step"
        type="button"
        :class="{ active: stepIndex === index }"
        :disabled="index > maxVisited"
        @click="stepIndex = index"
      >
        {{ index + 1 }}. {{ step }}
      </button>
    </div>

    <form v-if="stepIndex === 0" class="form-grid" @submit.prevent="goNext">
      <label>
        企业名称
        <input v-model.trim="draft.taxProfile.enterpriseName" required maxlength="80" />
      </label>
      <label>
        纳税人识别号
        <input v-model.trim="draft.taxProfile.taxpayerId" required maxlength="40" />
      </label>
      <label>
        地址电话
        <input v-model.trim="draft.taxProfile.addressPhone" required maxlength="120" />
      </label>
      <label>
        开户行及帐号
        <input v-model.trim="draft.taxProfile.bankAccount" required maxlength="120" />
      </label>
      <button class="hidden-submit" type="submit">下一步</button>
    </form>

    <form v-else-if="stepIndex === 1" class="option-grid" @submit.prevent="goNext">
      <label v-for="template in templates" :key="template.template_name" class="choice-card">
        <input v-model="draft.businessRules.templateName" type="radio" :value="template.template_name" required />
        <strong>{{ template.display_name }}</strong>
        <span>{{ template.minimum_confidence >= 0.9 ? "严格校验，减少误通过" : "均衡校验，减少人工量" }}</span>
      </label>
      <button class="hidden-submit" type="submit">下一步</button>
    </form>

    <form v-else-if="stepIndex === 2" class="naming-builder" @submit.prevent="goNext">
      <fieldset>
        <legend>命名组成项</legend>
        <label v-for="part in namingParts" :key="part.value">
          <input v-model="selectedNamingParts" type="checkbox" :value="part.value" />
          {{ part.label }}
        </label>
      </fieldset>
      <p class="muted">预览：{{ namingPreview }}</p>
      <button class="hidden-submit" type="submit">下一步</button>
    </form>

    <div v-else class="summary-grid">
      <div><strong>企业名称</strong><span>{{ draft.taxProfile.enterpriseName }}</span></div>
      <div><strong>纳税人识别号</strong><span>{{ draft.taxProfile.taxpayerId }}</span></div>
      <div><strong>审核策略</strong><span>{{ selectedTemplate?.display_name || "未选择" }}</span></div>
      <div><strong>命名方式</strong><span>{{ namingPreview }}</span></div>
    </div>

    <div class="inline-actions">
      <AppButton label="上一步" variant="secondary" :disabled="stepIndex === 0 || saving" @click="goBack" />
      <AppButton v-if="stepIndex < steps.length - 1" label="下一步" @click="goNext" />
      <AppButton v-else :label="submitLabel" :loading="saving" @click="submit" />
    </div>
    <p v-if="localNotice" class="info-notice">{{ localNotice }}</p>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from "vue";

import type { BusinessRuleTemplate } from "../../app/types";
import type { ConfigFieldDraft } from "../../domain/configDraft";
import AppButton from "../../ui-adapter/AppButton.vue";

const props = defineProps<{
  mode: "first_setup" | "settings_edit";
  initialDraft: ConfigFieldDraft;
  templates: BusinessRuleTemplate[];
  saving: boolean;
}>();

const emit = defineEmits<{
  submit: [draft: ConfigFieldDraft];
}>();

const steps = ["税务档案", "业务规则模板", "命名规则", "摘要确认"];
const namingParts = [
  { label: "发票日期", value: "date" },
  { label: "购方名称", value: "buyer" },
  { label: "金额", value: "amount" },
  { label: "发票号码", value: "number" },
];
const stepIndex = ref(0);
const maxVisited = ref(0);
const selectedNamingParts = ref(["date", "buyer", "amount"]);
const draft = reactive<ConfigFieldDraft>(structuredClone(props.initialDraft));
const localNotice = ref("");

const selectedTemplate = computed(
  () => props.templates.find((template) => template.template_name === draft.businessRules.templateName) ?? null,
);
const submitLabel = computed(() => (props.mode === "settings_edit" ? "进入发布确认" : "完成配置"));
const namingPreview = computed(() => selectedNamingParts.value.map((part) => `{{${part}}}`).join("-"));

watch(
  () => props.initialDraft,
  (nextDraft) => {
    Object.assign(draft.taxProfile, nextDraft.taxProfile);
    Object.assign(draft.businessRules, nextDraft.businessRules);
    Object.assign(draft.namingRule, nextDraft.namingRule);
  },
);

function goNext() {
  if (stepIndex.value === 2) {
    draft.namingRule.pattern = namingPreview.value;
  }
  stepIndex.value = Math.min(stepIndex.value + 1, steps.length - 1);
  maxVisited.value = Math.max(maxVisited.value, stepIndex.value);
}

function goBack() {
  stepIndex.value = Math.max(stepIndex.value - 1, 0);
}

function submit() {
  draft.namingRule.pattern = namingPreview.value;
  localNotice.value = props.mode === "settings_edit" ? "已生成发布确认，请在下方确认变更摘要和原因。" : "";
  emit("submit", structuredClone(draft));
}

</script>
