import { createApp } from "vue";

import App from "./App.vue";
import { router } from "./app/router";
import { installPublicPrimeVueProvider } from "./frontend-governance/runtime/providers/public-primevue/ProviderAdapter";
import "./styles.css";

const app = createApp(App);
installPublicPrimeVueProvider(app);
app.use(router);
app.mount("#app");
