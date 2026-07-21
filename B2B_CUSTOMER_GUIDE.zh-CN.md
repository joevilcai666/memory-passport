# Memory Passport：B 端客户安装与验收指南

这份指南面向第一次接触 Memory Passport 的产品、技术和采购评估人员。
不需要先理解项目源码；按顺序执行命令，即可在本地完成一轮可复现的
POC 验收。

> 当前开源版本适合本地评估、技术验证和 API 集成 POC。后端 API 是可运行、
> 可测试的产品能力；网页端目前是使用预置数据的交互原型，尚未完整连接后端，
> 因此不能只点击网页来判断后端是否验收通过。

## 1. 你会验证什么

完成本指南后，你可以确认：

- 客户可以从 GitHub 克隆项目并用一条命令启动；
- Memory Passport、PostgreSQL 和记忆引擎都正常运行；
- 应用能够写入、召回、修改和删除用户记忆；
- 策略、设备迁移、审计、用量统计和用户数据导出可以通过 API 使用；
- 没有模型密钥时，可以用确定性的本地演示引擎免费验收；
- 配置真实模型和 Embedding 密钥后，可以切换到真实 HMS 推理链路。

建议先完成“演示模式”，确认产品流程和本地环境没有问题，再测试真实 HMS。

## 2. 安装前准备

必需软件：

- Git；
- Docker Desktop，或安装了 Docker Compose 的 Docker Engine；
- `make`、`curl` 和 Python 3。

只有要查看网页原型或运行前端检查时，才需要 Node.js 22+ 和 pnpm 10+。
Windows 客户建议在 WSL2 中执行下面的命令。

先检查环境：

```bash
git --version
docker --version
docker compose version || docker-compose version
make --version
curl --version
python3 --version
```

## 3. 15 分钟完成本地安装

在一个新的目录中执行：

```bash
git clone --branch HMS --recursive https://github.com/joevilcai666/memory-passport.git
cd memory-passport
make demo
```

第一次运行会下载镜像并构建容器，所以会比后续启动更久。演示模式不需要任何
OpenAI 或其他模型供应商密钥，也不会产生模型调用费用。

安装成功时，最后一行是：

```text
Memory Passport local demo passed: http://127.0.0.1:8000/docs
```

`make demo` 不只是启动服务，它还会自动执行一条完整客户链路：

```text
健康检查 → 写入记忆 → 召回记忆 → 创建新版本 → 导出数据
          → 删除记忆 → 检查审计日志 → 检查用量统计
```

其中任何一步不符合预期，命令都会以非零状态退出，而不会显示 `passed`。

## 4. 确认安装结果

打开两个地址：

- API 文档：<http://localhost:8000/docs>
- 健康检查：<http://localhost:8000/v1/health>

也可以在终端执行：

```bash
curl -sS http://127.0.0.1:8000/v1/health | python3 -m json.tool
```

演示模式的正确结果是：

```json
{
  "mp": "ok",
  "hms": "ok",
  "db": "ok",
  "memory_engine": "demo"
}
```

这表示三个组件均可用：Memory Passport API、HMS 兼容记忆服务和数据库。

再检查容器状态：

```bash
docker compose ps || docker-compose ps
```

`postgres`、`hms-api` 和 `mp-backend` 应为 `running`/`Up`，并显示健康状态。

### 可选：浏览网页产品原型

如果已经安装 Node.js 22+ 和 pnpm 10+，在另一个终端执行：

```bash
pnpm install --frozen-lockfile
pnpm dev
```

然后打开 <http://localhost:3000>。`/console/*` 展示 B 端管理台，
`/app/*` 展示终端用户的记忆与设备迁移流程。这些页面用于体验产品设计，
目前显示的是预置前端状态；第 5 节的 API 请求才是后端能力验收。

## 5. 以客户应用的身份手动写入和召回

演示数据中已经包含一个 Luna 应用、Mia 用户和 Luna Agent。下面模拟客户应用
通过 API 保存一条新的用户偏好，再根据问题召回它。

先设置本次终端使用的地址和沙盒密钥：

```bash
export MP_API=http://127.0.0.1:8000
export MP_KEY=mp_sandbox_LK39sn8vQ4x2pR7wY1tBz0Hd
export MP_EVENT_ID="evt_customer_$(date +%s)"
```

写入一条只有本次测试才会出现的记忆：

```bash
curl -sS -X POST "$MP_API/v1/events/ingest" \
  -H "Authorization: Bearer $MP_KEY" \
  -H 'Content-Type: application/json' \
  --data "{
    \"user_id\":\"usr_mia\",
    \"agent_id\":\"agt_luna\",
    \"relationship_id\":\"rel_mia_luna\",
    \"source_type\":\"explicit_instruction\",
    \"content\":\"Mia's customer evaluation drink is jasmine tea.\",
    \"event_id\":\"$MP_EVENT_ID\"
  }" | python3 -m json.tool
```

响应的 `results` 中应至少有一项 `"action": "ADD"`。

然后召回：

```bash
curl -sS -X POST "$MP_API/v1/memories/retrieve" \
  -H "Authorization: Bearer $MP_KEY" \
  -H 'Content-Type: application/json' \
  --data '{
    "user_id":"usr_mia",
    "agent_id":"agt_luna",
    "relationship_id":"rel_mia_luna",
    "query":"What is Mia customer evaluation drink?",
    "model":"customer-poc"
  }' | python3 -m json.tool
```

正确结果应满足：

- `results` 中出现刚写入的 `jasmine tea`；
- 返回一个 `trace_id`，用于排查这次召回；
- 没有使用密钥时返回 `401`，不能匿名读取客户记忆。

可以用返回的 trace ID 查看召回链路：

```bash
curl -sS "$MP_API/v1/debug/traces/替换为实际TRACE_ID" \
  -H "Authorization: Bearer $MP_KEY" | python3 -m json.tool
```

## 6. B 端功能验收清单

建议由客户产品负责人和技术负责人共同勾选以下项目。

| 验收项目 | 客户应看到什么 | 最短验证方式 |
| --- | --- | --- |
| 安装与健康 | 三个组件均为 `ok` | `make demo` 与 `/v1/health` |
| 记忆写入/召回 | 新偏好可写入并按语义召回 | 本指南第 5 节 |
| 记忆生命周期 | 可列表、编辑生成新版本、审核、删除 | API 文档的 `/v1/memories*` |
| 策略控制 | 自动写入、敏感信息和召回上限按策略生效 | `/v1/policies` |
| 设备迁移 | 可预览、执行、重试和回滚 | `/v1/migrations*` |
| 合规可追溯 | 操作进入审计日志和用量统计 | `/v1/audit_logs`、`/v1/usage` |
| 数据可携带 | 可生成不含密钥和 Embedding 的 JSON 导出 | `/v1/exports` |
| 用户删除 | 删除 HMS bank、映射并吊销 Passport | `/v1/delete_user`，只对临时用户测试 |
| 租户安全 | 错误/缺失密钥被拒绝，跨租户访问返回 `403` | 自动化测试与 API 负向请求 |

所有接口的可复制示例在
[`docs/local-evaluation.md`](docs/local-evaluation.md)，每个 GitHub issue 对应的
自动化验收证据在 [`docs/issue-acceptance.md`](docs/issue-acceptance.md)。

如果客户需要进行代码级验收，运行完整本地质量门：

```bash
pnpm install --frozen-lockfile
make check
```

`make check` 会执行前端 lint/build、后端单元测试，以及容器内 PostgreSQL/HMS
集成测试；本项目不依赖 GitHub Actions。

## 7. 切换到真实 HMS 推理链路

### 7.1 配置真实密钥

在仓库根目录创建本地配置：

```bash
cp .env.example .env
```

打开 `.env`，至少替换下面三个占位值：

```dotenv
HMS_API_LLM_API_KEY=你的真实密钥
HMS_API_RETAIN_LLM_API_KEY=你的真实密钥
HMS_API_EMBEDDINGS_OPENAI_API_KEY=你的真实密钥
```

如果三个能力由同一 OpenAI 账号提供，可以填写同一个密钥；如果使用
OpenAI-compatible 服务，还要修改对应的 provider、model 和 base URL。
不要提交 `.env`，真实模式会产生供应商调用费用。

### 7.2 启动并证明当前不是模拟链路

```bash
make real-config
make real-up
```

`make real-config` 会先拒绝空值和 `*_change_me` 占位密钥。启动成功后执行：

```bash
curl -sS http://127.0.0.1:8000/v1/health | python3 -m json.tool
docker compose -f docker-compose.yml -f docker-compose.real.yml ps \
  || docker-compose -f docker-compose.yml -f docker-compose.real.yml ps
```

真实链路必须同时满足：

- 健康响应中是 `"memory_engine": "real"`；
- `hms-api` 和真实模式独有的 `hms-worker` 都处于健康状态；
- 第 5 节的写入与召回请求仍成功，且能召回一个全新的测试短语。

查看 HMS 的实际运行日志：

```bash
docker compose -f docker-compose.yml -f docker-compose.real.yml \
  logs --tail=200 hms-api hms-worker \
  || docker-compose -f docker-compose.yml -f docker-compose.real.yml \
  logs --tail=200 hms-api hms-worker
```

真实模式不要执行 `make demo`：该命令的自动断言刻意要求 `demo` 引擎。
真实模式请使用本节健康检查和第 5 节的手动写入/召回来验收。
供应商变量的完整说明见 [`docs/real-hms.md`](docs/real-hms.md)。

## 8. 客户如何把它接入自己的产品

本地 POC 推荐按以下顺序集成：

1. 客户后端保存 Memory Passport API 地址和租户 API key；不要把 key 放进浏览器或 App。
2. 为客户应用、Agent、用户和关系创建对应对象。
3. 对话产生明确事实或用户指令时，调用 `/v1/events/ingest`。
4. 生成模型回答前，调用 `/v1/memories/retrieve`，把允许返回的记忆加入模型上下文。
5. 在客户管理后台提供记忆查看、更正、删除、导出和审计入口。
6. 先在演示引擎验证业务集成，再用真实 HMS 重跑同一组 POC 用例。

仓库中的沙盒 key、示例数据库密码和 Luna 数据只能用于本地验收。进入试生产或
生产之前，客户还需要完成独立密钥、TLS/域名、持久化备份、监控告警、密钥轮换、
访问控制及本地区域/合规评审。当前网页端是交互原型；B 端正式集成应以 API 为准。

## 9. 停止、重启和彻底重置

```bash
make down                 # 停止演示模式，保留数据库
make demo                 # 再次启动并重复自动验收
make real-down            # 停止真实 HMS 模式，保留数据库
make clean                # 删除本地容器和数据库卷（不可恢复）
make clean && make demo   # 从空数据库重新验收安装过程
```

## 10. 常见问题

### `make demo` 无法连接 Docker

先启动 Docker Desktop，再运行 `docker compose version`。Linux 用户还应确认当前
用户有访问 Docker daemon 的权限。

### 端口 8000 或 18080 已被占用

在 `.env` 中修改本机映射端口，例如：

```dotenv
MP_PORT=18000
HMS_LOCAL_API_PORT=28080
```

如果修改 `MP_PORT`，后续把文档中的 `http://127.0.0.1:8000` 替换成新端口。
运行自动验收时还要把新地址传给脚本：

```bash
MP_DEMO_API_URL=http://127.0.0.1:18000 make demo
```

### 数据被之前的测试修改了

```bash
make seed
```

如果需要真正的全新环境，执行 `make clean && make demo`。注意 `make clean` 会删除
本项目的本地数据库卷。

### 查看服务错误

演示模式：

```bash
docker compose logs --tail=200 mp-backend hms-api postgres \
  || docker-compose logs --tail=200 mp-backend hms-api postgres
```

真实模式请使用第 7 节带两个 Compose 文件的日志命令。

## 11. 客户验收通过标准

一次可签字的 POC 至少应保留以下证据：

- `make demo` 最后一行的 `passed` 输出；
- `/v1/health` 的 JSON；
- 一组使用客户自定义短语的 ingest/retrieve 请求与响应；
- `/v1/audit_logs` 中对应的操作记录；
- 一个可下载且不含密钥/Embedding 的导出文件；
- 如果评估真实模型：`memory_engine=real`、`hms-worker` 健康状态和 HMS 日志；
- 客户完成第 6 节验收清单后的结论与未决生产化事项。

完成这些步骤后，客户验证的是一条真实、可重复的 Memory Passport API 链路，
而不只是查看一组静态页面。
