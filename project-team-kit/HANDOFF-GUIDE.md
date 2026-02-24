# Handoff Guide for Agent Team Adoption
# Agent 团队接入交接指南

**详细程度：极致细致**
**适用场景：单个 Agent 开发的项目交接给 4 人 Agent 团队**

---

## 目录 / Table of Contents

1. [什么时候需要交接？](#什么时候需要交接)
2. [交接前准备](#交接前准备)
3. [如何填写交接文件](#如何填写交接文件)
4. [完整交接流程](#完整交接流程)
5. [检查清单](#检查清单)
6. [常见问题](#常见问题)
7. [完整示例项目](#完整示例项目)

---

## 什么时候需要交接？

### 场景 A：你（单个 Agent）完成了某个阶段，需要 4 人团队接力

```
你可能的情况：
✓ 你一个人完成了原型开发
✓ 你用 Claude Code 写了一个完整的后端 API
✓ 你用 OpenCode 完成了一个前端页面
✓ 你用其他工具（如 Cursor、Windsurf）开发了项目的一部分
✓ 你的项目需要前后端分离开发
✓ 你的项目需要专业的测试

你需要交接给：
→ OpenClaw（项目经理）
→ OpenCode（前端开发)
→ Claude Code（后端开发）
→ Kimi Code（测试工程师）
```

### 场景 B：项目需要从单人开发升级为团队开发

```
现状：
- 项目越来越复杂
- 功能越来越多
- Bug 越来越难管理
- 代码质量需要保证

目标：
- 前后端分离开发
- 标准化的工作流
- 完善的测试
- 可维护的代码

交接给 4 人团队是最好的选择。
```

---

## 交接前准备

### Step 1: 确认你的项目状态 / Confirm Your Project Status

**问自己这些问题（非常重要）：**

```
1. 项目的主要功能是什么？
2. 项目的技术栈是什么？
3. 项目完成了哪些部分？
4. 项目有哪些未完成的部分？
5. 有哪些已知的 Bug？
6. 项目架构是怎样的？
7. 数据库设计了哪些表？
8. 有哪些 API 接口？
9. 前端有哪些页面/组件？
10. 有哪些特殊的配置或环境变量？
```

**把这些答案写在纸上或记事本里，后面填写的所有文件都会用到。**

---

### Step 2: 准备项目文件 / Prepare Project Files

**你需要准备这些信息：**

```
✓ 代码仓库地址（如果有的话）
✓ 项目的根目录路径
✓ 项目的启动命令
✓ 依赖说明（requirements.txt、package.json 等）
✓ 环境配置说明（.env.example）
✓ 数据库连接信息（不要泄露密码，可以用占位符）
```

---

### Step 3: 复制 Project Team Kit 到项目目录 / Copy Kit to Project

**Windows:**

```bash
# 打开命令提示符或 PowerShell
# 进入你的项目目录
cd C:\path\to\your-project

# 复制 Project Team Kit
copy C:\Users\Ywj\.openclaw\templates\project-team-kit\*.md .
```

**或者运行安装脚本：**

```bash
C:\Users\Ywj\.openclaw\templates\project-team-kit\install-project-kit.bat C:\path\to\your-project
```

**Linux/macOS:**

```bash
cd /path/to/your-project
cp ~/.openclaw/templates/project-team-kit/*.md .
```

---

## 如何填写交接文件

**重要提示：按照以下顺序填写，每一步都要仔细！**

---

### 文件 1: PROJECT-IDENTITY.md（项目身份）

**这个文件告诉团队：这是什么项目？**

---

#### 1.1 项目名称 / Project Name

```
填写格式：
[项目名称]

示例：
My Awesome E-commerce App
个人博客系统
在线聊天应用
```

---

#### 1.2 项目描述 / Project Description

```
填写格式（详细的描述）：
[这个项目解决什么问题？]
[主要功能有哪些？]
[目标用户是谁？]
[技术亮点是什么？]

示例：
一个现代化的电商网站，支持商品浏览、购物车、在线支付。
主要功能包括：用户注册登录、商品搜索、购物车管理、订单系统、支付集成。
目标用户是中小企业和独立卖家。
技术亮点：前后端分离架构，RESTful API 设计，支持多种支付方式。

更详细的示例：
这是一个基于 React + Node.js + PostgreSQL 的全栈电商平台。
前端使用 React 18 + TypeScript + Tailwind CSS，实现了响应式设计。
后端使用 Node.js + Express，提供了 RESTful API。
数据库使用 PostgreSQL，设计了订单、商品、用户、支付等核心表。
集成了支付宝和微信支付。
```

---

#### 1.3 项目目标 / Project Goals

```
填写格式（列出具体目标）：
- [目标 1]
- [目标 2]
- [目标 3]
...

示例：
- 实现用户注册登录功能
- 实现商品浏览和搜索功能
- 实现购物车管理
- 实现订单系统
- 集成在线支付
- 实现订单管理和查询

更详细的示例：
MVP 阶段目标（必须完成）：
- 用户系统：注册、登录、个人信息管理
- 商品系统：商品列表、商品详情、商品搜索
- 购物车：添加商品、删除商品、修改数量
- 订单系统：创建订单、订单列表、订单详情
- 支付系统：集成支付宝支付

后续阶段目标：
- 评论系统：商品评论、用户评分
- 优惠券系统：领取优惠券、使用优惠券
- 物流跟踪：订单物流状态查询
- 数据分析：销售数据统计、用户行为分析
```

---

#### 1.4 项目类型 / Project Type

**选择一个勾选：**

```
- [ ] New Project (新项目 - 从零开始)
- [x] Ongoing Project (进行中的项目 - 接手现有项目)
- [ ] Completed Project (完成的项目 - 维护/迭代)
```

**根据你的情况选择：**
- 如果你的项目刚开始，只是有一些需求文档 → 选择 "New Project"
- 如果你的项目已经开发了一部分（代码已存在） → 选择 "Ongoing Project"
- 如果你的项目已经完成并上线 → 选择 "Completed Project"

---

#### 1.5 创建日期 / Created Date

```
填写格式：
YYYY-MM-DD

示例：
2026-02-24
```

---

#### 1.6 项目状态 / Project Status

**填写表格：**

| 字段 | 值 |
|------|-----|
| Status | Planning（规划中）/ In Progress（进行中）/ Testing（测试中）/ Completed（已完成） |
| Version | 版本号，例如：v0.1.0 或 v1.0.0 |
| Last Updated | 最后更新日期，YYYY-MM-DD |

**示例：**

| 字段 | 值 |
|------|-----|
| Status | In Progress |
| Version | v0.5.0 |
| Last Updated | 2026-02-24 |

---

#### 1.7 利益相关者 / Stakeholders

**填写表格（谁关心这个项目）：**

| 角色 | 姓名/角色 |
|------|-----------|
| Product Manager | [产品经理姓名或"无"] |
| Tech Lead | [技术负责人姓名或你自己] |
| Frontend Lead | [前端负责人姓名或"无"] |
| Backend Lead | [后端负责人姓名或你自己] |
| QA Lead | [测试负责人姓名或"无"] |

**示例：**

| 角色 | 姓名/角色 |
|------|-----------|
| Product Manager | 无（个人项目） |
| Tech Lead | 言午间 |
| Frontend Lead | 无 |
| Backend Lead | 言午间 |
| QA Lead | 无 |

---

#### 1.8 关键需求 / Key Requirements

**列出主要需求：**

```
1. [需求 1 的详细说明]
2. [需求 2 的详细说明]
3. [需求 3 的详细说明]
...

示例：
1. 用户必须能够注册和登录账户
2. 用户必须能够浏览和搜索商品
3. 用户必须能够将商品添加到购物车
4. 用户必须能够完成在线支付
5. 用户必须能够查看订单状态

更详细的示例：
1. 用户系统
   - 用户可以使用邮箱或手机号注册
   - 支持密码登录和验证码登录
   - 用户可以编辑个人资料（昵称、头像、收货地址）

2. 商品系统
   - 商品列表支持分页显示（每页 20 个）
   - 商品搜索支持按名称、分类、价格范围过滤
   - 商品详情展示图片、价格、规格、库存信息

3. 购物车
   - 用户可以添加多个商品到购物车
   - 购物车商品可以增加或减少数量
   - 购物车商品可以删除
   - 购物车可以清空

4. 订单系统
   - 用户可以从购物车创建订单
   - 订单可以选择收货地址和支付方式
   - 订单创建后进入待支付状态
   - 支付成功后订单进入待发货状态

5. 支付系统
   - 支持支付宝支付
   - 支持微信支付
   - 支付成功后更新订单状态
   - 支付失败提示用户重试
```

---

#### 1.9 技术约束 / Technical Constraints

**列出技术限制（如果有的话）：**

```
- [技术限制 1]
- [技术限制 2]

示例：
- 必须兼容 Chrome 和 Firefox 浏览器
- 数据库必须使用 PostgreSQL
- API 必须遵循 RESTful 规范
- 前端必须支持响应式设计（桌面 + 移动）
- 系统必须支持至少 1000 并发用户

更详细的示例：
环境要求：
- Node.js 版本 >= 18.0.0
- PostgreSQL 版本 >= 14.0
- Redis 版本 >= 7.0（用于缓存）

兼容性要求：
- 浏览器：Chrome 120+、Firefox 120+、Safari 16+、Edge 120+
- 操作系统：Windows 10+、macOS 12+、iOS 15+、Android 12+

性能要求：
- API 响应时间 < 200ms（P95）
- 页面首次加载时间 < 2s
- 支持 1000 并发用户

安全要求：
- 所有 API 必须使用 JWT 认证
- 敏感数据必须加密存储（密码、手机号）
- API 必须防止 SQL 注入和 XSS 攻击
```

---

#### 1.10 下一步行动 / Next Actions

**列出未完成的任务（为团队提供方向）：**

```
1. [ ] 完成 [任务 1]
2. [ ] 完成 [任务 2]
3. [ ] 完成 [任务 3]
...

示例：
1. [ ] 完成商品详情前端页面实现
2. [ ] 实现订单列表 API
3. [ ] 集成支付宝支付
4. [ ] 编写单元测试
5. [ ] 修复已知 Bug（见 BUG-001）

更详细的示例：
优先级高（P0）：
1. [ ] 实现用户注册和登录前端页面
2. [ ] 实现购物车 API 后端逻辑
3. [ ] 修复登录接口的 Bug（BUG-001）

优先级中（P1）：
4. [ ] 实现商品搜索功能（前端 + 后端）
5. [ ] 实现订单状态查询 API
6. [ ] 优化页面加载速度

优先级低（P2）：
7. [ ] 添加用户评价功能
8. [ ] 添加商品推荐功能
9. [ ] 编写 API 文档
```

---

### 文件 1: PROJECT-IDENTITY.md - 完整示例

```markdown
# Project Identity / 项目的身份

## Project Name / 项目名称

My Awesome E-commerce App

## Description / 项目描述

一个现代化的电商平台，支持商品浏览、购物车、在线支付。
主要功能包括：用户注册登录、商品搜索、购物车管理、订单系统、支付集成。
目标用户是中小企业和独立卖家。

技术亮点：
- 前后端分离架构（React + Node.js）
- RESTful API 设计
- 响应式设计（桌面 + 移动）
- 支持支付宝和微信支付

## Project Goals / 项目目标

### MVP 阶段（必须完成）

- 实现用户注册登录功能
- 实现商品浏览和搜索功能
- 实现购物车管理
- 实现订单系统
- 集成在线支付（支付宝）

### 后续阶段（可选）

- 实现商品评论和评分
- 实现优惠券系统
- 实现物流跟踪
- 实现数据分析和统计

## Project Type / 项目类型

- [ ] New Project (新项目 - 从零开始)
- [x] Ongoing Project (进行中的项目 - 接手现有项目)
- [ ] Completed Project (完成的项目 - 维护/迭代)

## Created Date / 创建日期

2026-02-24

## Status / 项目状态

| Field | Value |
|-------|-------|
| Status | In Progress |
| Version | v0.5.0 |
| Last Updated | 2026-02-24 |

## Stakeholders / 利益相关者

| Role | Name/Role |
|------|-----------|
| Product Manager | 无（个人项目） |
| Tech Lead | 言午间 |
| Frontend Lead | 无 |
| Backend Lead | 言午间 |
| QA Lead | 无 |

## Key Requirements / 关键需求

### 1. 用户系统
- 用户可以使用邮箱或手机号注册
- 支持密码登录和验证码登录
- 用户可以编辑个人资料（昵称、头像、收货地址）

### 2. 商品系统
- 商品列表支持分页显示（每页 20 个）
- 商品搜索支持按名称、分类、价格范围过滤
- 商品详情展示图片、价格、规格、库存信息

### 3. 购物车
- 用户可以添加多个商品到购物车
- 购物车商品可以增加或减少数量
- 购物车商品可以删除
- 购物车可以清空

### 4. 订单系统
- 用户可以从购物车创建订单
- 订单可以选择收货地址和支付方式
- 订单创建后进入待支付状态
- 支付成功后订单进入待发货状态

### 5. 支付系统
- 支持支付宝支付
- 支付微信支付
- 支付成功后更新订单状态
- 支付失败提示用户重试

## Technical Constraints / 技术约束

### 环境要求
- Node.js 版本 >= 18.0.0
- PostgreSQL 版本 >= 14.0
- Redis 版本 >= 7.0（用于缓存）

### 兼容性要求
- 浏览器：Chrome 120+、Firefox 120+、Safari 16+、Edge 120+
- 操作系统：Windows 10+、macOS 12+、iOS 15+、Android 12+

### 性能要求
- API 响应时间 < 200ms（P95）
- 页面首次加载时间 < 2s
- 支持 1000 并发用户

### 安全要求
- 所有 API 必须使用 JWT 认证
- 敏感数据必须加密存储（密码、手机号）
- API 必须防止 SQL 注入和 XSS 攻击

## Next Steps / 下一步行动

### 优先级高（P0）
1. [ ] 实现用户注册和登录前端页面（当前进度：0%）
2. [ ] 实现购物车 API 后端逻辑（当前进度：80%）
3. [ ] 修复登录接口的 Bug（BUG-001）

### 优先级中（P1）
4. [ ] 实现商品搜索功能（前端 + 后端）（当前进度：20%）
5. [ ] 实现订单状态查询 API（当前进度：0%）

### 优先级低（P2）
6. [ ] 添加用户评价功能
7. [ ] 添加商品推荐功能
8. [ ] 编写 API 文档

---

*Last updated: 2026-02-24*
```

---

### 文件 2: TEAM-CONFIG.md（团队配置）

**这个文件不需要你填写太多，因为 4 人 Agent 团队的角色已经定义好了。**

**但是你需要注意：**

```
✓ 你的角色：原来你是用什么工具开发的？
• 如果你是用 OpenCode 开发的 → 你属于"前端开发"角色
• 如果你是用 Claude Code 开发的 → 你属于"后端开发"角色
• 如果你同时做了前后端 → 你在"当前工作"里都要标注

✓ 你的交接对象：工作交接给谁？
• 前端代码 → OpenCode（前端开发工程师）
• 后端代码 → Claude Code（后端开发工程师）
• 测试任务 → Kimi Code（测试工程师）
```

**可以保留 TEAM-CONFIG.md 的默认内容，不需要修改。**

---

### 文件 3: WORKFLOW-PROTOCOL.md（工作流协议）

**这个文件也不需要你填写，因为标准的 3 种场景工作流已经定义好了。**

**但是你需要注意：**

```
你的场景是：
- [x] Scenario 2: Ongoing Project（进行中的项目）

所以 4 人团队会遵循：
1. Context Gathering（上下文收集）
   - OpenClaw 读取所有 .md 文件
   - OpenCode 读取前端上下文
   - Claude Code 读取后端上下文
   - Kimi Code 读取质量上下文

2. Continue Development（继续开发）
   - 从你留下的"当前工作"继续
   - 从你留下的"任务清单"继续

3. Stabilization（稳定化）
   - Kimi Code 测试你留下的代码
   - 修复你报告的 Bug
```

**可以保留 WORKFLOW-PROTOCOL.md 的默认内容，不需要修改。**

---

### 文件 4: PROJECT-STATUS.md（项目状态）

**这个文件非常重要！告诉团队项目当前的整体状态。**

---

#### 4.1 总体状态 / Overall Status

**填写表格：**

| 字段 | 值 |
|------|-----|
| Overall Status | 【选择一个：Planning（规划中）、In Progress（进行中）、Testing（测试中）、Completed（已完成）】 |
| Current Phase | 【当前阶段，例如：Frontend Development（前端开发阶段）】 |
| Version | 【版本号，例如：v0.5.0】 |
| Release Date | 【如果未发布，留空或写 TBD】 |
| Last Updated | 【YYYY-MM-DD】 |

**示例：**

| 字段 | 值 |
|------|-----|
| Overall Status | In Progress |
| Current Phase | Backend Development（后端开发阶段） |
| Version | v0.5.0 |
| Release Date | TBD |
| Last Updated | 2026-02-24 |

---

#### 4.2 完成的功能 / Completed Features

**列出已经完成的功能（非常重要！）：**

| 功能 | 完成日期 | 哪个 Agent 完成的 |
|------|----------|-------------------|
| [功能 1] | YYYY-MM-DD | [OpenCode/Claude Code/Kimi Code 或你自己] |
| [功能 2] | YYYY-MM-DD | [OpenCode/Claude Code/Kimi Code 或你自己] |

**示例：**

| 功能 | 完成日期 | 谁完成的 |
|------|----------|----------|
| 数据库表设计 | 2026-02-20 | 言午间 |
| 注册登录 API | 2026-02-21 | 言午间 |
| 商品列表 API | 2026-02-22 | 言午间 |
| 首页前端页面 | 2026-02-23 | 言午间 |
| 购物车 API（部分） | 2026-02-24 | 言午间 |

---

#### 4.3 进行中的工作 / In Progress

**列出当前正在进行的任务：**

| 功能 | 状态 | 哪个 Agent 正在做 | 目标完成日期 |
|------|------|------------------|--------------|
| [功能 1] | [Planning/Dev/Testing] | [OpenCode/Claude Code/Kimi Code] | YYYY-MM-DD |
| [功能 2] | [Planning/Dev/Testing] | [OpenCode/Claude Code/Kimi Code] | YYYY-MM-DD |

**示例：**

| 功能 | 状态 | 谁在做 | 目标完成日期 |
|------|------|--------|--------------|
| 购物车 API | Dev | 言午间 → 将交接给 Claude Code | 2026-02-25 |
| 商品搜索 API | Planning | 言午间 → 将交接给 Claude Code | 2026-02-28 |
| 购物车前端 | Planning | 言午间 → 将交接给 OpenCode | 2026-03-01 |

---

#### 4.4 待办工作 / Pending Work

**列出还没开始的任务：**

| 功能 | 优先级 | 谁来做 | 目标阶段 |
|------|--------|--------|----------|
| [功能 1] | [Critical/High/Medium/Low] | [OpenCode/Claude Code/Kimi Code] | [哪个阶段] |
| [功能 2] | [Critical/High/Medium/Low] | [OpenCode/Claude Code/Kimi Code] | [哪个阶段] |

**示例：**

| 功能 | 优先级 | 谁来做 | 目标阶段 |
|------|--------|--------|----------|
| 订单创建 API | Critical | Claude Code | 后端开发阶段 |
| 支付集成 | Critical | Claude Code | 后端开发阶段 |
| 用户注册登录前端 | High | OpenCode | 前端开发阶段 |
| 购物车前端 | High | OpenCode | 前端开发阶段 |

---

#### 4.5 阻塞问题 / Blockers

**列出项目中遇到的阻塞问题（如果有）：**

| 问题 | 谁负责 | 天数 | 状态 |
|------|--------|------|------|
| [描述阻塞问题] | [谁在解决] | [已经阻塞几天了] | [Investigating/Fixing/Waiting] |

**示例：**

| 问题 | 谁负责 | 天数 | 状态 |
|------|--------|------|------|
| 支付宝 SDK 文档不清晰 | 言午间 | 3 | 正在联系支付宝技术支持 |
| 数据库性能问题 | 言午间 | 1 | 正在优化查询 |

**如果没有阻塞问题，可以写：**

```markdown
## Blockers / 阻塞问题

### Critical Blockers / 关键阻塞

无阻塞性问题。

---

### Known Issues / 已知问题

无已知阻塞问题。
```

---

#### 4.6 已知问题 / Known Issues

**列出已知的 Bug 或问题（非常重要！）：**

| 问题 | 严重等级 | 状态 | 谁修复 |
|------|----------|------|--------|
| [问题 1] | [Critical/High/Medium/Low] | [Open/In Progress/Resolved] | [谁来修] |
| [问题 2] | [Critical/High/Medium/Low] | [Open/In Progress/Resolved] | [谁来修] |

**严重等级说明：**
- **Critical（关键）**：系统无法使用（例如：登录接口挂了）
- **High（高）**：主要功能受影响（例如：购物车添加失败）
- **Medium（中）**：次要功能受影响（例如：图片加载慢）
- **Low（低）**：小问题（例如：文本显示错误）

**示例：**

| 问题 | 严重等级 | 状态 | 谁修复 |
|------|----------|------|--------|
| 登录接口 5% 概率返回 500 错误 | Critical | Open | Claude Code |
| 购物车商品数量不能增加 | High | In Progress | 言午间 |
| 商品图片偶尔加载失败 | Medium | Open | OpenCode |
| 页面标题显示错误 | Low | Open | OpenCode |

---

#### 4.7 质量指标 / Quality Metrics

**如果有的话，填写测试覆盖率等指标。如果没有，可以留空：**

| 组件 | 覆盖率 | 最后测试日期 |
|------|--------|--------------|
| 前端 | [X% 或"未测试"] | YYYY-MM-DD |
| 后端 | [X% 或"未测试"] | YYYY-MM-DD |
| 整体 | [X% 或"未测试"] | YYYY-MM-DD |

**示例：**

| 组件 | 覆盖率 | 最后测试日期 |
|------|--------|--------------|
| 前端 | 未测试 | - |
| 后端 | 30%（仅 API 接口手动测试） | 2026-02-23 |
| 整体 | 未测试 | - |

---

#### 4.8 Bug 统计 / Bug Statistics

**如果你的 Bug 有点多，可以写统计：**

| 时间段 | Bug 总数 | 已修复 | 未修复 | 修复率 |
|--------|---------|--------|--------|--------|
| 过去 7 天 | 5 | 3 | 2 | 60% |
| 过去 30 天 | 10 | 7 | 3 | 70% |
| 总计 | 10 | 7 | 3 | 70% |

**示例：**

| 时间段 | Bug 总数 | 已修复 | 未修复 | 修复率 |
|--------|---------|--------|--------|--------|
| 过去 7 天 | 5 | 3 | 2 | 60% |
| 过去 30 天 | 10 | 7 | 3 | 70% |
| 总计 | 10 | 7 | 3 | 70% |

**如果没有 Bug，可以写：**

| 时间段 | Bug 总数 | 已修复 | 未修复 | 修复率 |
|--------|---------|--------|--------|--------|
| 过去 7 天 | 0 | 0 | 0 | - |
| 过去 30 天 | 0 | 0 | 0 | - |
| 总计 | 0 | 0 | 0 | - |

---

#### 4.9 里程碑 / Milestones

**列出已经完成或计划完成的里程碑：**

| 里程碑 | 状态 | 目标日期 | 实际完成日期 | 备注 |
|--------|------|----------|--------------|------|
| [里程碑 1] | [Planning/In Progress/Completed] | YYYY-MM-DD | YYYY-MM-DD | [备注] |

**示例：**

| 里程碑 | 状态 | 目标日期 | 实际完成日期 | 备注 |
|--------|------|----------|--------------|------|
| MVP 设计完成 | Completed | 2026-02-20 | 2026-02-19 | 提前完成 |
| 数据库设计完成 | Completed | 2026-02-22 | 2026-02-21 | 提前完成 |
| 核心后端 API 完成 | In Progress | 2026-03-01 | TBD | 进行中 |
| 前端页面完成 | Planning | 2026-03-15 | TBD | 待开始 |

---

#### 4.10 部署历史 / Deployment History

**如果已经部署过，记录部署历史：**

| 版本 | 日期 | 谁部署的 | 备注 |
|------|------|----------|------|
| [v0.1.0] | YYYY-MM-DD | [部署者] | [备注] |

**示例：**

| 版本 | 日期 | 谁部署的 | 备注 |
|------|------|----------|------|
| v0.1.0 | 2026-02-15 | 言午间 | 初始版本，仅 API 服务 |

**如果没有部署过，可以写：**

| 版本 | 日期 | 谁部署的 | 备注 |
|------|------|----------|------|
| - | - | - | 项目尚未部署 |

---

#### 4.11 下一步行动 / Next Actions

**详细列出下一步要做的：**

```
1. **OpenClaw：** [下一步行动]
2. **OpenCode：** [下一步行动]
3. **Claude Code：** [下一步行动]
4. **Kimi Code：** [下一步行动]
```

**示例：**

```
1. **OpenClaw：** 评估待办工作优先级，分配任务给 OpenCode 和 Claude Code
2. **OpenCode：** 开始实现用户注册登录前端页面
3. **Claude Code：** 继续完成购物车 API，然后开始订单系统 API
4. **Kimi Code：** 等待第一批功能完成后，开始测试
```

---

#### 4.12 风险登记 / Risk Register

**列出潜在风险（如果有）：**

| 风险 | 概率 | 影响 | 应对计划 | 负责人 |
|------|------|------|----------|--------|
| [风险 1] | [High/Medium/Low] | [High/Medium/Low] | [应对策略] | [谁负责] |

**示例：**

| 风险 | 概率 | 影响 | 应对计划 | 负责人 |
|------|------|------|----------|--------|
| 支付宝集成困难 | Medium | High | 提前联系支付宝技术支持，准备备用方案 | Claude Code |
| 数据库性能不足 | Medium | Medium | 使用 Redis 缓存，优化 SQL 查询 | Claude Code |
| 前端开发进度延迟 | Low | Medium | 优先实现 MVP 核心功能 | OpenCode |

**如果没有明显风险，可以写：**

| 风险 | 概率 | 影响 | 应对计划 | 负责人 |
|------|------|------|----------|--------|
| 暂无明显风险 | - | - | - | - |

---

### 文件 4: PROJECT-STATUS.md - 完整示例

```markdown
# Project Status / 项目状态

## Overall Status / 总体状态

| Field | Value |
|-------|-------|
| **Overall Status** | In Progress |
| **Current Phase** | Backend Development（后端开发阶段） |
| **Version** | v0.5.0 |
| **Release Date** | TBD |
| **Last Updated** | 2026-02-24 |

## Progress Tracking / 进度追踪

### Completed Features / 已完成功能

| Feature | Date | Agent |
|---------|------|-------|
| 数据库表设计 | 2026-02-20 | 言午间 |
| 注册登录 API | 2026-02-21 | 言午间 |
| 商品列表 API | 2026-02-22 | 言午间 |
| 首页前端页面 | 2026-02-23 | 言午间 |
| 购物车 API（部分） | 2026-02-24 | 言午间 |

### In Progress / 进行中的工作

| Feature | Status | Agent | Target Date |
|---------|--------|-------|-------------|
| 购物车 API | Dev | 言午间 → Claude Code | 2026-02-25 |
| 商品搜索 API | Planning | 言午间 → Claude Code | 2026-02-28 |
| 购物车前端 | Planning | 言午间 → OpenCode | 2026-03-01 |

### Pending Work / 待办任务

| Feature | Priority | Agent | Target Phase |
|---------|----------|-------|-------------|
| 订单创建 API | Critical | Claude Code | 后端开发阶段 |
| 支付集成 | Critical | Claude Code | 后端开发阶段 |
| 用户注册登录前端 | High | OpenCode | 前端开发阶段 |
| 购物车前端 | High | OpenCode | 前端开发阶段 |

## Blockers / 阻塞问题

### Critical Blockers / 关键阻塞

无阻塞性问题。

### Known Issues / 已知问题

| Issue | Severity | Status | Assigned To |
|-------|----------|--------|-------------|
| 登录接口 5% 概率返回 500 错误 | Critical | Open | Claude Code |
| 购物车商品数量不能增加 | High | In Progress | 言午间 |
| 商品图片偶尔加载失败 | Medium | Open | OpenCode |
| 页面标题显示错误 | Low | Open | OpenCode |

## Quality Metrics / 质量指标

### Test Coverage / 测试覆盖率

| Component | Coverage % | Last Tested |
|-----------|------------|-------------|
| 前端 | 未测试 | - |
| 后端 | 30%（仅 API 接口手动测试） | 2026-02-23 |
| Overall | 未测试 | - |

### Bug Statistics / Bug 统计

| Period | Total Bugs | Fixed Bugs | Open Bugs | Resolution Rate |
|--------|-----------|------------|-----------|-----------------|
| Last 7 days | 5 | 3 | 2 | 60% |
| Last 30 days | 10 | 7 | 3 | 70% |
| Total | 10 | 7 | 3 | 70% |

## Milestones / 里程碑

| Milestone | Status | Target Date | Actual Date | Notes |
|-----------|--------|-------------|-------------|-------|
| MVP 设计完成 | Completed | 2026-02-20 | 2026-02-19 | 提前完成 |
| 数据库设计完成 | Completed | 2026-02-22 | 2026-02-21 | 提前完成 |
| 核心后端 API 完成 | In Progress | 2026-03-01 | TBD | 进行中 |
| 前端页面完成 | Planning | 2026-03-15 | TBD | 待开始 |

## Deployment History / 部署历史

| Version | Date | Deployed By | Notes |
|---------|------|-------------|-------|
| v0.1.0 | 2026-02-15 | 言午间 | 初始版本，仅 API 服务 |
| v0.5.0 | 2026-02-24 | 言午间 | 添加了购物车 API |

## Next Actions / 下一步行动

1. **OpenClaw：** 评估待办工作优先级，分配任务给 OpenCode 和 Claude Code
2. **OpenCode：** 开始实现用户注册登录前端页面
3. **Claude Code：** 继续完成购物车 API，修复登录接口 Bug
4. **Kimi Code：** 等待第一批功能完成后，开始测试

## Risk Register / 风险登记

| Risk | Probability | Impact | Mitigation Plan | Owner |
|------|-------------|--------|----------------|-------|
| 支付宝集成困难 | Medium | High | 提前联系支付宝技术支持，准备备用方案 | Claude Code |
| 数据库性能不足 | Medium | Medium | 使用 Redis 缓存，优化 SQL 查询 | Claude Code |
| 前端开发进度延迟 | Low | Medium | 优先实现 MVP 核心功能 | OpenCode |

---

*Last updated by: 言午间 on 2026-02-24*
```

---

### 文件 5: CURRENT-WORK.md（当前工作）

**这个文件最重要！告诉团队每个人现在在做什么。**

---

#### 5.1 OpenClaw - 当前活动

**如果项目中没有 OpenClaw（你是单人开发），可以写：**

```markdown
## OpenClaw - Current Activities

### Primary Task / 主任务

**当前状态：** 项目刚刚交接给 4 人团队

**任务：** 评估项目状态，分配任务给其他 Agent

| Field | Value |
|-------|-------|
| Task ID | TBD（待分配） |
| Type | Coordination（协调） |
| Started | 2026-02-24 |
| Target Completion | 2026-02-25 |
| Progress | 0% |

### Subtasks / 子任务

- [ ] 读取所有 .md 文件
- [ ] 评估 PROJECT-STATUS.md
- [ ] 分配任务给 OpenCode
- [ ] 分配任务给 Claude Code
- [ ] 制定测试计划给 Kimi Code

### Notes / 备注

项目刚刚从单人开发交接给 4 人团队，需要先全面了解项目状态。
```

---

#### 5.2 OpenCode - 当前活动（前端）

**如果你的项目有前端代码，填写这个部分：**

```markdown
## OpenCode - Current Activities

### Primary Task / 主任务

**任务描述：** [简单描述前端任务]

| Field | Value |
|-------|-------|
| Task ID | [TASK-XXX] |
| Component | [哪个组件/页面] |
| Started | YYYY-MM-DD |
| Target Completion | YYYY-MM-DD |
| Progress | [X%] |

### Files Modified / 修改的文件

| File | Type | Last Updated |
|------|------|--------------|
| [路径/文件1.tsx] | [Modified/New] | YYYY-MM-DD |
| [路径/文件2.css] | [Modified/New] | YYYY-MM-DD |

**示例：**

| File | Type | Last Updated |
|------|------|--------------|
| src/pages/HomePage.tsx | Modified | 2026-02-23 |
| src/components/ProductCard.tsx | New | 2026-02-23 |
| src/api/shop.ts | Modified | 2026-02-23 |

### Pending API Dependencies / 待完成的 API 依赖

| API Endpoint | 用在哪里 | 状态 | 请求谁开发 |
|--------------|----------|------|-----------|
| [GET /api/xxx] | [哪个组件] | [Pending/Ready] | Claude Code |

**示例：**

| API Endpoint | 用在哪里 | 状态 | 请求谁开发 |
|--------------|----------|------|-----------|
| GET /api/cart | CartPage.js | Pending | Claude Code |
| POST /api/cart/items | CartPage.js | Pending | Claude Code |

### Notes / 备注

```
[任何相关的备注信息]

示例：
前端首页已完成，但购物车功能需要后端 API 支持。
目前使用 Mock 数据进行开发，待后端 API 完成后替换。
```
```

**如果前端还没开始，可以写：**

```markdown
## OpenCode - Current Activities

### Primary Task / 主任务

**当前状态：** 前端尚未开始

**计划任务：** 实现 [功能描述]

| Field | Value |
|-------|-------|
| Task ID | TBD |
| Component | TBD |
| Started | TBD |
| Target Completion | TBD |
| Progress | 0% |

### Notes / 备注

项目目前处于后端开发阶段，前端将在后端 API 完成后开始。
```

---

#### 5.3 Claude Code - 当前活动（后端）

**如果你的项目有后端代码，填写这个部分（非常重要！）：**

```markdown
## Claude Code - Current Activities

### Primary Task / 主任务

**任务描述：** [简单描述后端任务]

| Field | Value |
|-------|-------|
| Task ID | [TASK-XXX] |
| API Endpoint | [如果涉及 API，填写 API 路径] |
| Started | YYYY-MM-DD |
| Target Completion | YYYY-MM-DD |
| Progress | [X%] |

### APIs in Development / 开发中的 API

| Endpoint | 方法 | 状态 | 前端请求者 |
|----------|------|--------|-----------|
| [/api/xxx] | [GET/POST/PUT/DELETE] | [In Progress/Testing/Ready] | OpenCode |

**示例：**

| Endpoint | 方法 | 状态 | 前端请求者 |
|----------|------|--------|-----------|
| /api/cart | GET | In Progress | OpenCode |
| /api/cart/items | POST | In Progress | OpenCode |
| /api/cart/items/:id | DELETE | Planning | OpenCode |

### Database Changes / 数据库变更

| 表名 | 操作 | 状态 | 最后更新 |
|------|------|------|----------|
| [表名] | [Create/Alter/Drop] | [Planned/In Progress/Done] | YYYY-MM-DD |

**示例：**

| 表名 | 操作 | 状态 | 最后更新 |
|------|------|------|----------|
| carts | Create | Done | 2026-02-21 |
| cart_items | Create | Done | 2026-02-21 |
| orders | Create | Planning | TBD |

### Notes / 备注

```
[任何相关的备注信息]

示例：
购物车 API 正在开发中，已完成 GET /api/cart 接口。
POST 和 DELETE 接口预计明天完成。
前端可以先用 Mock 数据开发，待后端完成后替换。
```
```

---

#### 5.4 Kimi Code - 当前活动（测试）

**如果项目还没测试，可以写：**

```markdown
## Kimi Code - Current Activities

### Primary Task / 主任务

**当前状态：** 项目尚未进入测试阶段

**计划任务：** 等待第一批功能完成后，开始集成测试

| Field | Value |
|-------|-------|
| Task Type | TBD |
| Target Component | TBD |
| Started | TBD |
| Target Completion | TBD |
| Progress | 0% |

### Test Execution Progress / 测试执行进度

| 测试套件 | 总测试数 | 通过 | 失败 | 待测 | 状态 |
|----------|----------|------|------|------|------|
| - | - | - | - | - | TBD |

### Bugs Found This Cycle / 本周期发现的 Bug

| Bug ID | 严重等级 | 组件 | 分配给 | 状态 |
|--------|----------|------|--------|------|
| - | - | - | - | - |

### Notes / 备注

项目目前处于开发阶段，尚未进入测试阶段。
待第一批功能完成后，Kimi Code 将开始集成测试。
```

---

#### 5.5 依赖关系 / Dependencies

**列出 Agent 之间的依赖（非常关键）：**

```markdown
## Dependencies / 依赖关系

```

**示例：**

```markdown
## Dependencies / 依赖关系

```
OpenCode (前端) 等待 Claude Code (后端)：
  - GET /api/cart → 需要用于购物车页面
  - POST /api/cart/items → 需要用于添加商品到购物车
  - DELETE /api/cart/items/:id → 需要用于删除购物车商品

Claude Code (后端) 等待 OpenCode (前端)：
  - 前端页面开发进度 → 确定需要哪些 API

Kimi Code (测试) 等待 OpenCode + Claude Code：
  - 购物车功能完成 → 需要进行集成测试
```

---

#### 5.6 当前阻塞 / Current Blockers

**列出阻塞问题（如果有的话）：**

```markdown
## Blockers / 当前阻塞

| 任务 | 被什么阻塞 | 严重等级 | 谁负责 | 解决计划 |
|------|-----------|----------|--------|----------|
| [任务] | [依赖/Bug/资源] | [Critical/High/Medium] | [Agent] | [计划] |

**示例：**

| 任务 | 被什么阻塞 | 严重等级 | 谁负责 | 解决计划 |
|------|-----------|----------|--------|----------|
| 购物车前端开发 | 后端 API 未完成 | High | Claude Code | 明天完成 API |
| 支付集成 | 支付宝 SDK 文档不清 | Medium | Claude Code | 联系支付宝技术支持 |
```

**如果没有阻塞，可以写：**

```markdown
## Blockers / 当前阻塞

无阻塞性问题。
```

---

#### 5.7 最近更新 / Recent Updates

**记录最近的更新（让团队知道发生了什么）：**

```markdown
## Recent Updates / 最近更新

| 日期 | Agent | 更新内容 |
|------|-------|----------|
| YYYY-MM-DD | 言午间 | [更新摘要] |
| YYYY-MM-DD | 言午间 | [更新摘要] |

**示例：**

| 日期 | Agent | 更新内容 |
|------|-------|----------|
| 2026-02-24 | 言午间 | 完成购物车 API 的 GET 接口；POST 和 DELETE 接口开发中 |
| 2026-02-23 | 言午间 | 完成首页前端页面；开始购物车页面设计 |
| 2026-02-22 | 言午间 | 完成商品列表 API；开始购物车 API 设计 |
| 2026-02-21 | 言午间 | 完成数据库表设计；完成注册登录 API |
```

---

#### 5.8 交接状态 / Handoff Status

**列出交接状态（哪些任务可以测试了）：**

```markdown
## Handoff Status / 交接状态

### Ready for Testing / 待测试

| 任务 | 组件/文件 | 谁提交的 | 日期 |
|------|-----------|----------|------|
| [任务 1] | [组件/文件列表] | [OpenCode/Claude Code] | YYYY-MM-DD |

**示例：**

| 任务 | 组件/文件 | 谁提交的 | 日期 |
|------|-----------|----------|------|
| 注册登录 API | src/api/auth.ts, routes/auth.ts | 言午间 → Claude Code | 2026-02-21 |
| 商品列表 API | src/api/products.ts, routes/products.ts | 言午间 → Claude Code | 2026-02-22 |

### Testing in Progress / 测试中

| 任务 | 测试套件 | 状态 | 预计完成 |
|------|----------|------|----------|
| - | - | - | - |

### Ready for Deployment / 待部署

| 任务 | 批准人 | 日期 |
|------|--------|------|
| - | - | - |

**示例：**

| 任务 | 批准人 | 日期 |
|------|--------|------|
| - | - | - |

### Notes about Handoff / 交接备注

项目刚开始交接给 4 人团队，尚未有任务进入测试阶段。
预计 2026-02-28 可以完成第一批功能，进入测试阶段。
```

---

### 文件 5: CURRENT-WORK.md - 完整示例

```markdown
# Current Work / 当前工作

## OpenClaw - Current Activities

### Primary Task / 主任务

**当前状态：** 项目刚刚交接给 4 人团队

**任务：** 评估项目状态，分配任务给其他 Agent

| Field | Value |
|-------|-------|
| Task ID | TBD（待分配） |
| Type | Coordination（协调） |
| Started | 2026-02-24 |
| Target Completion | 2026-02-25 |
| Progress | 0% |

### Subtasks / 子任务

- [ ] 读取所有 .md 文件
- [ ] 评估 PROJECT-STATUS.md
- [ ] 分配任务给 OpenCode
- [ ] 分配任务给 Claude Code
- [ ] 制定测试计划给 Kimi Code

### Notes / 备注

项目刚刚从单人开发交接给 4 人团队，需要先全面了解项目状态。

---

## OpenCode - Current Activities

### Primary Task / 主任务

**当前状态：** 前端部分完成，但需要 API 支持

**任务：** 首页已开发完成，等待后端 API 完善后继续

| Field | Value |
|-------|-------|
| Task ID | TASK-FE-001 |
| Component | HomePage, ProductCard |
| Started | 2026-02-23 |
| Target Completion | TBD（等待后端 API） |
| Progress | 80% |

### Files Modified / 修改的文件

| File | Type | Last Updated |
|------|------|--------------|
| src/pages/HomePage.tsx | Modified | 2026-02-23 |
| src/components/ProductCard.tsx | New | 2026-02-23 |
| src/api/shop.ts | Modified | 2026-02-23 |
| src/styles/HomePage.css | New | 2026-02-23 |

### Pending API Dependencies / 待完成的 API 依赖

| API Endpoint | 用在哪里 | 状态 | 请求谁开发 |
|--------------|----------|------|-----------|
| GET /api/products | HomePage | Ready | Claude Code |
| GET /api/products/:id | ProductCard | Ready | Claude Code |
| GET /api/cart | CartPage | Pending | Claude Code |
| POST /api/cart/items | CartPage | Pending | Claude Code |
| DELETE /api/cart/items/:id | CartPage | Pending | Claude Code |

### Notes / 备注

前端首页已完成，但购物车功能需要后端 API 支持。
目前使用 Mock 数据进行开发，待后端 API 完成后替换。

---

## Claude Code - Current Activities

### Primary Task / 主任务

**任务描述：** 完成购物车 API 的所有接口

| Field | Value |
|-------|-------|
| Task ID | TASK-BE-001 |
| API Endpoint | /api/cart/* |
| Started | 2026-02-23 |
| Target Completion | 2026-02-25 |
| Progress | 40% |

### APIs in Development / 开发中的 API

| Endpoint | 方法 | 状态 | 前端请求者 |
|----------|------|--------|-----------|
| /api/cart | GET | Done | OpenCode |
| /api/cart/items | POST | In Progress | OpenCode |
| /api/cart/items/:id | DELETE | Planning | OpenCode |
| /api/cart/clear | DELETE | Planning | OpenCode |

### API 文档

**GET /api/cart**
- 描述：获取用户的购物车
- 请求头：`Authorization: Bearer <token>`
- 响应：
  ```json
  {
    "cartId": "xxx",
    "items": [
      {
        "productId": "xxx",
        "name": "Product Name",
        "price": 99.99,
        "quantity": 2
      }
    ],
    "total": 199.98
  }
  ```

### Database Changes / 数据库变更

| 表名 | 操作 | 状态 | 最后更新 |
|------|------|------|----------|
| carts | Create | Done | 2026-02-21 |
| cart_items | Create | Done | 2026-02-21 |
| orders | Create | Planning | TBD |

### Notes / 备注

购物车 API 正在开发中，已完成 GET /api/cart 接口。
POST 和 DELETE 接口预计明天完成。
前端可以先用 Mock 数据开发，待后端完成后替换。

---

## Kimi Code - Current Activities

### Primary Task / 主任务

**当前状态：** 项目尚未进入测试阶段

**计划任务：** 等待第一批功能完成后，开始集成测试

| Field | Value |
|-------|-------|
| Task Type | TBD |
| Target Component | TBD |
| Started | TBD |
| Target Completion | TBD |
| Progress | 0% |

### Test Execution Progress / 测试执行进度

| 测试套件 | 总测试数 | 通过 | 失败 | 待测 | 状态 |
|----------|----------|------|------|------|------|
| - | - | - | - | - | TBD |

### Bugs Found This Cycle / 本周期发现的 Bug

| Bug ID | 严重等级 | 组件 | 分配给 | 状态 |
|--------|----------|------|--------|------|
| - | - | - | - | - |

### Notes / 备注

项目目前处于开发阶段，尚未进入测试阶段。
待第一批功能完成后，Kimi Code 将开始集成测试。

---

## Dependencies / 依赖关系

```
OpenCode (前端) 等待 Claude Code (后端)：
  - POST /api/cart/items → 需要用于添加商品到购物车
  - DELETE /api/cart/items/:id → 需要用于删除购物车商品

Claude Code (后端) 等待 OpenCode (前端)：
  - 前端需求 → 确定需要哪些 API 参数

Kimi Code (测试) 等待 OpenCode + Claude Code：
  - 购物车功能完成 → 需要进行集成测试
```

---

## Blockers / 当前阻塞

无阻塞性问题。

---

## Recent Updates / 最近更新

| 日期 | Agent | 更新内容 |
|------|-------|----------|
| 2026-02-24 | 言午间 → Claude Code | 完成购物车 API 的 GET 接口；POST 和 DELETE 接口开发中 |
| 2026-02-23 | 言午间 → OpenCode | 完成首页前端页面；开始购物车页面设计 |
| 2026-02-22 | 言午间 → Claude Code | 完成商品列表 API；开始购物车 API 设计 |
| 2026-02-21 | 言午间 → Claude Code | 完成数据库表设计；完成注册登录 API |

---

## Handoff Status / 交接状态

### Ready for Testing / 待测试

| 任务 | 组件/文件 | 谁提交的 | 日期 |
|------|-----------|----------|------|
| 注册登录 API | src/api/auth.ts, routes/auth.ts | 言午间 → Claude Code | 2026-02-21 |
| 商品列表 API | src/api/products.ts, routes/products.ts | 言午间 → Claude Code | 2026-02-22 |

### Testing in Progress / 测试中

| 任务 | 测试套件 | 状态 | 预计完成 |
|------|----------|------|----------|
| - | - | - | - |

### Ready for Deployment / 待部署

| 任务 | 批准人 | 日期 |
|------|--------|------|
| - | - | - |

---

*Last updated: 2026-02-24*
```

---

### 文件 6: TASK-BACKLOG.md（任务清单）

**这个文件列出所有待办任务。**

---

#### 6.1 优先级分类 / MoSCoW Prioritization

**填写优先级说明：**

| 优先级 | 描述 | 时间要求 |
|--------|------|----------|
| Must Have | MVP 必须有的功能，阻塞性的 | 本版本必须完成 |
| Should Have | 重要但非阻塞性的功能 | 下个版本完成 |
| Could Have | 锦上添花的功能 | 有时间再做 |
| Won't Have | 不在此版本范围内 | 以后再考虑 |

---

#### 6.2 必须有 / Must Have（Critical）

**列出所有必须完成的任务（详细描述）：**

```markdown
### [MH-001] [任务标题]

**描述：** [详细描述任务内容]

**类型：** [Frontend/Backend/Integration/Testing/Documentation]

**分配给：** [OpenCode/Claude Code/Kimi Code/OpenClaw]

**状态：** [Not Started/In Progress/Testing/Complete]

**优先级：** [Critical]

**工作量：** [Story Points/小时数]：[X]

**依赖关系：**

| 依赖 | 任务 ID | 状态 |
|------|---------|------|
| [依赖 1] | [MH-XXX] | [Not Started/In Progress/Complete] |

**验收标准：**

- [ ] [标准 1]
- [ ] [标准 2]
- [ ] [标准 3]

**备注：**

```
[任何相关备注]

示例：
注意：这个功能需要与后端 API 配对开发。
```
```

**详细示例（任务 MH-001）：**

```markdown
### [MH-001] 实现用户注册功能

**描述：**
用户可以通过邮箱或手机号注册账户。
注册时需要填写邮箱/手机号、密码、确认密码。
系统需要验证邮箱格式是否正确，手机号格式是否正确。
密码需要满足安全要求（至少 8 位，包含字母和数字）。
注册成功后发送验证邮件或短信（这个功能可以先做 Mock）。

**类型：** Frontend + Backend

**分配给：** OpenCode（前端界面）+ Claude Code（后端 API）

**状态：** In Progress

**优先级：** Critical

**工作量：** 8 小时

**依赖关系：**

| 依赖 | 任务 ID | 状态 |
|------|---------|------|
| 数据库表设计 | MH-000 | Complete |

**验收标准：**

- [ ] 前端：有注册页面，表单包含邮箱/手机号输入框、密码输入框、确认密码输入框、注册按钮
- [ ] 前端：表单验证（邮箱格式、手机号格式、密码强度）
- [ ] 前端：点击注册按钮调用后端 API
- [ ] 后端：有 POST /api/auth/register 接口，接收邮箱/手机号、密码
- [ ] 后端：验证输入参数，创建用户记录到数据库
- [ ] 后端：返回成功响应（包含 token）
- [ ] 后端：错误处理（邮箱已存在、密码不符合要求等）

**备注：**
注册页面设计参考 Modern UI 风格。
后端需要使用 bcrypt 加密密码存储。
暂时不需要做邮件/短信验证，注册成功后直接登录。
```

---

#### 6.3 应该有 / Should Have

**列出重要但非必须的任务：**

```markdown
### [SH-001] 实现商品评论功能

**描述：** 用户可以对商品进行评论和评分

**类型：** Frontend + Backend

**分配给：** OpenCode + Claude Code

**状态：** Not Started

**优先级：** High

**工作量：** 6 小时
```

---

#### 6.4 可以有 / Could Have

**列出锦上添花的任务：**

```markdown
### [CH-001] 实现商品推荐功能

**描述：** 根据用户浏览历史推荐商品

**类型：** Backend + Algorithm

**分配给：** Claude Code

**状态：** Not Started

**优先级：** Medium

**工作量：** 12 小时
```

---

#### 6.5 Bug 清单 / Bug Backlog

**列出已知的 Bug（非常重要！）：**

```markdown
### [BUG-001] 登录接口 5% 概率返回 500 错误

**严重等级：** Critical

**组件：** Backend / API

**发现者：** 言午间

**报告日期：** 2026-02-24

**分配给：** Claude Code

**状态：** Open（待修复）

**描述：**

```
Bug 详细描述：

现象：
用户登录时，有 5% 的概率会收到 HTTP 500 响应，而不是 200 OK。

重现步骤：
1. 用户访问登录页面 /login
2. 输入正确的用户名和密码
3. 点击"登录"按钮
4. 请求 POST /api/auth/login
5. 有 5% 的概率返回 500 错误

预期行为：
应该始终返回 200 OK（成功）或 401 Unauthorized（凭据错误）

实际行为：
偶尔返回 500 Internal Server Error，响应体中没有错误信息

日志：
（如果有日志，粘贴在这里）

Error: connect ECONNREFUSED 127.0.0.1:5432
    at TCPConnectWrap.afterConnect [as oncomplete] (net.js:1145:16)
```

**环境：**

| 项目 | 值 |
|------|-----|
| 浏览器 | Chrome 120 |
| 操作系统 | Windows 11 |
| Node.js 版本 | 18.17.0 |
| PostgreSQL 版本 | 14.10 |

**附件/相关文件：**

- `src/routes/auth.ts`（登录 API 路由）
- `src/api/auth.ts`（认证服务）
- `logs/error.log`（错误日志）

**备注：**

初步怀疑是数据库连接池的问题，偶尔连接池耗尽导致无法连接数据库。
需要检查数据库连接池配置。
```

---

**另一个 Bug 示例（前端 Bug）：**

```markdown
### [BUG-002] 购物车商品数量不能增加

**严重等级：** High

**组件：** Frontend / Cart Page

**发现者：** 用户反馈

**报告日期：** 2026-02-24

**分配给：** OpenCode

**状态：** Pending（待修复）

**描述：**

```
Bug 详细描述：

现象：
用户在购物车页面点击"+"按钮增加商品数量时，数量不增加。

重现步骤：
1. 用户访问购物车页面 /cart
2. 找到一个商品
3. 点击"+"按钮
4. 商品数量应该是 2 + 1 = 3，但仍然显示 2

预期行为：
点击"+"按钮后，商品数量应该增加 1
点击"-"按钮后，商品数量应该减少 1

实际行为：
点击"+"或"-"按钮后，商品数量没有变化，也没有任何提示
```

**环境：**

| 项目 | 值 |
|------|-----|
| 浏览器 | Chrome 120 |
| 操作系统 | Windows 11 |
| React 版本 | 18.2.0 |

**附件/相关文件：**

- `src/pages/CartPage.tsx`（购物车页面）
- `src/components/CartItem.tsx`（购物车商品项组件）

**备注：**

检查 `CartItem.tsx` 中的 `handleQuantityChange` 方法，可能没有正确调用 `setState`。
```

---

### 文件 6: TASK-BACKLOG.md - 完整示例（部分）

```markdown
# Task Backlog / 任务清单

## MoSCoW Prioritization / 优先级分类

| Priority | Description | Deadline |
|----------|-------------|----------|
| **Must Have** | MVP 必须的功能，阻碍用户使用 | 本版本必须完成 |
| **Should Have** | 重要但非阻塞性的功能 | 下个版本完成 |
| **Could Have** | 锦上添花的功能 | 有时间再做 |
| **Won't Have** | 不在此版本范围内 | 以后再考虑 |

---

## Must Have / 必须有（Critical）

### [MH-001] 实现用户注册功能

**描述：**
用户可以通过邮箱或手机号注册账户。
注册时需要填写邮箱/手机号、密码、确认密码。
系统需要验证邮箱格式是否正确，手机号格式是否正确。
密码需要满足安全要求（至少 8 位，包含字母和数字）。
注册成功后发送验证邮件或短信（这个功能可以先做 Mock）。

**类型：** Frontend + Backend

**分配给：** OpenCode + Claude Code

**状态：** In Progress

**优先级：** Critical

**工作量：** 8 小时

**依赖关系：**

| 依赖 | 任务 ID | 状态 |
|------|---------|------|
| 数据库表设计 | MH-000 | Complete |

**验收标准：**

- [ ] 前端：有注册页面，表单包含邮箱/手机号输入框、密码输入框、确认密码输入框、注册按钮
- [ ] 前端：表单验证（邮箱格式、手机号格式、密码强度）
- [ ] 后端：有 POST /api/auth/register 接口
- [ ] 后端：验证输入参数，创建用户记录
- [ ] 后端：返回成功响应（包含 token）
- [ ] 后端：错误处理

**备注：**
暂时不需要做邮件/短信验证。

---

### [MH-002] 实现用户登录功能

**描述：**
用户可以通过密码登录。
系统支持 JWT Token 认证。

**类型：** Frontend + Backend

**分配给：** OpenCode + Claude Code

**状态：** Complete

**优先级：** Critical

**工作量：** 4 小时

**依赖关系：**

| 依赖 | 任务 ID | 状态 |
|------|---------|------|
| 数据库表设计 | MH-000 | Complete |

---

### [MH-003] 实现商品列表功能

**描述：**
用户可以浏览商品列表，支持分页。

**类型：** Frontend + Backend

**分配给：** OpenCode + Claude Code

**状态：** Complete

**优先级：** Critical

**工作量：** 6 小时

---

### [MH-004] 实现购物车功能

**描述：**
用户可以将商品添加到购物车，查看购物车，修改数量，删除商品。

**类型：** Frontend + Backend

**分配给：** OpenCode + Claude Code

**状态：** In Progress

**优先级：** Critical

**工作量：** 12 小时

---

## Should Have / 应该有

### [SH-001] 实现商品评论功能

**描述：** 用户可以对商品进行评论和评分

**类型：** Frontend + Backend

**分配给：** OpenCode + Claude Code

**状态：** Not Started

**优先级：** High

**工作量：** 6 小时

---

## Bug Backlog / Bug 清单

### [BUG-001] 登录接口 5% 概率返回 500 错误

**严重等级：** Critical

**组件：** Backend / API

**发现者：** 言午间

**报告日期：** 2026-02-24

**分配给：** Claude Code

**状态：** Open

**详细描述：**
（见上面的详细示例）

---

### [BUG-002] 购物车商品数量不能增加

**严重等级：** High

**组件：** Frontend / Cart Page

**发现者：** 用户反馈

**报告日期：** 2026-02-24

**分配给：** OpenCode

**状态：** Pending

**详细描述：**
（见上面的详细示例）

---

*Last updated: 2026-02-24*
```

---

## 完整交接流程

**一旦你填写好了所有文件，按照以下步骤完成交接：**

---

### Step 1: 将所有文件放在项目根目录

```
你的项目目录：
  /your-project/
    ├── .git/                           （如果有 Git）
    ├── src/                            （源代码）
    │   ├── frontend/                   （前端代码）
    │   └── backend/                    （后端代码）
    ├── .gitignore
    ├── package.json
    ├── README.md                       （项目 README）
    ├── PROJECT-IDENTITY.md             ← 新增
    ├── TEAM-CONFIG.md                 ← 新增
    ├── WORKFLOW-PROTOCOL.md            ← 新增
    ├── PROJECT-STATUS.md              ← 新增
    ├── CURRENT-WORK.md                ← 新增
    ├── TASK-BACKLOG.md                ← 新增
    └── CONTEXT-BRIDGE.md              ← 新增
```

**位置很重要：**
- 所有 `.md` 文件必须放在项目根目录
- OpenClaw 会读取这些文件来理解项目

---

### Step 2: 验证所有文件

```
检查清单：

✓ PROJECT-IDENTITY.md 已填写完整
  - 项目名称
  - 项目描述（详细）
  - 项目目标（详细）
  - 项目类型已选择（应该选 Ongoing Project）
  - 项目状态（Overall Status）
  - 利益相关者
  - 关键需求（详细）
  - 技术约束（如果有）
  - 下一步行动

✓ PROJECT-STATUS.md 已填写完整
  - 总体状态
  - 已完成的功能（列表）
  - 进行中的工作（列表）
  - 待办任务（列表）
  - 阻塞问题
  - 已知问题（详细）
  - 质量指标
  - Bug 统计
  - 里程碑
  - 部署历史（如果有）
  - 下一步行动
  - 风险登记

✓ CURRENT-WORK.md 已填写完整
  - OpenClaw 当前活动（简单描述交接状态）
  - OpenCode 当前活动（如果有前端代码）
  - Claude Code 当前活动（如果有后端代码）
  - Kimi Code 当前活动（未开始，简单描述）
  - 依赖关系（非常重要！）
  - 阻塞问题
  - 最近更新
  - 交接状态（哪些任务可以测试）

✓ TASK-BACKLOG.md 已填写完整
  - 优先级分类（MoSCoW）
  - 必须有的任务（详细）
  - 应该有的任务
  - 不能有的任务
  - Bug 清单（详细，如果有的话）

✓ 其他文件（TEAM-CONFIG.md, WORKFLOW-PROTOCOL.md, CONTEXT-BRIDGE.md）
  - 可以使用默认内容，不需要修改
```

---

### Step 3: 通知 OpenClaw 开始交接

**如何通知：**

```
# 方法 1: 通过消息发送给 OpenClaw

"我已经完成了项目交接文档的填写。
项目位于：/path/to/your-project
请 OpenClaw 读取所有 .md 文件并开始协作。"

---

# 方法 2: 直接让 OpenClaw 读取文件

"OpenClaw，请读取以下文件：
- /path/to/your-project/PROJECT-IDENTITY.md
- /path/to/your-project/TEAM-CONFIG.md
- /path/to/your-project/WORKFLOW-PROTOCOL.md
- /path/to/your-project/PROJECT-STATUS.md
- /path/to/your-project/CURRENT-WORK.md
- /path/to/your-project/TASK-BACKLOG.md
- /path/to/your-project/CONTEXT-BRIDGE.md
- /path/to/your-project/ONBOARDING.md

然后开始协作。"
```

---

### Step 4: OpenClaw 开始工作

**OpenClaw 会做什么：**

```
1. OpenClaw 读取所有 .md 文件
2. OpenClaw 理解项目状态
3. OpenClaw 分析任务清单
4. OpenClaw 分配任务：
   - 前端任务 → OpenCode
   - 后端任务 → Claude Code
   - 测试任务 → Kimi Code
5. OpenClaw 开始协调工作
```

---

### Step 5: 其他 Agent 开始工作

```
OpenCode（前端）：
  读取 CURRENT-WORK.md 看前端任务
  读取 PROJECT-STATUS.md 了解已完成的功能
  开始实现待办的前端任务

Claude Code（后端）：
  读取 CURRENT-WORK.md 看后端任务
  读取 PROJECT-STATUS.md 了解已完成的 API
  继续实现待办的后端 API
  修复已知的 Bug

Kimi Code（测试）：
  等待第一批功能完成
  进行集成测试
  报告 Bug 给 OpenCode 或 Claude Code
```

---

## 检查清单

**在完成交接之前，确保所有项目都已完成：**

---

### 文件完整性检查

```
所有必需的文件都存在吗？

□ PROJECT-IDENTITY.md
□ TEAM-CONFIG.md
□ WORKFLOW-PROTOCOL.md
□ PROJECT-STATUS.md
□ CURRENT-WORK.md
□ TASK-BACKLOG.md
□ CONTEXT-BRIDGE.md
□ ONBOARDING.md
```

---

### 内容完整性检查

#### PROJECT-IDENTITY.md

```
□ 项目名称已填写
□ 项目描述已详细填写（至少 3 行）
□ 项目目标已详细列出（至少 3 个）
□ 项目类型已选择（应该选 Ongoing Project）
□ 创建日期已填写（YYYY-MM-DD 格式）
□ 项目状态表格已填写（Overall Status, Version, Last Updated）
□ 利益相关者表格已填写（至少填写 Tech Lead）
□ 关键需求已详细列出（至少 3 个）
□ 技术约束已填写（如果有）
□ 下一步行动已详细列出（至少 3 个）
```

---

#### PROJECT-STATUS.md

```
□ 总体状态表格已填写（Overall Status, Current Phase, Version, Last Updated）
□ 已完成的功能已详细列出（至少 3 个）
  - 每个功能都填写了完成日期
  - 每个功能都标记了谁完成的
□ 进行中的工作已详细列出（如果有）
□ 待办任务已详细列出（至少 3 个）
  - 每个任务都标记了优先级
  - 每个任务都标记了谁来做
□ 阻塞问题已填写（如果没有，写"无阻塞性问题"）
□ 已知问题已详细列出（如果有 Bug）
  - 每个问题都标记了严重等级
  - 每个问题都标记了状态
  - 每个问题都标记了谁来修复
□ 质量指标已填写（如果有测试数据）
□ Bug 统计已填写（如果有 Bug）
□ 里程碑已详细列出（至少 3 个）
□ 部署历史已填写（如果已部署）
□ 下一步行动已详细列出（每个 Agent 都有）
□ 风险登记已填写（如果有风险）
```

---

#### CURRENT-WORK.md

```
□ OpenClaw 当前活动已填写
□ OpenCode 当前活动已详细填写（如果有前端代码）
  - 已填写任务描述
  - 已列出修改的文件（如果有的话）
  - 已列出待完成的 API 依赖（如果有的话）
□ Claude Code 当前活动已详细填写（如果有后端代码）
  - 已填写任务描述
  - 已列出开发中的 API（如果有的话）
  - 已列出数据库变更（如果有的话）
□ Kimi Code 当前活动已填写
□ 依赖关系已详细列出（非常重要！）
  - 前端等待后端的什么
  - 后端等待前端的什么
  - 测试等待前后端的什么
□ 阻塞问题已填写（如果没有，写"无阻塞性问题"）
□ 最近更新已详细列出（最近 5 天的更新，如果有的话）
□ 交接状态已详细列出
  - 待测试的任务有哪些
  - 测试中的任务有哪些
  - 待部署的任务有哪些
```

---

#### TASK-BACKLOG.md

```
□ 优先级分类已说明（MoSCoW）
□ 必须有的任务已详细列出（至少 3 个）
  - 每个任务都有详细描述
  - 每个任务都标记了优先级
  - 每个任务都标记了分配给哪个 Agent
  - 每个任务都标记了状态
  - 每个任务都标记了工作量
  - 每个任务都标记了验收标准
□ 应该有的任务已列出（如果有）
□ 可以有的任务已列出（如果有）
□ Bug 清单已详细列出（如果有 Bug）
  - 每个 Bug 都有严重等级
  - 每个 Bug 都有详细描述
  - 每个 Bug 都有重现步骤
  - 每个 Bug 都标记了分配给哪个 Agent
```

---

### 文件位置检查

```
所有 Markdown 文件都放在项目根目录吗？

□ 是的，所有文件都在 /path/to/your-project/ 根目录下
□ 所有文件名正确（没有改名）
□ 所有文件内容完整（没有被截断）
□ 所有文件格式正确（Markdown 格式）
```

---

## 常见问题

**Q1: 我的前端和后端代码混在一起，怎么办？**

**A:** 没问题！你需要在 `CURRENT-WORK.md` 中明确标注：

```markdown
## OpenCode - Current Activities（前端部分）

如果有前端代码（即使很小），也列在这里。

## Claude Code - Current Activities（后端部分）

如果有后端代码，也列在这里。

## Dependencies / 依赖关系

写清楚前后端是如何交互的。
```

---

**Q2: 我的项目只有前端代码，没有后端，还要写 Claude Code 的部分吗？**

**A:** 要写的！但可以简单写：

```markdown
## Claude Code - Current Activities

### Primary Task / 主任务

**当前状态：** 项目目前不需要后端 API

**计划任务：** 纯前端应用，不需要后端

| Field | Value |
|-------|-------|
| Task ID | N/A |
| API Endpoint | N/A |
| Started | N/A |
| Target Completion | N/A |
| Progress | N/A |

### APIs in Development / 开发中的 API

N/A - 项目是纯前端应用

### Notes / 备注

项目目前是纯前端应用，不需要后端 API。
所有的数据存储使用 LocalStorage 或其他前端方案。
```

---

**Q3: 我的项目只有后端代码，没有前端，还要写 OpenCode 的部分吗？**

**A:** 要写的！但可以简单写：

```markdown
## OpenCode - Current Activities

### Primary Task / 主任务

**当前状态：** 项目目前不需要前端界面

**计划任务：** 纯后端 API 服务

| Field | Value |
|-------|-------|
| Task ID | N/A |
| Component | N/A |
| Started | N/A |
| Target Completion | N/A |
| Progress | N/A |

### Files Modified / 修改的文件

N/A - 项目是纯后端应用

### Notes / 备注

项目目前是纯后端应用，提供 RESTful API。
前端开发将在 API 完成后进行。
```

---

**Q4: 我没有 Bug，Bug 清单要怎么写？**

**A:** 简单写：

```markdown
## Bug Backlog / Bug 清单

无已知 Bug。

---

*Last updated: YYYY-MM-DD*
```

---

**Q5: 我不知道如何分配"工作量"（Story Points 或小时数），怎么办？**

**A:** 没关系！可以估算一个大概的数字，或者留空：

```markdown
**工作量：** TBD（待评估）

或者

**工作量：** 8 小时（估算）
```

---

**Q6: 我不知道应该分配给哪个 Agent，怎么办？**

**A:** 参考以下规则：

```
前端任务 → OpenCode
后端任务 → Claude Code
测试任务 → Kimi Code
协调和管理 → OpenClaw

如果不确定，可以从以下角度思考：

- 这个任务是关于 UI/界面/用户交互吗？→ OpenCode
- 这个任务是关于 API/数据库/服务器逻辑吗？→ Claude Code
- 这个任务是关于测试/质量保证吗？→ Kimi Code
- 这个任务是关于协调/规划/部署吗？→ OpenClaw
```

---

**Q7: 我不知道应该给多少"验收标准"，怎么办？**

**A:** 至少 3 个验收标准：

```
✓ 功能完成了吗？（例如：API 正常工作）
✓ 边界情况处理了吗？（例如：错误处理）
✓ 用户体验好吗？（例如：加载状态）
```

---

**Q8: 我的 Bug 描述不知道写多详细，怎么办？**

**A:** 至少包含以下内容：

```
✓ Bug 严重等级（Critical/High/Medium/Low）
✓ 发现者（谁发现的）
✓ 报告日期
✓ 简短描述（一句话）
✓ 详细描述（至少 3 行）
  - 现象（发生了什么）
  - 重现步骤（怎么触发）
  - 预期行为（应该发生什么）
  - 实际行为（实际发生了什么）
```

---

**Q9: 我不知道如何描述"依赖关系"，怎么办？**

**A:** 从这些角度描述：

```
OpenCode 等待 Claude Code：
- 前端页面需要哪个 API？
- 前端组件需要哪个后端接口？

Claude Code 等待 OpenCode：
- 后端 API 需要什么前端需求？
- 后端数据格式需要前端确认吗？

Kimi Code 等待 OpenCode + Claude Code：
- 哪些功能完成后可以开始测试？
```

---

**Q10: 我不知道是否需要填写"质量指标"，怎么办？**

**A:** 如果你没有测试覆盖率数据，可以写：

```markdown
### Test Coverage / 测试覆盖率

| Component | Coverage % | Last Tested |
|-----------|------------|-------------|
| Frontend | 未测试 | - |
| Backend | 未测试 | - |
| Overall | 未测试 | - |

### Bug Statistics / Bug 统计

| Period | Total Bugs | Fixed Bugs | Open Bugs | Resolution Rate |
|--------|-----------|------------|-----------|-----------------|
| Last 7 days | 0 | 0 | 0 | - |
| Last 30 days | 0 | 0 | 0 | - |
| Total | 0 | 0 | 0 | - |
```

---

## 完整示例项目

**由于篇幅限制，我无法在这里写一个完整的示例项目的所有文件。**

**但请参考以下部分的详细示例：**

1. **PROJECT-IDENTITY.md** - 完整示例（已提供）
2. **PROJECT-STATUS.md** - 完整示例（已提供）
3. **CURRENT-WORK.md** - 完整示例（已提供）
4. **TASK-BACKLOG.md** - 部分示例（已提供）

**其他文件：**

5. **TEAM-CONFIG.md** - 使用默认内容即可，不需要修改
6. **WORKFLOW-PROTOCOL.md** - 使用默认内容即可，不需要修改
7. **CONTEXT-BRIDGE.md** - 使用默认内容即可，不需要修改
8. **ONBOARDING.md** - 使用默认内容即可，不需要修改

---

## 总结

**交接的关键：**

```
✓ 详细的文档（不要怕字多！）
✓ 明确的状态（哪些完成了，哪些进行中，哪些没开始）
✓ 清晰的优先级（Must Have > Should Have > Could Have）
✓ 明确的依赖关系（谁等谁）
✓ 详细的 Bug 报告（如何重现、预期 vs 实际）
```

**4 人 Agent 团队会快速上手！**

---

**作者：** 言午间

**创建日期：** 2026-02-24

**版本：** 1.0.0

---

**最后建议：**

1. **花时间填写** - 交接文档越详细，团队上手越快
2. **不要怕字多** - 详细 > 简洁
3. **提供示例** - 如果不确定如何填写，参考本文档的示例
4. **多次检查** - 使用"检查清单"确保所有内容都完整
5. **及时更新** - 如果交接后项目有变化，及时更新文档

---

**祝交接顺利！🎉**
