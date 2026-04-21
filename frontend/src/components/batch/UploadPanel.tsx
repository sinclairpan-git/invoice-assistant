import { Alert, App, Button, Form, Input, Space, Typography, Upload } from "../../app/antd";
import type { UploadFile } from "../../app/antd";
import { InboxOutlined } from "../../app/icons";
import { useState } from "react";

import { createBatch, getErrorMessage } from "../../app/api";
import { useOperatorSettings } from "../../app/operator-settings";
import type { Batch } from "../../app/types";
import { SectionHeader } from "../common/SectionHeader";


interface UploadPanelProps {
  onCreated: (batch: Batch) => void;
  setupReady?: boolean;
  setupComplete?: boolean;
  setupError?: string | null;
  onOpenSetup?: () => void;
}

interface UploadFormValues {
  batchNo?: string;
}

export function UploadPanel({
  onCreated,
  setupReady = true,
  setupComplete = true,
  setupError = null,
  onOpenSetup,
}: UploadPanelProps) {
  const { message } = App.useApp();
  const { defaultOperatorName } = useOperatorSettings();
  const [form] = Form.useForm<UploadFormValues>();
  const [fileList, setFileList] = useState<UploadFile[]>([]);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (values: UploadFormValues) => {
    const files = fileList.flatMap((file) => (file.originFileObj ? [file.originFileObj as File] : []));

    if (files.length === 0) {
      message.warning("请选择至少一个 PDF 文件");
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

  const uploadEnabled = setupReady && setupComplete && !setupError;

  return (
    <section className="workspace-block">
      <SectionHeader title="新建批次" subtitle="接收 PDF 发票与清单附件" />
      {setupError ? (
        <Alert
          type="error"
          showIcon
          message="配置状态读取失败"
          description="当前无法确认首次配置是否完成，请先重试配置读取。"
        />
      ) : null}
      {!setupError && !setupReady ? (
        <Alert
          type="info"
          showIcon
          message="正在检查首次配置状态"
          description="首次配置状态未确认前，上传入口会保持禁用。"
        />
      ) : null}
      {!setupError && setupReady && !setupComplete ? (
        <Alert
          type="warning"
          showIcon
          message="首次配置未完成"
          description="完成首次配置后才可上传和创建批次。"
          action={
            onOpenSetup ? (
              <Button type="primary" size="small" onClick={onOpenSetup}>
                前往首次配置
              </Button>
            ) : undefined
          }
        />
      ) : null}
      <Form form={form} layout="vertical" onFinish={handleSubmit}>
        <Typography.Text type="secondary">{`当前操作者：${defaultOperatorName}`}</Typography.Text>
        <div className="form-grid">
          <Form.Item<UploadFormValues> label="批次号" name="batchNo">
            <Input placeholder="可选，留空则自动生成" maxLength={60} disabled={!uploadEnabled} />
          </Form.Item>
        </div>
        <Form.Item label="批次文件">
          <Upload.Dragger
            accept=".pdf"
            beforeUpload={() => false}
            disabled={!uploadEnabled}
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
          <Button type="primary" htmlType="submit" loading={submitting} disabled={!uploadEnabled}>
            创建批次
          </Button>
          <Button onClick={() => setFileList([])} disabled={!uploadEnabled || submitting || fileList.length === 0}>
            清空文件
          </Button>
        </Space>
      </Form>
    </section>
  );
}
