import { Button, Form, Input, Select, Space, Typography } from "../../app/antd";

import type { BusinessRuleTemplate } from "../../app/types";

export interface BusinessRulesTemplateFormValues {
  templateName: string;
  minimumConfidence: string;
}

interface BusinessRulesTemplateStepProps {
  initialValues: BusinessRulesTemplateFormValues;
  templates: BusinessRuleTemplate[];
  onSubmit: (values: BusinessRulesTemplateFormValues) => void;
}

function validateMinimumConfidence(_: unknown, value: string | undefined) {
  const normalized = value?.trim() ?? "";
  if (!normalized) {
    return Promise.reject(new Error("请填写最低置信度阈值"));
  }

  const parsed = Number(normalized);
  if (!Number.isFinite(parsed) || Number.isNaN(parsed)) {
    return Promise.reject(new Error("请输入 0 到 1 之间的数字"));
  }
  if (parsed < 0 || parsed > 1) {
    return Promise.reject(new Error("请输入 0 到 1 之间的数字"));
  }

  return Promise.resolve();
}

export function BusinessRulesTemplateStep({ initialValues, templates, onSubmit }: BusinessRulesTemplateStepProps) {
  const [form] = Form.useForm<BusinessRulesTemplateFormValues>();

  return (
    <Form form={form} layout="vertical" initialValues={initialValues} onFinish={onSubmit}>
      <Typography.Text type="secondary">这一步会影响风险分类阈值与系统建议通过判断。</Typography.Text>
      <Form.Item<BusinessRulesTemplateFormValues> label="模板方案" name="templateName" rules={[{ required: true, message: "请选择模板方案" }]}>
        <Select
          options={templates.map((template) => ({
            label: template.display_name,
            value: template.template_name,
          }))}
        />
      </Form.Item>
      <Form.Item<BusinessRulesTemplateFormValues> label="最低置信度阈值" name="minimumConfidence" rules={[{ validator: validateMinimumConfidence }]}>
        <Input />
      </Form.Item>
      <Space direction="vertical" size={4} className="full-width">
        <Typography.Text type="secondary">保守模板：更容易把可疑票据拦下来，误放行更少，但需要人工复核的票会更多。</Typography.Text>
        <Typography.Text type="secondary">常规模板：更适合日常批量处理，拦截和放行更均衡，人工复核量通常更可控。</Typography.Text>
      </Space>
      <Typography.Text type="secondary">先选一套模板，再按本公司容忍度做少量调整，首次配置阶段不展开全部规则项。</Typography.Text>
      <Button htmlType="submit" style={{ display: "none" }}>
        提交
      </Button>
    </Form>
  );
}
