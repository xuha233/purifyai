# PurifyAI 智能体系统 (Agent System)

## 概述

PurifyAI 智能体系统是一个基于 OpenCode 风格构建的多智能体协作架构，用于实现智能化的磁盘清理。

## 架构

```
src/agent/
├── __init__.py          # 包入口，导出便利函数
├── orchestrator.py      # 智能体编排器（核心）
├── models_agent.py     # 数据模型
├── integration.py      # 集成辅助模块
├── prompts/            # 提示词模板
│   └── __init__.py
├── tools/               # 工具层
│   ├── __init__.py      # 工具注册表
│   ├── base.py         # 工具基类
│   └── file_tools.py   # 文件系统工具
└── agents/              # 智能体层
    ├── __init__.py
    ├── scan_agent.py   # 扫描智能体
    ├── review_agent.py # 审查智能体
    ├── cleanup_agent.py# 清理智能体
    └── report_agent.py # 报告智能体
```

## 核心组件

### 1. AgentOrchestrator (编排器)

负责协调不同类型的智能体，管理会话状态，处理 AI API 调用。

```python
from agent import get_orchestrator, AIConfig

# 创建编排器
ai_config = AIConfig(api_key="your-api-key", model="claude-opus-4-6")
orchestrator = get_orchestrator(ai_config)
```

### 2. 工具层

提供文件系统操作工具：

- **ReadTool**: 读取文件/目录内容
- **WriteTool**: 写入文件
- **EditTool**: 编辑文件（字符串替换）
- **GlobTool**: 文件模式搜索
- **GrepTool**: 内容搜索

### 3. 智能体层

#### ScanAgent (扫描智能体)

扫描文件系统，识别垃圾文件并生成清理计划。

```python
from agent import create_scan_agent

scan_agent = create_scan_agent()
result = scan_agent.scan(
    scan_paths=["C:\\Temp", "C:\\Windows\\Temp"],
    scan_patterns=["temp_files", "cache_files"]
)
```

#### ReviewAgent (审查智能体)

审查清理计划的安全性，防止误删重要文件。

```python
from agent import create_review_agent

review_agent = create_review_agent()
result = review_agent.review_cleanup_plan(cleanup_items)
```

#### CleanupAgent (清理智能体)

执行文件清理操作。

```python
from agent import create_cleanup_agent

cleanup_agent = create_cleanup_agent()
result = cleanup_agent.execute_cleanup(
    cleanup_items=list_of_items,
    is_dry_run=True  # 演练模式
)
```

#### ReportAgent (报告智能体)

生成清理操作报告。

```python
from agent import create_report_agent

report_agent = create_report_agent()
report = report_agent.generate_report(scan_result, cleanup_result)
markdown = report_agent.format_report_as_markdown(report)
```

## 完整流程示例

```python
from agent.integration import get_agent_integration

# 创建集成管理器
integration = get_agent_integration()

# 运行完整清理流程
result = integration.run_full_cleanup(
    scan_paths=["C:\\Temp"],
    scan_patterns=["temp_files", "cache_files"],
    is_dry_run=True,      # 演练模式
    skip_review=False     # 执行审查
)

if result["success"]:
    print("清理成功！")
    print(f"释放空间: {result['cleanup_result']['total_freed_bytes']} 字节")
else:
    print(f"清理失败: {result['error']}")
```

## 提示词系统

每个智能体都有专门的系统提示词，定义在 `prompts/__init__.py` 中：

- `SCAN_PROMPT`: 扫描智能体提示词
- `REVIEW_PROMPT`: 审查智能体提示词
- `CLEANUP_PROMPT`: 清理智能体提示词
- `REPORT_PROMPT`: 报告智能体提示词

## 配置

在应用配置中添加 AI 设置：

```json
{
  "ai": {
    "api_key": "your-anthropic-api-key",
    "model": "claude-opus-4-6",
    "max_tokens": 8192,
    "temperature": 0.7
  }
}
```

## 模拟模式

当 API 密钥未配置时，系统会自动进入模拟模式，返回预设的模拟响应。

## 集成到 SmartCleaner

修改 `src/core/smart_cleaner.py` 以使用智能体系统：

```python
from agent.integration import get_agent_integration

class SmartCleaner:
    def __init__(self):
        # ... 现有初始化 ...
        self.agent_integration = get_agent_integration()

    def scan_with_agent(self, paths):
        """使用智能体进行扫描"""
        return self.agent_integration.run_scan_only(paths)

    def cleanup_with_agent(self, items, is_dry_run=True):
        """使用智能体进行清理"""
        return self.agent_integration.run_cleanup_only(items, is_dry_run)
```

## 安全性

- 审查智能体会自动过滤危险路径
- 默认启用演练模式
- 失败项可重试
- 详细日志记录所有操作

## 日志

智能体系统使用 `utils.logger` 进行日志记录：

```
[ORCHESTRATOR] 初始化完成, AI模型: claude-opus-4-6
[SCAN_AGENT] 初始化扫描智能体
[SCAN_AGENT] 开始扫描: ['C:\\Temp']
[REVIEW_AGENT] 审查完成: 阻断 0 项
[CLEANUP_AGENT] 清理完成: 成功 100, 失败 0
[REPORT_AGENT] 生成报告
```
