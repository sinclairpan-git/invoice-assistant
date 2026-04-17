import { Space, Typography } from "antd";
import type { ReactNode } from "react";


interface SectionHeaderProps {
  title: string;
  subtitle?: string;
  actions?: ReactNode;
}

export function SectionHeader({ title, subtitle, actions }: SectionHeaderProps) {
  return (
    <div className="section-header">
      <div>
        <Typography.Title level={4}>{title}</Typography.Title>
        {subtitle ? <Typography.Text type="secondary">{subtitle}</Typography.Text> : null}
      </div>
      {actions ? <Space>{actions}</Space> : null}
    </div>
  );
}
