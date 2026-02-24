# P3-1: 可视化规则编辑器

**任务编号：** P3-1
**类型：** 产品功能
**优先级：** P1
**负责人：** Claude Code
**预计时间：** 8 小时

---

## 📋 任务描述

开发可视化规则编辑器的后端逻辑，让用户可以通过界面自定义清理规则，而无需编写代码。

---

## 🎯 目标

### Part 1: 规则类型定义（2 小时）

**文件：** `src/core/cleanup_rule.py`

**任务：**

1. 定义 CleanupRule 类
   - rule_id: 唯一标识符
   - rule_name: 规则名称（用户可见）
   - description: 规则描述
   - rule_type: 规则类型
   - conditions: 条件列表
   - action: 执行动作
   - is_enabled: 是否启用
   - created_at/updated_at: 时间戳

2. 定义 RuleType 枚举
   - FILE_EXTENSION: 文件扩展名匹配
   - FILE_PATTERN: 文件名模式匹配（通配符）
   - REGEX: 正则表达式匹配
   - FILE_SIZE: 文件大小匹配
   - DATE_CREATED: 创建日期匹配
   - DATE_MODIFIED: 修改日期匹配
   - PATH_PATTERN: 路径模式匹配

3. 定义 RuleCondition 类
   - condition_type: 条件类型
   - operator: 操作符（=, !=, >, <, contains, matches 等）
   - value: 条件值
   - is_case_sensitive: 是否区分大小写

4. 定义 RuleAction 枚举
   - DELETE: 删除
   - MOVE_TO: 移动到文件夹
   - ARCHIVE: 归档（压缩）
   - LOG_ONLY: 仅记录不删除

5. 定义 RuleOperator 枚举
   - EQUALS: 等于
   - NOT_EQUALS: 不等于
   - GREATER_THAN: 大于
   - LESS_THAN: 小于
   - GREATER_EQUAL: 大于等于
   - LESS_EQUAL: 小于等于
   - CONTAINS: 包含
   - STARTS_WITH: 开头是
   - ENDS_WITH: 结尾是
   - MATCHES: 正则匹配
   - IN: 在列表中
   - NOT_IN: 不在列表中

**验收标准：**

- [ ] CleanupRule 类定义完整
- [ ] 所有枚举类型定义清晰
- [ ] RuleCondition 支持多种条件类型和操作符
- [ ] 数据类使用 @dataclass，支持 to_dict() 和 from_dict()

---

### Part 2: 规则引擎实现（3 小时）

**文件：** `src/core/rule_engine.py`

**任务：**

1. 实现 RuleEngine 类
   - 加载规则
   - 评估规则是否匹配文件
   - 执行规则动作

2. 实现文件匹配逻辑
   ```python
   def match_file(self, file_path: str, rule: CleanupRule) -> bool:
       """评估规则是否匹配文件"""
   ```

3. 实现条件评估
   ```python
   def evaluate_condition(self, file_info: FileInfo, condition: RuleCondition) -> bool:
       """评估单个条件"""
   ```

4. 实现动作执行
   ```python
   def execute_action(self, file_path: str, action: RuleAction) -> ActionResult:
       """执行规则动作"""
   ```

5. 实现规则优先级
   - 按规则 ID 的顺序执行
   - 第一个匹配的规则生效
   - 支持规则组（AND/OR 逻辑）

**验收标准：**

- [ ] RuleEngine 能正确加载规则
- [ ] 文件匹配逻辑准确（测试多种规则类型）
- [ ] 条件评估支持所有操作符
- [ ] 动作执行安全（删除、移动、归档）
- [ ] 优先级机制正确

---

### Part 3: 规则管理器（2 小时）

**文件：** `src/core/rule_manager.py`

**任务：**

1. 实现 RuleManager 类
   - 管理所有规则
   - 增删改查操作
   - 规则导入/导出

2. 核心方法
   ```python
   def add_rule(self, rule: CleanupRule) -> str
   def update_rule(self, rule_id: str, rule: CleanupRule) -> bool
   def delete_rule(self, rule_id: str) -> bool
   def get_rule(self, rule_id: str) -> Optional[CleanupRule]
   def list_rules(self) -> List[CleanupRule]
   def enable_rule(self, rule_id: str) -> bool
   def disable_rule(self, rule_id: str) -> bool
   def export_rules(self, file_path: str) -> bool
   def import_rules(self, file_path: str) -> List[CleanupRule]
   def reorder_rules(self, rule_ids: List[str]) -> bool
   ```

3. 持久化存储
   - 保存到 JSON 文件（`src/config/cleanup_rules.json`）
   - 自动加载
   - 备份机制（修改前备份）

4. 预置规则库
   - 常用清理规则
   - 场景化规则包（游戏、办公、开发）
   - 社区规则（可选）

**验收标准：**

- [ ] 增删改查操作正常
- [ ] 规则导入/导出成功（JSON 格式）
- [ ] 持久化存储可靠
- [ ] 预置规则库可用

---

### Part 4: 规则测试和验证（1 小时）

**文件：** `tests/test_rule_engine.py`

**任务：**

1. 编写单元测试
   - 测试 CleanupRule 序列化
   - 测试规则匹配逻辑
   - 测试条件评估
   - 测试动作执行

2. 编写集成测试
   - 测试完整规则流程
   - 测试规则优先级
   - 测试规则导入/导出

3. 创建预置规则
   - 创建至少 5 个常用规则
   - 创建 4 个场景化规则包
   - 测试规则可用性

**验收标准：**

- [ ] 单元测试覆盖率 > 80%
- [ ] 集成测试通过
- [ ] 预置规则测试通过

---

## 📂 文件结构

```
purifyai/
├── src/
│   ├── core/
│   │   ├── cleanup_rule.py          # 规则类定义
│   │   ├── rule_engine.py           # 规则引擎
│   │   └── rule_manager.py          # 规则管理器
│   ├── config/
│   │   ├── cleanup_rules.json       # 用户自定义规则
│   │   └── preset_rules.json        # 预置规则库
│   └── data/
│       └── rule_history.json        # 规则使用历史
└── tests/
    └── test_rule_engine.py          # 规则引擎测试
```

---

## 🔗 依赖关系

| 依赖任务 | 状态 |
|----------|------|
| Week 1-2 P0 任务 | ✅ 已完成 |
| Scanner 清理功能 | ✅ 已实现 |

---

## 📝 备注

- 规则设计要考虑未来扩展性（插件支持）
- UI 集成由 OpenCode 负责（P3-2）
- 风险评估要与 Rules 集成
- 支持规则共享和社区规则（可选，未来版本）

---

## 🎯 成功指标

- ✅ 规则引擎能准确匹配和执行规则
- ✅ 规则管理器支持完整 CRUD 操作
- ✅ 预置规则库包含 5+ 常用规则和 4 个场景化规则包
- ✅ 测试覆盖率 > 80%

---

**任务创建时间：** 2026-02-24 21:35
**预计完成时间：** 2026-02-25 05:35（8 小时后）
