import { App, Button, Descriptions, Form, Input, List, Space, Tag, Typography } from "../app/antd";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import { getActiveConfig, getErrorMessage, listConfigBundles, publishConfigBundle } from "../app/api";
import { useOperatorSettings } from "../app/operator-settings";
import type { ActiveConfigPayload, ConfigBundle } from "../app/types";
import { AsyncBoundary } from "../components/common/AsyncBoundary";
import { SectionHeader } from "../components/common/SectionHeader";
import {
  ConfigFieldEditor,
  buildConfigFieldDraft,
  type ConfigFieldDraft,
} from "../components/settings/ConfigFieldEditor";
import {
  describeBusinessTemplate,
  describeBusinessTemplateTone,
  describeNamingPattern,
} from "../components/settings/configPresentation";
import { SetupStatusCard } from "../components/settings/SetupStatusCard";

interface SettingsState {
  loading: boolean;
  error: string | null;
  config: ActiveConfigPayload | null;
}

interface PublishFormValues {
  changeSummary: string;
  changeReason: string;
}

function readString(content: Record<string, unknown>, ...keys: string[]): string {
  for (const key of keys) {
    const value = content[key];
    if (typeof value === "string" && value.trim()) {
      return value.trim();
    }
  }
  return "--";
}

export function Settings() {
  const { message } = App.useApp();
  const navigate = useNavigate();
  const { currentActor, defaultOperatorName, error: actorError, loading: actorLoading } = useOperatorSettings();
  const [publishForm] = Form.useForm<PublishFormValues>();
  const [state, setState] = useState<SettingsState>({
    loading: true,
    error: null,
    config: null,
  });
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [pendingDraft, setPendingDraft] = useState<ConfigFieldDraft | null>(null);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [bundleHistory, setBundleHistory] = useState<ConfigBundle[]>([]);

  const loadSettings = useCallback(async () => {
    setState((current) => ({
      ...current,
      loading: true,
      error: null,
    }));
    try {
      const config = await getActiveConfig();
      setState({
        loading: false,
        error: null,
        config,
      });
    } catch (error) {
      setState({
        loading: false,
        error: getErrorMessage(error),
        config: null,
      });
    }
  }, []);

  useEffect(() => {
    void loadSettings();
  }, [loadSettings]);

  const setupComplete = state.config?.setup_status.complete ?? false;
  const taxProfileContent = state.config?.active_snapshot.tax_profile?.content ?? {};
  const businessRuleContent = state.config?.active_snapshot.business_rules?.content ?? {};
  const namingRuleContent = state.config?.active_snapshot.naming_rules?.content ?? {};
  const templates = useMemo(
    () => Object.values(state.config?.setup_status.default_business_rule_templates ?? {}),
    [state.config],
  );
  const initialDraft = useMemo(() => buildConfigFieldDraft(state.config, templates), [state.config, templates]);

  const buildPublishPayload = (draft: ConfigFieldDraft, values: PublishFormValues) => {
    const selectedTemplate =
      templates.find((item) => item.template_name === draft.businessRules.templateName) ?? null;
    if (!selectedTemplate) {
      message.error("请先选择业务规则模板。");
      return null;
    }

    return {
      profile: {
        company_name: draft.taxProfile.enterpriseName.trim(),
        taxpayer_id: draft.taxProfile.taxpayerId.trim(),
        address_phone: draft.taxProfile.addressPhone.trim(),
        bank_account: draft.taxProfile.bankAccount.trim(),
      },
      reviewPolicy: {
        ...selectedTemplate,
      },
      namingPolicy: {
        pattern: draft.namingRule.pattern.trim(),
      },
      changeSummary: values.changeSummary.trim(),
      changeReason: values.changeReason.trim(),
    };
  };

  const submitSettings = (draft: ConfigFieldDraft) => {
    setPendingDraft(draft);
    publishForm.setFieldsValue({
      changeSummary: "字段化调整当前配置",
      changeReason: "配置中心字段表单调整",
    });
  };

  const confirmPublish = async (values: PublishFormValues) => {
    if (!pendingDraft) {
      return;
    }
    const payload = buildPublishPayload(pendingDraft, values);
    if (!payload) {
      return;
    }
    setSaving(true);
    try {
      await publishConfigBundle(payload);
      message.success("配置已发布。");
      setPendingDraft(null);
      setEditing(false);
      await loadSettings();
    } catch (error) {
      message.error(getErrorMessage(error));
    } finally {
      setSaving(false);
    }
  };

  const openHistory = async () => {
    setHistoryOpen(true);
    setHistoryLoading(true);
    try {
      setBundleHistory(await listConfigBundles());
    } catch (error) {
      message.error(getErrorMessage(error));
    } finally {
      setHistoryLoading(false);
    }
  };

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
        {setupComplete ? (
          <Space direction="vertical" size="large" className="full-width">
            <section className="workspace-block">
              <SectionHeader
                title="配置中心"
                subtitle="按字段查看当前公司的运行基线；需要修改时，进入字段表单重新填写并保存为新版本。"
                actions={
                  editing ? (
                    <Button
                      onClick={() => {
                        setPendingDraft(null);
                        setEditing(false);
                      }}
                      disabled={saving}
                    >
                      返回配置摘要
                    </Button>
                  ) : (
                    <Space>
                      <Button onClick={() => void openHistory()}>查看历史变更</Button>
                      <Button type="primary" onClick={() => setEditing(true)}>
                        按字段修改配置
                      </Button>
                    </Space>
                  )
                }
              />
              <Typography.Text type="secondary">当前页已隐藏技术配置 JSON，避免要求财务用户直接编辑系统键名。</Typography.Text>
            </section>
            {editing ? (
              <section className="workspace-block">
                <SectionHeader
                  title="字段化调整"
                  subtitle="复用首次配置的字段表单，统一维护税务档案、审核策略和文件命名。"
                />
                <ConfigFieldEditor
                  mode="settings_edit"
                  initialDraft={initialDraft}
                  templates={templates}
                  saving={saving}
                  onSubmit={(draft) => void submitSettings(draft)}
                />
                {pendingDraft ? (
                  <section className="workspace-block">
                    <SectionHeader
                      title="发布确认"
                      subtitle="保存前确认本次配置变更的业务影响，并写入统一配置包版本。"
                    />
                    <Space direction="vertical" size={12} className="full-width">
                      <Typography.Text strong>影响范围</Typography.Text>
                      <Typography.Text>
                        税务档案、审核策略、文件命名会整体生成新版本并立即生效。
                      </Typography.Text>
                      <Form form={publishForm} layout="vertical" onFinish={(values) => void confirmPublish(values)}>
                        <Form.Item<PublishFormValues>
                          label="变更摘要"
                          name="changeSummary"
                          rules={[{ required: true, message: "请输入变更摘要" }]}
                        >
                          <Input maxLength={80} />
                        </Form.Item>
                        <Form.Item<PublishFormValues>
                          label="变更原因"
                          name="changeReason"
                          rules={[{ required: true, message: "请输入变更原因" }]}
                        >
                          <Input maxLength={120} />
                        </Form.Item>
                        <Button type="primary" htmlType="submit" loading={saving}>
                          确认发布
                        </Button>
                      </Form>
                    </Space>
                  </section>
                ) : null}
              </section>
            ) : (
              <>
                <SetupStatusCard config={state.config} />
                {historyOpen ? (
                  <section className="workspace-block">
                    <SectionHeader title="历史变更" subtitle="历史版本仅供查阅，不允许直接编辑。" />
                    <List
                      bordered
                      loading={historyLoading}
                      dataSource={bundleHistory}
                      locale={{ emptyText: "暂无历史变更" }}
                      renderItem={(item) => (
                        <List.Item>
                          <Space direction="vertical" size={2} className="full-width">
                            <Typography.Text strong>{item.bundle_version_no}</Typography.Text>
                            <Typography.Text>{item.change_summary}</Typography.Text>
                            <Typography.Text type="secondary">{item.change_reason}</Typography.Text>
                            <Typography.Text type="secondary">{`${item.changed_by} · ${item.changed_at}`}</Typography.Text>
                          </Space>
                        </List.Item>
                      )}
                    />
                  </section>
                ) : null}
                <section className="workspace-block">
                  <SectionHeader title="公司税务档案" subtitle="影响购方抬头、税号匹配和基础校验。" />
                  <Descriptions bordered size="small" column={1}>
                    <Descriptions.Item label="企业名称">
                      {readString(taxProfileContent, "company_name", "buyer_name")}
                    </Descriptions.Item>
                    <Descriptions.Item label="纳税人识别号（税号）">
                      {readString(taxProfileContent, "taxpayer_id", "buyer_tax_no")}
                    </Descriptions.Item>
                    <Descriptions.Item label="地址电话">{readString(taxProfileContent, "address_phone")}</Descriptions.Item>
                    <Descriptions.Item label="开户行及帐号">{readString(taxProfileContent, "bank_account")}</Descriptions.Item>
                  </Descriptions>
                </section>
                <section className="workspace-block">
                  <SectionHeader title="审核策略" subtitle="影响系统建议和人工确认量。" />
                  <Descriptions bordered size="small" column={1}>
                    <Descriptions.Item label="模板方案">
                      {describeBusinessTemplate(
                        readString(businessRuleContent, "template_name"),
                        readString(businessRuleContent, "display_name"),
                      )}
                    </Descriptions.Item>
                    <Descriptions.Item label="审核倾向">
                      {describeBusinessTemplateTone(
                        readString(businessRuleContent, "template_name"),
                        readString(businessRuleContent, "display_name"),
                      )}
                    </Descriptions.Item>
                  </Descriptions>
                </section>
                <section className="workspace-block">
                  <SectionHeader title="文件命名" subtitle="影响识别完成后的建议文件名。" />
                  <Descriptions bordered size="small" column={1}>
                    <Descriptions.Item label="当前命名方式">
                      {describeNamingPattern(readString(namingRuleContent, "pattern"))}
                    </Descriptions.Item>
                  </Descriptions>
                </section>
              </>
            )}
          </Space>
        ) : (
          <section className="workspace-block">
            <SectionHeader title="配置中心" subtitle="请先完成首次配置，后续调整也会继续使用字段表单。" />
            <Button type="primary" onClick={() => navigate("/setup")}>
              前往首次配置
            </Button>
          </section>
        )}
      </AsyncBoundary>
    </div>
  );
}
