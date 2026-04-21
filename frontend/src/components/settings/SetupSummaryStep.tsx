import { Space, Typography } from "../../app/antd";

import type { BusinessRuleTemplate } from "../../app/types";
import type { BusinessRulesTemplateFormValues } from "./BusinessRulesTemplateStep";
import type { NamingRuleFormValues } from "./NamingRuleStep";
import type { TaxProfileFormValues } from "./TaxProfileStep";

interface SetupSummaryStepProps {
  taxProfile: TaxProfileFormValues;
  businessRules: BusinessRulesTemplateFormValues;
  namingRule: NamingRuleFormValues;
  selectedTemplate: BusinessRuleTemplate | null;
}

export function SetupSummaryStep({ taxProfile, businessRules, namingRule, selectedTemplate }: SetupSummaryStepProps) {
  return (
    <>
      <Typography.Paragraph type="secondary">确认后会一次性生成并激活三份版本：税务档案、业务规则模板、命名规则。</Typography.Paragraph>
      <Space direction="vertical" size={8} className="full-width">
        <div>
          <Typography.Text strong>公司名称</Typography.Text>
          <div>{taxProfile.companyName}</div>
        </div>
        <div>
          <Typography.Text strong>购方名称</Typography.Text>
          <div>{taxProfile.buyerName}</div>
        </div>
        <div>
          <Typography.Text strong>购方税号</Typography.Text>
          <div>{taxProfile.buyerTaxNo}</div>
        </div>
        <div>
          <Typography.Text strong>业务规则模板</Typography.Text>
          <div>{selectedTemplate ? `${selectedTemplate.display_name}（${businessRules.templateName}）` : businessRules.templateName}</div>
        </div>
        <div>
          <Typography.Text strong>文件命名模板</Typography.Text>
          <div>{namingRule.pattern}</div>
        </div>
      </Space>
    </>
  );
}
