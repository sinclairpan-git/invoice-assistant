import { Suspense, lazy } from "react";
import { createHashRouter } from "react-router-dom";
import type { ReactNode } from "react";
import type { RouteObject } from "react-router-dom";

import { AppShell } from "./shell";

const BatchWorkbench = lazy(async () => {
  const module = await import("../pages/BatchWorkbench");
  return { default: module.BatchWorkbench };
});

const BatchResults = lazy(async () => {
  const module = await import("../pages/BatchResults");
  return { default: module.BatchResults };
});

const Settings = lazy(async () => {
  const module = await import("../pages/Settings");
  return { default: module.Settings };
});

function withRouteSuspense(element: ReactNode) {
  return <Suspense fallback={<div>加载中...</div>}>{element}</Suspense>;
}

export const appRoutes: RouteObject[] = [
  {
    path: "/",
    element: <AppShell />,
    children: [
      {
        index: true,
        element: withRouteSuspense(<BatchWorkbench />),
        handle: { title: "批次工作台" },
      },
      {
        path: "results",
        element: withRouteSuspense(<BatchResults />),
        handle: { title: "批次结果" },
      },
      {
        path: "results/:batchId",
        element: withRouteSuspense(<BatchResults />),
        handle: { title: "批次结果" },
      },
      {
        path: "settings",
        element: withRouteSuspense(<Settings />),
        handle: { title: "配置中心" },
      },
    ],
  },
];

export function createAppRouter() {
  return createHashRouter(appRoutes);
}
