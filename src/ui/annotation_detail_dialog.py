"""
批注详情对话框
"""
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from qfluentwidgets import (
    StrongBodyLabel, BodyLabel, SimpleCardWidget, IconWidget,
    FluentIcon
)


class AnnotationDetailDialog(QDialog):
    """批注详情对话框"""

    def __init__(self, annotation, parent=None):
        super().__init__(parent)
        self.annotation = annotation
        self.setup_ui()

    def setup_ui(self):
        self.setWindowTitle('批注详情')
        self.setMinimumWidth(400)
        self.setMinimumHeight(300)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        # 标题
        title_layout = QHBoxLayout()

        risk_icon = IconWidget(self._get_risk_icon(self.annotation.risk_level))
        risk_icon.setFixedSize(28, 28)
        risk_icon.setStyleSheet(f"color: {self._get_risk_color(self.annotation.risk_level)};")
        title_layout.addWidget(risk_icon)

        title = StrongBodyLabel(self._get_risk_label(self.annotation.risk_level))
        title.setStyleSheet(f'font-size: 16px; color: {self._get_risk_color(self.annotation.risk_level)};')
        title_layout.addWidget(title)
        title_layout.addStretch()

        layout.addLayout(title_layout)

        # 文件信息卡片
        info_card = SimpleCardWidget()
        info_layout = QVBoxLayout(info_card)
        info_layout.setSpacing(6)
        info_layout.setContentsMargins(12, 12, 12, 12)

        # 文件路径
        path_label = StrongBodyLabel('文件路径')
        path_label.setStyleSheet('font-size: 11px; color: #666;')
        info_layout.addWidget(path_label)

        path_value = BodyLabel(self.annotation.item_path)
        path_value.setWordWrap(True)
        path_value.setStyleSheet('font-size: 12px; font-weight: 500;')
        info_layout.addWidget(path_value)

        # 文件信息
        info_row = QHBoxLayout()

        size_info = self._create_info_item('大小', self._format_size(self.annotation.file_size))
        info_row.addWidget(size_info)

        type_info = self._create_info_item('类型', '文件' if self.annotation.item_type == 'file' else '文件夹')
        info_row.addWidget(type_info)

        score_info = self._create_info_item('风险分', str(self.annotation.risk_score))
        info_row.addWidget(score_info)

        info_layout.addLayout(info_row)

        layout.addWidget(info_card)

        # 评估信息卡片
        eval_card = SimpleCardWidget()
        eval_layout = QVBoxLayout(eval_card)
        eval_layout.setSpacing(8)
        eval_layout.setContentsMargins(12, 12, 12, 12)

        # 评估来源
        source_label = StrongBodyLabel('评估方式')
        source_label.setStyleSheet('font-size: 11px; color: #666;')
        eval_layout.addWidget(source_label)

        source_badge = self._create_badge(self.annotation.assessment_method)
        eval_layout.addWidget(source_badge)

        # 置信度进度条
        conf_label = StrongBodyLabel('评估置信度')
        conf_label.setStyleSheet('font-size: 11px; color: #666;')
        eval_layout.addWidget(conf_label)

        conf_bar = self._create_confidence_bar(self.annotation.confidence)
        eval_layout.addWidget(conf_bar)

        layout.addWidget(eval_card)

        # 批注说明
        if self.annotation.annotation_note:
            note_card = SimpleCardWidget()
            note_layout = QVBoxLayout(note_card)
            note_layout.setContentsMargins(12, 12, 12, 12)

            note_title = StrongBodyLabel('批注说明')
            note_title.setStyleSheet('font-size: 11px; color: #666;')
            note_layout.addWidget(note_title)

            note_content = BodyLabel(self.annotation.annotation_note)
            note_content.setWordWrap(True)
            note_content.setStyleSheet('font-size: 12px; line-height: 1.5;')
            note_layout.addWidget(note_content)

            layout.addWidget(note_card)

        # 推荐操作
        rec_card = SimpleCardWidget()
        rec_layout = QVBoxLayout(rec_card)
        rec_layout.setContentsMargins(12, 12, 12, 12)

        rec_title = StrongBodyLabel('推荐操作')
        rec_title.setStyleSheet('font-size: 11px; color: #666;')
        rec_layout.addWidget(rec_title)

        rec_text = StrongBodyLabel(self.annotation.recommendation)
        rec_text.setStyleSheet(f'font-size: 14px; color: {self._get_recommendation_color(self.annotation.recommendation)};')
        rec_layout.addWidget(rec_text)

        layout.addWidget(rec_card)

        # 附加信息（如果有）
        if self.annotation.annotation_tags:
            tags_card = SimpleCardWidget()
            tags_layout = QVBoxLayout(tags_card)
            tags_layout.setContentsMargins(12, 12, 12, 12)

            tags_title = StrongBodyLabel('标签')
            tags_title.setStyleSheet('font-size: 11px; color: #666;')
            tags_layout.addWidget(tags_title)

            tags_row = QHBoxLayout()
            for tag in self.annotation.annotation_tags[:5]:
                tag_label = BodyLabel(tag)
                tag_label.setStyleSheet('background: #0078D415; color: #0078D4; padding: 4px 8px; border-radius: 4px; font-size: 10px;')
                tags_row.addWidget(tag_label)
            tags_layout.addLayout(tags_row)

            layout.addWidget(tags_card)

        # AI 状态（如果是AI评估）
        if self.annotation.assessment_method == 'ai':
            ai_card = SimpleCardWidget()
            ai_card.setStyleSheet('background: #E5A00010; border: 1px solid #E5A00030; border-radius: 8px;')
            ai_layout = QVBoxLayout(ai_card)
            ai_layout.setContentsMargins(12, 12, 12, 12)

            ai_status = BodyLabel('AI 评估')
            ai_card.setStyleSheet('font-size: 11px; color: #E5A000;')
            ai_layout.addWidget(ai_status)

            cache_status = "来自缓存" if self.annotation.cache_hit else "新评估结果"
            cache_label = BodyLabel(f"状态: {cache_status}")
            cache_label.setStyleSheet('font-size: 11px; color: #666;')
            ai_layout.addWidget(cache_label)

            if self.annotation.ai_confidence:
                ai_conf_label = BodyLabel(f"AI置信度: {int(self.annotation.ai_confidence * 100)}%")
                ai_conf_label.setStyleSheet('font-size: 11px; color: #666;')
                ai_layout.addWidget(ai_conf_label)

            layout.addWidget(ai_card)

        layout.addStretch()

        # 关闭按钮
        close_btn = QPushButton(FluentIcon.CLOSE.icon(), '关闭')
        close_btn.setFixedHeight(36)
        close_btn.setStyleSheet('''
            QPushButton {
                background: transparent;
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                color: #555;
                padding: 0 16px;
            }
            QPushButton:hover {
                background: #f5f5f5;
                border: 1px solid #0078D4;
            }
        ''')
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

    def _create_info_item(self, label, value):
        """创建信息项"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        l = BodyLabel(f'{label}:')
        l.setStyleSheet('font-size: 10px; color: #888;')
        layout.addWidget(l)

        v = StrongBodyLabel(value)
        v.setStyleSheet('font-size: 11px; color: #333;')
        layout.addWidget(v)

        return widget

    def _create_badge(self, method):
        """创建来源标签"""
        widget = QWidget()

        method_names = {
            'whitelist': '白名单',
            'rule': '规则引擎',
            'ai': 'AI 智能评估'
        }

        colors = {
            'whitelist': ('#28a745', 'rgba(40, 167, 69, 0.15)'),
            'rule': ('#667eea', 'rgba(102, 126, 234, 0.15)'),
            'ai': ('#E5A000', 'rgba(229, 160, 0, 0.15)')
        }

        color = colors.get(method, ('#666', 'rgba(102, 102, 102, 0.15)'))
        method_name = method_names.get(method, method)

        widget.setStyleSheet(f"""
            QWidget {{
                background: {color[1]};
                color: {color[0]};
                border: 1px solid {color[0]};
                border-radius: 4px;
                padding: 6px 12px;
            }}
        """)

        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)

        label = BodyLabel(method_name)
        label.setStyleSheet(f"color: {color[0]}; font-size: 12px; font-weight: 500;")
        layout.addWidget(label)

        return widget

    def _create_confidence_bar(self, confidence):
        """创建置信度进度条"""
        widget = QWidget()
        widget.setFixedHeight(24)

        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)

        # 背景
        bg = QFrame()
        bg.setStyleSheet('background: #e0e0e0; border-radius: 4px;')
        bg.setFixedHeight(20)

        # 进度
        fg = QFrame(bg)
        percent = int(confidence * 100)
        color = '#28a745' if confidence >= 0.8 else '#ffc107' if confidence >= 0.5 else '#dc3545'
        fg.setStyleSheet(f'background: {color}; border-radius: 4px;')
        fg.setGeometry(0, 0, int(bg.width() * confidence), 20)

        # 百分比文字
        text_label = BodyLabel(f"{percent}%")
        text_label.setStyleSheet(f'font-size: 11px; color: {color}; font-weight: 600; margin-left: 8px;')
        layout.addWidget(bg)
        layout.addWidget(text_label)
        layout.addStretch()

        return widget

    def _get_risk_icon(self, risk_level):
        return FluentIcon.CHECKBOX if risk_level == 'safe' else FluentIcon.INFO if risk_level == 'suspicious' else FluentIcon.DELETE

    def _get_risk_color(self, risk_level):
        return {
            'safe': '#28a745',
            'suspicious': '#ffc107',
            'dangerous': '#dc3545',
        }.get(risk_level, '#999')

    def _get_risk_label(self, risk_level):
        labels = {
            'safe': '安全',
            'suspicious': '疑似',
            'dangerous': '危险',
        }
        return labels.get(risk_level, risk_level)

    def _get_recommendation_color(self, recommendation):
        colors = {
            '可以清理': '#28a745',
            '保留': '#ff9800',
            '需确认': '#ffc107',
        }
        return colors.get(recommendation, '#666')

    def _format_size(self, size_bytes):
        """格式化文件大小"""
        if size_bytes == 0:
            return '0 B'

        units = ['B', 'KB', 'MB', 'GB', 'TB']
        size = float(size_bytes)
        unit_index = 0

        while size >= 1024 and unit_index < len(units) - 1:
            size /= 1024
            unit_index += 1

        return f'{size:.2f} {units[unit_index]}'
