import { App, Button, Form, Input, List, Space, Tag, Typography } from "antd";
import { useEffect, useState } from "react";

import { createRuleVersion, getErrorMessage } from "../../app/api";
import { useOperatorSettings } from "../../app/operator-settings";
import type { RuleKind, RuleVersion } from "../../app/types";
import { SectionHeader } from "../common/SectionHeader";


interface RuleVersionPanelProps {
  kind: RuleKind;
  title: string;
  subtitle: string;
  activeVersion?: RuleVersion;
  versions: RuleVersion[];
  onUpdated: () => Promise<void> | void;
}

interface RuleVersionFormValues {
  changedBy: string;
  changeSummary: string;
  changeReason: string;
  contentText: string;
}

export function RuleVersionPanel({
  kind,
  title,
  subtitle,
  activeVersion,
  versions,
  onUpdated,
}: RuleVersionPanelProps) {
  const { message } = App.useApp();
  const { defaultOperatorName } = useOperatorSettings();
  const [form] = Form.useForm<RuleVersionFormValues>();
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    form.setFieldsValue({
      changedBy: defaultOperatorName,
      contentText: JSON.stringify(activeVersion?.content ?? {}, null, 2),
    });
  }, [activeVersion, defaultOperatorName, form]);

  const handleSubmit = async (values: RuleVersionFormValues) => {
    let parsedContent: Record<string, unknown>;
    try {
      parsedContent = JSON.parse(values.contentText) as Record<string, unknown>;
    } catch {
      message.error("配置内容不是合法 JSON");
      return;
    }

    setSubmitting(true);
    try {
      await createRuleVersion({
        kind,
        content: parsedContent,
        changedBy: values.changedBy.trim(),
        changeSummary: values.changeSummary.trim(),
        changeReason: values.changeReason.trim(),
      });
      message.success(`${title} 已生成新版本`);
      form.setFieldValue("changeSummary", "");
      form.setFieldValue("changeReason", "");
      await onUpdated();
    } catch (error) {
      message.error(getErrorMessage(error));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <section className="workspace-block">
      <SectionHeader
        title={title}
        subtitle={subtitle}
        actions={activeVersion ? <Tag color="green">{activeVersion.version_no}</Tag> : <Tag>未配置</Tag>}
      />
      <Form form={form} layout="vertical" onFinish={handleSubmit}>
        <div className="form-grid">
          <Form.Item<RuleVersionFormValues> label="操作者" name="changedBy" rules={[{ required: true, message: "请输入操作者名" }]}>
            <Input />
          </Form.Item>
          <Form.Item<RuleVersionFormValues>
            label="变更摘要"
            name="changeSummary"
            rules={[{ required: true, message: "请输入变更摘要" }]}
          >
            <Input maxLength={80} />
          </Form.Item>
        </div>
        <Form.Item<RuleVersionFormValues>
          label="变更原因"
          name="changeReason"
          rules={[{ required: true, message: "请输入变更原因" }]}
        >
          <Input maxLength={120} />
        </Form.Item>
        <Form.Item<RuleVersionFormValues>
          label="配置内容"
          name="contentText"
          rules={[{ required: true, message: "请输入配置内容" }]}
        >
          <Input.TextArea rows={10} />
        </Form.Item>
        <Space>
          <Button type="primary" htmlType="submit" loading={submitting}>
            保存为新版本
          </Button>
        </Space>
      </Form>
      <List
        className="version-list"
        header="历史版本"
        bordered
        dataSource={versions}
        locale={{ emptyText: "暂无历史版本" }}
        renderItem={(item) => (
          <List.Item>
            <Space direction="vertical" size={2} className="full-width">
              <Space wrap>
                <Typography.Text strong>{item.version_no}</Typography.Text>
                {item.is_active ? <Tag color="green">当前生效</Tag> : null}
              </Space>
              <Typography.Text>{item.change_summary}</Typography.Text>
              <Typography.Text type="secondary">{`${item.changed_by} · ${item.changed_at}`}</Typography.Text>
              <Typography.Text type="secondary">{item.change_reason}</Typography.Text>
            </Space>
          </List.Item>
        )}
      />
    </section>
  );
}
