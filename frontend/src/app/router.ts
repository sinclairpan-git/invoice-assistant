import { createRouter, createWebHistory } from "vue-router";

import BatchResults from "../pages/BatchResults.vue";
import BatchWorkbench from "../pages/BatchWorkbench.vue";
import Settings from "../pages/Settings.vue";
import SetupWizard from "../pages/SetupWizard.vue";

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: "/",
      component: BatchWorkbench,
      meta: { title: "批次工作台" },
    },
    {
      path: "/results/:batchId?",
      component: BatchResults,
      meta: { title: "批次结果" },
    },
    {
      path: "/settings",
      component: Settings,
      meta: { title: "配置中心" },
    },
    {
      path: "/setup",
      component: SetupWizard,
      meta: { title: "首次配置" },
    },
  ],
});
