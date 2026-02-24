# UI 兼容性问题修复任务 - PurifyAI v0.7.0 RC1

**任务来源：** Kimi Code 集成测试报告
**Assigned To:** OpenCode
**Priority:** High
**Estimated Time:** 10-15 分钟
**Start Time:** 2026-02-24 11:50

---

## 1. 测试发现的问题

| Bug ID | 描述 | 文件 | 行号 | 严重程度 |
|--------|------|------|------|----------|
| BUG-010 | FluentIcon.TASK 不存在 | agent_widgets.py | 51 | High |
| BUG-011 | BodyLabel.setIcon() 不存在 | agent_hub_page.py | 239 | High |
| BUG-012 | AgentTheme.PRIMARY 属性缺失 | agent_hub_page.py | 155 | Medium |

**注意：** 经初步检查，`AgentTheme.PRIMARY` 实际上是存在的（在 agent_theme.py:29）。可能需要确认测试环境的一致性。

---

## 2. 修复步骤

### 任务 1: 检查并修复 FluentIcon 兼容性

**文件：** `G:\docker\diskclean\src\ui\agent_widgets.py`

**步骤：**
1. 查找所有 `FluentIcon.TASK` 的使用
2. 替换为有效的图标，如 `FluentIcon.CALENDAR` 或 `FluentIcon.VIEW`

**参考代码：**

```python
# ❌ 错误代码（如果存在）
icon = IconWidget(FluentIcon.TASK)

# ✅ 正确代码
icon = IconWidget(FluentIcon.CALENDAR)
# 或者
icon = IconWidget(FluentIcon.VIEW)
```

**可用的 FluentIcon 列表：**
- `FluentIcon.CALENDAR`
- `FluentIcon.VIEW`
- `FluentIcon.DOCUMENT`
- `FluentIcon.HISTORY`
- `FluentIcon.ROBOT`
- `FluentIcon.DELETE`
- `FluentIcon.SAVE`
- `FluentIcon.EDIT`
- `FluentIcon.ACCEPT`

---

### 任务 2: 检查并修复 BodyLabel.setIcon() 问题

**文件：** `G:\docker\diskclean\src\ui\agent_hub_page.py`

**步骤：**
1. 查找所有对 `BodyLabel` 对象调用 `setIcon()` 的代码
2. 使用正确的组件类型或在旁边添加 `IconWidget`

**参考代码：**

```python
# ❌ 错误代码
label = BodyLabel("文案")
label.setIcon(FluentIcon.SOME_ICON)  # ❌ BodyLabel 没有 setIcon 方法

# ✅ 正确代码 - 方式 1：使用 IconWidget
icon_widget = IconWidget(FluentIcon.SOME_ICON)
icon_widget.setFixedSize(20, 20)

# 或者 ✅ 正确代码 - 方式 2：使用 StrongBodyLabel + 图标（如果有）
# 根据上下文使用合适的组合
```

---

### 任务 3: 验证 AgentTheme 属性

**文件：** `G:\docker\diskclean\src\ui\agent_hub_page.py`
**参考：** `G:\docker\diskclean\src\ui\agent_theme.py`

**步骤：**
1. 确认 `AgentTheme.PRIMARY` 是否在 `agent_theme.py` 中定义
2. 如果已定义（目前看是存在的），则无需修复
3. 如果未定义，在使用的地方替换为已存在的属性值

**AgentTheme 已定义的属性：**
```python
IDLE = "#999999"
RUNNING = "#0078D4"
COMPLETED = "#28a745"
ERROR = "#dc3545"
PAUSED = "#FFA500"
PRIMARY = "#0078D4"  # ✅ 已定义

SCAN_COLOR = "#0078D4"
REVIEW_COLOR = "#FFA500"
CLEANUP_COLOR = "#28a745"
REPORT_COLOR = "#9C27B0"
```

---

## 3. 验证修复

修复完成后，执行以下命令验证：

```bash
cd G:\docker\diskclean

# 检查 Python 语法
python -m py_compile src/ui/agent_widgets.py
python -m py_compile src/ui/agent_hub_page.py

# 尝试导入模块
python -c "from src.ui.agent_widgets import *; print('agent_widgets OK')"
python -c "from src.ui.agent_hub_page import *; print('agent_hub_page OK')"
python -c "from src.ui.agent_theme import AgentTheme; print('PRIMARY:', AgentTheme.PRIMARY)"

# 运行 UI 相关测试（如果有）
python -m pytest tests/ -k "ui" -v
```

---

## 4. 测试建议

修复后，建议进行简单测试：

1. **启动应用测试**
   ```bash
   python src/main.py
   ```
   - 应用应该能正常启动
   - Agent Hub 页面应该能正常加载
   - 不应该抛出 AttributeError

2. **页面切换测试**
   - 在不同页面之间切换
   - 确保图标正常显示
   - 确保没有崩溃

---

## 5. 提交修复

修复完成后，提交代码：

```bash
cd G:\docker\diskclean

# 添加修改的文件
git add src/ui/agent_widgets.py
git add src/ui/agent_hub_page.py

# 提交修复
git commit -m "修复 UI 兼容性问题

- 修复 FluentIcon.TASK 不存在的问题
- 修复 BodyLabel.setIcon() 不存在的问题
- 验证 AgentTheme.PRIMARY 属性可用

Bug: BUG-010, BUG-011, BUG-012
来源: Kimi Code 集成测试报告"

# 推送到远程（可选）
git push origin master
```

---

## 6. 注意事项

1. **确认目标环境：**
   - 确认 qfluentwidgets 版本
   - 确认 PyQt5 版本

2. **兼容性原则：**
   - 使用最常见的 FluentIcon 属性
   - 避免使用实验性或新增的 API

3. **日志记录：**
   - 如果修复了某个具体的代码行，记录下来
   - 修复前后对比

---

## 7. 如果问题不存在

如果在修复时发现这些问题实际上不存在（可能是测试环境问题）：

1. 记录实际代码状态
2. 说明问题可能的原因（缓存、测试环境差异等）
3. 运行测试确认代码确实没有问题

---

## 8. 修复后报告

**请在修复完成后，提供以下信息：**

| Bug ID | 修复状态 | 修复方式 | 备注 |
|--------|----------|----------|------|
| BUG-010 | ☐ |  |  |
| BUG-011 | ☐ |  |  |
| BUG-012 | ☐ |  |  |

**验证结果：**
- [ ] Python 语法检查通过
- [ ] 模块导入成功
- [ ] 应用可以正常启动
- [ ] Agent Hub 页面正常加载

**遇到的问题（如果有）：**
[填写]

---

**祝修复顺利！如有问题，随时联系 OpenClaw。**

---

**版本：** v0.7.0 RC1
**创建时间：** 2026-02-24 11:50
**创建者：** 小午（OpenClaw）
