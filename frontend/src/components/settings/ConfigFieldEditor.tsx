import { Button, Space, Typography } from "../../app/antd";

import type { ActiveConfigPayload, BusinessRuleTemplate } from "../../app/types";
import {
  BusinessRulesTemplateStep,
  type BusinessRulesTemplateFormValues,
} from "./BusinessRulesTemplateStep";
import { NamingRuleStep, type NamingRuleFormValues } from "./NamingRuleStep";
import { SetupSummaryStep } from "./SetupSummaryStep";
import { TaxProfileStep, type TaxProfileFormValues } from "./TaxProfileStep";
import { useMemo, useState } from "react";

const STEP_TITLES = ["税务档案", "业务规则模板", "命名规则", "摘要确认"] as const;

export interface ConfigFieldDraft {
  taxProfile: TaxProfileFormValues;
  businessRules: BusinessRulesTemplateFormValues;
  namingRule: NamingRuleFormValues;
}

interface ConfigFieldEditorProps {
  mode: "first_setup" | "settings_edit";
  initialDraft: ConfigFieldDraft;
  templates: BusinessRuleTemplate[];
  saving: boolean;
  onSubmit: (draft: ConfigFieldDraft) => void;
}

function readString(content: Record<string, unknown>, ...keys: string[]): string {
  for (const key of keys) {
    const value = content[key];
    if (typeof value === "string") {
      return value;
    }
  }
  return "";
}

function joinCombined(left: string, right: string): string {
  if (left && right) {
    return `${left} ${right}`;
  }
  return left || right;
}

export function buildConfigFieldDraft(
  config: ActiveConfigPayload | null,
  templates: BusinessRuleTemplate[],
): ConfigFieldDraft {
  const taxProfileContent = config?.active_snapshot.tax_profile?.content ?? {};
  const businessRuleContent = config?.active_snapshot.business_rules?.content ?? {};
  const namingRuleContent = config?.active_snapshot.naming_rules?.content ?? {};
  const buyerAddress = readString(taxProfileContent, "buyer_address");
  const buyerPhone = readString(taxProfileContent, "buyer_phone");
  const buyerBank = readString(taxProfileContent, "buyer_bank");
  const buyerAccount = readString(taxProfileContent, "buyer_account");
  const templateName = readString(businessRuleContent, "template_name") || templates[0]?.template_name || "";

  return {
    taxProfile: {
      enterpriseName: readString(taxProfileContent, "company_name", "buyer_name"),
      taxpayerId: readString(taxProfileContent, "taxpayer_id", "buyer_tax_no"),
      addressPhone: readString(taxProfileContent, "address_phone") || joinCombined(buyerAddress, buyerPhone),
      bankAccount: readString(taxProfileContent, "bank_account") || joinCombined(buyerBank, buyerAccount),
    },
    businessRules: {
      templateName,
    },
    namingRule: {
      pattern: readString(namingRuleContent, "pattern") || "{{date}}-{{buyer}}-{{amount}}",
    },
  };
}

export function ConfigFieldEditor({
  mode,
  initialDraft,
  templates,
  saving,
  onSubmit,
}: ConfigFieldEditorProps) {
  const [stepIndex, setStepIndex] = useState(0);
  const [taxProfile, setTaxProfile] = useState<TaxProfileFormValues>(initialDraft.taxProfile);
  const [businessRules, setBusinessRules] = useState<BusinessRulesTemplateFormValues>(initialDraft.businessRules);
  const [namingRule, setNamingRule] = useState<NamingRuleFormValues>(initialDraft.namingRule);

  const selectedTemplate = useMemo(
    () => templates.find((item) => item.template_name === businessRules.templateName) ?? null,
    [businessRules.templateName, templates],
  );
  const submitLabel = mode === "settings_edit" ? "保存配置" : "完成配置";
  const goNext = () => setStepIndex((current) => Math.min(current + 1, STEP_TITLES.length - 1));
  const goBack = () => setStepIndex((current) => Math.max(current - 1, 0));

  const submitCurrentForm = () => {
    const submitter = document.querySelector("form button[type='submit']") as HTMLButtonElement | null;
    submitter?.click();
  };

  return (
    <Space direction="vertical" size={16} className="full-width">
      <Space wrap>
        {STEP_TITLES.map((title, index) => (
          <Button key={title} type={index === stepIndex ? "primary" : "default"} disabled={index > stepIndex}>
            {`${index + 1}. ${title}`}
          </Button>
        ))}
      </Space>

      <Typography.Title level={5}>{STEP_TITLES[stepIndex]}</Typography.Title>

      {stepIndex === 0 ? (
        <TaxProfileStep
          initialValues={taxProfile}
          onSubmit={(values) => {
            setTaxProfile(values);
            goNext();
          }}
        />
      ) : null}

      {stepIndex === 1 ? (
        <BusinessRulesTemplateStep
          initialValues={businessRules}
          templates={templates}
          onSubmit={(values) => {
            setBusinessRules(values);
            goNext();
          }}
        />
      ) : null}

      {stepIndex === 2 ? (
        <NamingRuleStep
          initialValues={namingRule}
          onSubmit={(values) => {
            setNamingRule(values);
            goNext();
          }}
        />
      ) : null}

      {stepIndex === 3 ? (
        <SetupSummaryStep
          taxProfile={taxProfile}
          businessRules={businessRules}
          namingRule={namingRule}
          selectedTemplate={selectedTemplate}
        />
      ) : null}

      <Space>
        <Button onClick={goBack} disabled={stepIndex === 0 || saving}>
          上一步
        </Button>
        {stepIndex < STEP_TITLES.length - 1 ? (
          <Button type="primary" onClick={submitCurrentForm}>
            下一步
          </Button>
        ) : (
          <Button
            type="primary"
            loading={saving}
            onClick={() =>
              onSubmit({
                taxProfile,
                businessRules,
                namingRule,
              })
            }
          >
            {submitLabel}
          </Button>
        )}
      </Space>
    </Space>
  );
}
