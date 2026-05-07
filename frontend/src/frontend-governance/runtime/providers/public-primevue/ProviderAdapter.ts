import type { App } from "vue";
import PrimeVue from "primevue/config";
import Aura from "@primeuix/themes/aura";

export function installPublicPrimeVueProvider(app: App) {
  app.use(PrimeVue, {
    ripple: true,
    theme: {
      preset: Aura,
      options: {
        darkModeSelector: false,
      },
    },
  });
}

export const PUBLIC_PRIMEVUE_PROVIDER_ID = "public-primevue";
