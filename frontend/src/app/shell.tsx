import { Layout, Menu, Space, Tag, Typography } from "./antd";
import { useEffect, useState } from "react";
import { FileSearchOutlined, InboxOutlined, SettingOutlined } from "./icons";
import { Outlet, useLocation, useMatches, useNavigate } from "react-router-dom";

import { getActiveConfig, getErrorMessage } from "./api";
import { useOperatorSettings } from "./operator-settings";
import type { ActiveConfigPayload, ConfigLoadState } from "./types";
import { SetupStatusCard } from "../components/settings/SetupStatusCard";


const { Content, Header, Sider } = Layout;

const MENU_ITEMS = [
  {
    key: "/",
    icon: <InboxOutlined />,
    label: "批次工作台",
  },
  {
    key: "/results",
    icon: <FileSearchOutlined />,
    label: "批次结果",
  },
  {
    key: "/settings",
    icon: <SettingOutlined />,
    label: "配置中心",
  },
];

function resolveTitle(matches: ReturnType<typeof useMatches>): string {
  const routeMatch = [...matches].reverse().find((match) => {
    const handle = match.handle as { title?: string } | undefined;
    return Boolean(handle?.title);
  });
  return ((routeMatch?.handle as { title?: string } | undefined)?.title ?? "发票整理助手");
}

function resolveMenuKey(pathname: string): string {
  if (pathname.startsWith("/settings") || pathname.startsWith("/setup")) {
    return "/settings";
  }
  if (pathname.startsWith("/results")) {
    return "/results";
  }
  return "/";
}

export function AppShell() {
  const location = useLocation();
  const matches = useMatches();
  const navigate = useNavigate();
  const { defaultOperatorName } = useOperatorSettings();
  const [config, setConfig] = useState<ActiveConfigPayload | null>(null);
  const [configState, setConfigState] = useState<ConfigLoadState>("loading");
  const [configError, setConfigError] = useState<string | null>(null);

  useEffect(() => {
    let disposed = false;

    async function loadConfig() {
      setConfigState("loading");
      try {
        const payload = await getActiveConfig();
        if (!disposed) {
          setConfig(payload);
          setConfigError(null);
          setConfigState("ready");
        }
      } catch (error) {
        if (!disposed) {
          setConfig(null);
          setConfigError(getErrorMessage(error));
          setConfigState("error");
        }
      }
    }

    void loadConfig();
    return () => {
      disposed = true;
    };
  }, [location.pathname]);

  return (
    <Layout className="app-shell">
      <Sider width={220} breakpoint="lg" collapsedWidth={0} className="app-sider">
        <div className="brand-block">
          <Typography.Text className="brand-eyebrow">本机工作台</Typography.Text>
          <Typography.Title level={3}>发票整理助手</Typography.Title>
        </div>
        <Menu
          mode="inline"
          selectedKeys={[resolveMenuKey(location.pathname)]}
          items={MENU_ITEMS}
          onClick={({ key }) => navigate(key)}
        />
      </Sider>
      <Layout>
        <Header className="app-header">
          <div>
            <Typography.Text type="secondary">当前页面</Typography.Text>
            <Typography.Title level={3}>{resolveTitle(matches)}</Typography.Title>
          </div>
          <Space size="middle">
            <Typography.Text type="secondary">可信上下文</Typography.Text>
            <Tag color="green">{defaultOperatorName}</Tag>
          </Space>
        </Header>
        <Content className="app-content">
          <SetupStatusCard
            config={config}
            loading={configState === "loading"}
            error={configError}
            showAction
            onOpenSetup={() => navigate("/setup")}
            onOpenWorkbench={() => navigate("/")}
          />
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
}
