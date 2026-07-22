# Memory Passport：客户快速上手指南

这份指南面向第一次使用 Memory Passport 的产品和技术人员。按顺序执行，
十几分钟内就能在本地跑起一个**真实可用的记忆系统**——前端 UI 已连接后端，
你在浏览器上的操作会真实写入数据库。

> 如果你要做正式的 API 验收（逐条 curl 每个接口、对照验收清单签字），
> 请配合 [`B2B_CUSTOMER_GUIDE.zh-CN.md`](./B2B_CUSTOMER_GUIDE.zh-CN.md) 一起看。
> 本指南偏重"跑起来 + 点一遍"的快速体验路径。

---

## 0. 这个版本能做什么

你拿到的是一套**可在本地完整运行**的记忆基础设施：

- **后端**：完整的记忆 API——写入、语义检索、编辑、删除、设备迁移、
  策略、审计日志、用量统计、数据导出、用户删除。租户隔离，所有操作留痕。
- **前端 UI**：一个可视化控制台（B 端）+ 终端用户界面（C 端），
  **已真实连接后端**。UI 操作 = 真实数据库变更。
- **两种运行模式**：
  - **demo 模式**（默认）：免凭证，确定性的记忆引擎。适合快速体验全流程。
  - **real 模式**：接你自己的大模型（OpenAI 或兼容服务），真实 LLM 提取
    + 向量检索。有调用费用。

**建议路径**：先用 demo 模式体验完所有流程，确认满意后再切 real 模式。

---

## 1. 前置准备（一次性）

| 依赖 | 版本 | 检查命令 |
| --- | --- | --- |
| Docker Desktop（含 Compose v2） | 任意 | `docker compose version` |
| Git | 任意 | `git --version` |
| Make | macOS 自带，Linux 多数自带 | `make --version` |
| Node.js | 22+ | `node --version` |
| pnpm | 10+ | `pnpm --version` |
| Python | 3.11+（demo 脚本用） | `python3 --version` |

缺 pnpm 时：`npm install -g pnpm`

Windows 上完整的 `make demo` 流程支持 WSL2；原生 PowerShell 的 Compose
等价命令和可执行位说明见 [`docs/windows.md`](docs/windows.md)。

---

## 2. 拉代码并启动后端

```bash
git clone --recursive https://github.com/joevilcai666/memory-passport.git
cd memory-passport
git checkout HMS              # 当前发布分支
cp .env.example .env          # 生成默认配置（demo 模式，免凭证）
make demo
```

`make demo` 会：①启动 Postgres + 记忆引擎 + 后端；②初始化数据库并注入
Luna 示例数据集；③跑一遍端到端自检。

**看到这行就代表成功**：

```
Memory Passport local demo passed: http://127.0.0.1:8000/docs
```

验证后端状态：

```bash
curl http://127.0.0.1:8000/v1/health
# 应返回 {"mp":"ok","hms":"ok","db":"ok","memory_engine":"demo"}
```

浏览器打开 `http://127.0.0.1:8000/docs` 可看到完整的 Swagger API 文档，
每个接口都能直接在页面上试。

---

## 3. 启动前端 UI

```bash
pnpm install
pnpm dev
```

看到 `✓ Ready` 后，浏览器打开 `http://localhost:3000`。

> 页面加载后，右下角**不应**出现 "Backend offline — showing demo data"
> 提示。如果出现，确认后端在跑（回到第 2 步），再刷新页面。

---

## 4. 用浏览器体验（核心）

### 4.1 B 端控制台 `/console`（你的运营 / 管理视角）

| 页面 | 能做什么 |
| --- | --- |
| **Overview** | 看 KPI（MAU、记忆操作数）、活动趋势图、告警 |
| **Apps** | 查看你的应用、产品类型、数据区域 |
| **Quickstart** | ⭐ **4 步集成向导**，显示你的真实 API key，可点 "Run test event" 实测写入 |
| **Memory → Users** | 选用户 → 看他的所有记忆、状态、可移植性；点行打开 **Trace Sheet**（看检索链路、模型溯源）；每行可归档 / 删除 |
| **Memory → Policy** | 调自动写入规则、4 轴可移植性开关（跨设备 / 跨角色 / 跨模型 / 跨品牌）、检索上限 |
| **Devices** | 设备健康、升级路径（v1 → v2 迁移楔子） |
| **Settings** | 团队成员、审计日志（所有操作留痕） |

**重点试这几个真实操作**（都真的写后端，可在审计日志里看到痕迹）：

1. **Quickstart → "Run test event"** → 看记忆被创建，检查清单打钩。
2. **Memory → Users → 选 Mia → 点任一记忆行 → 下拉菜单 "Delete"**
   → 看状态变 deleted + 审计日志多一条。
3. **Policy → 关掉某个可移植性轴** → 审计日志记录 `policy.changed`。

### 4.2 C 端嵌入 UI `/app`（你的终端用户视角，手机宽度）

| 页面 | 模拟场景 |
| --- | --- |
| **/app/consent** | 用户授权记忆 |
| **/app/memory** | 记忆中心——看 / 删自己的记忆 |
| **/app/devices** + **/bind** | 设备绑定（扫码 + 配对码） |
| **/app/migrate** | ⭐ **核心卖点**：v1 → v2 设备迁移预览，3 个桶（推荐迁移 / 需人工 / 不可迁移） |
| **/app/migrate/complete** | 迁移完成盖章动画——"换了设备，记忆跟着走" |

**重点试迁移流程**（这是产品的差异化卖点）：

`/app/migrate` → 勾选要迁移的记忆 → 选旧设备处理方式（保留 / 移除）→
执行 → 看完成页的盖章动画。

---

## 5. 用 API 验证（可选但推荐）

UI 之外，你的工程团队会用 API 集成。真实 API key（写在 Quickstart 页上）：

```
mp_sandbox_LK39sn8vQ4x2pR7wY1tBz0Hd
```

三条最常用的调用（直接复制到终端）：

```bash
# 写入一条记忆
curl -X POST http://127.0.0.1:8000/v1/events/ingest \
  -H "Authorization: Bearer mp_sandbox_LK39sn8vQ4x2pR7wY1tBz0Hd" \
  -H "Content-Type: application/json" \
  -d '{"user_id":"usr_mia","agent_id":"agt_luna","relationship_id":"rel_mia_luna","source_type":"explicit_instruction","content":"我在测试 API 写入。"}'

# 语义检索
curl -X POST http://127.0.0.1:8000/v1/memories/retrieve \
  -H "Authorization: Bearer mp_sandbox_LK39sn8vQ4x2pR7wY1tBz0Hd" \
  -H "Content-Type: application/json" \
  -d '{"user_id":"usr_mia","agent_id":"agt_luna","relationship_id":"rel_mia_luna","query":"jasmine tea","model":"my-llm"}'

# 看所有记忆
curl http://127.0.0.1:8000/v1/memories \
  -H "Authorization: Bearer mp_sandbox_LK39sn8vQ4x2pR7wY1tBz0Hd"
```

完整接口列表在 `http://127.0.0.1:8000/docs`，逐条 curl 命令参考
[`docs/local-evaluation.md`](./docs/local-evaluation.md)。

---

## 6.（可选）切换到真实 AI 模式

demo 模式的 "记忆提取 / 检索" 是确定性的（不调大模型）。想测真实 LLM 提取
+ 向量检索：

1. 编辑 `.env`，把这三个 key 换成你的真实 OpenAI key（或兼容服务）：

   ```
   HMS_API_LLM_API_KEY=sk-...
   HMS_API_RETAIN_LLM_API_KEY=sk-...
   HMS_API_EMBEDDINGS_OPENAI_API_KEY=sk-...
   ```

2. 启动真实模式：

   ```bash
   make down          # 停掉 demo
   make real-up       # 启真实 HMS（会调大模型，有费用）
   ```

3. 验证：`curl http://127.0.0.1:8000/v1/health` 看 `memory_engine` 变成 `real`。

切回 demo：`make real-down && make demo`。

详细配置见 [`docs/real-hms.md`](./docs/real-hms.md)。

---

## 7. 集成到你的产品

你的后端只需调 Memory Passport 的 API（就是第 5 步那几条）。典型集成：

1. **写入**：用户和你的 agent 对话时，把对话事件 POST 到
   `/v1/events/ingest`，系统自动提取记忆、去重、存储。
2. **检索**：生成回复前，先 POST `/v1/memories/retrieve` 拿到相关记忆，
   拼进你的 prompt。
3. **管理**：用户在你的产品里管理记忆时，调 `/v1/memories`
   （列表 / 编辑 / 删除）。

数据隔离：每个用户用 `user_id` 隔离；每个客户租户用 API key 隔离。

---

## 8. 日常操作速查

| 操作 | 命令 |
| --- | --- |
| 停止（保留数据） | `make down` |
| 重新启动 | `make up` |
| 重置所有数据（⚠️ 删库） | `make clean && make demo` |
| 重新注入示例数据 | `make seed` |
| 看后端日志 | `docker compose logs -f mp-backend` |
| 前端停止 | 在 `pnpm dev` 的终端按 `Ctrl+C` |

---

## 9. 常见问题

**Q：前端右下角提示 "Backend offline"？**
后端没起。跑 `make demo`，再刷新页面。

**Q：改了 `.env` 不生效？**
后端配置要重启容器：`make down && make up`。前端环境变量要重启
`pnpm dev`。

**Q：想给多个客户 / 多租户用？**
当前 V0.1 是单租户（Luna）。多租户 HMS 支持在
[Issue #12](https://github.com/joevilcai666/memory-passport/issues/12) 跟踪，尚未实现。

**Q：数据存在哪？**
Docker volume 里的 Postgres。`make clean` 会删；`make down` 不会。

**Q：demo 模式的检索为什么不太准？**
demo 模式用 token 重叠匹配，不是真实向量检索。要看真实效果，用第 6 步
切 real 模式。

**Q：我在 UI 上删了一条记忆，但后端报错？**
极少数情况下，对"已归档（archived）"的记忆再点"删除"，后端状态机会拒绝
（`archived → deleted` 不是合法转换）。UI 会弹 "Backend sync failed" 软提示，
本地仍标记为已删除——不影响其他操作，重置数据后即恢复。

---

## 10. 更多文档（仓库内）

| 文档 | 内容 |
| --- | --- |
| [`README.md`](./README.md) | 项目总览 + 快速开始 |
| [`B2B_CUSTOMER_GUIDE.zh-CN.md`](./B2B_CUSTOMER_GUIDE.zh-CN.md) | API 验收清单 + 11 节正式 POC 手册 |
| [`docs/local-evaluation.md`](./docs/local-evaluation.md) | 每个接口的 curl 逐条演示 |
| [`docs/real-hms.md`](./docs/real-hms.md) | 真实 AI 模式配置详解 |
| [`docs/issue-acceptance.md`](./docs/issue-acceptance.md) | 验收标准矩阵 |

---

## 反馈

使用中遇到问题，欢迎在 GitHub Issues 提问，或在 POC 过程中把遇到的需求
反馈给我们——V0.1 之后的能力路线（多租户、生产硬化、CI）已在 Issues 里
公开跟踪。
