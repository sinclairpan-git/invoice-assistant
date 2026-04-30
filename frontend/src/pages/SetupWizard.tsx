import { App, Spin, Typography } from "../app/antd";
import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import { createInitialSetup, getActiveConfig, getErrorMessage } from "../app/api";
import type { ActiveConfigPayload, BusinessRuleTemplate } from "../app/types";
import { SectionHeader } from "../components/common/SectionHeader";
import {
  ConfigFieldEditor,
  buildConfigFieldDraft,
  type ConfigFieldDraft,
} from "../components/settings/ConfigFieldEditor";

export function SetupWizard() {
  const { message } = App.useApp();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [config, setConfig] = useState<ActiveConfigPayload | null>(null);

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

  const templates = useMemo(
    () => Object.values(config?.setup_status.default_business_rule_templates ?? {}),
    [config],
  );
  const initialDraft = useMemo(() => buildConfigFieldDraft(config, templates), [config, templates]);
  const setupAlreadyComplete = config?.setup_status.complete ?? false;

  const submitSetup = async (draft: ConfigFieldDraft) => {
    const selectedTemplate =
      templates.find((item) => item.template_name === draft.businessRules.templateName) ?? null;
    if (!selectedTemplate) {
      message.error("请先选择业务规则模板。");
      return;
    }

    setSaving(true);
    try {
      await createInitialSetup({
        taxProfile: {
          company_name: draft.taxProfile.enterpriseName.trim(),
          taxpayer_id: draft.taxProfile.taxpayerId.trim(),
          address_phone: draft.taxProfile.addressPhone.trim(),
          bank_account: draft.taxProfile.bankAccount.trim(),
        },
        businessRules: {
          ...selectedTemplate,
        },
        namingRules: {
          pattern: draft.namingRule.pattern.trim(),
        },
        changeSummary: setupAlreadyComplete ? "字段化调整当前配置" : "首次配置",
        changeReason: setupAlreadyComplete ? "配置中心字段表单调整" : "首次配置向导",
      });
      message.success(setupAlreadyComplete ? "配置已更新。" : "首次配置已完成。");
      navigate(setupAlreadyComplete ? "/settings" : "/");
    } catch (submitError) {
      message.error(getErrorMessage(submitError));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="page-stack">
      <section className="workspace-block">
        <SectionHeader
          title={setupAlreadyComplete ? "配置调整" : "首次配置向导"}
          subtitle={
            setupAlreadyComplete
              ? "继续按字段调整税务档案、审核策略和命名规则，再一次性确认保存。"
              : "按顺序补齐税务档案、业务规则模板和命名规则，再一次性确认生效。"
          }
        />
        {loading ? <Spin tip="正在读取首次配置…" /> : null}
        {error ? <Typography.Text type="danger">{error}</Typography.Text> : null}

        {!loading && !error ? (
          <ConfigFieldEditor
            mode={setupAlreadyComplete ? "settings_edit" : "first_setup"}
            initialDraft={initialDraft}
            templates={templates}
            saving={saving}
            onSubmit={(draft) => void submitSetup(draft)}
          />
        ) : null}
      </section>
    </div>
  );
}
