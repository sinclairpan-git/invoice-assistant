import { App as AntdApp, ConfigProvider } from "antd";
import type { PropsWithChildren } from "react";

import { OperatorSettingsProvider } from "./operator-settings";


export function AppProviders({ children }: PropsWithChildren) {
  return (
    <ConfigProvider
      theme={{
        token: {
          colorPrimary: "#118a62",
          colorInfo: "#118a62",
          colorSuccess: "#118a62",
          colorWarning: "#c48a11",
          colorError: "#c35f4c",
          colorBgLayout: "#f3f3ef",
          colorBgContainer: "#ffffff",
          colorTextBase: "#1f221d",
          borderRadius: 6,
          fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
        },
      }}
    >
      <AntdApp>
        <OperatorSettingsProvider>{children}</OperatorSettingsProvider>
      </AntdApp>
    </ConfigProvider>
  );
}
