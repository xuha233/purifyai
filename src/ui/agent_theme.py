# -*- coding: utf-8 -*-
"""
智能体主题颜色定义

定义智能体系统中使用的各种状态颜色
"""


class AgentTheme:
    """智能体主题颜色"""

    # 状态颜色
    IDLE = "#999999"  # 灰色
    RUNNING = "#0078D4"  # 蓝色
    COMPLETED = "#28a745"  # 绿色
    ERROR = "#dc3545"  # 红色
    PAUSED = "#FFA500"  # 橙色
    PRIMARY = "#0078D4"  # 主色调 - 蓝色

    # 阶段颜色
    SCAN_COLOR = "#0078D4"  # 蓝色
    REVIEW_COLOR = "#FFA500"  # 橙色
    CLEANUP_COLOR = "#28a745"  # 绿色
    REPORT_COLOR = "#9C27B0"  # 紫色

    # AI 风险等级颜色
    SAFE = "#52C41A"  # 绿色
    SUSPICIOUS = "#FAAD14"  # 黄色
    DANGEROUS = "#FF4D4F"  # 红色

    # 背景颜色
    CARD_BG = "#ffffff"
    BG_LIGHT = "#f5f5f5"
    BG_DARK = "#e9ecef"

    # 文本颜色
    TEXT_PRIMARY = "#2c2c2c"
    TEXT_SECONDARY = "#666666"
    TEXT_TERTIARY = "#999999"

    # 渐变色
    PRIMARY_GRADIENT = ("#0078D4", "#005a9e")
    SUCCESS_GRADIENT = ("#28a745", "#218838")
    WARNING_GRADIENT = ("#ffa500", "#e69400")
    ERROR_GRADIENT = ("#dc3545", "#c82333")

    @classmethod
    def get_stage_color(cls, stage: str) -> str:
        """获取阶段颜色

        Args:
            stage: 阶段名称 (scan/review/cleanup/report)

        Returns:
            颜色字符串
        """
        return {
            "scan": cls.SCAN_COLOR,
            "review": cls.REVIEW_COLOR,
            "cleanup": cls.CLEANUP_COLOR,
            "report": cls.REPORT_COLOR,
        }.get(stage, cls.IDLE)

    @classmethod
    def get_risk_color(cls, risk: str) -> str:
        """获取风险等级颜色

        Args:
            risk: 风险等级 (safe/suspicious/dangerous)

        Returns:
            颜色字符串
        """
        return {
            "safe": cls.SAFE,
            "suspicious": cls.SUSPICIOUS,
            "dangerous": cls.DANGEROUS,
        }.get(risk, cls.TEXT_TERTIARY)

    @classmethod
    def get_status_color(cls, status: str) -> str:
        """获取状态颜色

        Args:
            status: 状态 (idle/running/completed/error/paused)

        Returns:
            颜色字符串
        """
        return {
            "idle": cls.IDLE,
            "running": cls.RUNNING,
            "completed": cls.COMPLETED,
            "error": cls.ERROR,
            "paused": cls.PAUSED,
        }.get(status, cls.TEXT_TERTIARY)


# 阶段定义
class AgentStage:
    """智能体阶段常量"""

    SCAN = "scan"
    REVIEW = "review"
    CLEANUP = "cleanup"
    REPORT = "report"

    STAGE_NAMES = {SCAN: "扫描", REVIEW: "审查", CLEANUP: "执行", REPORT: "报告"}

    STAGE_ICONS = {
        SCAN: "search",
        REVIEW: "checkbox",
        CLEANUP: "delete",
        REPORT: "document",
    }

    @classmethod
    def get_name(cls, stage: str) -> str:
        """获取阶段名称"""
        return cls.STAGE_NAMES.get(stage, stage)

    @classmethod
    def get_icon(cls, stage: str) -> str:
        """获取阶段图标名称"""
        return cls.STAGE_ICONS.get(stage, "info")

    @classmethod
    def get_all_stages(cls) -> list:
        """获取所有阶段列表"""
        return [cls.SCAN, cls.REVIEW, cls.CLEANUP, cls.REPORT]


# 状态定义
class AgentStatus:
    """智能体状态常量"""

    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    ERROR = "error"

    STATUS_NAMES = {
        IDLE: "就绪",
        RUNNING: "运行中",
        PAUSED: "已暂停",
        COMPLETED: "已完成",
        ERROR: "错误",
    }

    @classmethod
    def get_name(cls, status: str) -> str:
        """获取状态名称"""
        return cls.STATUS_NAMES.get(status, status)


# 导出
__all__ = ["AgentTheme", "AgentStage", "AgentStatus"]
