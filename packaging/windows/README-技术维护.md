# 发票整理助手 Windows 便携版维护说明

## 1. 支持范围

- 仅支持 `Windows 10/11 x64`
- 交付形态为单目录便携包
- 固定本地访问地址：`http://127.0.0.1:18080`
- 运行边界是“本机单进程发布态服务 + 后端托管前端静态资源”

不支持：

- 依赖目标机器现装 Python/Node
- 首次启动联网安装依赖
- 随机切换监听端口
- 通过开发态 Vite 启动前端
- 放宽为远程访问或绑定非 loopback 地址
- 在非便携本机运行态暴露带宿主机副作用的 runtime helper

## 2. 唯一启动入口

唯一允许的发布态启动入口：

```bat
app\python\python.exe app\bootstrap\start_server.py --portable-root "<便携包根目录>" --host 127.0.0.1 --port 18080
```

要求：

- `启动发票助手.bat` 只能调用这一入口
- 不允许再维护第二套等价启动命令
- `start_server.py` 负责把 `portable-root`、`data/`、`logs/`、`runtime/`、`frontend-dist/` 转成发布态绝对路径

## 3. 运行目录约定

```text
发票助手便携版/
├─ 启动发票助手.bat
├─ 停止发票助手.bat
├─ 用户指引.html
├─ README-技术维护.md
├─ manifest.json
├─ app/
│  ├─ python/
│  ├─ bootstrap/
│  └─ server/
├─ data/
│  ├─ app.db
│  ├─ storage/
│  └─ exports/
├─ logs/
└─ runtime/
```

说明：

- `app/python/`：内置 Python 运行时
- `app/bootstrap/`：发布态启动辅助逻辑
- `app/server/`：后端代码与前端构建产物
- `data/`：用户业务数据，迁移时最关键
- `logs/`：运行和启动问题排查入口
- `runtime/`：PID、URL 等临时运行态

## 4. build 输入要求

打包脚本输入至少应满足：

- `frontend/dist/` 已存在，并且包含可用的 `index.html`
- `backend/` 目录完整，包含发布态运行需要的源码
- `packaging/windows/bootstrap/start_server.py`
- `packaging/windows/启动发票助手.bat`
- `packaging/windows/停止发票助手.bat`
- 如存在，则复制：
  - `packaging/windows/用户指引.html`
  - `packaging/windows/README-技术维护.md`

输出目录至少应包含：

- `启动发票助手.bat`
- `停止发票助手.bat`
- `app/python/python.exe`
- `app/python/Lib/site-packages/`
- `app/bootstrap/start_server.py`
- `app/server/frontend-dist/index.html`
- `app/server/backend/`
- `manifest.json`
- `invoice-assistant-windows-x64-<version>.zip`

这些不是“建议项”，而是便携包能否真正交付的强制输出。

## 5. runtime 输入要求

运行便携包前需要确认：

- `app/python/python.exe` 存在
- `app/python/Lib/site-packages/` 已包含发布态依赖
- `app/bootstrap/start_server.py` 存在
- `app/server/backend/` 存在
- `app/server/frontend-dist/` 存在
- 便携包根目录对当前用户可写
- `data/`、`logs/`、`runtime/` 可创建或可写

## 6. 升级、备份、迁移

### 升级便携包

建议流程：

1. 仅支持“上一正式便携版 -> 下一正式便携版”的顺序升级。
2. 双击 `停止发票助手.bat`
3. 备份旧包的 `data/`
4. 解压新版本便携包
5. 将旧包的 `data/` 覆盖到新包中
6. 启动新版本并验证首页、首次配置状态、历史批次和导出记录

若升级后失败：

1. 立即停止新包
2. 不要继续在失败状态下处理新票
3. 用刚才备份的 `data/` 回退到上一正式便携版
4. 记录 `logs/` 和 `runtime/` 状态后再交给维护人员排查

### 备份

最低要求：

1. 先停止服务
2. 备份整个 `data/`

建议同时保留：

- `manifest.json`
- `logs/` 中最近一次故障日志

### 迁移到新机器

1. 在旧机器停止服务
2. 拷贝旧包 `data/`
3. 在新机器解压新包
4. 将 `data/` 放入新包根目录
5. 启动并验证

## 7. 日志位置

优先检查：

- `logs/`：启动失败、运行异常的第一排查入口
- `runtime/`：确认是否残留 `app.pid`、`app.url`

建议关注的问题：

- 是否启动后根本没有写出运行态文件
- 是否存在旧 PID 文件导致误判
- 是否能正常访问 `/health`

## 8. 常见故障排查

### 8.1 双击启动后浏览器没打开

先做：

1. 手动访问 `http://127.0.0.1:18080`
2. 如果无法访问，检查 `logs/`
3. 确认 `app/python/python.exe` 是否存在

### 8.2 关闭浏览器后用户以为已经停止

说明：

- 关闭浏览器不等于停止服务
- 标准操作是双击 `停止发票助手.bat`

### 8.3 再次启动时提示已在运行或端口异常

先做：

1. 双击 `停止发票助手.bat`
2. 检查 `runtime/app.pid` 是否残留
3. 若仍异常，查看 `logs/`

### 8.4 首页可打开，但上传被硬性拦截

通常原因：

- 首次配置未完成

确认方式：

- 检查首次配置向导是否已完成；必要时重新走一次首次设置，确认公司发票信息和规则已经保存生效

### 8.5 导出后用户找不到结果

引导口径：

- 去“批次结果”页
- 找到“最近导出”
- 点击“打开导出文件夹”

### 8.6 迁移后历史数据丢失

通常原因：

- 没有复制旧包的 `data/`
- 只复制了程序目录，没有复制业务数据目录

## 9. 维护边界

当前文档只覆盖：

- Windows 便携版支持边界
- 唯一启动入口
- build/runtime 输入要求
- 升级、备份、迁移
- 日志与常见故障排查

若后续扩展安装器、自动升级、服务守护或多端口策略，需要单独更新维护说明，而不是在现有口径上隐式放宽。
当前维护边界还包括：

- 服务只允许监听 `127.0.0.1:18080`
- 不能把本机副作用接口放宽为局域网或公网访问
- 不能在缺少 `python.exe`、标准库、`Lib/site-packages` 或 zip 分发物时视为“打包完成”
