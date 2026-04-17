import { Alert, Empty, Spin } from "antd";
import type { PropsWithChildren } from "react";


interface AsyncBoundaryProps extends PropsWithChildren {
  loading: boolean;
  error?: string | null;
  empty?: boolean;
  emptyDescription?: string;
}

export function AsyncBoundary({
  loading,
  error,
  empty,
  emptyDescription = "暂无数据",
  children,
}: AsyncBoundaryProps) {
  if (loading) {
    return (
      <div className="state-panel">
        <Spin size="large" />
      </div>
    );
  }

  if (error) {
    return <Alert type="error" showIcon message="加载失败" description={error} />;
  }

  if (empty) {
    return (
      <div className="state-panel">
        <Empty description={emptyDescription} />
      </div>
    );
  }

  return <>{children}</>;
}
