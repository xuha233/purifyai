# P0-5: 智能体页面重新设计

**任务编号：** P0-5
**创建时间：** 2026-02-24 18:30
**开发者：** frontend + docs
**预计时间：** 6 小时
**优先级：** P0（核心功能）
**状态：** 待开始

---

## 任务目标

重新设计 AgentHubPage（智能体中心页面），提升用户体验和视觉一致性，集成所有清理功能入口。

---

## 核心需求

### 1. 现状分析

**当前问题：**
- 页面功能布局混乱
- 选项卡过多（7-8 个）
- 视觉层次不清晰
- 新功能（一键清理、增量清理）缺乏明确入口

**需要整合的功能：**
- 一键清理
- 增量清理
- 智能推荐
- 智能体状态显示
- 智能体控制（启动/停止/配置）

### 2. 设计目标

- **简化选项卡**：从 7-8 个缩减到 3-4 个
- **清晰视觉层次**：最重要的功能突出显示
- **统一设计语言**：使用 Fluent Design 风格
- **完整功能入口**：所有 P0 功能都有明确入口

---

## 详细任务分解

### Part 1: 重新设计页面布局（docs，30 分钟）

**文件：** `project-team-kit/AGENT-HUB-PAGE-REDESIGN.md`

**任务：**
1. 分析当前 `src/ui/agent_hub_page.py` 代码结构
2. 设计新的页面布局
3. 定义新的选项卡结构（4 个）
4. 设计功能入口位置
5. 创建设计文档

**交付物：**
- 页面布局设计图（文字描述）
- 选项卡结构定义
- 功能入口分配

---

### Part 2: 精简选项卡（frontend，2 小时）

**文件：** `src/ui/agent_hub_page.py`

**新选项卡结构：**
1. **概览**（Overview）
   - 智能体状态卡片
   - 一键清理按钮（主入口）
   - AI 健康评分（P1，未来）
   - 清理统计信息

2. **清理**（Cleanup）
   - 一键清理（详细操作）
   - 增量清理
   - 智能推荐模式选择

3. **控制**（Control）
   - 智能体列表
   - 智能体控制（启动/停止/配置）
   - 性能监控

4. **设置**（Settings）
   - 清理偏好设置
   - 智能体配置
   - 备份设置

**任务：**
1. 重构 `AgentHubPage` 类
2. 创建新的选项卡容器
3. 实现选项卡导航（Fluent 样式）
4. 迁移现有功能到新选项卡

---

### Part 3: 主入口优化（frontend，2 小时）

**文件：** `src/ui/agent_hub_page.py + src/ui/agent_home_widget.py`

**目标：** 在"概览"选项卡中突出显示主入口

**任务：**
1. 一键清理按钮优化
   - 更大、更醒目
   - 添加图标
   - 显示预计清理空间

2. 增量清理按钮
   - 次重要按钮
   - 与一键清理并列或次要位置
   - 显示"仅新增文件"提示

3. 操作引导
   - 添加简短说明
   - 首次使用时显示引导（可选）

---

### Part 4: 视觉优化（frontend，1.5 小时）

**文件：** `src/ui/agent_hub_page.py`

**任务：**
1. 统一颜色方案（使用 AgentTheme）
2. 优化间距和布局
3. 添加卡片阴影和圆角
4. 改善字体层次结构
5. 添加微动画（按钮悬停、点击反馈）

---

## 验收标准

### P0-4 验证结果：93% ✅

**已完成部分：**
- ✅ 后端方法：`load_last_cleanup_files()`, `save_last_cleanup_files()`, `recommend_incremental()`
- ✅ 前端 UI：增量清理按钮、CleanupPreviewCard 徽章、CleanupProgressWidget 保存逻辑

**潜在问题：**
- ⚠️ CleanupOrchestrator 未集成增量清理逻辑（仅在 UI 层保存）
- ⚠️ 数据目录硬编码

**总体完成度：** 93% ✅

---

### P0-5 验收标准（待完成）

1. ✅ 选项卡精简到 4 个
2. ✅ 所有 P0 功能都有明确入口
3. ✅ 视觉设计一致（Fluent Design）
4. ✅ 主入口突出显示
5. ✅ 代码编译通过
6. ✅ UI 功能测试通过

---

## 实施步骤

### Step 1: 创建 P0-5 任务文件

```bash
# 在 project-team-kit/tasks/ 创建任务文件
# P0-5: 智能体页面重新设计
```

### Step 2: 使用 Agent Teams 执行

```bash
# 在 Claude Code 中启用 Agent Teams
cd G:/docker/diskclean
claude

# docs 团队负责 Part 1
# frontend 团队负责 Part 2-4
```

### Step 3: 测试验证

```bash
# 编译检查
python -m py_compile src/ui/agent_hub_page.py

# UI 测试（frontend 团队）
python src/main.py
```

### Step 4: Git 提交

```bash
git add src/ui/agent_hub_page.py
git commit -m "feat: P0-5 智能体页面重新设计"
```

---

## 参考文件

- `src/ui/agent_hub_page.py` - 当前实现
- `src/ui/agent_theme.py` - 颜色主题
- `src/ui/agent_widgets.py` - 自定义 widgets
- `project-team-kit/DEV-PROGRESS-REPORT-v1.0.md` - 开发进度

---

## 预期成果

### P0-4：93% ✅（已完成）

### P0-5（目标）

- 完成时间：6 小时
- 代码变更：~800 行修改/新增
- 用户体验：大幅提升
- 代码质量：编译通过 + 测试通过

---

**更新时间：** 2026-02-24 18:30
**负责人：** 小午 🦁

