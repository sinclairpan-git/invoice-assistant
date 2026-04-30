import { Alert, Button, Space, Tag, Typography } from "../../app/antd";

import type { ActiveConfigPayload, BusinessRuleTemplate } from "../../app/types";
import { describeNamingPattern } from "./configPresentation";

interface SetupStatusCardProps {
  config: ActiveConfigPayload | null;
  loading?: boolean;
  error?: string | null;
  showAction?: boolean;
  onOpenSetup?: () => void;
  onOpenWorkbench?: () => void;
}

function resolveTaxProfileSummary(config: ActiveConfigPayload | null): string {
  const content = config?.active_snapshot.tax_profile?.content ?? {};
  const enterpriseName =
    typeof content.company_name === "string"
      ? content.company_name
      : typeof content.buyer_name === "string"
        ? content.buyer_name
        : null;
  const taxpayerId =
    typeof content.taxpayer_id === "string"
      ? content.taxpayer_id
      : typeof content.buyer_tax_no === "string"
        ? content.buyer_tax_no
        : null;

  if (enterpriseName && taxpayerId) {
    return `${enterpriseName} / ${taxpayerId}`;
  }
  return "待填写";
}

function resolveTemplateSummary(config: ActiveConfigPayload | null): string {
  const content = config?.active_snapshot.business_rules?.content ?? {};
  const displayName = typeof content.display_name === "string" ? content.display_name : null;
  const templateName = typeof content.template_name === "string" ? content.template_name : null;
  return displayName ?? templateName ?? "待选择";
}

function resolveNamingSummary(config: ActiveConfigPayload | null): string {
  const content = config?.active_snapshot.naming_rules?.content ?? {};
  const pattern = typeof content.pattern === "string" ? content.pattern : null;
  return describeNamingPattern(pattern);
}

function resolveMissingLabels(config: ActiveConfigPayload | null): string[] {
  const missing = config?.setup_status.missing_required_fields;
  if (!missing) {
    return [];
  }

  const labels: Array<[keyof typeof missing, string]> = [
    ["tax_profile", "税务档案"],
    ["business_rules", "业务规则模板"],
    ["naming_rules", "命名规则"],
  ];

  return labels.filter(([key]) => (missing[key] ?? []).length > 0).map(([, label]) => label);
}

function resolveTemplateCount(config: ActiveConfigPayload | null): number {
  return Object.values(config?.setup_status.default_business_rule_templates ?? {}).filter(
    (value): value is BusinessRuleTemplate => Boolean(value),
  ).length;
}

function resolveRemainingSteps(config: ActiveConfigPayload | null): number {
  return resolveMissingLabels(config).length;
}

function resolveLastModifiedAt(config: ActiveConfigPayload | null): string {
  const latest = Object.values(config?.active_versions ?? {})
    .map((item) => item?.changed_at ?? null)
    .filter((value): value is string => Boolean(value))
    .sort()
    .at(-1);

  if (!latest) {
    return "尚未生成版本";
  }

  return latest.replace("T", " ").slice(0, 16);
}

export function SetupStatusCard({
  config,
  loading = false,
  error = null,
  showAction = false,
  onOpenSetup,
  onOpenWorkbench,
}: SetupStatusCardProps) {
  const unknown = !loading && Boolean(error);
  const complete = config?.setup_status.complete ?? false;
  const missingLabels = resolveMissingLabels(config);
  const remainingSteps = resolveRemainingSteps(config);

  return (
    <section className="workspace-block">
      <Space direction="vertical" size={12} className="full-width">
        <div className="section-header">
          <div>
            <Typography.Title level={4}>当前公司配置</Typography.Title>
            <Typography.Text type="secondary">
              首次配置完成后，这份摘要会持续作为当前公司的运行基线。
            </Typography.Text>
          </div>
          <Tag color={unknown ? "red" : complete ? "green" : "gold"}>
            {unknown ? "配置状态未知" : complete ? "首次配置已完成" : "首次配置未完成"}
          </Tag>
        </div>

        {loading ? <Typography.Text type="secondary">正在读取当前配置…</Typography.Text> : null}

        {!loading ? (
          <Space direction="vertical" size={8} className="full-width">
            <div>
              <Typography.Text strong>税务档案</Typography.Text>
              <div>{resolveTaxProfileSummary(config)}</div>
            </div>
            <div>
              <Typography.Text strong>业务规则模板</Typography.Text>
              <div>
                <Space wrap>
                  <Typography.Text>{resolveTemplateSummary(config)}</Typography.Text>
                  <Typography.Text type="secondary">{`候选模板 ${resolveTemplateCount(config)} 个`}</Typography.Text>
                </Space>
              </div>
            </div>
            <div>
              <Typography.Text strong>命名规则</Typography.Text>
              <div>{resolveNamingSummary(config)}</div>
            </div>
            <div>
              <Typography.Text type="secondary">{`最后修改于 ${resolveLastModifiedAt(config)}`}</Typography.Text>
            </div>
          </Space>
        ) : null}

        {unknown ? (
          <Alert
            type="error"
            showIcon
            message="当前无法确认首次配置状态"
            description={`${error}。上传入口会继续保持禁用。`}
          />
        ) : !complete ? (
          <Alert
            type="warning"
            showIcon
            message="完成首次配置后才可上传和创建批次。"
            description={missingLabels.length > 0 ? `还差 ${remainingSteps} 步：${missingLabels.join("、")}` : "仍有必填项未补齐。"}
            action={
              showAction && onOpenSetup ? (
                <Button type="primary" size="small" onClick={onOpenSetup}>
                  前往首次配置
                </Button>
              ) : undefined
            }
          />
        ) : showAction && onOpenWorkbench ? (
          <Button type="primary" onClick={onOpenWorkbench}>
            去处理发票
          </Button>
        ) : null}
      </Space>
    </section>
  );
}
