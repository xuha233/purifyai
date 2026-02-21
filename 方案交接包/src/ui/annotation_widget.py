"""
批注展示组件 - 显示批注的UI组件
"""
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QSizePolicy, QPushButton
)
from PyQt5.QtCore import Qt, pyqtProperty, QPropertyAnimation, QEasingCurve, QSize
from PyQt5.QtGui import QPainter, QColor, QFont

from qfluentwidgets import (
    StrongBodyLabel, BodyLabel, SimpleCardWidget, IconWidget, FluentIcon,
    PushButton, SubtitleLabel, PrimaryPushButton
)


class ExpandableNoteCard(SimpleCardWidget):
    """可展开的批注卡片"""
    expanded = pyqtProperty(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._expanded = False
        self.setup_ui()

    def setup_ui(self):
        self.setStyleSheet("""
            ExpandableNoteCard {
                background: white;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)

        # 头部 - 可展开区域
        header = QWidget()
        header.setStyleSheet("QWidget#cardHeader:hover { background: rgba(0, 120, 212, 0.05); padding: 8px; border-radius: 4px; }")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)

        self.label = BodyLabel('批注说明')
        self.label.setStyleSheet("font-size: 12px; color: #666; font-weight: 500;")
        header_layout.addWidget(self.label)
        header_layout.addStretch()

        self.toggle_btn = QPushButton(FluentIcon.DOWN.icon())
        self.toggle_btn.setFixedSize(24, 24)
        self.toggle_btn.setStyleSheet('''
            QPushButton {
                background: transparent;
                border: none;
            }
            QPushButton:hover {
                background: #0078D410;
                border-radius: 12px;
            }
        ''')
        self.toggle_btn.clicked.connect(self.toggle_expansion)
        header_layout.addWidget(self.toggle_btn)

        layout.addWidget(header)

        # 内容区域
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(6)

        self.content_widget.setVisible(self._expanded)

        layout.addWidget(self.content_widget)

    def set_content(self, content: str):
        """设置内容"""
        # 清空原有内容
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # 添加新内容
        note_label = BodyLabel(content)
        note_label.setStyleSheet("font-size: 11px; color: #666; word-wrap: wrap;")
        note_label.setWordWrap(True)
        self.content_layout.addWidget(note_label)

    def toggle_expansion(self):
        self._expanded = not self._expanded
        card_height = 36 + (self.content_widget.sizeHint().height() if self._expanded else 0)
        self.setFixedHeight(card_height if self._expanded else 36)

        self.content_widget.setVisible(self._expanded)
        self.toggle_btn.setIcon(FluentIcon.DOWN if not self._expanded else FluentIcon.RIGHT)

    def setExpanded(self, expanded):
        self._expanded = expanded
        self.content_widget.setVisible(expanded)
        self.toggle_btn.setIcon(FluentIcon.DOWN if not expanded else FluentIcon.RIGHT)


class CompactAnnotationDisplay(QWidget):
    """紧凑型批注显示组件 - 在列表中显示简化信息"""

    def __init__(self, annotation=None, parent=None):
        super().__init__(parent)
        self.annotation = annotation
        self.setup_ui(annotation)

    def setup_ui(self, annotation):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(4)

        if not annotation:
            empty_label = BodyLabel('')
            layout.addWidget(empty_label)
            return

        # 来源 badge
        badge = self._create_badge(annotation.assessment_method)
        badge.setFixedHeight(18)
        layout.addWidget(badge)

        # 置信度
        conf_text = f"{int(annotation.confidence * 100)}%"
        conf_label = BodyLabel(conf_text)
        conf_label.setStyleSheet(self._get_confidence_style(annotation.confidence))
        conf_label.setFixedHeight(18)
        layout.addWidget(conf_label)

        # AI 缓存状态
        if annotation.assessment_method == 'ai':
            cache_status = "缓存" if annotation.cache_hit else "新评估"
            cache_label = BodyLabel(cache_status)
            cache_label.setStyleSheet('font-size: 9px; color: #999; padding: 0 4px;')
            cache_label.setFixedHeight(18)
            layout.addWidget(cache_label)

        layout.addStretch()

    def _create_badge(self, method: str) -> QWidget:
        """创建来源标签"""
        badge = QWidget()

        method_names = {
            'whitelist': '白名单',
            'rule': '规则',
            'ai': 'AI'
        }

        colors = {
            'whitelist': ('#28a745', 'rgba(40, 167, 69, 0.15)'),
            'rule': ('#667eea', 'rgba(102, 126, 234, 0.15)'),
            'ai': ('#E5A000', 'rgba(229, 160, 0, 0.15)')
        }

        color = colors.get(method, ('#666', 'rgba(102, 102, 102, 0.15)'))
        method_name = method_names.get(method, method)

        badge.setStyleSheet(f"""
            QWidget {{
                background: {color[1]};
                color: {color[0]};
                border: 1px solid {color[0]};
                border-radius: 4px;
                padding: 0 6px;
                font-size: 9px;
            }}
        """)

        badge_layout = QHBoxLayout(badge)
        badge_layout.setContentsMargins(0, 0, 0, 0)
        badge_layout.setSpacing(0)

        label = BodyLabel(method_name)
        label.setStyleSheet(f"color: {color[0]}; font-size: 9px;")
        badge_layout.addWidget(label)

        return badge

    def _get_confidence_style(self, confidence):
        if confidence >= 0.8:
            return 'color: #28a745; font-size: 10px; font-weight: 600;'
        elif confidence >= 0.5:
            return 'color: #ffc107; font-size: 10px; font-weight: 500;'
        else:
            return 'color: #999; font-size: 10px;'


class AnnotationDisplay(QWidget):
    """扫描项批注显示组件"""

    def __init__(self, item_data: dict, parent=None):
        super().__init__(parent)
        self.item_data = item_data
        self.annotation = item_data.get('annotation')
        self.init_ui()

    def init_ui(self):
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(8)
        layout.setContentsMargins(12, 12, 12, 12)

        # 批注标题行
        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)

        # 风险状态图标
        risk_icon = self._get_risk_icon(self.annotation.risk_level)
        risk_icon.setFixedSize(24, 24)
        risk_icon.setStyleSheet(f"color: {self._get_risk_color(self.annotation.risk_level)};")
        header_layout.addWidget(risk_icon)

        # 批注来源标签
        source_badge = self._create_badge()
        self._set_badge_properties(source_badge, self.annotation.assessment_method)

        header_layout.addWidget(source_badge)
        header_layout.addStretch()

        # 置信度显示
        conf_text = f"{int(self.annotation.confidence * 100)}%"
        conf_label = BodyLabel(conf_text)
        conf_label.setStyleSheet(self._get_confidence_style(self.annotation.confidence))
        header_layout.addWidget(conf_label)

        layout.addWidget(header)

        # AI 状态条
        if self.annotation.assessment_method == 'ai':
            cache_status = "缓存" if self.annotation.cache_hit else "新评估"
            cache_label = BodyLabel(cache_status)
            cache_label.setStyleSheet('font-size: 10px; color: #999;')
            layout.addWidget(cache_label)

        # 批注说明
        if self.annotation.annotation_note:
            note_card = self._create_note_card()
            note_card.set_content(self.annotation.annotation_note)
            layout.addWidget(note_card)

        # 推荐操作
        action_label = BodyLabel(self._get_recommendation_display(self.annotation.recommendation))
        action_label.setStyleSheet(f"font-size: 11px; {self._get_recommendation_color(self.annotation.recommendation)}; font-weight: 500;")
        layout.addWidget(action_label)

        container.setLayout(layout)
        self.setLayout(container)

    def update_annotation(self, annotation):
        """更新批注内容"""
        self.annotation = annotation

        # 更新风险图标
        risk_icon = self.findChild(IconWidget, "risk_icon")
        if risk_icon:
            risk_icon.setIcon(self._get_risk_icon(annotation.risk_level))
            risk_icon.setStyleSheet(f"color: {self._get_risk_color(annotation.risk_level)};")

        # 更新来源badge
        source_badge = self.findChild(QWidget, "source_badge")
        if hasattr(self, 'source_badge'):
            self._set_badge_properties(source_badge, annotation.assessment_method)

    def _get_risk_icon(self, risk_level):
        return FluentIcon.CHECKBOX if risk_level == 'safe' else FluentIcon.INFO if risk_level == 'suspicious' else FluentIcon.DELETE

    def _get_risk_color(self, risk_level):
        return {
            'safe': '#28a745',
            'suspicious': '#ffc107',
            'dangerous': '#dc3545',
        }.get(risk_level, '#999')

    def _get_confidence_style(self, confidence):
        if confidence >= 0.8:
            return 'color: #28a745; font-weight: 600;'
        elif confidence >= 0.5:
            return 'color: #ffc107; font-weight: 500;'
        else:
            return 'color: #999;'

    def _get_recommendation_display(self, recommendation):
        labels = {
            '可以清理': '可清理',
            '保留': '建议保留',
            '需确认': '需确认',
        }
        return labels.get(recommendation, recommendation)

    def _get_recommendation_color(self, recommendation):
        colors = {
            '可以清理': '#28a745',
            '保留': '#ff9800',
            '需确认': '#ffc107',
        }
        return colors.get(recommendation, '#666')

    def _set_badge_properties(self, badge, method: str):
        if method == 'whitelist':
            badge.setStyleSheet("""
                QFrame {
                    background: rgba(40, 167, 69, 0.15);
                    color: #28a745;
                    border: 1px solid #28a745;
                    border-radius: 4px;
                    padding: 2px 6px;
                    font-size: 10px;
                }
            """)
        elif method == 'rule':
            badge.setStyleSheet("""
                QFrame {
                    background: rgba(102, 126, 234, 0.15);
                    color: #2d2d2d;
                    border: 1px solid #2d2d2d;
                    border-radius: 4px;
                    padding: 2px 6px;
                    font-size: 10px;
                }
            """)
        else:  # ai or uncertain
            badge.setStyleSheet("""
                QFrame {
                    background: rgba(229, 115, 39, 0.15);
                    color: #E5A000;
                    border: 1px solid #E5A000;
                    border-radius: 4px;
                    padding: 2px 6px;
                    font-size: 10px;
                }
            """)

    def _create_badge(self):
        from PyQt5.QtWidgets import QFrame
        badge = QFrame()
        return badge

    def _create_note_card(self):
        """创建批注说明卡片"""
        card = ExpandableNoteCard()
        card.setExpanded(True)
        return card
    """扫描项批注显示组件"""

    def __init__(self, item_data: dict, parent=None):
        super().__init__(parent)
        self.item_data = item_data
        self.annotation = item_data.get('annotation')
        self.init_ui()

    def init_ui(self):
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(8)
        layout.setContentsMargins(12, 12, 12, 12)

        # 批注标题行
        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)

        # 风险状态图标
        risk_icon = self._get_risk_icon(self.annotation.risk_level)
        risk_icon.setFixedSize(24, 24)
        risk_icon.setStyleSheet(f"color: {self._get_risk_color(self.annotation.risk_level)};")
        header_layout.addWidget(risk_icon)

        # 批注来源标签
        source_badge = self._create_badge()
        self._set_badge_properties(source_badge, self.annotation.assessment_method)

        header_layout.addWidget(source_badge)
        header_layout.addStretch()

        # 置信度显示
        conf_text = f"{int(self.annotation.confidence * 100)}%"
        conf_label = BodyLabel(conf_text)
        conf_label.setStyleSheet(self._get_confidence_style(self.annotation.confidence))
        header_layout.addWidget(conf_label)

        layout.addWidget(header)

        # AI 状态条
        if self.annotation.assessment_method == 'ai':
            cache_status = "缓存" if self.annotation.cache_hit else "新评估"
            cache_label = BodyLabel(cache_status)
            cache_label.setStyleSheet('font-size: 10px; color: #999;')
            layout.addWidget(cache_label)

        # 批注说明
        if self.annotation.annotation_note:
            note_card = self._create_note_card()
            note_card.set_content(self.annotation.annotation_note)
            layout.addWidget(note_card)

        # 推荐操作
        action_label = BodyLabel(self._get_recommendation_display(self.annotation.recommendation))
        action_label.setStyleSheet(f"font-size: 11px; {self._get_recommendation_color(self.annotation.recommendation)}; font-weight: 500;")
        layout.addWidget(action_label)

        container.setLayout(layout)
        self.setLayout(container)

    def update_annotation(self, annotation):
        """更新批注内容"""
        self.annotation = annotation

        # 更新风险图标
        risk_icon = self.findChild(IconWidget, "risk_icon")
        if risk_icon:
            risk_icon.setIcon(self._get_risk_icon(annotation.risk_level))
            risk_icon.setStyleSheet(f"color: {self._get_risk_color(annotation.risk_level)};")

        # 更新来源badge
        source_badge = self.findChild(QWidget, "source_badge")
        if hasattr(self, 'source_badge'):
            self._set_badge_properties(source_badge, annotation.assessment_method)

    def _get_risk_icon(self, risk_level):
        return FluentIcon.CHECKBOX if risk_level == 'safe' else FluentIcon.INFO if risk_level == 'suspicious' else FluentIcon.DELETE

    def _get_risk_color(self, risk_level):
        return {
            'safe': '#28a745',
            'suspicious': '#ffc107',
            'dangerous': '#dc3545',
        }.get(risk_level, '#999')

    def _get_confidence_style(self, confidence):
        if confidence >= 0.8:
            return 'color: #28a745; font-weight: 600;'
        elif confidence >= 0.5:
            return 'color: #ffc107; font-weight: 500;'
        else:
            return 'color: #999;'

    def _get_recommendation_display(self, recommendation):
        labels = {
            '可以清理': '可清理',
            '保留': '建议保留',
            '需确认': '需确认',
        }
        return labels.get(recommendation, recommendation)

    def _get_recommendation_color(self, recommendation):
        colors = {
            '可以清理': '#28a745',
            '保留': '#ff9800',
            '需确认': '#ffc107',
        }
        return colors.get(recommendation, '#666')

    def _set_badge_properties(self, badge, method: str):
        if method == 'whitelist':
            badge.setStyleSheet("""
                QFrame {
                    background: rgba(40, 167, 69, 0.15);
                    color: #28a745;
                    border: 1px solid #28a745;
                    border-radius: 4px;
                    padding: 2px 6px;
                    font-size: 10px;
                }
            """)
        elif method == 'rule':
            badge.setStyleSheet("""
                QFrame {
                    background: rgba(102, 126, 234, 0.15);
                    color: #2d2d2d;
                    border: 1px solid #2d2d2d;
                    border-radius: 4px;
                    padding: 2px 6px;
                    font-size: 10px;
                }
            """)
        else:  # ai or uncertain
            badge.setStyleSheet("""
                QFrame {
                    background: rgba(229, 115, 39, 0.15);
                    color: #E5A000;
                    border: 1px solid #E5A000;
                    border-radius: 4px;
                    padding: 2px 6px;
                    font-size: 10px;
                }
            """)

    def _create_badge(self):
        from PyQt5.QtWidgets import QFrame
        badge = QFrame()
        return badge

    def _create_note_card(self):
        """创建批注说明卡片"""
        card = ExpandableNoteCard()
        card.setExpanded(True)
        return card
