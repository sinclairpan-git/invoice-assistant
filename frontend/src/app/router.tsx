import { createHashRouter } from "react-router-dom";
import type { RouteObject } from "react-router-dom";

import { AppShell } from "./shell";
import { BatchWorkbench } from "../pages/BatchWorkbench";
import { BatchResults } from "../pages/BatchResults";
import { Settings } from "../pages/Settings";


export const appRoutes: RouteObject[] = [
  {
    path: "/",
    element: <AppShell />,
    children: [
      {
        index: true,
        element: <BatchWorkbench />,
        handle: { title: "批次工作台" },
      },
      {
        path: "results",
        element: <BatchResults />,
        handle: { title: "批次结果" },
      },
      {
        path: "results/:batchId",
        element: <BatchResults />,
        handle: { title: "批次结果" },
      },
      {
        path: "settings",
        element: <Settings />,
        handle: { title: "配置中心" },
      },
    ],
  },
];

export function createAppRouter() {
  return createHashRouter(appRoutes);
}
