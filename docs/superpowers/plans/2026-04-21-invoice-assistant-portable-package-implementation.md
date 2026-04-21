# Invoice Assistant Portable Package Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Windows portable, single-process delivery of the invoice assistant with release-mode static hosting, first-run configuration wizard, export-folder reachability, and bundle/build artifacts.

**Architecture:** Keep FastAPI as the only runtime server in release mode. Add an explicit runtime configuration layer so the backend can serve built frontend assets, portable data/log/runtime directories, and Windows helper actions. In the frontend, replace the current hash-router/config-panels flow with a guided setup wizard plus persistent config status, while reusing the existing batch/results/settings modules where possible.

**Tech Stack:** FastAPI, SQLAlchemy, React, React Router, Vite build output, Vitest, pytest, Windows batch scripts, Python packaging script

---

## File Structure Map

### Existing files to modify

- `backend/app/main.py`
  - Add release runtime configuration plumbing.
  - Mount frontend static assets and SPA fallback routes.
  - Include runtime helper API routes.
- `backend/app/db/session.py`
  - Allow runtime-configured SQLite path instead of only repo-root defaults.
- `backend/app/services/config_service.py`
  - Add setup completeness evaluation and wizard defaults.
- `backend/app/api/config.py`
  - Return setup status, defaults, and current config summary.
- `backend/app/api/batches.py`
  - Reject batch creation when setup is incomplete.
- `frontend/src/app/router.tsx`
  - Replace `createHashRouter` with browser routing and add `/setup`.
- `frontend/src/app/shell.tsx`
  - Show persistent active-company summary and setup state.
- `frontend/src/app/api.ts`
  - Add setup/runtime/export-folder helper requests.
- `frontend/src/app/types.ts`
  - Add setup-status, runtime helper, and wizard payload types.
- `frontend/src/pages/BatchWorkbench.tsx`
  - Gate uploads until setup completes and show current company summary.
- `frontend/src/pages/BatchResults.tsx`
  - Show latest export record and open-export-folder action.
- `frontend/src/pages/Settings.tsx`
  - Keep advanced version history/editor role after the wizard exists.
- `frontend/src/components/batch/UploadPanel.tsx`
  - Support disabled state and setup guidance text.
- `frontend/src/components/settings/RuleVersionPanel.tsx`
  - Narrow it to advanced editing, not first-run onboarding.
- `frontend/vite.config.ts`
  - Keep dev proxy, but align build output with release hosting.
- `frontend/tests/app-shell.test.tsx`
- `frontend/tests/runtime-ui.test.tsx`
- `backend/tests/test_app_boot.py`
- `backend/tests/test_api_workflows.py`
- `backend/tests/test_config_versioning.py`

### New files to create

- `backend/app/core/runtime_config.py`
  - Central runtime path/host/port/static-dir resolution for repo mode and portable mode.
- `backend/app/api/runtime.py`
  - Local-only runtime helper endpoints such as `open-path`.
- `backend/tests/test_release_runtime.py`
  - Release static-hosting and SPA fallback tests.
- `backend/tests/test_portable_build.py`
  - Bundle layout and manifest tests for the Windows package builder.
- `frontend/src/pages/SetupWizard.tsx`
  - First-run wizard page.
- `frontend/src/components/settings/SetupStatusCard.tsx`
  - Reusable summary card for active company/rules status.
- `frontend/src/components/settings/TaxProfileStep.tsx`
- `frontend/src/components/settings/BusinessRulesTemplateStep.tsx`
- `frontend/src/components/settings/NamingRuleStep.tsx`
- `frontend/src/components/settings/SetupSummaryStep.tsx`
  - Wizard step components with focused responsibilities.
- `packaging/windows/bootstrap/start_server.py`
  - Release entrypoint invoked by the batch script inside the bundle.
- `packaging/windows/启动发票助手.bat`
- `packaging/windows/停止发票助手.bat`
- `packaging/windows/用户指引.html`
- `packaging/windows/README-技术维护.md`
- `scripts/build_windows_portable.py`
  - Build/copy/package script that produces `dist/invoice-assistant-windows-x64-<version>/`.

## Task 1: Release Runtime Configuration and SPA Hosting

**Files:**
- Create: `backend/app/core/runtime_config.py`
- Create: `backend/tests/test_release_runtime.py`
- Modify: `backend/app/main.py`
- Modify: `backend/app/db/session.py`
- Modify: `frontend/src/app/router.tsx`
- Test: `backend/tests/test_app_boot.py`
- Test: `frontend/tests/app-shell.test.tsx`

- [ ] **Step 1: Write failing backend tests for release static hosting**

```python
# backend/tests/test_release_runtime.py
from pathlib import Path

from starlette.testclient import TestClient

from backend.app.main import create_app


def test_release_runtime_serves_index_and_assets(tmp_path):
    static_dir = tmp_path / "frontend-dist"
    assets_dir = static_dir / "assets"
    assets_dir.mkdir(parents=True)
    (static_dir / "index.html").write_text(
        "<!doctype html><html><body><div id='root'></div></body></html>",
        encoding="utf-8",
    )
    (assets_dir / "app.js").write_text("console.log('ok');", encoding="utf-8")

    app = create_app(
        f"sqlite:///{tmp_path / 'release.db'}",
        runtime_overrides={"frontend_static_dir": static_dir},
    )
    client = TestClient(app)

    assert client.get("/").status_code == 200
    assert client.get("/assets/app.js").status_code == 200
    assert client.get("/results/demo-batch").status_code == 200
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest backend/tests/test_release_runtime.py backend/tests/test_app_boot.py -q`
Expected: FAIL because `create_app()` does not accept runtime overrides and the app does not serve static frontend files yet.

- [ ] **Step 3: Add runtime config and backend static hosting**

```python
# backend/app/core/runtime_config.py
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RuntimeConfig:
    portable_root: Path | None
    database_url: str
    storage_root: Path
    logs_dir: Path
    runtime_dir: Path
    frontend_static_dir: Path | None
    host: str = "127.0.0.1"
    port: int = 8000


def build_runtime_config(
    *,
    database_url: str,
    portable_root: Path | None = None,
    frontend_static_dir: Path | None = None,
) -> RuntimeConfig:
    root = portable_root
    if root is not None:
        data_dir = root / "data"
        return RuntimeConfig(
            portable_root=root,
            database_url=f"sqlite:///{data_dir / 'app.db'}",
            storage_root=data_dir / "storage",
            logs_dir=root / "logs",
            runtime_dir=root / "runtime",
            frontend_static_dir=frontend_static_dir or root / "app" / "server" / "frontend-dist",
            host="127.0.0.1",
            port=18080,
        )
    return RuntimeConfig(
        portable_root=None,
        database_url=database_url,
        storage_root=Path(database_url.removeprefix("sqlite:///")).expanduser().parent / "storage",
        logs_dir=Path("backend/data/logs").resolve(),
        runtime_dir=Path("backend/data/runtime").resolve(),
        frontend_static_dir=frontend_static_dir,
    )
```

```python
# backend/app/main.py (core shape)
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.app.core.runtime_config import build_runtime_config


def create_app(database_url: str = DEFAULT_DATABASE_URL, *, trusted_actor=LOCAL_TRUSTED_ACTOR, runtime_overrides: dict[str, object] | None = None) -> FastAPI:
    runtime_config = build_runtime_config(
        database_url=database_url,
        portable_root=runtime_overrides.get("portable_root") if runtime_overrides else None,
        frontend_static_dir=runtime_overrides.get("frontend_static_dir") if runtime_overrides else None,
    )
    app.state.runtime_config = runtime_config
    app.state.storage_root = runtime_config.storage_root
    ...
    if runtime_config.frontend_static_dir and runtime_config.frontend_static_dir.exists():
        app.mount("/assets", StaticFiles(directory=runtime_config.frontend_static_dir / "assets"), name="assets")

        @app.get("/{full_path:path}")
        def spa_fallback(full_path: str):
            if full_path.startswith("api/") or full_path == "health":
                raise HTTPException(status_code=404, detail="Not found.")
            return FileResponse(runtime_config.frontend_static_dir / "index.html")
```

- [ ] **Step 4: Switch the frontend router to browser history**

```tsx
// frontend/src/app/router.tsx
import { createBrowserRouter } from "react-router-dom";

export const appRoutes: RouteObject[] = [
  {
    path: "/",
    element: <AppShell />,
    children: [
      { index: true, element: withRouteSuspense(<BatchWorkbench />), handle: { title: "批次工作台" } },
      { path: "setup", element: withRouteSuspense(<SetupWizard />), handle: { title: "首次配置向导" } },
      { path: "results", element: withRouteSuspense(<BatchResults />), handle: { title: "批次结果" } },
      { path: "results/:batchId", element: withRouteSuspense(<BatchResults />), handle: { title: "批次结果" } },
      { path: "settings", element: withRouteSuspense(<Settings />), handle: { title: "配置中心" } },
    ],
  },
];

export function createAppRouter() {
  return createBrowserRouter(appRoutes);
}
```

- [ ] **Step 5: Run focused tests**

Run: `uv run pytest backend/tests/test_release_runtime.py backend/tests/test_app_boot.py -q`
Expected: PASS

Run: `corepack pnpm --dir frontend test -- --run frontend/tests/app-shell.test.tsx`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/core/runtime_config.py backend/app/main.py backend/app/db/session.py backend/tests/test_release_runtime.py backend/tests/test_app_boot.py frontend/src/app/router.tsx frontend/tests/app-shell.test.tsx
git commit -m "feat: add release runtime and spa hosting"
```

## Task 2: Setup Completeness Contract and Upload Gate

**Files:**
- Modify: `backend/app/services/config_service.py`
- Modify: `backend/app/api/config.py`
- Modify: `backend/app/api/batches.py`
- Modify: `frontend/src/app/types.ts`
- Modify: `frontend/src/app/api.ts`
- Test: `backend/tests/test_config_versioning.py`
- Test: `backend/tests/test_api_workflows.py`

- [ ] **Step 1: Write failing tests for setup completeness and batch blocking**

```python
# backend/tests/test_config_versioning.py
def test_config_service_reports_incomplete_until_all_required_rules_exist(tmp_path):
    session = build_session(tmp_path)
    service = ConfigService(session)

    service.create_version(
        kind="tax_profile",
        content={"buyer_name": "Shanghai Example Co"},
        changed_by="fin-admin",
        change_summary="seed incomplete tax profile",
        change_reason="test",
    )

    status = service.get_setup_status()
    assert status["complete"] is False
    assert "buyer_tax_no" in status["missing_required_fields"]["tax_profile"]
```

```python
# backend/tests/test_api_workflows.py
def test_create_batch_requires_completed_setup(tmp_path):
    app = create_app(f"sqlite:///{tmp_path / 'blocked.db'}")
    client = TestClient(app)

    response = client.post(
        "/api/batches",
        files=[("files", ("invoice.pdf", b"%PDF-1.7\nstub", "application/pdf"))],
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "请先完成首次配置向导，再开始上传发票。"}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest backend/tests/test_config_versioning.py backend/tests/test_api_workflows.py -q`
Expected: FAIL because setup completeness helpers and upload gating do not exist.

- [ ] **Step 3: Implement setup completeness and defaults**

```python
# backend/app/services/config_service.py
REQUIRED_FIELDS = {
    "tax_profile": ("buyer_name", "buyer_tax_no"),
    "business_rules": ("template_name",),
    "naming_rules": ("pattern",),
}

DEFAULT_BUSINESS_RULE_TEMPLATES = {
    "conservative": {
        "template_name": "保守模板",
        "minimum_confidence": 0.9,
        "require_manual_review_keywords": ["餐饮", "招待", "礼品"],
    },
    "standard": {
        "template_name": "常规模板",
        "minimum_confidence": 0.75,
        "require_manual_review_keywords": ["礼品"],
    },
}

def get_setup_status(self) -> dict[str, object]:
    snapshot = self.get_active_snapshot()
    missing_required_fields: dict[str, list[str]] = {}
    for kind, fields in REQUIRED_FIELDS.items():
        content = (snapshot.get(kind) or {}).get("content", {})
        missing = [field for field in fields if not content.get(field)]
        if missing:
            missing_required_fields[kind] = missing
    return {
        "complete": not missing_required_fields,
        "missing_required_fields": missing_required_fields,
        "default_business_rule_templates": DEFAULT_BUSINESS_RULE_TEMPLATES,
        "active_snapshot": snapshot,
    }
```

```python
# backend/app/api/batches.py
config_service = ConfigService(session)
setup_status = config_service.get_setup_status()
if not setup_status["complete"]:
    raise HTTPException(status_code=400, detail="请先完成首次配置向导，再开始上传发票。")
```

```python
# backend/app/api/config.py
return {
    "active_snapshot": service.get_active_snapshot(),
    "active_versions": active_versions,
    "setup_status": service.get_setup_status(),
}
```

- [ ] **Step 4: Update frontend types and API client**

```ts
// frontend/src/app/types.ts
export interface SetupStatus {
  complete: boolean;
  missing_required_fields: Partial<Record<RuleKind, string[]>>;
  default_business_rule_templates: Record<string, Record<string, unknown>>;
}

export interface ActiveConfigPayload {
  active_snapshot: ActiveSnapshot;
  active_versions: Partial<Record<RuleKind, RuleVersion>>;
  setup_status: SetupStatus;
}
```

- [ ] **Step 5: Run focused tests**

Run: `uv run pytest backend/tests/test_config_versioning.py backend/tests/test_api_workflows.py -q`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/config_service.py backend/app/api/config.py backend/app/api/batches.py backend/tests/test_config_versioning.py backend/tests/test_api_workflows.py frontend/src/app/types.ts frontend/src/app/api.ts
git commit -m "feat: add setup completeness contract"
```

## Task 3: First-Run Wizard and Persistent Company Status

**Files:**
- Create: `frontend/src/pages/SetupWizard.tsx`
- Create: `frontend/src/components/settings/SetupStatusCard.tsx`
- Create: `frontend/src/components/settings/TaxProfileStep.tsx`
- Create: `frontend/src/components/settings/BusinessRulesTemplateStep.tsx`
- Create: `frontend/src/components/settings/NamingRuleStep.tsx`
- Create: `frontend/src/components/settings/SetupSummaryStep.tsx`
- Modify: `frontend/src/app/router.tsx`
- Modify: `frontend/src/app/shell.tsx`
- Modify: `frontend/src/pages/BatchWorkbench.tsx`
- Modify: `frontend/src/pages/Settings.tsx`
- Modify: `frontend/src/components/batch/UploadPanel.tsx`
- Test: `frontend/tests/runtime-ui.test.tsx`

- [ ] **Step 1: Write failing UI tests for the wizard gate**

```tsx
// frontend/tests/runtime-ui.test.tsx
it("redirects first-run users to the setup wizard and disables upload actions", async () => {
  apiMocks.getActiveConfig.mockResolvedValue({
    active_snapshot: {},
    active_versions: {},
    setup_status: {
      complete: false,
      missing_required_fields: {
        tax_profile: ["buyer_name", "buyer_tax_no"],
        business_rules: ["template_name"],
        naming_rules: ["pattern"],
      },
      default_business_rule_templates: {
        conservative: { template_name: "保守模板" },
        standard: { template_name: "常规模板" },
      },
    },
  });

  const router = createMemoryRouter(appRoutes, { initialEntries: ["/"] });
  render(<AppProviders><RouterProvider router={router} /></AppProviders>);

  expect(await screen.findByText("首次配置向导")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "去完成首次配置" })).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "创建批次" })).not.toBeEnabled();
});
```

- [ ] **Step 2: Run the UI tests to verify they fail**

Run: `corepack pnpm --dir frontend test -- --run frontend/tests/runtime-ui.test.tsx`
Expected: FAIL because there is no setup wizard route or upload gate UI.

- [ ] **Step 3: Implement the wizard and current-company status card**

```tsx
// frontend/src/pages/SetupWizard.tsx
export function SetupWizard() {
  const [step, setStep] = useState<"tax" | "business" | "naming" | "summary">("tax");
  const [draft, setDraft] = useState({
    tax_profile: { buyer_name: "", buyer_tax_no: "" },
    business_rules: { template_name: "保守模板", minimum_confidence: 0.9 },
    naming_rules: { pattern: "{date}_{amount}_{number}" },
  });

  async function saveAndFinish() {
    await createRuleVersion({ kind: "tax_profile", content: draft.tax_profile, changeSummary: "首次配置税务档案", changeReason: "首次配置向导" });
    await createRuleVersion({ kind: "business_rules", content: draft.business_rules, changeSummary: "首次配置业务规则", changeReason: "首次配置向导" });
    await createRuleVersion({ kind: "naming_rules", content: draft.naming_rules, changeSummary: "首次配置命名模板", changeReason: "首次配置向导" });
    navigate("/");
  }
}
```

```tsx
// frontend/src/components/settings/SetupStatusCard.tsx
export function SetupStatusCard({ payload }: { payload: ActiveConfigPayload }) {
  const taxProfile = payload.active_snapshot.tax_profile?.content as Record<string, string> | undefined;
  const businessRules = payload.active_snapshot.business_rules?.content as Record<string, string> | undefined;
  const namingRules = payload.active_snapshot.naming_rules?.content as Record<string, string> | undefined;

  return (
    <section className="workspace-block">
      <SectionHeader title="当前公司配置" subtitle={payload.setup_status.complete ? "已完成首次配置" : "尚未完成首次配置"} />
      <Typography.Text>{taxProfile?.buyer_name ?? "未配置公司名称"}</Typography.Text>
      <Typography.Text>{taxProfile?.buyer_tax_no ? `税号尾号 ${taxProfile.buyer_tax_no.slice(-4)}` : "未配置税号"}</Typography.Text>
      <Typography.Text>{String(businessRules?.template_name ?? "未选择模板")}</Typography.Text>
      <Typography.Text>{String(namingRules?.pattern ?? "未配置命名模板")}</Typography.Text>
    </section>
  );
}
```

- [ ] **Step 4: Gate workbench upload and keep settings as advanced editor**

```tsx
// frontend/src/pages/BatchWorkbench.tsx
const [config, setConfig] = useState<ActiveConfigPayload | null>(null);
...
<SetupStatusCard payload={config} />
<UploadPanel
  disabled={!config?.setup_status.complete}
  disabledReason="请先完成首次配置向导，再开始上传发票。"
  primaryActionLabel={config?.setup_status.complete ? "创建批次" : "去完成首次配置"}
  onGoSetup={() => navigate("/setup")}
  onCreated={...}
/>
```

```tsx
// frontend/src/pages/Settings.tsx
<SectionHeader
  title="配置中心"
  subtitle="首次配置完成后，可在这里查看历史版本和做受控调整"
/>
```

- [ ] **Step 5: Run focused frontend tests**

Run: `corepack pnpm --dir frontend test -- --run frontend/tests/runtime-ui.test.tsx frontend/tests/app-shell.test.tsx`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add frontend/src/pages/SetupWizard.tsx frontend/src/components/settings/SetupStatusCard.tsx frontend/src/components/settings/TaxProfileStep.tsx frontend/src/components/settings/BusinessRulesTemplateStep.tsx frontend/src/components/settings/NamingRuleStep.tsx frontend/src/components/settings/SetupSummaryStep.tsx frontend/src/app/router.tsx frontend/src/app/shell.tsx frontend/src/pages/BatchWorkbench.tsx frontend/src/pages/Settings.tsx frontend/src/components/batch/UploadPanel.tsx frontend/tests/runtime-ui.test.tsx
git commit -m "feat: add first-run setup wizard"
```

## Task 4: Export Folder Reachability and Runtime Helper API

**Files:**
- Create: `backend/app/api/runtime.py`
- Modify: `backend/app/main.py`
- Modify: `frontend/src/app/api.ts`
- Modify: `frontend/src/app/types.ts`
- Modify: `frontend/src/pages/BatchResults.tsx`
- Test: `backend/tests/test_release_runtime.py`
- Test: `frontend/tests/runtime-ui.test.tsx`

- [ ] **Step 1: Write failing tests for opening the export folder**

```python
# backend/tests/test_release_runtime.py
def test_runtime_open_path_rejects_outside_storage(tmp_path):
    app = create_app(f"sqlite:///{tmp_path / 'runtime.db'}", runtime_overrides={"portable_root": tmp_path})
    client = TestClient(app)

    response = client.post("/api/runtime/open-path", json={"relative_path": "../secrets.txt"})
    assert response.status_code == 400
```

```tsx
// frontend/tests/runtime-ui.test.tsx
it("shows latest export and opens export folder from batch results", async () => {
  apiMocks.getBatch.mockResolvedValue({
    id: "batch-1",
    batch_no: "BATCH-EXPORT-001",
    export_jobs: [
      {
        id: "job-1",
        export_type: "excel_manifest",
        status: "completed",
        output_path: "exports/BATCH-EXPORT-001/excel_manifest_20260421.xlsx",
        created_at: "2026-04-21T08:00:00Z",
        summary: {},
      },
    ],
  });
  apiMocks.openRuntimePath.mockResolvedValue({ opened: true });
  ...
  expect(await screen.findByText("excel_manifest_20260421.xlsx")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "打开导出文件夹" }));
  await waitFor(() => expect(apiMocks.openRuntimePath).toHaveBeenCalled());
});
```

- [ ] **Step 2: Run the targeted tests to verify they fail**

Run: `uv run pytest backend/tests/test_release_runtime.py -q`
Expected: FAIL because `/api/runtime/open-path` does not exist.

Run: `corepack pnpm --dir frontend test -- --run frontend/tests/runtime-ui.test.tsx`
Expected: FAIL because the results page has no open-folder action.

- [ ] **Step 3: Implement the local runtime helper endpoint**

```python
# backend/app/api/runtime.py
from pathlib import Path
import subprocess

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

router = APIRouter(prefix="/api/runtime", tags=["runtime"])


class OpenPathRequest(BaseModel):
    relative_path: str


@router.post("/open-path")
def open_path(payload: OpenPathRequest, request: Request) -> dict[str, object]:
    storage_root = Path(request.app.state.storage_root).resolve()
    target = (storage_root / payload.relative_path).resolve()
    if storage_root not in target.parents and target != storage_root:
        raise HTTPException(status_code=400, detail="只能打开便携包数据目录内的路径。")
    if not target.exists():
        raise HTTPException(status_code=404, detail="目标路径不存在。")
    subprocess.Popen(["explorer", str(target if target.is_dir() else target.parent)])
    return {"opened": True, "path": str(target)}
```

- [ ] **Step 4: Surface latest export and folder action on the results page**

```tsx
// frontend/src/app/api.ts
export async function openRuntimePath(relativePath: string): Promise<{ opened: boolean; path: string }> {
  return requestJson("/api/runtime/open-path", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ relative_path: relativePath }),
  });
}
```

```tsx
// frontend/src/pages/BatchResults.tsx
const latestExport = [...(batch?.export_jobs ?? [])]
  .filter((item) => item.status === "completed" && item.output_path)
  .sort((left, right) => String(right.created_at).localeCompare(String(left.created_at)))[0];

<Button
  onClick={() => latestExport && openRuntimePath(latestExport.output_path)}
  disabled={!latestExport}
>
  打开导出文件夹
</Button>
```

- [ ] **Step 5: Run focused tests**

Run: `uv run pytest backend/tests/test_release_runtime.py -q`
Expected: PASS

Run: `corepack pnpm --dir frontend test -- --run frontend/tests/runtime-ui.test.tsx`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/runtime.py backend/app/main.py backend/tests/test_release_runtime.py frontend/src/app/api.ts frontend/src/app/types.ts frontend/src/pages/BatchResults.tsx frontend/tests/runtime-ui.test.tsx
git commit -m "feat: add export folder reachability"
```

## Task 5: Windows Portable Bootstrap and Build Packaging

**Files:**
- Create: `packaging/windows/bootstrap/start_server.py`
- Create: `packaging/windows/启动发票助手.bat`
- Create: `packaging/windows/停止发票助手.bat`
- Create: `scripts/build_windows_portable.py`
- Create: `backend/tests/test_portable_build.py`

- [ ] **Step 1: Write failing tests for the build output layout**

```python
# backend/tests/test_portable_build.py
from pathlib import Path

from scripts.build_windows_portable import build_portable_bundle


def test_build_portable_bundle_creates_expected_layout(tmp_path):
    output_dir = build_portable_bundle(project_root=Path.cwd(), dist_root=tmp_path, version="0.1.0-test")
    assert (output_dir / "启动发票助手.bat").exists()
    assert (output_dir / "停止发票助手.bat").exists()
    assert (output_dir / "用户指引.html").exists()
    assert (output_dir / "README-技术维护.md").exists()
    assert (output_dir / "app" / "bootstrap" / "start_server.py").exists()
    assert (output_dir / "app" / "server" / "frontend-dist" / "index.html").exists()
    assert (output_dir / "manifest.json").exists()
```

- [ ] **Step 2: Run the packaging test to verify it fails**

Run: `uv run pytest backend/tests/test_portable_build.py -q`
Expected: FAIL because the builder and packaging assets do not exist.

- [ ] **Step 3: Implement the release bootstrap entrypoint and batch scripts**

```python
# packaging/windows/bootstrap/start_server.py
from argparse import ArgumentParser
from pathlib import Path

import uvicorn

from backend.app.main import create_app


def main() -> None:
    parser = ArgumentParser()
    parser.add_argument("--portable-root", required=True)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=18080)
    args = parser.parse_args()

    portable_root = Path(args.portable_root).resolve()
    app = create_app(runtime_overrides={"portable_root": portable_root})
    uvicorn.run(app, host=args.host, port=args.port)
```

```bat
:: packaging/windows/启动发票助手.bat
@echo off
set ROOT=%~dp0
if not exist "%ROOT%runtime" mkdir "%ROOT%runtime"
if not exist "%ROOT%logs" mkdir "%ROOT%logs"
"%ROOT%app\python\python.exe" "%ROOT%app\bootstrap\start_server.py" --portable-root "%ROOT%" --host 127.0.0.1 --port 18080
```

```bat
:: packaging/windows/停止发票助手.bat
@echo off
if not exist "%~dp0runtime\app.pid" (
  echo 当前未运行
  exit /b 0
)
for /f %%p in (%~dp0runtime\app.pid) do taskkill /PID %%p /T /F
```

- [ ] **Step 4: Implement the builder**

```python
# scripts/build_windows_portable.py
def build_portable_bundle(*, project_root: Path, dist_root: Path, version: str) -> Path:
    output_dir = dist_root / f"invoice-assistant-windows-x64-{version}"
    ...
    shutil.copytree(project_root / "frontend" / "dist", output_dir / "app" / "server" / "frontend-dist")
    shutil.copy(project_root / "packaging" / "windows" / "启动发票助手.bat", output_dir / "启动发票助手.bat")
    ...
    (output_dir / "manifest.json").write_text(json.dumps({
        "version": version,
        "built_at": datetime.now(UTC).isoformat(),
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    return output_dir
```

- [ ] **Step 5: Run focused tests**

Run: `uv run pytest backend/tests/test_portable_build.py -q`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add packaging/windows/bootstrap/start_server.py packaging/windows/启动发票助手.bat packaging/windows/停止发票助手.bat scripts/build_windows_portable.py backend/tests/test_portable_build.py
git commit -m "feat: add windows portable bundle builder"
```

## Task 6: Bundle Docs and End-to-End Verification

**Files:**
- Create: `packaging/windows/用户指引.html`
- Create: `packaging/windows/README-技术维护.md`
- Modify: `frontend/tests/manual-checklist.md`

- [ ] **Step 1: Write the assistant-facing and maintainer docs**

```html
<!-- packaging/windows/用户指引.html -->
<h1>发票助手用户指引</h1>
<p>第一次使用前，请先打开首次配置向导，填写你们公司的发票信息和规则。</p>
<ol>
  <li>双击“启动发票助手.bat”</li>
  <li>按向导填写公司名称、税号、规则模板、命名方式</li>
  <li>回到工作台上传 PDF 发票</li>
  <li>导出后点击“打开导出文件夹”直接找到文件</li>
  <li>用完双击“停止发票助手.bat”</li>
</ol>
```

```md
<!-- packaging/windows/README-技术维护.md -->
# 发票助手便携版维护说明

- 支持：Windows 10/11 x64、本地可写目录、非管理员用户
- 不支持：网络盘、只读介质、强同步占锁目录
- 启动入口：`app\python\python.exe app\bootstrap\start_server.py --portable-root ...`
- 升级方式：停止服务 -> 备份 `data/` -> 替换程序目录 -> 恢复 `data/`
```

- [ ] **Step 2: Update the manual checklist for Windows portable acceptance**

```md
## Windows 便携版验收

- 干净机器无需预装 Python / Node
- 首次启动进入首次配置向导
- 未配置完成前无法创建批次
- 导出后可点击“打开导出文件夹”
- 停止脚本可正常关闭服务
- 复制 `data/` 后历史批次仍可读取
```

- [ ] **Step 3: Build the frontend and the Windows portable output**

Run: `corepack pnpm --dir frontend build`
Expected: PASS

Run: `uv run python scripts/build_windows_portable.py --version 0.1.0-dev`
Expected: PASS and create `dist/invoice-assistant-windows-x64-0.1.0-dev/`

- [ ] **Step 4: Run full verification**

Run: `uv run pytest backend/tests -q`
Expected: PASS

Run: `corepack pnpm --dir frontend test`
Expected: PASS

Run: `python -m ai_sdlc verify constraints`
Expected: `verify constraints: no BLOCKERs.`

Run: `python -m ai_sdlc run --dry-run`
Expected: no open gates caused by missing tasks/tests for this work.

- [ ] **Step 5: Commit**

```bash
git add packaging/windows/用户指引.html packaging/windows/README-技术维护.md frontend/tests/manual-checklist.md
git commit -m "docs: add portable package user and maintainer guides"
```

## Self-Review

- Spec coverage:
  - Windows x64 + embedded runtime boundary: Task 5
  - Release static hosting and SPA refresh contract: Task 1
  - Fixed-port local runtime and entrypoint: Task 1 and Task 5
  - First-run wizard + default templates + upload hard gate: Task 2 and Task 3
  - Persistent current-company status: Task 3
  - Export file reachability: Task 4
  - Bundle docs, manifest, and validation: Task 5 and Task 6
- Placeholder scan: no `TODO`, `TBD`, or “handle appropriately” placeholders remain in tasks.
- Type consistency:
  - Backend setup API uses `setup_status`.
  - Frontend wizard consumes `ActiveConfigPayload.setup_status`.
  - Runtime helper route uses `openRuntimePath(relativePath)`.

