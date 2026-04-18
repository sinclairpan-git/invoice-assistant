import { Layout, Menu, Space, Tag, Typography } from "./antd";
import { FileSearchOutlined, InboxOutlined, SettingOutlined } from "./icons";
import { Outlet, useLocation, useMatches, useNavigate } from "react-router-dom";

import { useOperatorSettings } from "./operator-settings";


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
  if (pathname.startsWith("/settings")) {
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
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
}
