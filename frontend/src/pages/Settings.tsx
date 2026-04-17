import { App, Button, Form, Input, Space } from "../app/antd";
import { useCallback, useEffect, useMemo, useState } from "react";

import { getActiveConfig, getErrorMessage, listRuleVersions } from "../app/api";
import { useOperatorSettings } from "../app/operator-settings";
import type { ActiveConfigPayload, RuleKind, RuleVersion } from "../app/types";
import { AsyncBoundary } from "../components/common/AsyncBoundary";
import { SectionHeader } from "../components/common/SectionHeader";
import { RuleVersionPanel } from "../components/settings/RuleVersionPanel";


type VersionState = Partial<Record<RuleKind, RuleVersion[]>>;

const RULE_META: Array<{ kind: RuleKind; title: string; subtitle: string }> = [
  {
    kind: "tax_profile",
    title: "公司税务档案",
    subtitle: "维护购方名称、税号等核验基线",
  },
  {
    kind: "business_rules",
    title: "业务风险规则",
    subtitle: "维护风险分类阈值和业务判定规则",
  },
  {
    kind: "naming_rules",
    title: "命名模板",
    subtitle: "维护重命名模板和归档格式",
  },
];

interface SettingsState {
  loading: boolean;
  error: string | null;
  config: ActiveConfigPayload | null;
  versions: VersionState;
}

export function Settings() {
  const { message } = App.useApp();
  const { defaultOperatorName, setDefaultOperatorName } = useOperatorSettings();
  const [operatorForm] = Form.useForm<{ operatorName: string }>();
  const [state, setState] = useState<SettingsState>({
    loading: true,
    error: null,
    config: null,
    versions: {},
  });

  const loadSettings = useCallback(async () => {
    setState((current) => ({
      ...current,
      loading: true,
      error: null,
    }));
    try {
      const [config, taxProfileVersions, businessRuleVersions, namingVersions] = await Promise.all([
        getActiveConfig(),
        listRuleVersions("tax_profile"),
        listRuleVersions("business_rules"),
        listRuleVersions("naming_rules"),
      ]);
      setState({
        loading: false,
        error: null,
        config,
        versions: {
          tax_profile: taxProfileVersions,
          business_rules: businessRuleVersions,
          naming_rules: namingVersions,
        },
      });
    } catch (error) {
      setState({
        loading: false,
        error: getErrorMessage(error),
        config: null,
        versions: {},
      });
    }
  }, []);

  useEffect(() => {
    operatorForm.setFieldValue("operatorName", defaultOperatorName);
  }, [defaultOperatorName, operatorForm]);

  useEffect(() => {
    void loadSettings();
  }, [loadSettings]);

  const activeVersions = useMemo(() => state.config?.active_versions ?? {}, [state.config]);

  return (
    <div className="page-stack">
      <section className="workspace-block">
        <SectionHeader title="默认操作者" subtitle="结果导出、复核和配置变更都会使用这里的默认姓名" />
        <Form
          form={operatorForm}
          layout="inline"
          onFinish={(values) => {
            setDefaultOperatorName(values.operatorName);
            message.success("默认操作者已更新");
          }}
        >
          <Form.Item<{ operatorName: string }>
            name="operatorName"
            rules={[{ required: true, message: "请输入默认操作者名" }]}
          >
            <Input style={{ width: 280 }} maxLength={40} />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit">
              保存
            </Button>
          </Form.Item>
        </Form>
      </section>

      <AsyncBoundary loading={state.loading} error={state.error}>
        <Space direction="vertical" size="large" className="full-width">
          {RULE_META.map((item) => (
            <RuleVersionPanel
              key={item.kind}
              kind={item.kind}
              title={item.title}
              subtitle={item.subtitle}
              activeVersion={activeVersions[item.kind]}
              versions={state.versions[item.kind] ?? []}
              onUpdated={loadSettings}
            />
          ))}
        </Space>
      </AsyncBoundary>
    </div>
  );
}
