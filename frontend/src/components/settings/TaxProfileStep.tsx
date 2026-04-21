import { Button, Form, Input, Typography } from "../../app/antd";

export interface TaxProfileFormValues {
  companyName: string;
  buyerName: string;
  buyerTaxNo: string;
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
      <Form.Item<TaxProfileFormValues> label="公司名称" name="companyName" rules={[{ required: true, message: "请填写公司名称" }]}>
        <Input maxLength={120} />
      </Form.Item>
      <Form.Item<TaxProfileFormValues> label="购方名称" name="buyerName" rules={[{ required: true, message: "请填写购方名称" }]}>
        <Input maxLength={120} />
      </Form.Item>
      <Form.Item<TaxProfileFormValues>
        label="购方税号"
        name="buyerTaxNo"
        rules={[{ required: true, message: "请填写购方税号" }]}
      >
        <Input maxLength={32} />
      </Form.Item>
      <Button htmlType="submit" style={{ display: "none" }}>
        提交
      </Button>
    </Form>
  );
}
