# Memory Passport PRD v2.0

**版本**：V2.0（战略转向版，替代 V0.1 雏形）
**产品类型**：B2B2C 可携带记忆基础设施
**一句话**：换设备，不换关系；换模型，不换记忆。
**日期**：2026-07-05

> 本文档是「Memory Passport 方案雏形.md」的战略转向重写版。原雏形把 ~20 个模块全标 P0，模糊了楔子，且在 portability 护城河与销售叙事之间存在直接矛盾。本版基于结构化访谈锁定战略主线后重写，明确 V0.1 = 最小楔子 + 可运营最薄层（10–12 周），并完整留档 P1/P2/P3 轨迹。

> **2026-07-05 更新（原型对齐版）**：本文档已与可交互原型（`/Users/jichuncai/MemoryPassport`，Next.js 16 + Ink & Paper 设计系统）对齐。所有 IA、页面结构、交互模式以原型实现为准；本文 Part 3 / Part 4 / Part 5 / Part 6 / Part 14 已据此重写。战略层（Part 0–2）、数据模型（Part 7）、API（Part 8）、权限（Part 9）、状态机（Part 10）、计费（Part 11）、Roadmap（Part 12）不变。原型使用 Luna 数据集（42 条记忆 + v1→v2 迁移）作为 seeded mock，无真实后端。

---

## 目录

- [Part 0 — 一页纸摘要 + 战略论证](#part-0--一页纸摘要--战略论证)
- [Part 1 — 产品原则（修订版）](#part-1--产品原则修订版)
- [Part 2 — 客户与角色](#part-2--客户与角色)
- [Part 3 — 产品形态](#part-3--产品形态)
- [Part 4 — 信息架构](#part-4--信息架构)
- [Part 5 — UI / UX 线框图](#part-5--ui--ux-线框图)
- [Part 6 — 核心客户流程](#part-6--核心客户流程)
- [Part 7 — 核心功能需求](#part-7--核心功能需求)
- [Part 8 — API 总表](#part-8--api-总表)
- [Part 9 — 权限与安全](#part-9--权限与安全)
- [Part 10 — 状态机](#part-10--状态机)
- [Part 11 — 计费模型](#part-11--计费模型)
- [Part 12 — Roadmap](#part-12--roadmap)
- [Part 13 — 风险与缓解](#part-13--风险与缓解)
- [Part 14 — 不重不漏检查表](#part-14--不重不漏检查表)
- [Part 15 — 团队执行口径](#part-15--团队执行口径)

---

# Part 0 — 一页纸摘要 + 战略论证

## 0.1 我们到底做什么（一句话）

Memory Passport 是一个**用户拥有、跨模型、跨设备、可携带**的长期关系记忆层，以嵌入式 SDK 形态接入 B 端 AI companion / 机器人客户。换身体不换关系，换模型不换记忆。

## 0.2 与 Shadow / 共鸣 的三线关系（这是 GTM 防御工事本身）

Memory Passport 不是孤立产品，是公司三线组合中的 B 端商业化腿：

```
┌─────────────────────────────────────────────────────────┐
│                  记忆论点的三种证明                          │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  Shadow（本地 · 开发者）   共鸣（C 端 · 数据入口）          │
│   "纠错一次，所有编码 agent 记住"  "你 × 城市 × 人的记忆"   │
│         ↓                          ↓                     │
│         └────── 共享记忆引擎论点 ──────┘                  │
│                     ↓                                    │
│            Memory Passport（B 端 · 商业化）               │
│   "AI companion / 机器人客户的可携带记忆基础设施"           │
│                                                          │
│  三线组合 = 内置需求（自家 dogfood）+ 跨场景验证            │
│  + 不可被竞品复制的组合护城河                                │
└─────────────────────────────────────────────────────────┘
```

- **Shadow** 已本地证明了记忆论点（cross-tool/cross-session continuity for coding agents），并把"绝不入库密钥/凭证""默认只存提炼后规则""坚决不卖数据给模型公司""统一规则→各 agent 原生上下文适配器"等原则固化为产品硬约束。
- **共鸣** 是 C 端记忆数据入口，证明"人 × 地点 × 关系"的长期记忆对终端用户有吸引力。
- **Memory Passport** 把同一套记忆论点商业化到 B 端 companion / 机器人垂直，是 Shadow 本地引擎 + 共鸣 C 端洞察的云化、平台化、可携带化。

这三线不是三个独立产品，是同一论点的三个市场面。组合本身是 GTM 防御工事：竞品可以复制其中一条腿，但很难复制三线组合。

## 0.3 Privy 类比：拿灵魂，不拿外壳

创始人原话："账号功能（类似于 privy payment）"。这是关键类比，但必须拿对层。

**Privy 的灵魂不是"嵌入式钱包"，而是"非托管 + 跨应用携带"。**

| 层 | Privy 做了什么 | 对 MP 的对应 |
|---|---|---|
| 外壳（拿错就崩） | 嵌入式 SDK + 白标 UI + freemium→usage 计费 | 嵌入式 SDK + Powered by 联名 + MAU 计费 |
| 灵魂（拿对才行） | **非托管**：钱包密钥属于用户，不属于应用；跨应用携带是**架构原生**，不是后期补丁 | **非托管记忆**：记忆属于用户的 Passport，不属于某个 app；跨设备/跨模型携带是**架构原生**（portable-native 数据模型） |

**Privy 教训 1（拿灵魂）**：Privy 从 Day 1 把非托管写进架构，所以"跨应用携带"在 n=1 时不可见，在 n=100 时变成垄断护城河。MP 必须 Day 1 就 portable-native，否则 V2+ 跨品牌迁移时要从头重构。

**Privy 教训 2（拿灵魂）**：Privy 不向应用卖"跨应用携带"（那是敌对的），而是卖"嵌入式钱包 infra，你不用自建"（n=1 自洽）。跨应用携带是网络效应的副产品。MP 同理：V0.1 不向 B 端卖跨品牌迁移，卖"你不用自建记忆 infra"；跨品牌是网络效应副产品。

**Privy 教训 3（拿灵魂）**：应用保留用户关系（auth/profile/业务），钱包属于用户。MP 同理：app 保留用户关系、角色、对话；记忆属于用户的 Passport。"Powered by Memory Passport" 不是抢用户，是用户拥有自己记忆的可见标识。

**为什么 strong-passport 是唯一一致解**：如果选"弱/嵌入式"（app 拥有记忆），portability 需要额外导出/导入机制，"Passport"这个名字不名副其实，且 V2+ 跨品牌时要重构。只有 strong-passport（用户拥有 + 嵌入式交付）能让楔子（跨设备）与护城河（可携带）共用一套基建，一次构建。

## 0.4 LLM 威胁分析（这是塑造 beachhead 的二阶思考）

**共识**：AI companion 需要记忆。**这是 Howard Marks 会警告的「too-obvious」first-level 思考**——人人都知道，所以没有 alpha。

**OpenAI/Anthropic/Google 正把记忆原生塞进模型**。如果 GPT-7 记忆足够好，**软件段**的「记忆层」thesis 直接崩盘——软件客户直接用模型自带记忆即可。

这重塑了 beachhead 优先级：

| 段 | LLM 原生记忆威胁 | 唯一防御 |
|---|---|---|
| 软件 companion | **高**（模型记忆直接替代） | 跨模型可携带性（GPT 记忆不通 Anthropic → MP 是中立层） |
| 机器人 / 硬件 | **低**（边缘/本地模型，OpenAI 云记忆进不来） | 物理隔离本身就是防御 |

**Non-consensus（真正的 alpha）**：不是"companion 需要记忆"（共识），而是 **"记忆必须属于用户且跨模型中立"**——因为只有这样才不被 LLM 厂商锁定、不被硬件世代锁定、不被单一 app 锁定。这是 Privy 在 web3 已经证明过的 non-custodial 论点，搬到 AI 关系记忆上。

## 0.5 四轴可携带性澄清（这是调和 draft 19.1 矛盾的关键）

Draft 19.1 说"跨品牌迁移藏起来"，但 portability 又被选为护城河——直接矛盾。澄清：portability 有四个轴，B2B 友好度天差地别，draft 把它们混为一谈了。

| 可携带轴 | 含义 | B2B 友好度 | LLM 防御力 | Draft 立场 | V2.0 立场 |
|---|---|---|---|---|---|
| **跨设备（品牌内）** | v1→v2 机器人、手机↔桌面 | ✓✓✓ 盟友 | — | P0 | **P0（楔子）** |
| **跨角色（品牌内）** | 用户的多个 AI 角色共享核心记忆 | ✓✓✓ 盟友 | — | P0 | **P0（软件卖点）** |
| **跨模型（LLM 中立）** | 同一记忆可被 GPT/Anthropic/本地模型读 | ✓✓ 盟友（反锁定） | ✓✓✓ 强 | ✗ 未区分 | **P0（护城河）** |
| **跨品牌 App（Luna→竞品）** | 用户把记忆从一个 app 带到竞品 | ✗✗ 敌对 | — | P3 | **P2/P3（架构 ready，叙事延后）** |

**突破口**：**"跨模型"才是 V0.1 护城河**。它 B2B 友好（客户不想被 OpenAI 锁定 → 想要中立记忆层），LLM 防御力强，且**调和 19.1 矛盾**——因为"跨品牌 App"才是真正对 B2B 敌对的部分，那才需要藏到 P2/P3。"跨模型"是 B2B 销售话术，不是"帮用户流失到竞品"。

**架构含义**：四轴共用一套 portable-native 数据模型，区别只在策略开关。V0.1 开放前三轴（跨设备/跨角色/跨模型），关闭第四轴（跨品牌 App）。一次构建，逐步解锁。

## 0.6 Peter Thiel / Howard Marks 视角的战略论证

**Thiel（垄断 via 单一维度 10x）**：不与 Supabase/Pinecone 比"存储/检索"（它们 10x 我们），不在"记忆质量"上卷（红海）。**在"可携带性"上做 10x**——这是唯一一个维度，竞品即使复制我们所有其他功能，也无法拿走用户已积累的可携带记忆（数据重力 + 网络效应 + 切换成本）。Memory Passport = "AI 关系记忆的可携带性标准"，类比 Privy = "web3 钱包的非托管标准"。

**Marks（second-level thinking）**：
- Level 1（共识，无 alpha）："companion 需要记忆" → 被卷进红海，被 LLM 厂商吃掉。
- Level 2（non-consensus，有 alpha）："记忆必须属于用户且跨模型中立" → 防御 LLM 锁定 + 建立可携带护城河 + 让 B 端客户也受益（反锁定）。
- Level 3（极端场景，what-if）：如果未来 AI 关系像社交关系一样是用户的核心资产，那么"AI 关系记忆"会像"信用记录"一样需要中立征信局。Memory Passport 是这条路径的种子。

**Occam's Razor**：V0.1 只做最小楔子（跨设备连续性 end-to-end）+ 可运营最薄层（Audit/Webhook/删除导出）。其余全部 P1+ 留档。**绝不为"完整"而增加任何不直接服务楔子的实体。**

## 0.7 北极星指标

Memory Passport 的北极星不是 API 调用量，而是：

**Memory Continuity Rate**：用户在新会话 / 新设备 / 新角色 / 新模型中，被正确继承并有效使用的记忆比例。

辅助指标（V0.1 目标）：

| 指标 | 定义 | V0.1 目标 |
|---|---|---|
| Useful Memory Rate | 被用户/客户认为有帮助的记忆比例 | > 70% |
| False Memory Rate | 用户反馈错误记忆比例 | < 3% |
| Delete Propagation Time | 用户删除后不再被检索的时间 | < 1 分钟 |
| Migration Success Rate | 角色/设备迁移成功率 | > 95% |
| Time to First Memory | 客户接入后终端用户首次产生有效记忆的时间 | < 10 分钟 |
| Customer Time to Demo | B 端客户从注册到跑通 demo 的时间 | < 2 小时 |
| Cross-Model Retrieval Parity | 同一记忆跨模型检索的相关性一致性 | > 0.85 |
| Powered-by Recall | 终端用户对"Powered by Memory Passport"的认知率（P1 起） | 留档 |

---

# Part 1 — 产品原则（修订版）

Draft 有 5 条原则，部分与战略转向冲突。修订为锁定后的 5 条：

## 1.1 Portable-native（Day 1 写进架构）

每一条记忆在写入时就标记为 **PORTABLE 语义层**（偏好/边界/关系历史/事件，可跨设备/跨角色/跨模型迁移）或 **DEVICE-LOCAL 层**（传感器校准/空间地图/硬件状态，永不迁移）。

品牌内迁移与跨品牌迁移**共用一套基建**，区别只在策略开关。V0.1 只开放前三轴（跨设备/跨角色/跨模型），但架构必须支持第四轴（跨品牌 App）以备 P2/P3 解锁。**不二次构建。**

## 1.2 Non-custodial（用户拥有记忆）

类比 Privy 非托管钱包：app 保留用户关系（auth/profile/角色/对话），**记忆属于用户的 Passport**。"Powered by Memory Passport"是用户拥有自己记忆的可见标识，不是抢用户。

这不是"用户关系是你的、记忆是你的"二选一，而是**分层所有权**：
- App 拥有：用户身份认证、角色 persona、对话历史、业务逻辑
- 用户拥有（via Passport）：跨 app/设备/模型可携带的长期关系记忆

## 1.3 最小引擎（Occam）

V0.1 不做完整记忆引擎。只做：
- **最小结构化写入**：客户 app 或用户发送结构化事实 → 存为 portable/local 记忆
- **按 scope 检索**：retrieve relevant memories by user/relationship/agent/device
- **文本投影**：把记忆拼成 plain text 注入 prompt

不做：复杂抽取、consolidation、conflict resolution、PII 深度扫描、丰富策略引擎。这些全部 V1.1 或推给客户自带引擎（开放 schema）。

## 1.4 B2B 盟友话术（不卖跨品牌，卖 infra + 反锁定）

V0.1 对 B 端客户的话术必须是：
- ✓ "你不用自建记忆 infra，10 分钟接入"
- ✓ "换身体不换关系（v1→v2 机器人继承记忆）"
- ✓ "记忆层跨模型中立，你不被 OpenAI 锁定"
- ✗ 不说"用户未来可以把记忆带到竞品"（那是 P2/P3 才讲的）

跨品牌 App 迁移叙事延后，但架构 ready。

## 1.5 三线 synergy（Shadow + 共鸣 + MP）

MP 不是孤立产品。Shadow 提供本地引擎验证 + 原则沉淀；共鸣提供 C 端数据入口 + 用户洞察；MP 是 B 端商业化。三线共享记忆论点与原则（绝不入库凭证、默认只存提炼后规则、坚决不卖数据、统一规则→原生上下文适配器）。**这条 synergy 是 GTM 防御工事本身。**

---

# Part 2 — 客户与角色

## 2.1 双线滩头堡

| 线 | 客户画像 | 主卖点 | GTM 速度 | LLM 威胁 | 单价 |
|---|---|---|---|---|---|
| **软件线** | AI companion / character / pet app | 跨角色记忆共享 + 多设备同步 + 反 LLM 锁定 | 快 | 高 | 中 |
| **机器人线** | 陪伴机器人 / AI pet / 桌面机器人 / 仿生机器人 OEM | v1→v2 跨世代继承（"Her"叙事） | 慢 | 低（边缘/本地模型） | 高 |

**双线并行的合理性**：软件线快速拿量、验证引擎、积累跨模型证据；机器人线拿高单价 + 最强叙事 + LLM 免疫。两条线共享同一引擎与 portable-native 数据模型，资源开销可控（详见风险章节）。

**内部 dogfood 候选**：origin-ai v2.0 已是 companion app（"Origin 同伴人格"），且已有 embryonic Context Graph + Auth。是 MP 的天然首个内部客户，可 de-risk 引擎与迁移 3–6 个月后再外推。**注意风险：origin-ai 需求 ≠ B 端通用需求，dogfood 阶段需刻意保持引擎通用性。**

## 2.2 B 端客户角色

| 角色 | 关心什么 | 典型问题 |
|---|---|---|
| CEO / Founder | 留存、复购、付费、壁垒 | "记忆能不能成为我们产品壁垒？会不会被 OpenAI 吃掉？" |
| 产品经理 | 用户体验、记忆策略、迁移体验 | "用户怎么看到 AI 记住了什么？换设备体验怎样？" |
| 工程负责人 | 接入成本、稳定性、延迟、安全、模型中立 | "几天能接完？会不会拖慢模型回复？换 LLM 要重做吗？" |
| 法务 / 合规 | 数据权属、删除、审计、未成年人 | "用户要求删除时，我们能证明删了吗？记忆到底归谁？" |
| 客服 / 运营 | 用户投诉、错误记忆、权限问题 | "用户说 AI 乱记了，我怎么查？怎么改？" |
| 硬件负责人 | 设备绑定、换代、维修、二手转让 | "v1 到 v2 怎么继承记忆？二手买家会不会看到旧记忆？" |

## 2.3 终端用户角色

| 用户 | 核心需求 |
|---|---|
| AI companion 重度用户 | AI 越来越懂自己，换 app 不丢关系 |
| AI 角色平台用户 | 每个角色有独立关系记忆，但共享核心偏好 |
| 机器人用户 | 换新机器人后关系不丢（"Her"） |
| 家庭用户 | 设备知道家庭规则，但不泄露个人隐私 |
| 隐私敏感用户 | 查看、删除、关闭、导出记忆，记忆归我 |

---

# Part 3 — 产品形态

## 3.0 设计系统：Ink & Paper（原型实现基准）

原型采用自有的 **"Ink & Paper"** 设计系统（不照抄 Anyway Design System 的 token 或金色品牌色，只借鉴其纪律：中性 chrome、边框优先于阴影、Geist + Geist Mono、radius 层级）。

- **隐喻**：passport —— 记忆是 ink stamps，属于用户、跟着用户走。
- **双面**：B 端 Console = 石墨色 instrument-panel（默认深色）；C 端 Embedded = 暖纸面（强制浅色 `.paper-surface`）。
- **强调色**：passport ink `#1E3A8A`（深靛蓝）—— 用于主操作、active 态、portability 标记、印章图形。Hue 仅用于状态/数据，chrome 是中性灰。
- **字体**：`geist` 包 → Geist Sans + Geist Mono（所有 ID / 计数 / 模型名走 mono + tabular figures）。
- **Radius**：8（按钮）/ 10（输入）/ 14（卡片）/ full（pills）。
- **Motion**：framer-motion，最小且功能性（仅迁移完成页有 earned 的印章动画）。

## 3.1 B 端 Admin Console（V0.1 实现版）

原型把 Console 导航按用户旅程分为 **3 个分组**（Start → Build → Operate），而非按功能模块平铺：

| 分组 | 导航项 | V0.1 实现 | P1+ 扩展 |
|---|---|---|---|
| **Start** | Overview | KPI + 活动图 + Alerts + **实时 onboarding 横幅**（未接入时显示，接入后消失）+ **migration demo 入口卡** | 完整报表、Memory Health |
| | Get started（原 Quickstart） | 4 步 SDK 接入 + **实时集成状态 checklist**（点 Run Test Event / Retrieve 实时打勾） | — |
| **Build** | Apps | App 列表 + 创建 App（含 live consent 预览）+ App 详情/API Keys（reveal/copy/roll）+ 集成健康 | Branding、多环境、Webhooks |
| | Policy | Auto-write 规则表 + **4 轴 portability 开关**（cross_brand_app 锁定关闭 P2）+ Retrieval 配置 | Policy 版本管理 |
| | Users | **合并 Debugger + End Users**：全宽 master-detail 卡，顶部内联用户切换 Select + 记忆表格，**点击任意行 → 右侧 Sheet 滑出 Memory Trace** | — |
| **Operate** | Devices | **迁移优先叙事**：Health tiles + Generation upgrade path 可视化 + Recent migrations + Device registry（支撑信息） | Repair/Wipe/Transfer、Migration Dashboard |
| | Settings | Team Members（Owner/Admin/Support）+ Audit Log（timeline 式） | 完整 RBAC、Webhooks、Data Residency、Security |

**Topbar（全局）**：
- **"Preview as user" 按钮**（Stripe "View as customer" 模式）—— 永久可见的下拉，直通 C 端 Embedded UI（Memory Center / Consent / Device binding），并把 **Migration demo** 置顶标 `wedge` 徽章。这是 wedge demo 的常驻入口，不再藏在某个页面深处。
- Sandbox/Prod 切换器 + 主题切换（深/浅）+ 账户菜单。

**关键 IA 决策（与原 PRD draft 的差异）**：
1. **Debugger 与 End Users 合并为单一 "Users"**——用户是实体，记忆是用户的子属性（Intercom/Stripe 模式）。拆成两个 tab 是冗余 IA。
2. **Memory Trace 从独立路由改为右侧 Sheet 抽屉**——点击表格行不跳页、不丢上下文（Linear/Notion 模式）。
3. **Agents 不作为独立 nav 项**——Agent 存在于数据中，在 Users / Policy 的上下文里展示。
4. **Quickstart 重定位**——onboarding 是状态不是页面；横幅嵌入 Overview，nav 项置顶并更名 "Get started"。
5. **Devices 重定位**——从"设备台账"改为"迁移生命周期"（health tiles + upgrade path），registry 降级为支撑信息。

**V0.1 不做**：独立 Billing 页（手动计费）、独立 Agents 页、独立 Policy 版本页、Memory Health、独立 Migration Dashboard。

## 3.2 落地页（`/`，新增）

原型新增一个公开落地页（非 Console、非 Embedded），承担 wedge 叙事与双面入口：
- **Hero**：一句话 wedge（"Switch devices, not relationships. Switch models, not memory."）+ 两个入口（"I'm building a companion" → Console；"See it as a user" → Embedded）。
- **Privy 类比段**："Like a wallet. But for memory." + 3 原则卡（Non-custodial / Portable-native / Yours to control）。
- **四轴 portability 表**：B2B 友好度 × LLM 防御力 × 优先级。
- **楔子 CTA**："Upgrade the body. Keep the relationship." → 直通 migration demo。

## 3.3 Embedded User UI（V0.1 完整集）

嵌入客户 App / WebView / 小程序 / 机器人配套 App，**带 "Powered by Memory Passport" 联名**（每屏底部水印，网络效应种子）。

| 页面 | 路由 | V0.1 范围 |
|---|---|---|
| 记忆授权页 | `/app/consent` | 首次启用记忆 / 绑定设备 / 迁移时；✓/✕ 列表 + Powered by 水印 |
| 聊天内记忆确认卡 | （组件） | 仅敏感/高影响记忆（S2/S3），[Don't save][Edit][Save]；不打断普通记忆 |
| Memory Center | `/app/memory` | ON/Pause + 计数 + category chips + 搜索 + 记忆列表 |
| Memory Detail | `/app/memory/[id]` | 内容 + **Portability badges（✓✓✓ / Device-local）** + 来源（"Why was this saved?"）+ Used by + Edit/Delete/Report |
| Device Management | `/app/devices` | 当前设备 + 绑定入口 + migration banner |
| 机器人绑定 | `/app/devices/bind` | QR 扫描（模拟）+ pairing code |
| 迁移预览 | `/app/migrate` | **楔子核心页**：3 buckets（Recommended/Needs review/Not moved）+ v1 access radio + `[Move N]` |
| 迁移完成 | `/app/migrate/complete` | 印章动画 + v2 继承文案（"I still remember you call me Luna…"）+ 统计 |
| 删除全部记忆 | `/app/memory/delete` | 输入 `DELETE` 确认 + 破坏性说明 |

**AppShell**：手机宽度居中（max-w-md），暖纸 `.paper-surface`，顶部 app-style header（返回 + 标题 + 溢出菜单），底部 Powered by 水印。

## 3.4 SDK / API

| 形态 | V0.1 | P1+ |
|---|---|---|
| JavaScript / TypeScript SDK | ✓ | — |
| Python SDK | ✓ | — |
| REST API | ✓ | — |
| React Embedded Components（Consent/Memory Center/确认卡） | ✓ | — |
| Webhook（最薄：memory.created/deleted、migration.completed） | ✓ | 完整事件 |
| Mobile WebView 页面 | ✓ | iOS/Android 原生 SDK |
| Robot SDK / Edge Agent | P1 | ✓ |
| ROS / XR / Spatial SDK | P2 | ✓ |

## 3.5 Co-branded 机制（"Powered by Memory Passport"）

**默认联名**：用户首次授权页、Memory Center 底部、迁移完成页、落地页 footer 出现 "Powered by Memory Passport" 小字 + 印章 logo。

**白标选项（P1）**：Enterprise 客户可关闭联名，但需支付溢价（类比 Privy Enterprise）。

**为什么联名是 V0.1 而非 P1**：portability 护城河需要 C 端认知，C 端认知需要品牌可见。联名是网络效应的种子，必须在 V0.1 就播种。

---

# Part 4 — 信息架构

## 4.1 Admin Console 信息架构（原型实现版）

导航按用户旅程分 3 组（Start → Build → Operate），而非按功能模块平铺。Memory 模块不再拆 Agents/Policy/Debugger/End Users 四个子 tab，而是合并为 **Policy** + **Users** 两个 nav 项。

```
Memory Passport Console
│
├── Topbar（全局）
│   ├── [Preview as user ▾]  ← 永久入口，直通 C 端 UI（含 migration demo）
│   ├── [Sandbox | Prod] 切换
│   ├── 主题切换（深/浅）
│   └── 账户菜单
│
├── Start
│   ├── Overview                      /console
│   │   ├── 实时 onboarding 横幅（未接入时显示，4 步 checklist + 进度条）
│   │   ├── KPI（Memory MAU / Ops / Useful Rate / False Rate / Migration Success / Cross-Model Parity）
│   │   ├── Memory Activity（reads/writes chart）
│   │   ├── Alerts（false memory / migration 失败 / parity）
│   │   ├── Migration demo 入口卡（"Try the migration demo"，wedge）
│   │   └── System health（Ingest/Retrieve/Migration/Webhooks）
│   └── Get started                   /console/quickstart
│       ├── 4 步（Install → Init → Run Test Event → Run Retrieve Test）
│       └── 实时集成状态 checklist（随操作打勾）
│
├── Build
│   ├── Apps                          /console/apps
│   │   ├── App 列表
│   │   ├── Create App                /console/apps/new（含 live consent 预览）
│   │   └── App 详情 + API Keys       /console/apps/[id]（reveal/copy/roll + 集成健康）
│   ├── Policy                        /console/memory/policy
│   │   ├── Auto-write 规则表（Type × Action × Sensitivity × TTL）
│   │   ├── Portability（4 轴开关；cross_model=moat 高亮；cross_brand_app 锁定）
│   │   └── Retrieval（max per response / sensitive in prompt）
│   └── Users                         /console/memory/users
│       ├── 用户切换 Select（顶部内联，搜索 name/ID）
│       ├── 用户头部（avatar / passport_id / age_group / Memory ON-OFF / 记忆数）
│       ├── Memory records 表格（全宽；Status/Type/Content/Scope/Portability/Used/Actions）
│       └── 【点击任意行 → 右侧 Sheet 滑出 Memory Trace】（不跳页，不丢上下文）
│           Trace 内容：Request(Model:gpt-4o) / User message / Retrieved memories /
│                      Projection / Feedback / Cross-model parity
│
└── Operate
    ├── Devices                       /console/devices
    │   ├── Health tiles（Migration success / Memory retention / Devices bound / Resale-safe wipes）
    │   ├── Generation upgrade path（v1 → migration engine → v2 可视化）
    │   ├── Recent migrations 表（User/Source/Target/Moved/Status/Actions）
    │   └── Device registry（Model/Gen/Serial/Status/Bound user/Last seen）
    └── Settings                      /console/settings
        ├── Team（Owner/Admin/Support）
        └── Audit Log（timeline 式）
```

**被移除/合并的原 IA 项**（与 draft 差异）：
- ~~Memory/Agents~~（独立 nav）→ Agent 存在于数据，在 Users/Policy 上下文展示。
- ~~Memory/Debugger~~ + ~~Memory/End Users~~ → 合并为 **Users**（master-detail + Trace Sheet）。
- ~~Memory/Trace 独立路由~~ → 改为右侧 Sheet 抽屉。
- ~~Quickstart 作为 Apps 子项~~ → 提升为 Start 组顶层，更名 "Get started"，并在 Overview 嵌入横幅。

**P1+ 扩展点**（留档，不在 V0.1）：
- 独立 Agents 页、独立 Policy 版本管理
- Migration Dashboard 独立页
- Usage & Billing 页
- 完整 RBAC（Developer/Viewer/Billing 角色）
- Webhooks 配置页
- Data Residency / Security 页

## 4.2 Embedded User UI 信息架构（原型实现版）

```
Embedded（Powered by Memory Passport，每屏底部水印）
│
├── Consent                           /app/consent
│   └── ✓/✕ 列表 + "Your memories belong to you" + [Not now]/[Turn on]
│
├── Memory Center                     /app/memory
│   ├── Memory ON/Pause 状态 + 计数（"Luna remembers 42 things about you"）
│   ├── 搜索 + category chips（Preferences/Relationship/Events/Boundaries/Tasks/Archived）
│   ├── 记忆列表（MemoryCard：content + type + source + Portability compact badge）
│   └── 溢出菜单 → Devices / Export / Delete all
│
├── Memory Detail                     /app/memory/[id]
│   ├── 内容 + status
│   ├── Portability badges（full：cross_device/role/model/brand_app ✓✓✓/✕）
│   ├── 元数据网格（Type/Scope/Confidence/Created/Last used/Times used）
│   ├── Why was this saved?（source quote + source_type）
│   ├── Used by（Luna iOS App + 设备 + 模型检索历史）
│   └── [Edit] [Delete] [Report wrong]
│
├── Devices                           /app/devices
│   ├── migration banner（v2 ready 或 completed）
│   ├── 当前设备列表
│   └── [Bind new device]
│
├── Bind device                       /app/devices/bind
│   └── QR 扫描（模拟）+ pairing code + [Bind to my Passport]
│
├── Migrate                           /app/migrate
│   ├── v1 → v2 pills
│   ├── Bucket: Recommended（☑ 选中，Select all）
│   ├── Bucket: Needs review（☐ 逐条确认）
│   ├── Bucket: Not moved（✕ device-local，不可选）
│   ├── After migration radio（Keep v1 / Remove v1）
│   └── [Move N]（sticky CTA）
│
├── Migrate complete                  /app/migrate/complete
│   ├── 印章动画（spring + ripple）
│   ├── v2 首次对话文案（"I still remember you call me Luna…"）
│   └── 统计（Moved / Skipped / v1 access）
│
└── Delete all                        /app/memory/delete
    ├── 破坏性警告 + 范围说明
    └── 输入 DELETE 确认 → [Delete forever]
```

---

# Part 5 — UI / UX 线框图

> 每个 UI 页面：先文字逻辑（出现场景、P0 要求、状态变化），再 ASCII 线框图。
> **所有线框图已与原型（`/Users/jichuncai/MemoryPassport`）对齐。** 原型为高保真可交互实现，ASCII 仅为结构示意。

## 5.1 Admin Console

### 5.1.1 Overview 首页

**出现场景**：客户登录后默认落地页。
**P0 要求**：
- 默认展示客户最关心的业务指标（6 KPI tiles）。
- **未完成 onboarding 时**，顶部显示实时进度横幅（4 步 checklist + 进度条 + [Continue setup]）；完成后自动消失。
- Migration demo 作为**高亮入口卡**（wedge），常驻主区域。
- 客户还没接入时，首页展示 onboarding 横幅，而不是空图表。
- 点击任意指标进入明细（最小：跳到 Users）。

**ASCII 线框**：
```
┌──────────────────────────────────────────────────────────────────┐
│ Memory Passport     [Preview as user ▾] [Sandbox|Prod]  ☀  [MC]  │
├───────────────┬──────────────────────────────────────────────────┤
│ Start         │ Overview                                         │
│  Overview     │ Luna Inc. · Luna app · 42 memories               │
│  Get started  │                                                  │
│ Build         │ ┌─ Get started — ship a memory loop in 2h ─────┐ │
│  Apps         │ │ ● API key  ● Test user  ○ First event  ○ Retr │ │
│  Policy       │ │ ████████░░░░░░░░  2 of 4          [Continue]  │ │
│  Users        │ └────────────────────────────────────────────────┘ │
│ Operate       │                                                  │
│  Devices      │ ┌──────────┐┌──────────┐┌──────────┐┌──────────┐│
│  Settings     │ │Memory MAU││Memory Ops││UsefulRate││FalseRate ││
│               │ │  12,430 ↑││ 892,104 ↑││  76.2% ↑ ││  1.9% ↓  ││
│               │ └──────────┘└──────────┘└──────────┘└──────────┘│
│               │ ┌──────────┐┌──────────┐                          │
│               │ │Migr OK   ││X-Model   │                          │
│               │ │ 98.1% ↑  ││Parity .91│                          │
│               │ └──────────┘└──────────┘                          │
│               │                                                  │
│               │ Memory Activity            Alerts                │
│               │ ┌────────────────────┐ ┌────────────────────┐    │
│               │ │ reads/writes chart │ │ ⚠ 2 flagged wrong  │    │
│               │ └────────────────────┘ │ ℹ parity 0.91      │    │
│               │                        │ ✕ 1 migration fail │    │
│               │                        └────────────────────┘    │
│               │ ┌─ Try the migration demo [wedge] ── [Try it] ┐ │
│               │ └────────────────────────────────────────────────┘│
└───────────────┴──────────────────────────────────────────────────┘
```

**关键交互**：
- onboarding 横幅读取 Quickstart 状态（apiKeyCreated / testUserCreated / firstEventSent / firstRetrieveDone），实时更新进度条；全部完成 → 横幅消失。
- Migration demo 卡点击 → 直达 `/app/migrate`（楔子）。
- "Preview as user" 顶栏按钮是 wedge 的**常驻入口**（Stripe 模式），任何页面都能一键到达 C 端。

### 5.1.2 创建 App

**出现场景**：客户首次创建产品。
**P0 要求**：
- Product type 决定后续默认模板（software companion 默认创建 Agent 模板；robot 默认创建 Device Model 模板）。
- 默认 Sandbox，不允许新客户直接 Production。
- Data region 必选（合规）。

**ASCII 线框**：
```
┌──────────────────────────────────────────────────────────────┐
│ Create App                                                    │
├──────────────────────────────────────────────────────────────┤
│ App name                                                      │
│ ┌──────────────────────────────────────────────────────────┐ │
│ │ Luna Companion                                           │ │
│ └──────────────────────────────────────────────────────────┘ │
│                                                              │
│ Product type                                                  │
│ ○ AI companion / character app（software 线）                 │
│ ○ Robot / hardware device（机器人线）                          │
│ ○ Hybrid: software + hardware                                 │
│                                                              │
│ Environment                                                   │
│ ● Sandbox                                                     │
│ ○ Production                                                  │
│                                                              │
│ Data region                                                   │
│ [ US ▾ ]                                                      │
│                                                              │
│ Branding（V0.1 默认联名，不可改；白标 P1）                       │
│ ☑ Show "Powered by Memory Passport"                          │
│                                                              │
│                 [Cancel]           [Create App]               │
└──────────────────────────────────────────────────────────────┘
```

### 5.1.3 Get started（原 Quickstart）/ SDK 接入页

**出现场景**：客户创建 App 后引导接入。位于 nav "Start" 组，Overview 之下。
**P0 要求**：
- 客户 10 分钟内跑通一次 write / retrieve。
- 4 步（Install → Init → Send event → Retrieve），每步有 Copy、Run Test。
- 失败时错误必须指向具体原因（API key / user_id / agent_id / policy / payload / 权限）。
- **接入状态实时更新**——点 [Run Test Event] → checklist 第 3 步打勾并真的写入一条记忆；点 [Run Retrieve Test] → 第 4 步打勾。Overview 横幅同步更新。

**ASCII 线框**：
```
┌──────────────────────────────────────────────────────────────────┐
│ Quickstart: Luna Companion                                       │
├──────────────────────────────────────────────────────────────────┤
│ Step 1. Install SDK                                              │
│ ┌──────────────────────────────────────────────────────────────┐ │
│ │ npm install @memory-passport/client                          │ │
│ └──────────────────────────────────────────────────────────────┘ │
│ [Copy]                                                           │
│                                                                  │
│ Step 2. Initialize                                               │
│ ┌──────────────────────────────────────────────────────────────┐ │
│ │ const mp = new MemoryPassport({                              │ │
│ │   apiKey: "mp_sandbox_xxx",                                  │ │
│ │   appId: "app_luna"                                          │ │
│ │ })                                                           │ │
│ └──────────────────────────────────────────────────────────────┘ │
│ [Copy]                                                           │
│                                                                  │
│ Step 3. Send an event（写入一条记忆）                              │
│ [Run Test Event]                                                 │
│                                                                  │
│ Step 4. Retrieve memory（检索并注入 prompt）                       │
│ [Run Retrieve Test]                                              │
│                                                                  │
│ Integration status                                               │
│ ┌──────────────────────────────────────────────────────────────┐ │
│ │ ✅ API key created                                             │ │
│ │ ✅ Test user created                                           │ │
│ │ ⏳ Waiting for first event                                     │ │
│ │ ⏳ Waiting for first retrieve                                  │ │
│ └──────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
```

### 5.1.4 Memory Policy 配置页（V0.1 单页默认）

**出现场景**：客户配置记忆策略。
**P0 要求**：
- V0.1 只提供单一默认 Policy，单页配置（不做版本管理，P1）。
- 修改 Production Policy 必须二次确认。
- 所有策略变更写 Audit Log。
- Sandbox policy 和 production policy 内置分离（不同 API key）。

**ASCII 线框**：
```
┌──────────────────────────────────────────────────────────────────┐
│ Memory Policy: Default                                           │
├──────────────────────────────────────────────────────────────────┤
│ Auto-write                                                       │
│ ┌───────────────────────┬─────────────┬─────────────┬────────┐ │
│ │ Memory Type            │ Action      │ Sensitivity │ TTL    │ │
│ ├───────────────────────┼─────────────┼─────────────┼────────┤ │
│ │ User preference        │ Auto write  │ Low         │ Never  │ │
│ │ Relationship memory    │ Auto write  │ Medium      │ Never  │ │
│ │ Event memory           │ Auto write  │ Low         │ 180d   │ │
│ │ Boundary / dislike     │ Auto write  │ Medium      │ Never  │ │
│ │ Health / mental state  │ Confirm     │ High        │ 90d    │ │
│ │ Minor-related memory   │ Block       │ Critical    │ N/A    │ │
│ │ Financial info         │ Confirm     │ High        │ 90d    │ │
│ └───────────────────────┴─────────────┴─────────────┴────────┘ │
│                                                                  │
│ Portability（V0.1 关键新增）                                       │
│ ┌───────────────────────┬────────────────────────────────────┐ │
│ │ 跨设备（品牌内）         │ ☑ Allowed                          │ │
│ │ 跨角色（品牌内）         │ ☑ Allowed                          │ │
│ │ 跨模型（LLM 中立）       │ ☑ Allowed（护城河轴，默认开）         │ │
│ │ 跨品牌 App（Luna→竞品）  │ ☐ Disabled（P2/P3 解锁）            │ │
│ └───────────────────────┴────────────────────────────────────┘ │
│                                                                  │
│ Retrieval                                                        │
│ Max memories per response [ 8 ]                                  │
│ Sensitive memories in prompt: [ Never unless confirmed ▾ ]       │
│                                                                  │
│                    [Save]            [Publish Policy]             │
└──────────────────────────────────────────────────────────────────┘
```

### 5.1.5 Users（合并原 Debugger + End Users）

**出现场景**：客服处理用户投诉 / 客户运营查看记忆效果 / 审计终端用户。
**IA 决策**：原 draft 把 Debugger 和 End Users 拆成两个 tab——冗余。用户是实体，记忆是用户的子属性（Intercom/Stripe 模式）。合并为单一 "Users" 页面，master-detail 全宽布局。
**P0 要求**：
- 顶部内联用户切换 Select（可按 name / passport_id / external_user_id 搜索）。
- 用户头部：avatar + passport_id（mono）+ age_group + Memory ON/OFF + 记忆数 + region + joined。
- 记忆表格全宽（Status / Type / Content / Scope / Portability / Used / Actions）。
- **点击表格任意行 → 右侧 Sheet 滑出 Memory Trace**（不跳页，表格上下文不丢）。
- 默认隐藏高敏感内容（S3 显示 `••••• masked`），查看需 elevated permission。
- 每次查看用户记忆都写 Audit Log。不能成为内部员工偷窥工具。
- Actions 菜单（⋮）：View source / Open trace / Edit / Archive / Delete。

**ASCII 线框**：
```
┌──────────────────────────────────────────────────────────────────┐
│ Users  [🔒 elevated]                                              │
│ End users and their memories. Select a user to inspect...        │
├──────────────────────────────────────────────────────────────────┤
│ ┌── 用户头部 ─────────────────────────────────── [All types ▾] ┐ │
│ │ (MC) Mia Chen [▾]  pp_4f2a8c91e3  [adult] [Memory ON]         │ │
│ │      42 memories · region US · joined 25 days ago              │ │
│ ├────────────────────────────────────────────────────────────────┤ │
│ │ Status │Type │Content                  │Scope│Portable│Used│ ⋮ │ │
│ │ ●Active│Pref│You prefer calm replies… │Rel  │✓ Port │47×│ ⋮ │ │
│ │ ●Active│Rel │You call this "Luna"     │Rel  │✓ Port │312│ ⋮ │ │
│ │ ◐Review│Event│Home desk is on left    │Dev  │✕ Local│2×│ ⋮ │ │
│ │ ●Active│Bdry│Don't discuss work 10pm  │Rel  │✓ Port │44×│ ⋮ │ │
│ └────────────────────────────────────────────────────────────────┘ │
│ 🔒 Sensitive content masked. Every view writes the audit log.    │
│    external_user_id customer-owned · passport_id ownership anchor │
└──────────────────────────────────────────────────────────────────┘
         点击任意行 ↓
                                    ┌── Memory trace（右侧 Sheet）──┐
                                    │ mem_001                        │
                                    │ ┌ Request ────────────────────┐│
                                    │ │ User Mia · Agent 🌙 Luna    ││
                                    │ │ Model: [🤖 gpt-4o]  Time …  ││ ← 跨模型标注
                                    │ ├ User message ───────────────┤│
                                    │ │ "how should I talk tonight?"││
                                    │ ├ Retrieved (3) ──────────────┤│
                                    │ │ 1 You prefer calm… high ✓   ││
                                    │ │ 2 Don't discuss work… high ✓││
                                    │ ├ Projection ─────────────────┤│
                                    │ │ Relevant memories: - … - …  ││
                                    │ ├ Feedback ───────────────────┤│
                                    │ │ [Useful][Not][Wrong][No]    ││
                                    │ ├ Cross-model parity ─────────┤│
                                    │ │ gpt-4o ✓ used · claude ✓    ││
                                    │ └──────────────────────────────┘│
                                    └────────────────────────────────┘
```

**关键交互**：
- Trace 是**右侧 Sheet 抽屉**（非新页面），保持表格可见，可连续审查多条。
- Trace 显式标注 `Model: gpt-4o` + Cross-model parity 表 —— 跨模型护城河的可观测性基础。

### 5.1.6（已合并入 5.1.5）

原独立 Memory Trace 页已合并为 Users 页的右侧 Sheet（见 5.1.5）。Trace 内容不变：Request(Model 标注) / User message / Retrieved memories / Projection / Feedback / Cross-model parity。

### 5.1.7 Devices（迁移生命周期优先）

**出现场景**：硬件/混合客户管理设备代际与记忆迁移。
**IA 决策**：原 draft 把 Devices 做成"设备台账"（哪些已激活/绑定给谁）——资产盘点思维，客户不买 MP 是为了盘点。客户买 MP 是为了 **wedge（跨代迁移）**。所以页面以"迁移生命周期"为主线，设备 registry 降为支撑信息。
**P0 要求**：
- **顶部 Health tiles**：Migration success %、Memory retention %、Devices bound、Resale-safe wipes（硬件客户关心的运营指标）。
- **Generation upgrade path**（核心可视化）：v1 → migration engine（portable ✓ travels / device-local ✕ stays）→ v2，状态随当前 migration 实时更新（current/awaiting/active）。
- **Recent migrations** 表：User / Source / Target / Memories moved / Status / Actions(Retry/Export)。
- **Device registry**（降级为支撑）：Model / Gen / Serial / Status(Bound/Registered/Unbound/Wiped) / Bound user / Last seen。
- 当前 migration 完成时，对应行高亮 + upgrade path 卡片显示继承结果。

**ASCII 线框**：
```
┌──────────────────────────────────────────────────────────────────┐
│ Devices  [hybrid]                                                │
│ How memories move across device generations. The wedge.          │
├──────────────────────────────────────────────────────────────────┤
│ ┌────────────┐┌────────────┐┌────────────┐┌────────────┐        │
│ │Migration   ││Memory      ││Devices     ││Resale-safe │        │
│ │success 98% ││retention98%││bound    2  ││wipes     3 │        │
│ └────────────┘└────────────┘└────────────┘└────────────┘        │
│                                                                  │
│ ┌─ Generation upgrade path ─────────────────── [Preview a migration] ┐
│ │ ┌─────────────┐    ┌──────────────┐    ┌─────────────┐          │
│ │ │ Luna v1     │ →  │ Migration    │ →  │ Luna v2     │          │
│ │ │ Current     │    │ engine       │    │ Awaiting    │          │
│ │ │             │    │ portable ✓   │    │             │          │
│ │ └─────────────┘    │ local   ✕    │    └─────────────┘          │
│ │                    └──────────────┘                             │
│ └──────────────────────────────────────────────────────────────────┘
│                                                                  │
│ Recent migrations                                                │
│ ┌──────────┬──────┬──────┬───────┬──────────┬────────┬─────────┐ │
│ │ User     │ Src  │ Tgt  │ Moved │ Status   │ Time   │ Actions │ │
│ ├──────────┼──────┼──────┼───────┼──────────┼────────┼─────────┤ │
│ │ Mia Chen │ v1   │ v2   │  31   │ Completed│ today  │ ⋮ Retry │ │
│ │ Alex R.  │ v1   │ v2   │  28   │ Completed│ 2d ago │ ⋮       │ │
│ │ Sam O.   │ v1   │ v2   │  12   │ Failed   │ 5d ago │ ⋮ Retry │ │
│ └──────────┴──────┴──────┴───────┴──────────┴────────┴─────────┘ │
│                                                                  │
│ Device registry                                                  │
│ ┌────────────┬──────┬──────────┬───────────┬──────────┬─────────┐│
│ │ Model      │ Gen  │ Serial   │ Status    │ Bound    │ Last    ││
│ ├────────────┼──────┼──────────┼───────────┼──────────┼─────────┤│
│ │ Luna Robot │ v2   │ b8c1…    │ Registered│ —        │ —       ││
│ │ Luna Robot │ v1   │ a4f2…    │ Bound     │ Mia Chen │ 2h ago  ││
│ └────────────┴──────┴──────────┴───────────┴──────────┴─────────┘│
└──────────────────────────────────────────────────────────────────┘
```

**Devices 模块对不同产品形态的价值**：
- **纯软件客户**（如 Character.AI）：几乎不用，可在 Policy 里隐藏；软件客户端无"设备"概念。
- **硬件/混合客户**（如 Luna Robot）：核心模块。价值 = ① 迁移监控（wedge 的运营后台）；② 转售/回收合规（unbind/wipe 状态，二手买家不能看到前任主人记忆）。

## 5.2 Embedded User UI

> **AppShell 模式**：所有 C 端页面共享 AppShell —— 手机宽度居中（max-w-md）、暖纸 `.paper-surface`（强制浅色，无视站点主题）、顶部 app-style header（返回 + 标题 + 溢出菜单）、底部 **Powered by Memory Passport 水印**（每屏必有，网络效应种子）。

### 5.2.1 记忆授权页（带 Powered by 联名）

**出现场景**：
- 用户首次启用 AI companion。
- 用户首次绑定机器人。
- 用户开启长期记忆。
- 用户迁移记忆到新设备。

**P0 要求**：
- 用户必须能拒绝；拒绝后产品仍可用，但没有长期记忆。
- 客户可以白标文案，但不得隐藏"可查看/可删除/可关闭"。
- **必须显示 "Powered by Memory Passport"**——这是用户认知"记忆属于我"的种子。

**ASCII 线框**：
```
┌──────────────────────────────────────────────┐
│ Luna can remember you                         │
├──────────────────────────────────────────────┤
│ Luna can save helpful memories so future      │
│ conversations feel more continuous.            │
│                                               │
│ What Luna may remember:                       │
│ ✓ Your preferences                            │
│ ✓ Important things you tell Luna              │
│ ✓ Boundaries, dislikes, and reminders         │
│                                               │
│ What Luna will not save by default:           │
│ ✕ Sensitive health or financial info          │
│ ✕ Temporary chats                             │
│ ✕ Anything you delete                         │
│                                               │
│ Your memories belong to you, not Luna.        │
│ You can view, edit, or delete anytime.        │
│                                               │
│ [Not now]                         [Turn on]   │
│                                               │
│ ─────────────────────────────────────────     │
│ Powered by Memory Passport                    │
└──────────────────────────────────────────────┘
```

### 5.2.2 聊天内记忆写入提示（仅敏感/高影响）

**出现场景**：敏感或高影响记忆写入前确认。**不用于普通低敏记忆**（普通记忆自动写入，否则 companion 体验会变差）。
**P0 要求**：
- 普通低敏记忆自动写入。
- 敏感记忆必须确认。
- 用户可编辑后保存。
- 用户选 Don't save 后，该候选记忆丢弃，不再反复提醒。

**ASCII 线框**：
```
┌──────────────────────────────────────────────┐
│ Luna                                         │
│ I'll keep that in mind.                      │
│                                               │
│ ┌──────────────────────────────────────────┐ │
│ │ Save this memory?                         │ │
│ │ "You prefer quiet check-ins after 10pm."  │ │
│ │                                          │ │
│ │ [Don't save] [Edit] [Save]               │ │
│ └──────────────────────────────────────────┘ │
└──────────────────────────────────────────────┘
```

### 5.2.3 Memory Center 首页

**出现场景**：用户主动管理 AI 记住了什么。
**P0 要求**：
- 用户能搜索、按类型筛选。
- 用户能暂停长期记忆。
- 用户能进入设备管理、导出、删除全部。
- 顶部显示记忆状态 + "记忆属于你"提示。

**ASCII 线框**：
```
┌──────────────────────────────────────────────┐
│ Memory Center                                │
├──────────────────────────────────────────────┤
│ Memory is ON                         [Pause] │
│ Luna remembers 42 things about you.           │
│ These memories belong to you.                 │
│                                               │
│ Search memories                              │
│ ┌──────────────────────────────────────────┐ │
│ │ Search                                   │ │
│ └──────────────────────────────────────────┘ │
│                                               │
│ Categories                                   │
│ [Preferences 12] [Relationship 8] [Events 9] │
│ [Boundaries 4] [Tasks 6] [Archived 3]        │
│                                               │
│ Recent memories                              │
│ ┌──────────────────────────────────────────┐ │
│ │ You prefer calm replies at night.     ⋯  │ │
│ │ Source: chat, Jun 12                     │ │
│ ├──────────────────────────────────────────┤ │
│ │ You call this companion "Luna."       ⋯  │ │
│ │ Source: setup, Jun 10                    │ │
│ ├──────────────────────────────────────────┤ │
│ │ Don't discuss work after 10pm.        ⋯  │ │
│ │ Source: explicit instruction             │ │
│ └──────────────────────────────────────────┘ │
│                                               │
│ [Devices] [Export] [Delete all memory]        │
│                                               │
│ ─────────────────────────────────────────     │
│ Powered by Memory Passport                    │
└──────────────────────────────────────────────┘
```

### 5.2.4 Memory Detail

**出现场景**：用户点击单条记忆查看详情。
**P0 要求**：
- 每条记忆必须解释来源（Why was this saved?）。
- 用户能编辑、删除、举报错误。
- 展示"哪些 agent / device 可以用"+ portability 标记。

**ASCII 线框**：
```
┌──────────────────────────────────────────────┐
│ Memory Detail                                │
├──────────────────────────────────────────────┤
│ Memory                                       │
│ ┌──────────────────────────────────────────┐ │
│ │ You prefer calm replies at night.         │ │
│ └──────────────────────────────────────────┘ │
│                                               │
│ Type: Preference                              │
│ Scope: Luna only                              │
│ Portability: Portable (跨设备/跨角色/跨模型)   │
│ Confidence: High                              │
│ Created: Jun 12, 2026                         │
│ Last used: Today                              │
│                                               │
│ Why was this saved?                           │
│ You explicitly told Luna:                     │
│ "At night I prefer calmer replies."           │
│                                               │
│ Used by                                      │
│ ✓ Luna iOS App                                │
│ ✓ Luna Robot v1                               │
│                                               │
│ [Edit] [Delete] [Report wrong]                │
└──────────────────────────────────────────────┘
```

**注意 Portability 字段**：用户能看到这条记忆是 Portable（可携带）还是 Device-local（设备本地）。这是"记忆属于我、可以跟我走"的产品化表达。

### 5.2.5 Device Management

**出现场景**：用户管理使用自己记忆的设备。
**P0 要求**：展示当前设备、最近活跃、访问范围；支持绑定新设备、解绑。

**ASCII 线框**：
```
┌──────────────────────────────────────────────┐
│ Devices using your memory                    │
├──────────────────────────────────────────────┤
│ Current devices                              │
│                                               │
│ ┌──────────────────────────────────────────┐ │
│ │ Luna Robot v1                            │ │
│ │ Last active: 2 hours ago                 │ │
│ │ Access: Relationship + Preferences       │ │
│ │ [Manage] [Unbind]                        │ │
│ ├──────────────────────────────────────────┤ │
│ │ iPhone App                               │ │
│ │ Last active: now                         │ │
│ │ Access: All Luna memories                │ │
│ │ [Manage]                                 │ │
│ └──────────────────────────────────────────┘ │
│                                               │
│ [Bind new device]                             │
└──────────────────────────────────────────────┘
```

### 5.2.6 机器人绑定页（QR / pairing code）

**出现场景**：用户绑定新机器人。
**P0 要求**：扫码或输入配对码；绑定后调用 Device Bind API。

**ASCII 线框**：
```
┌──────────────────────────────────────────────┐
│ Bind your new robot                          │
├──────────────────────────────────────────────┤
│ Scan the QR code shown on your robot screen. │
│                                               │
│ ┌──────────────────────────────────────────┐ │
│ │                Camera                    │ │
│ │                                          │ │
│ │              [ QR area ]                 │ │
│ │                                          │ │
│ └──────────────────────────────────────────┘ │
│                                               │
│ Or enter pairing code                         │
│ ┌──────────────────────────────┐ [Continue]  │
│ │  8-digit code                 │             │
│ └──────────────────────────────┘             │
└──────────────────────────────────────────────┘
```

### 5.2.7 迁移预览页：v1 → v2（楔子验证页）

**出现场景**：用户购买 v2 机器人，扫描后发现已有 v1 relationship memory。
**P0 要求**：
- 迁移不是全量复制；必须展示 recommended / needs review / not moved。
- 用户可取消勾选。
- 用户可决定旧设备权限（保留/降权/移除）。
- 完成后写 Audit Log。
- **这是 V0.1 楔子的核心体验页**——"Upgrade the body, keep the relationship" 的具象化。

**ASCII 线框**：
```
┌──────────────────────────────────────────────┐
│ Move memories to Luna Robot v2               │
├──────────────────────────────────────────────┤
│ Source: Luna Robot v1                         │
│ Target: Luna Robot v2                         │
│                                               │
│ We found 38 memories that can be moved.       │
│ Please review before continuing.              │
│                                               │
│ Recommended (Portable)                        │
│ ☑ You call this robot "Luna"                  │
│ ☑ You prefer quiet mode after 10pm            │
│ ☑ You dislike morning wake-up reminders       │
│                                               │
│ Needs review                                  │
│ ☐ Your home desk is on the left side          │
│ ☐ You often place your cup near the desk      │
│                                               │
│ Not moved (Device-local)                      │
│ ✕ v1 sensor calibration                       │
│ ✕ temporary task: remind tomorrow             │
│                                               │
│ After migration                               │
│ ○ Keep v1 access                              │
│ ● Remove v1 access after v2 is ready          │
│                                               │
│ [Cancel]                         [Move 31]    │
└──────────────────────────────────────────────┘
```

**关键设计**：迁移预览页**显式区分 Portable（可迁移）vs Device-local（不迁移）**——这是 portable-native 数据模型在用户侧的具象化，也是"为什么有些记忆跟不了你走"的诚实表达。

**Bucket 折叠交互**：三个 bucket 是可折叠的 Card；标题行整体可点击（`role="button"`，键盘可达），"Select all" 作为标题内的独立按钮（避免 button-in-button 无效 HTML）。底部 `[Move N]` 是 sticky CTA，N 随选择实时更新。

### 5.2.8 迁移完成页

**出现场景**：迁移执行完成。
**P0 要求**：展示 moved/skipped/old device access；给出 v2 首次对话的预期（让用户感受到"她还记得我"）。

**ASCII 线框**：
```
┌──────────────────────────────────────────────┐
│ Memories moved                               │
├──────────────────────────────────────────────┤
│ Luna Robot v2 can now use your approved       │
│ memories.                                    │
│                                               │
│ Moved: 31 memories                            │
│ Skipped: 7 memories                           │
│ Old device access: Removed                    │
│                                               │
│ Luna v2 may say:                              │
│ "I still remember you call me Luna, and I'll  │
│ keep quiet after 10pm."                       │
│                                               │
│ [View memories]                 [Done]        │
└──────────────────────────────────────────────┘
```

### 5.2.9 删除全部记忆确认页

**出现场景**：用户请求删除全部记忆。
**P0 要求**：
- 必须明确删除范围。
- 必须说明是否删除客户自己的聊天记录。
- 删除后 MP 不再返回这些记忆。
- 删除请求写入 tombstone，确保其他设备同步删除。

**ASCII 线框**：
```
┌──────────────────────────────────────────────┐
│ Delete all memories?                         │
├──────────────────────────────────────────────┤
│ This will delete Luna's long-term memories    │
│ about you from this app and connected devices.│
│                                               │
│ Deleted memories will no longer be used in    │
│ future conversations.                         │
│                                               │
│ This does not delete your account or chat     │
│ history stored by [Customer App], unless      │
│ that app says otherwise.                      │
│                                               │
│ Type DELETE to confirm                        │
│ ┌──────────────────────────────────────────┐ │
│ │                                          │ │
│ └──────────────────────────────────────────┘ │
│                                               │
│ [Cancel]                     [Delete forever] │
└──────────────────────────────────────────────┘
```

## 5.3 空状态、错误状态、边界场景

### 5.3.1 End User 空状态（无记忆）

```
┌──────────────────────────────────────────────┐
│ Memory Center                                │
├──────────────────────────────────────────────┤
│ No memories yet                              │
│                                               │
│ Luna will save helpful memories as you chat,  │
│ if memory is turned on.                       │
│                                               │
│ [How memory works]                            │
└──────────────────────────────────────────────┘
```

### 5.3.2 Admin 空状态（未发事件）

```
┌──────────────────────────────────────────────┐
│ No memory events yet                         │
├──────────────────────────────────────────────┤
│ Send your first ingest event to create a      │
│ memory candidate.                             │
│                                               │
│ [Open Quickstart] [Run sample event]          │
└──────────────────────────────────────────────┘
```

### 5.3.3 错误状态覆盖

| 场景 | UI / 系统处理 |
|---|---|
| API key 错误 | 返回 401 + Quickstart 指向 |
| user_id 不存在 | 自动创建或返回明确错误（由客户配置） |
| memory policy 阻止写入 | 返回 blocked_reason |
| retrieve 无结果 | 返回 empty projection，不报错 |
| 设备离线 | 本地缓存可用，恢复后同步（P1 edge cache） |
| 删除同步失败 | 重试 + dashboard alert |
| 迁移失败 | 展示失败原因，可 retry / rollback |
| 冲突记忆 | needs_review，用户或客户裁决（V1.1 完整；V0.1 标记后人工处理） |
| 敏感记忆误写 | 自动标记 + 通知客户处理 |
| 用户关闭记忆 | ingest 不写长期记忆，retrieve 由策略决定是否继续读旧记忆 |
| 跨模型检索不一致 | Trace 标注 + Cross-Model Parity 指标暴露（V0.1 监控，不自动修复） |

---

# Part 6 — 核心客户流程

V0.1 聚焦 6 条核心流程（精简自 draft 的 7 条，合并 B 端 offboarding 到 P1）。

## Flow A：B 端客户从注册到跑通 Sandbox（2 小时 demo）

**目标**：客户 2 小时内完成 demo，看到"用户说过一次，下一轮 AI 真的记得"。

**流程**：
```
客户注册 → 创建 Tenant → 创建 App → 选择产品类型
  → 创建 Agent → 复制 SDK key → 发送第一条 ingest event
  → 调用 retrieve → 在 Test Console 看到记忆被生成和召回
```

**UI 触点**：Landing `/` → Console → Create App `/console/apps/new` → Get started `/console/quickstart`（Run Test Event / Retrieve 实时打勾）→ Users `/console/memory/users`（看记忆 + 点行开 Trace Sheet）
**API 触点**：
```
POST /v1/apps
POST /v1/agents
POST /v1/users
POST /v1/relationships
POST /v1/events/ingest
POST /v1/memories/retrieve
GET  /v1/debug/traces/{trace_id}
```

**验收标准**：
- 客户不需要销售介入也能跑通 sandbox。
- Get started 页面显示实时接入状态（checklist 随操作打勾，Overview 横幅同步）。
- Test Event 能生成一条候选记忆（写入 store）。
- Retrieve 能返回这条记忆。
- Users 页能看到记忆列表，点行能在 Trace Sheet 里看到来源、状态、Model 标注、projection。

## Flow B：软件 companion 接入（跨角色为卖点）

**典型客户**：AI 恋人 / 朋友 / 角色平台 / 心情陪伴 / AI 宠物软件。

**终端用户流程**：
```
用户打开客户 App → 客户 App 创建/登录用户
  → 调用 MP 创建 End User → 用户选择 AI 角色 → 创建 Relationship
  → 展示记忆授权页（Powered by Memory Passport）
  → 用户开启记忆 → 用户聊天
  → 客户 App 将对话事件传入 ingest → MP 抽取候选记忆
  → 低敏自动写入，高敏要求确认 → 下一轮聊天前 retrieve
  → 客户 App 将相关记忆注入模型上下文 → AI 回复更连续
```

**软件线主卖点**：用户在 Luna 的多个 AI 角色（恋人/教练/宠物）共享关于用户的核心记忆（偏好/边界），但各自有独立 relationship memory。

**客户侧集成点**：

| 集成点 | 客户要做什么 | 我们提供什么 |
|---|---|---|
| 用户登录 | 传 external_user_id | User Sync API |
| 角色创建 | 传 agent_id / persona | Agent API |
| 对话前 | retrieve relevant memories | Retrieve API |
| 对话后 | ingest transcript / events | Ingest API |
| 用户控制 | 嵌入 Memory Center | Embedded UI |
| 敏感确认 | 展示 confirmation component | React Component |
| 删除导出 | 调用 deletion / export | Privacy API |

## Flow C：机器人 / 硬件客户接入（v1→v2 跨世代为卖点）

**典型客户**：陪伴机器人 / AI pet / 桌面机器人 / 家庭机器人 / 仿生机器人 OEM。

**设备首次激活流程**：
```
用户收到机器人 → 机器人显示 QR code / pairing code
  → 用户打开客户 App 扫码 → 客户 App 调用 Device Bind
  → MP 建立 device_id 与 user_id 绑定 → 用户授权机器人使用记忆
  → 系统创建 Relationship → 机器人开始读取 Memory View
  → 机器人与用户互动 → 互动事件进入 ingest → 长期记忆沉淀
```

**API 触点**：
```
POST /v1/devices/register
POST /v1/devices/bind
POST /v1/relationships
POST /v1/consents
POST /v1/events/ingest
POST /v1/memories/retrieve
```

**设备状态机**（V0.1 子集）：

| 状态 | 含义 | 可读记忆 |
|---|---|---|
| unregistered | 设备未注册 | 不可读 |
| registered | 出厂注册 | 不可读用户记忆 |
| pairing | 等待用户绑定 | 不可读 |
| bound | 用户已绑定 | 可按授权读取 |
| unbound | 用户解绑 | 不可读 |
| wiped | 已清除 | 不可读 |
| repair_mode | 维修模式（P1） | 默认不可读 |
| transferred | 二手转让（P1） | 新用户重新绑定 |

## Flow D：v1 机器人升级到 v2（楔子验证点）

**目标**：让硬件客户把"换代"变成产品卖点——"Upgrade the body, keep the relationship."

**用户流程**：
```
用户购买 v2 → 打开客户 App → 扫描 v2 机器人二维码
  → 系统发现用户已有 v1 relationship memory → 生成迁移预览
  → 用户选择迁移哪些记忆 → 用户决定旧设备权限
  → 执行迁移 → v2 获得新 Memory View → v1 被解绑/降权/保留
  → v2 首次对话使用继承记忆
```

**迁移规则**：

| 记忆类型 | 默认迁移 | 说明 |
|---|---|---|
| 用户称呼 | 是 | Portable，低风险 |
| 互动偏好 | 是 | Portable，低风险 |
| 长期边界 | 是 | Portable，对体验和安全重要 |
| 关系历史 | 是 | Portable，核心价值 |
| 未完成任务 | 视情况 | 过期则不迁移 |
| 设备传感器校准 | 否 | Device-local，不迁移 |
| 临时聊天 | 否 | temporary |
| 敏感记忆 | 需确认 | 高风险，单独确认 |
| 空间记忆 | P1 | V0.1 只预留 schema |

## Flow E：用户查看、编辑、删除记忆

**用户流程**：
```
用户打开 Memory Center → 查看 AI 记住了什么 → 点击某条记忆
  → 查看来源和使用范围 → 编辑/删除/举报错误
  → MP 更新状态 → 相关 agent/device 不再使用旧版本
  → Audit Log 记录操作
```

**状态变化**：

| 用户动作 | Memory Record 状态 |
|---|---|
| 编辑 | old archived, new active |
| 删除 | deleted + tombstone |
| 举报错误 | flagged_wrong |
| 暂停记忆 | user memory_enabled=false |
| 临时模式 | current session not persisted |

## Flow F：客服处理用户投诉

**场景**：用户说"AI 记错了，我从来没说过这个。"

**客服流程**：
```
客服进入 Users（/console/memory/users）→ 顶部 Select 切换/搜索用户 → 查看记忆表格
  → 点击任意行 → 右侧 Trace Sheet 滑出 → 查看 source / Model 标注 / projection
  → 判断是写入错、检索错、还是模型误用
  → Actions: Archive / Delete / Correct → 系统同步更新 → 回复用户
```

**客服权限要求**（V0.1 最小）：
- 默认不能看敏感内容。
- 查看敏感内容需要 elevated permission（Admin 角色或临时提权）。
- 所有查看动作写 Audit Log。
- 客服只能处理自己 tenant 的用户。

---

# Part 7 — 核心功能需求

> P0 = V0.1 必须交付；P1/P2/P3 留档，不在 V0.1。

## 7.1 Tenant / App 管理

| 功能 | P0 | 描述 |
|---|---|---|
| 创建 Tenant | ✓ | 每个客户一个独立 tenant |
| 创建 App | ✓ | 一个客户可有多个 app |
| Sandbox / Production | ✓ | 环境隔离 |
| API Key | ✓ | 分环境发放，可轮换 |
| Team Members | ✓ | Owner / Admin / Support 三角色 |
| Branding | P1 | 白标 logo/颜色/文案（V0.1 默认联名） |

**验收标准**：Sandbox 数据不能进入 Production；API Key 泄露后可轮换；Support 角色不能修改 policy。

## 7.2 End User Identity

V0.1 默认推荐 **Customer-owned identity**（客户传 external_user_id，我们不接管登录）。Hosted lightweight identity 留 P1（小客户/demo 用）。

**User 对象字段**：

| 字段 | 说明 |
|---|---|
| user_id | MP 内部 ID |
| tenant_id | 客户 ID |
| external_user_id | 客户侧用户 ID |
| age_group | adult / minor / unknown |
| region | 数据区域 |
| memory_enabled | 是否开启长期记忆 |
| passport_id | **V0.1 新增**：用户的 Passport 标识（强 passport 模型，记忆归属锚点） |
| created_at | 创建时间 |

## 7.3 Agent 管理

**Agent 类型**：character / companion / pet / robot / assistant。

**Agent 字段**：

| 字段 | 说明 |
|---|---|
| agent_id | Agent ID |
| name | 名字 |
| type | 类型 |
| persona_version | persona 版本 |
| memory_policy_id | 使用的 policy |
| allowed_memory_types | 可读取记忆类型 |
| projection_template | prompt 投射模板 |

## 7.4 Device 管理（楔子核心）

| 功能 | P0 | P1 |
|---|---|---|
| 注册设备型号 | ✓ | — |
| 设备激活 | ✓ | — |
| 用户绑定设备 | ✓ | — |
| 解绑设备 | ✓ | — |
| 设备维修模式 | — | ✓ |
| 设备擦除 | ✓（基础） | 完整 wipe |
| 设备换代迁移 | ✓（楔子核心） | — |

**Device 字段**：

| 字段 | 说明 |
|---|---|
| device_id | 设备 ID |
| model | 型号 |
| generation | v1 / v2 |
| serial_number_hash | 序列号哈希 |
| status | registered / bound / unbound / wiped |
| bound_user_id | 当前绑定用户 |
| last_seen_at | 最近在线 |

## 7.5 Relationship

Relationship 是 MP 的关键实体：某个用户和某个 AI 角色/机器人之间的长期关系。同一用户可能有 AI 恋人、AI 宠物、家庭机器人、工作助手——这些记忆不能全部混在一起。

**Relationship 字段**：

| 字段 | 说明 |
|---|---|
| relationship_id | 关系 ID |
| user_id | 用户 |
| agent_id | AI 角色 |
| device_id | 可选 |
| relationship_type | companion / pet / robot / assistant |
| memory_enabled | 是否开启 |
| created_at | 创建时间 |

## 7.6 Memory Record（portable-native 双层标记，V0.1 核心）

**数据结构**：
```json
{
  "memory_id": "mem_123",
  "tenant_id": "tenant_luna",
  "app_id": "app_luna",
  "passport_id": "pp_001",
  "user_id": "user_001",
  "relationship_id": "rel_001",
  "agent_id": "agent_luna",
  "device_id": "device_v1_optional",
  "type": "preference",
  "content": "User prefers calm replies at night.",
  "scope": "relationship_only",
  "sensitivity": "S1",
  "status": "active",
  "confidence": 0.91,
  "portability": {
    "layer": "portable",
    "cross_device": true,
    "cross_role": true,
    "cross_model": true,
    "cross_brand_app": false
  },
  "source": {
    "event_id": "evt_789",
    "source_type": "chat",
    "timestamp": "2026-07-04T10:00:00Z"
  },
  "valid_from": "2026-07-04T10:00:00Z",
  "expires_at": null,
  "version": 3,
  "supersedes": ["mem_099"],
  "last_used_at": "2026-07-04T18:12:00Z",
  "usage_count": 24,
  "model_provenance": {
    "created_by_model": "gpt-4o",
    "retrieval_history": [
      {"model": "gpt-4o", "used": true},
      {"model": "claude-3.5", "used": true}
    ]
  }
}
```

**关键设计**：
- `portability` 字段显式标记双层（portable / device_local）+ 四轴开关。V0.1 默认前三轴开、第四轴关。
- `passport_id` 锚定记忆归属（用户拥有）。
- `model_provenance` 记录记忆由哪个模型生成、被哪些模型检索用过——这是跨模型护城河的可观测性基础，也是 Cross-Model Retrieval Parity 指标的数据源。

**Memory Type**（V0.1 子集）：

| 类型 | 示例 | P0 |
|---|---|---|
| profile | 用户叫小林，住在上海 | ✓ |
| preference | 用户喜欢晚上轻松聊天 | ✓ |
| boundary | 不要叫用户全名 | ✓ |
| relationship | 用户把机器人叫 Luna | ✓ |
| event | 用户下周有面试 | ✓ |
| task | 明天提醒浇花 | ✓ |
| safety | 用户有高风险表达 | 限制 |
| spatial | 水杯常放在书桌右侧 | P2 |

**Scope**：user_global / relationship_only / agent_only / device_only / private / blocked。

**Sensitivity**：

| 等级 | 示例 | 默认动作 |
|---|---|---|
| S0 | 喜欢猫、喜欢轻松语气 | 自动写入 |
| S1 | 家庭成员、作息、城市 | 自动写入 + 可见 |
| S2 | 健康、财务、亲密关系 | 用户确认 |
| S3 | 未成年人、自伤、违法 | 阻止或安全流程 |

## 7.7 最小引擎（V0.1 Occam 核心）

### Ingest（最小抽取）

**输入来源（V0.1）**：Chat transcript / Voice transcript（文本）/ App event / Robot event（结构化）/ Manual "remember this"。**不收** Raw audio / Raw video / Spatial map（P2）。

**Ingest 流程（V0.1 简版）**：
```
Event received
  → 基础 PII / sensitive scan（V0.1 简版，深度扫描 P1）
  → Memory candidate extraction（V0.1 最小：显式事实 + 简单偏好/边界抽取；
    复杂抽取/consolidation/conflict 留 V1.1）
  → Classification（type / sensitivity / portability layer）
  → Policy evaluation（auto write / needs confirmation / block）
  → Store（portable-native 双层标记）
  → Emit webhook（最薄：memory.created / memory.needs_confirmation）
```

**Ingest API**：`POST /v1/events/ingest`

| 字段 | 说明 |
|---|---|
| user_id | 用户 |
| relationship_id | 关系 |
| agent_id | agent |
| device_id | 可选 |
| event_type | chat / voice_transcript / app_event / robot_event |
| content | 文本或结构化事件 |
| timestamp | 时间 |
| metadata | 业务元数据 |

### Retrieve（按 scope 检索）

**Retrieve 流程**：
```
客户即将调用模型 → 发送 current_context
  → MP 根据 user/agent/relationship/device 权限检索
  → 过滤敏感与过期记忆 → 排序 → 生成 Projection
  → 返回给客户
```

**Retrieve API**：`POST /v1/memories/retrieve`

| 输入字段 | 说明 |
|---|---|
| user_id | 用户 |
| relationship_id | 关系 |
| agent_id | agent |
| device_id | 可选 |
| current_context | 当前对话/任务 |
| max_memories | 最大返回条数 |
| sensitivity_limit | 可用敏感等级 |
| projection_format | plain / prompt / json |
| target_model | **V0.1 新增**：目标模型（用于跨模型 parity 追踪） |

**输出示例**：
```json
{
  "trace_id": "trace_123",
  "memories": [
    {
      "memory_id": "mem_1",
      "content": "User prefers calm replies at night.",
      "reason": "Relevant to current request about keeping tone light.",
      "confidence": 0.93
    }
  ],
  "projection": "Relevant memories:\n- User prefers calm replies at night."
}
```

### Projection（文本投影）

V0.1 只做 `prompt_block`（plain text 拼进 prompt）。其余类型（json_context / system_context / device_context / embedded_file）留 P1。

**Prompt 示例**：
```
Relevant long-term memories for this user:
- The user prefers calm, light conversations at night.
- The user calls this companion "Luna".
- The user does not want work topics after 10pm.
Use these memories only when relevant. Do not mention that you have memory unless natural.
```

## 7.8 Memory Control（用户控制）

用户必须能：
- 查看记忆
- 编辑记忆
- 删除记忆
- 举报错误
- 关闭长期记忆
- 开启临时模式
- 管理设备权限
- 导出记忆
- 删除全部记忆

## 7.9 Migration（楔子核心）

**Migration 对象**：

| 字段 | 说明 |
|---|---|
| migration_id | 迁移 ID |
| source_relationship_id | 来源关系 |
| target_relationship_id | 目标关系 |
| source_device_id | 来源设备 |
| target_device_id | 目标设备 |
| status | preview / confirmed / running / done / failed |
| selected_memory_ids | 用户选择 |
| skipped_memory_ids | 跳过 |
| audit_log_id | 审计 |

**API**：
```
POST /v1/migrations/preview
POST /v1/migrations/execute
GET  /v1/migrations/{id}
POST /v1/migrations/{id}/rollback
```

## 7.10 Audit Log / Webhook / Privacy API（V0.1 可运营最薄层）

### Audit Log（V0.1）
记录：memory access / memory delete / policy change / device binding / export / migration。每次查看用户记忆写一条。

### Webhook（V0.1 最薄）
| Event | 触发时机 |
|---|---|
| memory.created | 新记忆创建 |
| memory.needs_confirmation | 需要用户确认 |
| memory.deleted | 记忆被删除 |
| migration.completed | 迁移完成 |
| migration.failed | 迁移失败 |
| device.bound | 设备绑定 |
| device.unbound | 设备解绑 |

完整事件（memory.updated / memory.flagged_wrong / policy.updated）留 P1。

### Privacy API（V0.1）
```
POST /v1/exports        导出用户记忆
POST /v1/delete_user    删除用户全部记忆（写 tombstone，同步所有设备）
```

---

# Part 8 — API 总表

| API | 用途 | P0 | P1 | P2 |
|---|---|---|---|---|
| POST /v1/apps | 创建 App | ✓ | | |
| POST /v1/agents | 创建 Agent | ✓ | | |
| POST /v1/users | 创建/同步用户 | ✓ | | |
| POST /v1/relationships | 创建关系 | ✓ | | |
| POST /v1/devices/register | 注册设备 | ✓ | | |
| POST /v1/devices/bind | 绑定设备 | ✓ | | |
| POST /v1/devices/unbind | 解绑设备 | ✓ | | |
| POST /v1/events/ingest | 写入事件 | ✓ | | |
| POST /v1/memories/retrieve | 检索记忆 | ✓ | | |
| GET /v1/memories | 查看记忆 | ✓ | | |
| PATCH /v1/memories/{id} | 编辑记忆 | ✓ | | |
| DELETE /v1/memories/{id} | 删除记忆 | ✓ | | |
| POST /v1/migrations/preview | 迁移预览 | ✓ | | |
| POST /v1/migrations/execute | 执行迁移 | ✓ | | |
| GET /v1/migrations/{id} | 迁移状态 | ✓ | | |
| POST /v1/migrations/{id}/rollback | 回滚迁移 | ✓ | | |
| GET /v1/audit_logs | 审计日志 | ✓ | | |
| POST /v1/policies | 配置策略 | ✓ | | |
| GET /v1/usage | 使用量 | ✓（基础） | 完整报表 | |
| POST /v1/exports | 导出 | ✓ | | |
| POST /v1/delete_user | 删除用户记忆 | ✓ | | |
| GET /v1/debug/traces/{trace_id} | 检索 trace | ✓ | | |
| POST /v1/devices/wipe | 设备擦除 | ✓（基础） | 完整 | |
| POST /v1/devices/repair | 维修模式 | | ✓ | |
| POST /v1/devices/transfer | 二手转让 | | ✓ | |
| POST /v1/passport/export | **跨品牌 App 导出** | | | ✓ |
| POST /v1/passport/import | **跨品牌 App 导入** | | | ✓ |
| GET /v1/memory_health | 记忆健康度 | | ✓ | |
| POST /v1/webhooks/config | Webhook 配置 | | ✓ | |
| POST /v1/billing/plan | 计费套餐 | | ✓ | |

---

# Part 9 — 权限与安全

## 9.1 权限原则

| 原则 | 要求 |
|---|---|
| Tenant 隔离 | 不允许跨客户读取 |
| 用户归属 | 每条记忆必须绑定 passport_id + user_id |
| 关系隔离 | 不同 AI 角色默认不共享 relationship memory |
| 设备授权 | 设备绑定后才可读取 |
| 敏感遮罩 | 内部支持默认看不到敏感内容 |
| 可删除 | 删除后不可 retrieve（tombstone） |
| 可审计 | 查看、删除、迁移、导出都记录 |
| 跨模型中立 | 记忆以模型无关语义格式存，不绑死单一 LLM |

## 9.2 RBAC（V0.1 最小三角色）

| 角色 | V0.1 能做什么 | P1 扩展 |
|---|---|---|
| Owner | 全部权限 | — |
| Admin | 管理 app、policy、team | — |
| Support | 查询用户、处理错误记忆，不能改 policy | — |
| Developer | — | API key、logs、sandbox |
| Viewer | — | 看汇总指标 |
| Billing | — | 看账单，不看用户记忆 |

## 9.3 数据不用于训练

必须写进产品承诺和合同：**Memory Passport 不把客户用户数据卖给模型公司，不默认用于训练第三方模型。** 这条继承自 Shadow PRD 的硬约束——一边说数据归用户、一边卖数据会让信任崩塌。

## 9.4 跨模型 Embedding 可移植性（V0.1 架构要求）

为支持跨模型检索，V0.1 记忆存储**不以供应商专属 embedding 为主索引**：
- 主存储：语义文本 + 结构化字段
- Embedding：按需为各模型生成（缓存可复用部分），不绑死单一模型
- 跨模型检索 parity 通过 `model_provenance` 追踪，V0.1 监控不自动修复

---

# Part 10 — 状态机

## 10.1 Memory Record 状态机（V0.1）

```
candidate
  ↓ auto approve / user confirm
active
  ├── edit → archived + new active
  ├── conflict → needs_review（V0.1 标记后人工处理；V1.1 自动 consolidation）
  ├── user delete → deleted + tombstone
  ├── TTL expire → expired
  ├── low usage → archived（V1.1 自动；V0.1 手动）
  └── report wrong → flagged_wrong
```

## 10.2 Device 状态机（V0.1 子集）

```
registered
  ↓ user pairing
bound
  ├── user unbind → unbound
  ├── wipe → wiped
  └── transfer → transferred（P1）
repair_mode（P1）
```

## 10.3 Migration 状态机

```
draft
  ↓ preview generated
preview
  ↓ user confirm
running
  ├── success → completed
  ├── partial → completed_with_warnings
  └── fail → failed
        ↓
      retry / rollback
```

---

# Part 11 — 计费模型

## 11.1 V0.1 计费（手动，结构留档）

V0.1 不做计费 UI，手动出账单。但计费维度结构留档，为 P1 自动化做准备。

| 维度 | 说明 |
|---|---|
| Memory MAU | 每月有记忆读写的终端用户 |
| Memory Ops | ingest / retrieve / update / delete |
| Storage | 结构化记忆存储 |
| Device Activation | 每台激活设备 |
| Migration | 设备/角色迁移次数 |
| Enterprise Add-on | 私有化、BYOK、SLA、审计、白标（关闭联名溢价） |

## 11.2 套餐（P1 上线）

| 套餐 | 适合谁 | 包含 |
|---|---|---|
| Developer | 测试客户 | Sandbox、少量 MAU、基础 SDK、Powered by 联名 |
| Startup | AI companion app | Memory MAU、Embedded UI、Dashboard、Powered by 联名 |
| Hardware OEM | 机器人客户 | Device activation、migration、device dashboard |
| Enterprise | 大客户 | 私有化、BYOK、数据区域、SLA、审计、白标（关闭联名，溢价） |

---

# Part 12 — Roadmap

## 12.1 V0.1（0–12 周）：楔子 + 可运营最薄层

**目标**：跨设备连续性 end-to-end 跑通，客户能 pilot 不是只 demo。

**交付**：
- Tenant / App / API key（Sandbox/Prod 隔离）
- User / Agent / Relationship
- 最小引擎（最小抽取 Ingest / scoped Retrieve / text Projection）
- Memory Record（portable-native 双层标记 + model_provenance）
- Device register / bind / unbind / wipe（基础）
- Migration preview / execute / rollback（楔子核心）
- Memory Policy（单页默认 + portability 四轴开关）
- Users 页（合并 Debugger + End Users，master-detail + Trace Sheet 抽屉）
- Embedded Consent（Powered by 联名）+ Memory Center + Memory Detail
- Device Management + 机器人绑定（QR）
- v1→v2 迁移预览/完成
- Audit Log + 最薄 Webhook + 删除/导出 API
- 最小三角色 RBAC（Owner/Admin/Support）

**验收**：
- 客户 2 小时跑通 demo。
- 终端用户第二次回来，AI 正确记得上次重要信息。
- 用户能看见、改掉、删掉记忆。
- 用户换设备后，关系记忆能继承（v1→v2 demo 成功）。
- 客户能解释每条记忆从哪来、为什么被用、什么时候被删。
- 同一记忆可被至少 2 个模型检索（跨模型 parity 可观测）。

## 12.2 P1（V1.1，13–24 周）：完整引擎 + 运营化

- 完整抽取/consolidation/conflict resolution
- Memory Health 报表 + 自动 archive 建议
- Migration Dashboard 独立页
- 计费 UI + 套餐
- 完整 RBAC（Developer/Viewer/Billing）
- 完整 Webhook 事件
- Repair mode / 完整 wipe / 二手转让流程
- Policy 版本管理
- Robot SDK / Edge Agent
- Offline sync / edge cache

## 12.3 P2（V2.0，6–12 个月）：跨品牌 App 迁移（解锁护城河叙事）

- 跨品牌 App 迁移（passport/export + import）
- 用户主动升级为强 Passport 跨品牌携带
- Household memory / Room-object memory schema
- 空间记忆索引（语义 × 几何）
- iOS / Android 原生 SDK
- 私有化部署

## 12.4 P3（V3.0，1–2 年）：AI 关系征信局 + 多模态

- 多模态记忆（第一视角事件抽取、物体位置）
- 3D asset reference
- 眼镜/手机/机器人共享记忆
- 独立 C 端 Memory Passport 面（app/网页）
- AI 关系征信局形态：中立第三方持有用户关系记忆，任意 AI 凭用户授权读写

---

# Part 13 — 风险与缓解

| 风险 | 严重度 | 缓解 |
|---|---|---|
| **LLM 厂商原生记忆吃掉软件段** | 高 | 跨模型可携带性（中立层在模型间读）+ 机器人线（LLM 免疫）+ 合规/审计（模型记忆不可审计） |
| **B2B 抵触"用户拥有记忆"** | 高 | 机器人先行（记忆是 feature 不是 crown jewel）+ 嵌入式交付（app 保留用户关系）+ 数据证明"记忆属于用户"是信任红利（提升 engagement）+ Powered by 默认但 Enterprise 可关闭 |
| **跨模型 embedding portability 工程难度** | 中 | 语义存储为主 + 按需重算 embedding + model_provenance 追踪 parity；V0.1 监控不自动修复 |
| **双线 GTM 资源分散** | 中 | 共享同一引擎与 portable-native 数据模型；软件线快速迭代验证，机器人线慢但高单价 |
| **dogfood 风险（origin-ai 需求 ≠ B 端通用）** | 中 | dogfood 阶段刻意保持引擎通用性；定期用外部客户访谈校准 |
| **跨品牌 App 迁移叙事过早泄露吓跑 B2B** | 中 | V0.1 严格只讲 infra + 反锁定 + 跨设备；跨品牌 App 架构 ready 但叙事延后 P2 |
| **隐私/合规（未成年人、医疗边界）** | 中 | V0.1 默认 block 未成年相关；不做医疗/心理治疗场景；删除可证明（tombstone + audit） |
| **数据安全（凭证/PII 入库）** | 高 | 继承 Shadow 硬约束：绝不入库凭证、默认只存提炼后规则、上云前本地脱敏 |
| **"Powered by"联名被 B2B 拒绝** | 中 | Enterprise 白标溢价；中小客户用"信任红利"数据说服（用户更愿意开记忆） |

---

# Part 14 — 不重不漏检查表

## 14.1 B 端客户侧（V0.1）

| 流程 | 覆盖 | 对应模块 |
|---|---|---|
| 注册组织 | ✓ | Tenant |
| 创建 App | ✓ | Build/Apps |
| 创建 Agent | ✓ | 数据层（在 Users/Policy 上下文展示，无独立 nav） |
| 创建设备型号 | ✓ | Operate/Devices |
| 配置策略 | ✓ | Build/Policy |
| 复制 API key | ✓ | Build/Apps/[id] + Start/Get started |
| 跑通 Sandbox | ✓ | Start/Get started（实时 checklist） |
| 上线 Production | ✓ | API key（手动切换） |
| 查看使用量 | ✓ 基础 | Start/Overview |
| 处理用户投诉 | ✓ | Build/Users（Trace Sheet） |
| 查看记忆来源 | ✓ | Build/Users → 点行 → Trace Sheet |
| 删除用户记忆 | ✓ | Delete API + Users Actions |
| 导出用户记忆 | ✓ | Export API |
| 审计员工访问 | ✓ | Operate/Settings/Audit Log |
| 迁移设备 | ✓ | Operate/Devices（Recent migrations） |
| 预览迁移体验 | ✓ | Topbar [Preview as user] → Migration demo |
| 终止服务 | P1 | Offboarding（V0.1 手动） |

## 14.2 终端用户侧

| 流程 | 覆盖 | 对应 UI |
|---|---|---|
| 首次授权记忆 | ✓ | Consent |
| 拒绝记忆 | ✓ | Not Now |
| 开启记忆 | ✓ | Turn On |
| 聊天中产生记忆 | ✓ | Ingest |
| 敏感记忆确认 | ✓ | Confirmation Card |
| 查看记忆 | ✓ | Memory Center |
| 编辑记忆 | ✓ | Memory Detail |
| 删除单条记忆 | ✓ | Memory Detail |
| 删除全部记忆 | ✓ | Delete All |
| 关闭长期记忆 | ✓ | Pause / Off |
| 临时聊天 | ✓ | Temporary Mode |
| 查看设备 | ✓ | Devices |
| 绑定新设备 | ✓ | QR Pairing |
| 解绑旧设备 | ✓ | Device Management |
| v1 → v2 迁移 | ✓ | Migration Preview |
| 导出记忆 | ✓ | Export |
| 举报错误记忆 | ✓ | Report Wrong |

## 14.3 技术侧

| 流程 | 覆盖 | 对应能力 |
|---|---|---|
| 写入 | ✓ | Ingest |
| 抽取（最小） | ✓ | Memory Engine（最小） |
| 分类 | ✓ | Type / Sensitivity / Portability layer |
| 冲突处理 | V0.1 标记 / V1.1 自动 | needs_review |
| 检索 | ✓ | Retrieve |
| 投射 | ✓ | Projection（text） |
| 删除 | ✓ | Tombstone |
| 同步 | ✓ | Device sync（V0.1 基础） |
| 审计 | ✓ | Audit Log |
| Webhook | ✓（最薄） | Event system |
| 计费 | V0.1 手动 | Usage（基础） |
| 隔离 | ✓ | Tenant |
| 权限 | ✓（三角色） | RBAC |
| 可观测 | ✓ | Trace / Dashboard |
| 跨模型 parity | ✓（监控） | model_provenance |

---

# Part 15 — 团队执行口径

## 15.1 V0.1 一句话定义

> Memory Passport V0.1 只做一件事：让 B 端 AI companion / 机器人客户，用最小接入成本拥有**"用户拥有、跨设备连续、跨模型中立"的长期关系记忆**。

## 15.2 成功标准（5 条）

1. 客户 2 小时跑通 demo。
2. 终端用户第二次回来，AI 正确记得上次重要信息。
3. 用户能看见、改掉、删掉记忆，且知道"记忆属于我"。
4. 用户换设备后，关系记忆能继承（v1→v2 跑通）。
5. 同一记忆可被至少 2 个模型检索，parity 可观测（跨模型护城河的种子）。

## 15.3 产品心智

> **换设备，不换关系；换模型，不换记忆。**

AI 关系不会因为换手机、换机器人、换模型而丢失。Memory Passport 让用户的 AI 关系记忆成为可携带的、属于用户自己的长期资产——就像 Privy 让用户的钱包成为可携带的、属于用户自己的资产一样。

## 15.4 给团队的三条红线

1. **portable-native 从 Day 1 写进架构**——不二次构建。每条记忆必须标记 portable/device-local + 四轴开关。
2. **记忆属于用户**——passport_id 锚定归属，Powered by 联名是用户认知的种子，绝不隐藏"可查看/可删除/可关闭"。
3. **最小引擎**——V0.1 不做完整抽取/consolidation/conflict。只做楔子（跨设备）+ 可运营最薄层。其余全部 P1+。

---

## 附录 A：与原雏形的主要差异

| 维度 | 原雏形 V0.1 | 本版 V2.0 |
|---|---|---|
| 护城河 | 未明确 | 跨模型可携带性（model-neutral） |
| 楔子 | ~20 模块全 P0 | 跨设备连续性 end-to-end（唯一楔子） |
| 数据模型 | 单层 | portable-native 双层 + 四轴开关 + model_provenance |
| 账号模型 | 未明确（隐含弱/嵌入式） | 强 Passport（non-custodial，用户拥有）+ 嵌入式交付 |
| 跨品牌 App 迁移 | P3（19.1 说藏起来） | P2/P3（架构 ready，叙事延后；与护城河不矛盾，因为护城河是跨模型不是跨品牌App） |
| 品牌可见度 | 1.2 白标优先，Passport 后置 | Powered by 联名 V0.1 默认（网络效应种子） |
| 范围 | V1.5 体量 | V0.1 = 楔子 + 可运营最薄层（10-12 周） |
| LLM 威胁应对 | 未涉及 | 跨模型可携带性作为防御 |
| 三线 synergy | 仅引用 Shadow 原则 | 显式作为 GTM 防御工事 |

## 附录 B：未解决的开问题（V0.1 之后需验证）

1. 软件客户对"记忆属于用户 + Powered by 联名"的真实接受度（需签 3 个软件客户验证）。
2. 机器人 OEM 的销售周期实际长度（需接触 3-5 家头部机器人公司）。
3. 跨模型 embedding parity 的工程成本（V0.1 prototype 后评估）。
4. origin-ai dogfood 的通用性偏差程度（dogfood 3 个月后评估）。
5. "Powered by"联名对终端用户 engagement 的实际影响（A/B 测试）。

## 附录 C：原型对齐变更记录（2026-07-05）

本附录记录 PRD 与可交互原型（`/Users/jichuncai/MemoryPassport`）对齐时，相对原 V2.0 draft 的具体变更。**一切以原型实现为基准。**

| # | 变更 | 原因 | 影响章节 |
|---|---|---|---|
| 1 | **Console 导航重构**：5 模块平铺 → 3 分组（Start / Build / Operate） | 按用户旅程组织优于按功能模块平铺（Stripe/Vercel 模式） | Part 3.1, Part 4.1 |
| 2 | **Quickstart → "Get started"**，提升至 Start 组顶层 + Overview 嵌入实时横幅 | onboarding 是状态不是页面；横幅让客户不用"找" | Part 3.1, Part 4.1, Part 5.1.1, Part 5.1.3 |
| 3 | **Debugger + End Users 合并为单一 "Users"** | 用户是实体，记忆是子属性；拆两个 tab 是冗余 IA（Intercom/Stripe 模式） | Part 3.1, Part 4.1, Part 5.1.5 |
| 4 | **Memory Trace 从独立路由改为右侧 Sheet 抽屉** | 点击行不跳页、不丢上下文（Linear/Notion 模式），交互更丝滑 | Part 4.1, Part 5.1.5 |
| 5 | **Agents 不作为独立 nav 项** | Agent 存在于数据，在 Users/Policy 上下文展示即可 | Part 3.1, Part 4.1 |
| 6 | **Devices 重定位**：从"设备台账"改为"迁移生命周期"（health tiles + upgrade path + registry 降级） | 客户买 MP 是为了 wedge（跨代迁移），不是为了盘点资产 | Part 3.1, Part 4.1, Part 5.1.7 |
| 7 | **Topbar 新增 "Preview as user" 永久按钮** | Stripe "View as customer" 模式；wedge demo 的常驻入口，不再隐藏 | Part 3.1, Part 5.1.1 |
| 8 | **Overview 新增 onboarding 横幅 + migration demo 入口卡** | 让 onboarding 状态可见；wedge 入口在主区域常驻 | Part 5.1.1 |
| 9 | **新增落地页 `/`** | wedge 叙事 + 双面入口（build / experience）+ Privy 类比 + 四轴表 | Part 3.2 |
| 10 | **新增设计系统 "Ink & Paper"** | 自有视觉语言（ink `#1E3A8A` + 暖纸），借鉴 Anyway 纪律不照抄 token | Part 3.0 |
| 11 | **迁移 Bucket 折叠头改为 `role="button"` div** | 避免 button-in-button 无效 HTML（hydration error） | Part 5.2.7 |
| 12 | **C 端 AppShell 模式**：max-w-md + `.paper-surface` 强制浅色 + 底部水印 | 消费者体验始终温暖、可信，无视站点主题 | Part 5.2 |

**未变更**（战略与数据层保持稳定）：Part 0–2（战略）、Part 7（数据模型/API 字段）、Part 8（API 总表）、Part 9（权限）、Part 10（状态机）、Part 11（计费）、Part 12（Roadmap 优先级）、Part 13（风险）。

*本文档基于结构化访谈锁定战略后重写。所有战略决策（护城河/楔子/滩头堡/引擎/数据模型/账号/品牌）可追溯至 Part 0 的论证。UI/UX 线框图覆盖 V0.1 全部必要页面，P1/P2/P3 扩展点在各章节显式标注。*
