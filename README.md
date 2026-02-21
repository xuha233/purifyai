# PurifyAI - 智能清理工具

> 基于 PyQt5 开发的 Windows 系统清理工具，集成 AI 智能评估功能

## 📖 快速开始

### 环境要求

- Python 3.14+
- Windows 7/8/10/11

### 安装

```bash
cd src
pip install -r ../requirements.txt
python main.py
```

## 📚 技术文档

完整的技术文档请参阅 **`技术档案.md`**

- [x] 项目概述与功能特性
- [x] 技术架构设计
- [x] 模块依赖关系
- [x] 核心类说明
- [x] API 接口文档
- [x] 数据库结构
- [x] 配置管理说明
- [x] 安装部署指南
- [x] 开发与测试指南
- [x] 常见问题解答

## 📦 项目结构

```
diskclean/
├── src/              # 源代码目录
│   ├── core/         # 核心业务模块
│   ├── ui/           # UI 模块
│   ├── utils/        # 工具模块
│   ├── data/         # 数据文件
│   └── docs/         # 文档
├── requirements.txt   # 依赖清单
├── settings.json     # 应用配置
└── 技术档案.md      # 完整技术文档
```

## 🚀 主要功能

| 功能模块 | 说明 |
|---------|------|
| **系统扫描** | 扫描临时文件、预取文件、日志等 |
| **浏览器清理** | 支持 Chrome、Edge、Firefox |
| **AppData扫描** | 智能风险评估的 AppData 数据扫描 |
| **自定义扫描** | 用户自定义路径扫描 |
| **AppData迁移** | 大型文件夹迁移工具(Demo版本) |
| **系统托盘** | 后台运行和快速清理 |
| **自动清理** | 定时清理和磁盘空间阈值触发 |
| **回收功能** | 可选的自定义回收站 |

## ⚙️ 配置说明

配置文件: `src/purifyai_config.json`

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| notification | 系统通知 | true |
| system_tray | 系统托盘 | true |
| ai | AI评估功能 | false |
| appdata_migration | AppData迁移功能 | false |

## 📞 技术支持

详见 `技术档案.md` 第14章"常见问题"

---

**版本**: v1.0
**更新日期**: 2026-02-21
