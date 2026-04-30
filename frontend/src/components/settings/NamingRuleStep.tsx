import { Button, Form, Select, Typography } from "../../app/antd";

import { describeNamingPattern, getNamingPatternDescription, getNamingPatternOptions } from "./configPresentation";

export interface NamingRuleFormValues {
  pattern: string;
}

interface NamingRuleStepProps {
  initialValues: NamingRuleFormValues;
  onSubmit: (values: NamingRuleFormValues) => void;
}

export function NamingRuleStep({ initialValues, onSubmit }: NamingRuleStepProps) {
  const [form] = Form.useForm<NamingRuleFormValues>();
  const selectedPattern = Form.useWatch("pattern", form) ?? initialValues.pattern;

  return (
    <Form form={form} layout="vertical" initialValues={initialValues} onFinish={onSubmit}>
      <Typography.Text type="secondary">这一步会影响归档文件名与后续人工检索。</Typography.Text>
      <Form.Item<NamingRuleFormValues> label="归档命名方式" name="pattern" rules={[{ required: true, message: "请选择归档命名方式" }]}>
        <Select options={getNamingPatternOptions(initialValues.pattern)} />
      </Form.Item>
      <Typography.Text>{`当前命名方式：${describeNamingPattern(selectedPattern)}`}</Typography.Text>
      <Typography.Text type="secondary">{getNamingPatternDescription(selectedPattern)}</Typography.Text>
      <Button htmlType="submit" style={{ display: "none" }}>
        提交
      </Button>
    </Form>
  );
}
