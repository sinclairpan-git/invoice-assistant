import { render, screen } from "@testing-library/react";
import { RouterProvider, createMemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { AppProviders } from "../src/app/providers";
import { appRoutes } from "../src/app/router";


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
        return new Response(JSON.stringify({ detail: "not mocked" }), {
          status: 404,
          headers: { "Content-Type": "application/json" },
        });
      }),
    );
  });

  it("renders navigation and workbench title", async () => {
    const router = createMemoryRouter(appRoutes, {
      initialEntries: ["/"],
    });

    render(
      <AppProviders>
        <RouterProvider router={router} />
      </AppProviders>,
    );

    expect(await screen.findAllByText("批次工作台")).not.toHaveLength(0);
    expect(screen.getByText("批次结果")).toBeInTheDocument();
    expect(screen.getByText("配置中心")).toBeInTheDocument();
    expect(await screen.findByText("新建批次")).toBeInTheDocument();
    expect(await screen.findByText("后端可信身份")).toBeInTheDocument();
    expect(screen.queryByText("前端伪造姓名")).not.toBeInTheDocument();
  });
});
