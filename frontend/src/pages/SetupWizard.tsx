import { App, Button, Space, Spin, Typography } from "../app/antd";
import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import { createInitialSetup, getActiveConfig, getErrorMessage } from "../app/api";
import type { ActiveConfigPayload, BusinessRuleTemplate } from "../app/types";
import { SectionHeader } from "../components/common/SectionHeader";
import {
  BusinessRulesTemplateStep,
  type BusinessRulesTemplateFormValues,
} from "../components/settings/BusinessRulesTemplateStep";
import { NamingRuleStep, type NamingRuleFormValues } from "../components/settings/NamingRuleStep";
import { SetupSummaryStep } from "../components/settings/SetupSummaryStep";
import { TaxProfileStep, type TaxProfileFormValues } from "../components/settings/TaxProfileStep";

const STEP_TITLES = ["税务档案", "业务规则模板", "命名规则", "摘要确认"] as const;

function parseMinimumConfidence(value: string): number | null {
  const parsed = Number(value.trim());
  if (!Number.isFinite(parsed) || Number.isNaN(parsed)) {
    return null;
  }
  if (parsed < 0 || parsed > 1) {
    return null;
  }
  return parsed;
}

function readTaxProfileDefaults(config: ActiveConfigPayload | null): TaxProfileFormValues {
  const content = config?.active_snapshot.tax_profile?.content ?? {};
  return {
    companyName: typeof content.company_name === "string" ? content.company_name : "",
    buyerName: typeof content.buyer_name === "string" ? content.buyer_name : "",
    buyerTaxNo: typeof content.buyer_tax_no === "string" ? content.buyer_tax_no : "",
  };
}

function readTemplateDefaults(config: ActiveConfigPayload | null, templates: BusinessRuleTemplate[]): BusinessRulesTemplateFormValues {
  const content = config?.active_snapshot.business_rules?.content ?? {};
  const currentTemplate = typeof content.template_name === "string" ? content.template_name : "";
  return {
    templateName: currentTemplate || templates[0]?.template_name || "",
    minimumConfidence:
      typeof content.minimum_confidence === "number"
        ? content.minimum_confidence.toFixed(2)
        : (templates[0]?.minimum_confidence?.toFixed(2) ?? "0.85"),
  };
}

function readNamingDefaults(config: ActiveConfigPayload | null): NamingRuleFormValues {
  const content = config?.active_snapshot.naming_rules?.content ?? {};
  return {
    pattern: typeof content.pattern === "string" ? content.pattern : "{{date}}-{{buyer}}-{{amount}}",
  };
}

export function SetupWizard() {
  const { message } = App.useApp();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [config, setConfig] = useState<ActiveConfigPayload | null>(null);
  const [stepIndex, setStepIndex] = useState(0);
  const [taxProfile, setTaxProfile] = useState<TaxProfileFormValues>({
    companyName: "",
    buyerName: "",
    buyerTaxNo: "",
  });
  const [businessRules, setBusinessRules] = useState<BusinessRulesTemplateFormValues>({
    templateName: "",
    minimumConfidence: "0.85",
  });
  const [namingRule, setNamingRule] = useState<NamingRuleFormValues>({
    pattern: "{{date}}-{{buyer}}-{{amount}}",
  });

  useEffect(() => {
    let disposed = false;

    async function loadConfig() {
      setLoading(true);
      try {
        const nextConfig = await getActiveConfig();
        if (disposed) {
          return;
        }
        const templates = Object.values(nextConfig.setup_status.default_business_rule_templates ?? {});
        setConfig(nextConfig);
        setTaxProfile(readTaxProfileDefaults(nextConfig));
        setBusinessRules(readTemplateDefaults(nextConfig, templates));
        setNamingRule(readNamingDefaults(nextConfig));
        setError(null);
      } catch (loadError) {
        if (!disposed) {
          setError(getErrorMessage(loadError));
        }
      } finally {
        if (!disposed) {
          setLoading(false);
        }
      }
    }

    void loadConfig();
    return () => {
      disposed = true;
    };
  }, []);

  const templates = useMemo(() => Object.values(config?.setup_status.default_business_rule_templates ?? {}), [config]);
  const selectedTemplate = useMemo(
    () => templates.find((item) => item.template_name === businessRules.templateName) ?? null,
    [businessRules.templateName, templates],
  );

  const goNext = () => setStepIndex((current) => Math.min(current + 1, STEP_TITLES.length - 1));
  const goBack = () => setStepIndex((current) => Math.max(current - 1, 0));

  const submitSetup = async () => {
    if (!selectedTemplate) {
      message.error("请先选择业务规则模板。");
      return;
    }
    const minimumConfidence = parseMinimumConfidence(businessRules.minimumConfidence);
    if (minimumConfidence === null) {
      message.error("请输入 0 到 1 之间的数字");
      return;
    }

    setSaving(true);
    try {
      await createInitialSetup({
        taxProfile: {
          company_name: taxProfile.companyName.trim(),
          buyer_name: taxProfile.buyerName.trim(),
          buyer_tax_no: taxProfile.buyerTaxNo.trim(),
        },
        businessRules: {
          ...selectedTemplate,
          minimum_confidence: minimumConfidence,
        },
        namingRules: {
          pattern: namingRule.pattern.trim(),
        },
        changeSummary: "首次配置",
        changeReason: "首次配置向导",
      });
      message.success("首次配置已完成");
      navigate("/");
    } catch (submitError) {
      message.error(getErrorMessage(submitError));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="page-stack">
      <section className="workspace-block">
        <SectionHeader title="首次配置向导" subtitle="按顺序补齐税务档案、业务规则模板和命名规则，再一次性确认生效。" />
        <Space direction="vertical" size={16} className="full-width">
          <Space wrap>
            {STEP_TITLES.map((title, index) => (
              <Button key={title} type={index === stepIndex ? "primary" : "default"} disabled={index > stepIndex}>
                {`${index + 1}. ${title}`}
              </Button>
            ))}
          </Space>

          {loading ? <Spin tip="正在读取首次配置…" /> : null}
          {error ? <Typography.Text type="danger">{error}</Typography.Text> : null}

          {!loading && !error ? (
            <>
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
                  <Button
                    type="primary"
                    onClick={() => {
                      const submitter = document.querySelector("form button[type='submit']") as HTMLButtonElement | null;
                      submitter?.click();
                    }}
                  >
                    下一步
                  </Button>
                ) : (
                  <Button type="primary" loading={saving} onClick={() => void submitSetup()}>
                    完成配置
                  </Button>
                )}
              </Space>
            </>
          ) : null}
        </Space>
      </section>
    </div>
  );
}
