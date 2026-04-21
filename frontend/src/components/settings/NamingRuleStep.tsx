import { Button, Form, Input, Typography } from "../../app/antd";

export interface NamingRuleFormValues {
  pattern: string;
}

interface NamingRuleStepProps {
  initialValues: NamingRuleFormValues;
  onSubmit: (values: NamingRuleFormValues) => void;
}

export function NamingRuleStep({ initialValues, onSubmit }: NamingRuleStepProps) {
  const [form] = Form.useForm<NamingRuleFormValues>();

  return (
    <Form form={form} layout="vertical" initialValues={initialValues} onFinish={onSubmit}>
      <Typography.Text type="secondary">这一步会影响归档文件名与后续人工检索。</Typography.Text>
      <Form.Item<NamingRuleFormValues> label="文件命名规则" name="pattern" rules={[{ required: true, message: "请填写文件命名规则" }]}>
        <Input maxLength={120} />
      </Form.Item>
      <Typography.Text type="secondary">建议把日期、购方、金额等关键字段放进规则，便于后续查找与复核。</Typography.Text>
      <Button htmlType="submit" style={{ display: "none" }}>
        提交
      </Button>
    </Form>
  );
}
