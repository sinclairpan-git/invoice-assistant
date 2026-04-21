import { render, screen } from "@testing-library/react";
import { RouterProvider, createMemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { AppProviders } from "../src/app/providers";
import { appRoutes, createAppRouter } from "../src/app/router";


describe("App shell", () => {
  beforeEach(() => {
    window.localStorage.setItem("invoice-assistant/default-operator-name", "前端伪造姓名");
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
        if (url.includes("/api/batches")) {
          return new Response(JSON.stringify({ items: [] }), {
            status: 200,
            headers: { "Content-Type": "application/json" },
          });
        }
        if (url.includes("/api/config")) {
          return new Response(JSON.stringify({
            active_snapshot: {},
            active_versions: {
              tax_profile: {
                id: "tax-draft",
                kind: "tax_profile",
                version_no: "tax-draft",
                content: {},
                is_active: false,
                change_summary: "草稿",
                changed_by: "后端可信身份",
                changed_at: "2026-04-20T10:02:00Z",
                change_reason: "首次配置",
              },
            },
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
        return new Response(JSON.stringify({ detail: "not mocked" }), {
          status: 404,
          headers: { "Content-Type": "application/json" },
        });
      }),
    );
  });

  it("renders navigation and workbench title", async () => {
    const router = createMemoryRouter(appRoutes, {
      initialEntries: ["/results"],
    });

    render(
      <AppProviders>
        <RouterProvider router={router} />
      </AppProviders>,
    );

    expect(await screen.findAllByText("批次工作台")).not.toHaveLength(0);
    expect(screen.getAllByText("批次结果").length).toBeGreaterThan(0);
    expect(screen.getByText("配置中心")).toBeInTheDocument();
    expect(await screen.findByText("当前公司配置")).toBeInTheDocument();
    expect(await screen.findByText("后端可信身份")).toBeInTheDocument();
    expect(screen.queryByText("前端伪造姓名")).not.toBeInTheDocument();
  });

  it("boots /setup from browser history", async () => {
    window.history.replaceState({}, "", "/setup");
    const router = createAppRouter();

    render(
      <AppProviders>
        <RouterProvider router={router} />
      </AppProviders>,
    );

    expect(await screen.findByText("首次配置向导")).toBeInTheDocument();
    expect(await screen.findByText("首次配置未完成")).toBeInTheDocument();
    expect(screen.getByText("配置中心").closest("li")).toHaveClass("ant-menu-item-selected");
    expect(screen.getByText("批次工作台").closest("li")).not.toHaveClass("ant-menu-item-selected");
  });

  it("shows unknown config status when /api/config read fails", async () => {
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
          return new Response(JSON.stringify({ detail: "配置读取失败" }), {
            status: 503,
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

    const router = createMemoryRouter(appRoutes, {
      initialEntries: ["/"],
    });

    render(
      <AppProviders>
        <RouterProvider router={router} />
      </AppProviders>,
    );

    expect(await screen.findByText("当前无法确认首次配置状态")).toBeInTheDocument();
    expect(screen.getByText("当前公司配置")).toBeInTheDocument();
    expect(screen.getByText("配置状态未知")).toBeInTheDocument();
    expect(screen.queryByText("首次配置未完成")).not.toBeInTheDocument();
  });
});
