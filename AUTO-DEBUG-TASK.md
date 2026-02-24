# Debug 任务: 一键清理按钮报错

## 任务描述

用户点击"一键清理"按钮时，应用报错：

```
错误类型: AttributeError
发生次数: 18

最近错误详情:
============================================================

时间: 2026-02-24 23:16:32.826420
消息: 'IconWidget' object has no attribute 'isNull'

调用上下文:
  exception_type: <class 'AttributeError'>
  uncaught: True
  caller_function: mouseReleaseEvent
  caller_line: 82
```

## 调试目标

1. 定位 IconWidget.isNull 调用的具体代码位置
2. 修复 AttributeError
3. 验证修复后一键清理功能正常

## 调试步骤

### Phase 1: 问题定位

1. 在 `G:/docker/diskclean/src/` 目录下搜索 IconWidget 的使用
2. 查找可能导致 mouseReleaseEvent 调用的代码
3. 检查与一键清理相关的文件：
   - agent_hub_page.py（一键清理按钮）
   - cleanup_preview_card.py
   - cleanup_progress_widget.py

### Phase 2: 问题分析

1. 检查 IconWidget 的正确用法（查阅 qfluentwidgets 文档或示例）
2. 找出为什么 IconWidget 会调用 .isNull()
3. 判断是否应该用其他方法替换，或者移除这个调用

### Phase 3: 修复实现

1. 实施修复方案
2. 确保不破坏其他功能

### Phase 4: 验证测试

1. 编译检查：`python -m py_compile [修改的文件]`
2. 启动应用测试：运行 `python src/main.py`
3. 模拟用户操作：点击"一键清理"按钮
4. 检查是否还有报错

## 报告要求

请按以下格式输出调试报告：

```
# Debug 报告: 一键清理按钮报错

## 问题描述
[简要描述]

## 问题定位
- 发现的问题文件：[文件名:行号]
- 错误代码：[代码片段]
- 根本原因：[原因]

## 修复方案
- 修复代码：[修复后的代码]
- 修复说明：[说明]

## 测试结果
- 编译状态：✅ / ❌
- 运行测试：✅ / ❌
- 一键清理功能：✅ 正常 / ❌ 异常

## 附加说明
[任何相关说明]
```

## 项目信息

- 项目路径：`G:/docker/diskclean`
- 分支：`feature/v1.0-refactor`
- Agent: Claude Code (调试) / OpenCode (复审)

---

**任务创建时间：** 2026-02-24 23:22
**任务创建者：** 小午 🦁
