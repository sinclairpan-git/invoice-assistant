import { Space, Tag, Typography } from "../app/antd";
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
  const { currentActor, defaultOperatorName, error: actorError, loading: actorLoading } = useOperatorSettings();
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
    void loadSettings();
  }, [loadSettings]);

  const activeVersions = useMemo(() => state.config?.active_versions ?? {}, [state.config]);

  return (
    <div className="page-stack">
      <section className="workspace-block">
        <SectionHeader title="当前操作者" subtitle="由后端可信上下文提供，用于复核、导出和配置变更审计" />
        <Space direction="vertical" size={8} className="full-width">
          <Typography.Text strong>{defaultOperatorName}</Typography.Text>
          <Space wrap>
            {currentActor.roles.length > 0 ? (
              currentActor.roles.map((role) => <Tag key={role}>{role}</Tag>)
            ) : (
              <Typography.Text type="secondary">当前未分配受控角色</Typography.Text>
            )}
          </Space>
          {actorLoading ? <Typography.Text type="secondary">正在读取后端可信身份…</Typography.Text> : null}
          {actorError ? <Typography.Text type="danger">{actorError}</Typography.Text> : null}
        </Space>
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
