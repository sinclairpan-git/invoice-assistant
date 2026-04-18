import { App, Button, Form, Input, Space, Typography, Upload } from "../../app/antd";
import type { UploadFile } from "../../app/antd";
import { InboxOutlined } from "../../app/icons";
import { useState } from "react";

import { createBatch, getErrorMessage } from "../../app/api";
import { useOperatorSettings } from "../../app/operator-settings";
import type { Batch } from "../../app/types";
import { SectionHeader } from "../common/SectionHeader";


interface UploadPanelProps {
  onCreated: (batch: Batch) => void;
}

interface UploadFormValues {
  batchNo?: string;
}

export function UploadPanel({ onCreated }: UploadPanelProps) {
  const { message } = App.useApp();
  const { defaultOperatorName } = useOperatorSettings();
  const [form] = Form.useForm<UploadFormValues>();
  const [fileList, setFileList] = useState<UploadFile[]>([]);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (values: UploadFormValues) => {
    const files = fileList.flatMap((file) => (file.originFileObj ? [file.originFileObj as File] : []));

    if (files.length === 0) {
      message.warning("请选择至少一张 PDF 发票");
      return;
    }

    setSubmitting(true);
    try {
      const batch = await createBatch({
        batchNo: values.batchNo?.trim() || undefined,
        files,
      });
      setFileList([]);
      form.setFieldValue("batchNo", undefined);
      message.success(`批次 ${batch.batch_no} 已创建`);
      onCreated(batch);
    } catch (error) {
      message.error(getErrorMessage(error));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <section className="workspace-block">
      <SectionHeader title="新建批次" subtitle="仅接收 PDF 发票" />
      <Form form={form} layout="vertical" onFinish={handleSubmit}>
        <Typography.Text type="secondary">{`当前操作者：${defaultOperatorName}`}</Typography.Text>
        <div className="form-grid">
          <Form.Item<UploadFormValues> label="批次号" name="batchNo">
            <Input placeholder="可选，留空则自动生成" maxLength={60} />
          </Form.Item>
        </div>
        <Form.Item label="发票文件">
          <Upload.Dragger
            accept=".pdf"
            beforeUpload={() => false}
            fileList={fileList}
            multiple
            onChange={({ fileList: nextFileList }) => setFileList(nextFileList)}
          >
            <p className="ant-upload-drag-icon">
              <InboxOutlined />
            </p>
            <Typography.Text>拖入 PDF，或点击选择文件</Typography.Text>
          </Upload.Dragger>
        </Form.Item>
        <Space>
          <Button type="primary" htmlType="submit" loading={submitting}>
            创建批次
          </Button>
          <Button onClick={() => setFileList([])} disabled={submitting || fileList.length === 0}>
            清空文件
          </Button>
        </Space>
      </Form>
    </section>
  );
}
