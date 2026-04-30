import { Button, Form, Input, Typography } from "../../app/antd";

export interface TaxProfileFormValues {
  enterpriseName: string;
  taxpayerId: string;
  addressPhone: string;
  bankAccount: string;
}

interface TaxProfileStepProps {
  initialValues: TaxProfileFormValues;
  onSubmit: (values: TaxProfileFormValues) => void;
}

export function TaxProfileStep({ initialValues, onSubmit }: TaxProfileStepProps) {
  const [form] = Form.useForm<TaxProfileFormValues>();

  return (
    <Form form={form} layout="vertical" initialValues={initialValues} onFinish={onSubmit}>
      <Form.Item>
        <Typography.Text type="secondary">这一步会影响购方抬头、税号匹配以及基础合规判断。</Typography.Text>
      </Form.Item>

      <Form.Item<TaxProfileFormValues>
        label="企业名称"
        name="enterpriseName"
        rules={[{ required: true, message: "请填写企业名称" }]}
      >
        <Input maxLength={120} />
      </Form.Item>

      <Form.Item<TaxProfileFormValues>
        label="纳税人识别号（税号）"
        name="taxpayerId"
        rules={[{ required: true, message: "请填写纳税人识别号（税号）" }]}
      >
        <Input maxLength={32} />
      </Form.Item>

      <Form.Item<TaxProfileFormValues>
        label="地址电话"
        name="addressPhone"
      >
        <Input maxLength={200} />
      </Form.Item>

      <Form.Item<TaxProfileFormValues>
        label="开户行及帐号"
        name="bankAccount"
      >
        <Input maxLength={200} />
      </Form.Item>

      <Button htmlType="submit" style={{ display: "none" }}>
        提交
      </Button>
    </Form>
  );
}
