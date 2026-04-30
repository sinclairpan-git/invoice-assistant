import { Button, Form, Select, Space, Typography } from "../../app/antd";

import type { BusinessRuleTemplate } from "../../app/types";
import { describeBusinessTemplateTone } from "./configPresentation";

export interface BusinessRulesTemplateFormValues {
  templateName: string;
}

interface BusinessRulesTemplateStepProps {
  initialValues: BusinessRulesTemplateFormValues;
  templates: BusinessRuleTemplate[];
  onSubmit: (values: BusinessRulesTemplateFormValues) => void;
}

export function BusinessRulesTemplateStep({ initialValues, templates, onSubmit }: BusinessRulesTemplateStepProps) {
  const [form] = Form.useForm<BusinessRulesTemplateFormValues>();
  const selectedTemplateName = Form.useWatch("templateName", form) ?? initialValues.templateName;
  const selectedTemplate = templates.find((item) => item.template_name === selectedTemplateName) ?? null;

  return (
    <Form form={form} layout="vertical" initialValues={initialValues} onFinish={onSubmit}>
      <Typography.Text type="secondary">这一步会影响系统建议、人工确认量和拦截倾向。</Typography.Text>
      <Form.Item<BusinessRulesTemplateFormValues> label="模板方案" name="templateName" rules={[{ required: true, message: "请选择模板方案" }]}>
        <Select
          options={templates.map((template) => ({
            label: template.display_name,
            value: template.template_name,
          }))}
        />
      </Form.Item>
      {selectedTemplate ? (
        <Space direction="vertical" size={4} className="full-width">
          <Typography.Text strong>审核倾向</Typography.Text>
          <Typography.Text>{describeBusinessTemplateTone(selectedTemplate.template_name, selectedTemplate.display_name)}</Typography.Text>
        </Space>
      ) : null}
      <Space direction="vertical" size={4} className="full-width">
        <Typography.Text type="secondary">保守模板：更容易把可疑票据拦下来，误放行更少，但需要人工复核的票会更多。</Typography.Text>
        <Typography.Text type="secondary">常规模板：更适合日常批量处理，拦截和放行更均衡，人工复核量通常更可控。</Typography.Text>
      </Space>
      <Typography.Text type="secondary">系统会按所选模板自动带出阈值和建议规则，当前阶段不要求财务用户直接调整技术参数。</Typography.Text>
      <Button htmlType="submit" style={{ display: "none" }}>
        提交
      </Button>
    </Form>
  );
}
