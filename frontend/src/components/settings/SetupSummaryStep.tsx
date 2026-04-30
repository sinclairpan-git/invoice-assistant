import { Space, Typography } from "../../app/antd";

import type { BusinessRuleTemplate } from "../../app/types";
import type { BusinessRulesTemplateFormValues } from "./BusinessRulesTemplateStep";
import type { NamingRuleFormValues } from "./NamingRuleStep";
import type { TaxProfileFormValues } from "./TaxProfileStep";
import { describeNamingPattern } from "./configPresentation";

interface SetupSummaryStepProps {
  taxProfile: TaxProfileFormValues;
  businessRules: BusinessRulesTemplateFormValues;
  namingRule: NamingRuleFormValues;
  selectedTemplate: BusinessRuleTemplate | null;
}

export function SetupSummaryStep({
  taxProfile,
  businessRules,
  namingRule,
  selectedTemplate,
}: SetupSummaryStepProps) {
  return (
    <>
      <Typography.Paragraph type="secondary">
        确认后会一次性生成并激活三份版本：税务档案、业务规则模板、命名规则。
      </Typography.Paragraph>
      <Space direction="vertical" size={8} className="full-width">
        <div>
          <Typography.Text strong>企业名称</Typography.Text>
          <div>{taxProfile.enterpriseName}</div>
        </div>
        <div>
          <Typography.Text strong>纳税人识别号（税号）</Typography.Text>
          <div>{taxProfile.taxpayerId}</div>
        </div>
        <div>
          <Typography.Text strong>地址电话</Typography.Text>
          <div>{taxProfile.addressPhone}</div>
        </div>
        <div>
          <Typography.Text strong>开户行及帐号</Typography.Text>
          <div>{taxProfile.bankAccount}</div>
        </div>
        <div>
          <Typography.Text strong>业务规则模板</Typography.Text>
          <div>{selectedTemplate?.display_name || businessRules.templateName}</div>
        </div>
        <div>
          <Typography.Text strong>文件命名方式</Typography.Text>
          <div>{describeNamingPattern(namingRule.pattern)}</div>
        </div>
      </Space>
    </>
  );
}
