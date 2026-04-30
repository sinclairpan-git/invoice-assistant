# 发票整理助手 Windows + Codex 开发指引

这份包不是给最终助理使用的运行包，而是给你自己在 Windows 上继续开发这个仓库。

## 1. 你会拿到什么

解压后目录结构大致如下：

```text
invoice-assistant-windows-dev-<version>/
├─ workspace/      # 完整源码工程
├─ windows-dev/    # Windows 开发辅助脚本
└─ manifest.json
```

后续在 Codex 里打开的是 `workspace/`，不是外层目录。

## 2. Windows 机器先准备什么

至少先装好这几样：

1. Git for Windows
2. Node.js 20+
3. Python 3.11+
4. Codex Windows 客户端

建议：

- 使用 PowerShell 7
- 把仓库放在本地可写目录，例如 `D:\Work\invoice-assistant-dev\`
- 不要放在同步盘、网络盘、只读盘
- `uv` 仍然推荐安装；若未安装，初始化和构建脚本会自动回退到 `python + venv + pip`

## 3. 第一次初始化

在 PowerShell 里进入解压后的外层目录，然后执行：

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\windows-dev\初始化开发环境.ps1
```

这个脚本会做三件事：

1. 初始化 workspace 根目录 Python 环境
2. 初始化 backend 开发环境
3. 安装 frontend 的 pnpm 依赖

若当前机器没有全局 `uv`，脚本会自动创建：

- `workspace/.venv`
- `workspace/backend/.venv`

## 4. 用 Codex 打开哪里

在 Windows 上启动 Codex，打开：

```text
<解压目录>\workspace
```

不要打开外层 bundle 根目录。真正的 git 仓库在 `workspace/` 里面。

## 5. 日常开发怎么跑

### 后端

```powershell
.\windows-dev\启动后端开发.ps1
```

默认地址：

```text
http://127.0.0.1:8000
```

### 前端

```powershell
.\windows-dev\启动前端开发.ps1
```

默认地址：

```text
http://127.0.0.1:5173
```

## 6. 在 Windows 上重新构建便携包

```powershell
.\windows-dev\构建便携包.ps1
```

它会：

1. 重新构建前端发布产物
2. 下载并准备 Windows 便携 Python 运行时
3. 重新生成运行给助理用的离线包

若当前机器没有全局 `uv`，构建脚本会优先使用 `workspace/.venv`；若不存在，则回退到系统 `python` / `py -3.11`。

产物在：

```text
workspace\dist\
```

## 7. 为什么建议切到 Windows 主开发

这个项目当前卡点主要集中在：

- `.bat`
- Windows 路径拼接
- `python.exe` 启动
- `tasklist/taskkill`
- 本地浏览器自动打开
- 便携包双击行为

这些都属于 Windows 原生行为。在 macOS 上只能间接推断，在 Windows 上可以直接验证。

## 8. 迁移后你该怎么用

推荐工作方式：

1. 在 Windows 上把这个 bundle 解压
2. 在 Codex 打开 `workspace/`
3. 平时开发直接在 Windows 上改
4. 每次涉及便携包或启动器改动，都在 Windows 本机直接双击验证

## 9. 这份开发包故意没带什么

为了避免包体失控，开发包不会内置：

- `.git/`
- `.venv/`
- `backend/.venv/`
- `frontend/node_modules/`
- `frontend/dist/`
- `dist/`
- `.tmp/`

也就是说，这是一份“源码迁移包”，不是已经装好所有开发依赖的镜像盘。
