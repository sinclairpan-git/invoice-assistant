<template>
  <div class="app-shell">
    <aside class="app-sider">
      <div class="brand-block">
        <span class="brand-eyebrow">本机工作台</span>
        <h1>发票整理助手</h1>
      </div>
      <nav class="app-nav" aria-label="主导航">
        <RouterLink v-for="item in menuItems" :key="item.to" :to="item.to" :class="{ active: activeMenu === item.key }">
          <span aria-hidden="true">{{ item.icon }}</span>
          <span>{{ item.label }}</span>
        </RouterLink>
      </nav>
    </aside>
    <main class="app-main">
      <header class="app-header">
        <div>
          <span class="eyebrow">当前页面</span>
          <h2>{{ title }}</h2>
        </div>
        <div class="trusted-context" aria-label="可信上下文">
          <span>可信上下文</span>
          <strong>{{ defaultOperatorName }}</strong>
        </div>
      </header>
      <section class="app-content">
        <SetupStatusCard
          :config="config"
          :loading="configState === 'loading'"
          :error="configError"
          show-action
          @open-setup="router.push('/setup')"
          @open-workbench="router.push('/')"
          @retry-config="loadConfig"
        />
        <RouterView />
      </section>
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { RouterLink, RouterView, useRoute, useRouter } from "vue-router";

import { getActiveConfig, getErrorMessage } from "./api";
import { refreshCurrentActor, useOperatorSettings } from "./operator";
import type { ActiveConfigPayload, ConfigLoadState } from "./types";
import SetupStatusCard from "../components/settings/SetupStatusCard.vue";

const router = useRouter();
const route = useRoute();
const { defaultOperatorName } = useOperatorSettings();
const config = ref<ActiveConfigPayload | null>(null);
const configState = ref<ConfigLoadState>("loading");
const configError = ref<string | null>(null);

const menuItems = [
  { key: "workbench", to: "/", label: "批次工作台", icon: "□" },
  { key: "results", to: "/results", label: "批次结果", icon: "◇" },
  { key: "settings", to: "/settings", label: "配置中心", icon: "△" },
];

const title = computed(() => String(route.meta.title ?? "发票整理助手"));
const activeMenu = computed(() => {
  if (route.path.startsWith("/settings") || route.path.startsWith("/setup")) {
    return "settings";
  }
  if (route.path.startsWith("/results")) {
    return "results";
  }
  return "workbench";
});

async function loadConfig() {
  configState.value = "loading";
  try {
    config.value = await getActiveConfig();
    configError.value = null;
    configState.value = "ready";
  } catch (error) {
    config.value = null;
    configError.value = getErrorMessage(error);
    configState.value = "error";
  }
}

onMounted(() => {
  void refreshCurrentActor();
  void loadConfig();
});

watch(
  () => route.path,
  () => {
    void loadConfig();
  },
);
</script>
