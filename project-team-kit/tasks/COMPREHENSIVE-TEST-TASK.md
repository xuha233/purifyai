# PurifyAI v0.7.0 RC1 - 综合测试任务

**测试版本：** v0.7.0 RC1
**测试日期：** 2026-02-24 12:00
**测试工程师：** Kimi Code
**测试目标：** 验证 UI 修复效果完成功能测试

---

## 🎯 测试目标

1. **验证 UI 修复效果** - 确认 OpenCode 修复的 3 个 Bug 已解决
2. **完整功能测试** - 验证所有核心功能正常工作
3. **集成测试** - 端到端测试完整的清理流程

---

## ✅ 已修复的 Bug（待验证）

| Bug ID | 描述 | 修复内容 | 位置 |
|--------|------|----------|------|
| BUG-013 | QCheckBox 导入缺失 | 添加 QCheckBox 到导入列表 | agent_widgets.py:21 |
| BUG-014 | selected_items 未初始化 | 添加 `self.selected_items = set()` | agent_widgets.py:581 |
| BUG-015 | STATUS_NAMES 引用错误 | 修复为 STATUS_NAMES | agent_theme.py:159 |

**验证方法：** 运行单元测试 + 导入测试

---

## 🧪 测试计划

### Phase 1: 单元测试（核心模块）

#### 1.1 扫描模块测试

```bash
pytest tests/test_scan.py -v
```

**预期结果：** 所有测试通过 ✅
```
tests/test_scan.py::test_basic_scan PASSED
tests/test_scan.py::test_file_pattern_filter PASSED
...
```

---

#### 1.2 评分模块测试

```bash
pytest tests/test_rating.py -v
```

**预期结果：** 所有测试通过 ✅

---

#### 1.3 规则引擎测试

```bash
pytest tests/test_rules.py -v
```

**预期结果：** 所有测试通过 ✅

---

#### 1.4 AI 分析器测试

```bash
pytest tests/test_ai_analyzer.py -v
```

**预期结果：** 所有测试通过 ✅

---

#### 1.5 成本控制测试

```bash
pytest tests/test_cost_control_simple.py -v
```

**预期结果：** 所有测试通过 ✅

**关键验证点：**
- ✅ 成本限制正常工作
- ✅ 降级到规则引擎正常切换
- ✅ 成本统计准确

---

#### 1.6 Agent 系统测试

```bash
pytest tests/test_agent_system.py -v
```

**预期结果：**
- 核心测试通过 ✅
- GUI 相关测试如果跳过可以接受
- 19/25 测试通过（6 个 GUI 跳过）

---

### Phase 2: UI 修复验证

#### 2.1 检查 QCheckBox 导入

```bash
cd G:\docker\diskclean && grep "QCheckBox" src/ui/agent_widgets.py
```

**预期结果：**
```python
from PyQt5.QtWidgets import (
    # ...
    QCheckBox,
)
```

✅ **验证通过：** QCheckBox 已导入

---

#### 2.2 检查 selected_items 初始化

```bash
cd G:\docker\diskclean && grep -A 2 "def __init__" src/ui/agent_widgets.py | grep "selected_items"
```

**预期结果：**
```python
self.selected_items = set()
```

✅ **验证通过：** selected_items 已初始化

---

#### 2.3 检查 STATUS_NAMES 引用

```bash
cd G:\docker\diskclean && grep "STATUS_NAMES" src/ui/agent_theme.py
```

**预期结果：**
```python
return cls.STATUS_NAMES.get(status, status)
```

✅ **验证通过：** STATUS_NAMES 引用正确

---

#### 2.4 UI 模块导入测试

```bash
cd G:\docker\diskclean && python -c "
import sys
sys.path.insert(0, '.')
from src.ui.agent_widgets import TaskCard, ItemListCard
from src.ui.agent_hub_page import AgentHubPage
from src.ui.agent_theme import AgentTheme, AgentStatus
print('✅ All UI imports successful')
print(f'AgentTheme.PRIMARY = {AgentTheme.PRIMARY}')
print(f'AgentStatus.get_name(\"idle\") = {AgentStatus.get_name(\"idle\")}')
"
```

**预期结果：**
```
✅ All UI imports successful
AgentTheme.PRIMARY = #0078D4
✅ AgentStatus.get_name('idle') = 就绪
```

---

### Phase 3: 集成测试

#### 3.1 扫描流程集成测试

**测试目标：** 验证完整的扫描流程

```bash
cd G:\docker\diskclean && python -c "
import sys
sys.path.insert(0, '.')

from src.core.scanner import DiskScanner
from src.core.rating import RatingSystem
from src.core.rule_engine import RuleEngine

# 初始化
scanner = DiskScanner()
rating = RatingSystem()
engine = RuleEngine()

# 扫描测试目录
test_dir = 'C:\\Windows\\Temp'
items = scanner.scan_directory(test_dir, max_files=100)

print(f'✅ 扫描完成: {len(items)} 个文件')

# 评分
for item in items[:10]:
    score = rating.rate_item(item)
    item.score = score

print(f'✅ 评分完成: 前 10 个文件已评分')

# 规则过滤
high_risk = [item for item in items if item.score >= 70]
print(f'✅ 规则过滤: {len(high_risk)} 个高风险文件')
"
```

**预期结果：**
```
✅ 扫描完成: XX 个文件
✅ 评分完成: 前 10 个文件已评分
✅ 规则过滤: XX 个高风险文件
```

---

#### 3.2 AI 分析集成测试

**测试目标：** 验证 AI 分析器与成本控制的协作

```bash
cd G:\docker\diskclean && python -c "
import sys
sys.path.insert(0, '.')

from src.core.ai_analyzer import AIAnalyzer
from src.core.cost_controller import CostController

# 初始化
analyzer = AIAnalyzer()
cost_controller = CostController(mode='BUDGET', budget_usd=1.0)

# 创建测试待分析项
from src.core.models import ScanItem, RiskLevel
test_item = ScanItem(
    path='C:\\test.txt',
    size=1024,
    risk_level=RiskLevel.MEDIUM
)

# 测试成本控制
if cost_controller.can_make_call():
    print('✅ 成本控制允许 AI 调用')
else:
    print('⚠️ 成本控制拒绝 AI 调用')

# 获取成本报告
report = cost_controller.get_usage_report()
print(f'✅ 成本报告: {report}')
"
```

**预期结果：**
```
✅ 成本控制允许 AI 调用
✅ 成本报告: {'total_calls': X, 'estimated_cost_usd': X.XX}
```

---

#### 3.3 Agent 错误恢复测试

**测试目标：** 验证错误处理和恢复机制

```bash
cd G:\docker\diskclean && python -c "
import sys
sys.path.insert(0, '.')

from src.agent.orchestrator import AgentOrchestrator

# 初始化
orchestrator = AgentOrchestrator()

# 测试异常处理
try:
    orchestrator.handle_error('测试错误', 'test_module')
    print('✅ 错误处理成功')
except Exception as e:
    print(f'❌ 错误处理失败: {e}')

# 测试恢复机制
try:
    recovered = orchestrator.attempt_recovery('test_module')
    print(f'✅ 恢复机制正常: succeed={recovered}')
except Exception as e:
    print(f'⚠️ 恢复机制: {e}')
"
```

**预期结果：**
```
✅ 错误处理成功
✅ 恢复机制正常: succeed=True/False
```

---

### Phase 4: 端到端测试（可选）

**注意：** 此测试可能需要 GUI 环境，如果不可用可跳过

```bash
cd G:\docker\diskclean && python src/main.py
```

**测试步骤：**
1. 启动应用 ✅
2. Agent Hub 页面加载 ✅
3. 扫描目录 ✅
4. 查看评分结果 ✅
5. 执行清理 ✅
6. 查看清理报告 ✅

---

## 📊 测试报告模板

请在测试完成后，填写以下报告：

---

### 测试执行摘要

| 测试阶段 | 测试项 | 通过 | 失败 | 跳过 | 通过率 |
|----------|--------|------|------|------|--------|
| Phase 1: 单元测试 | 6 | - | - | - | -% |
| Phase 2: UI 验证 | 4 | - | - | - | -% |
| Phase 3: 集成测试 | 3 | - | - | - | -% |
| Phase 4: 端到端测试 | 1 | - | - | - | -% |
| **总计** | **14** | **-** | **-** | **-** | **-%** |

---

### Bug 修复验证

| Bug ID | 描述 | 修复状态 | 验证结果 |
|--------|------|----------|----------|
| BUG-013 | QCheckBox 导入缺失 | 已修复 | ⬜ 待验证 |
| BUG-014 | selected_items 未初始化 | 已修复 | ⬜ 待验证 |
| BUG-015 | STATUS_NAMES 引用错误 | 已修复 | ⬜ 待验证 |

---

### 发现的问题

| 编号 | 描述 | 严重程度 | 位置 |
|------|------|----------|------|
| - | (留空) | - | - |

---

### 性能测试结果

| 测试项 | 目标 | 实际 | 状态 |
|--------|------|------|------|
| 页面切换响应 | <500ms | -ms | ⬜ 待测 |
| 5000 项列表渲染 | <800ms | -ms | ⬜ 待测 |

---

### 总体评估

**发布建议：**
- ⬜ ✅ 通过 - 可以发布 v0.7.0 RC1
- ⬜ ⚠️ 有条件通过 - 需修复小问题后发布
- ⬜ ❌ 不通过 - 需修复重要问题后重新测试

**备注：**
```
（在此填写测试总结和建议）
```

---

## 📝 测试注意事项

1. **环境要求：**
   - Python 3.14.3
   - PyQt5 已安装
   - 测试目录有足够权限

2. **已知限制：**
   - GUI 测试可能不可用，可以跳过 Phase 4
   - AI 测试需要 API 密钥，可能跳过

3. **失败处理：**
   - 如果测试失败，记录详细错误信息
   - 如果是环境问题，标记为"跳过"
   - 如果是代码问题，记录为"失败"并提供建议

---

## 🔚 测试完成标准

**必须满足：**
- ⬜ 所有关键单元测试通过
- ⬜ UI 修复验证通过
- ⬜ 集成测试至少 2/3 通过
- ⬜ 没有严重错误（High/Blocker）

**理想满足：**
- ⬜ 所有单元测试通过
- ⬜ 所有集成测试通过
- ⬜ 端到端测试通过

---

**准备好后开始执行测试。**
