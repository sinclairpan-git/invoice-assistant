import { mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import App from "../src/App.vue";
import { router } from "../src/app/router";

describe("Vue app shell", () => {
  beforeEach(() => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input);
        if (url.includes("/api/me")) {
          return new Response(JSON.stringify({
            item: {
              actor_id: "trusted-actor-1",
              display_name: "后端可信身份",
              roles: ["reviewer", "exporter"],
            },
          }), {
            status: 200,
            headers: { "Content-Type": "application/json" },
          });
        }
        if (url.includes("/api/config")) {
          return new Response(JSON.stringify({
            active_snapshot: {},
            active_versions: {},
            setup_status: {
              complete: false,
              default_business_rule_templates: {
                strict_v1: {
                  template_name: "strict_v1",
                  display_name: "严格校验",
                  minimum_confidence: 0.92,
                },
              },
              missing_required_fields: {
                tax_profile: ["buyer_name"],
                business_rules: ["template_name"],
                naming_rules: ["pattern"],
              },
            },
          }), {
            status: 200,
            headers: { "Content-Type": "application/json" },
          });
        }
        if (url.includes("/api/batches")) {
          return new Response(JSON.stringify({ items: [] }), {
            status: 200,
            headers: { "Content-Type": "application/json" },
          });
        }
        return new Response(JSON.stringify({ detail: "not mocked" }), {
          status: 404,
          headers: { "Content-Type": "application/json" },
        });
      }),
    );
  });

  it("renders Vue navigation and trusted backend actor", async () => {
    router.push("/");
    await router.isReady();
    const wrapper = mount(App, {
      global: {
        plugins: [router],
      },
    });

    await vi.waitFor(() => {
      expect(wrapper.text()).toContain("批次工作台");
      expect(wrapper.text()).toContain("批次结果");
      expect(wrapper.text()).toContain("配置中心");
      expect(wrapper.text()).toContain("后端可信身份");
    });
  });
});
