"""
自定义回收站模块
支持将删除的文件压缩保存到指定目录，以便恢复
支持扫描和管理回收站内的所有文件（包括用户手动添加的）
"""
import os
import shutil
import zipfile
import json
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass
from pathlib import Path


@dataclass
class RecycleItem:
    """回收站项目"""
    id: str
    original_path: str
    original_name: str
    description: str
    risk_level: str
    original_size: int
    deleted_at: str
    zip_file: str
    exists: bool
    is_managed: bool  # 是否由 PurifyAI 管理


class CustomRecycleBin:
    """自定义回收站实现

    将删除的文件压缩保存到指定目录，支持恢复功能
    """

    def __init__(self, recycle_path: Optional[str] = None):
        """
        初始化自定义回收站

        Args:
            recycle_path: 回收站路径，如果为 None 使用默认路径
        """
        if not recycle_path:
            recycle_path = os.path.join(os.path.expanduser('~'), 'PurifyAI_RecycleBin')

        self.recycle_path = os.path.normpath(recycle_path)
        self._ensure_recycle_dir()

    def _ensure_recycle_dir(self):
        """确保回收站目录存在"""
        os.makedirs(self.recycle_path, exist_ok=True)
        # 创建索引文件
        self._init_index()

    def _get_index_file(self) -> str:
        """获取索引文件路径"""
        return os.path.join(self.recycle_path, 'recycle_index.json')

    def _init_index(self):
        """初始化索引文件"""
        index_file = self._get_index_file()
        if not os.path.exists(index_file):
            self._save_index({'items': []})

    def _load_index(self) -> Dict[str, Any]:
        """加载索引"""
        index_file = self._get_index_file()
        try:
            with open(index_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {'items': []}

    def _save_index(self, index: Dict[str, Any]):
        """保存索引"""
        index_file = self._get_index_file()
        try:
            with open(index_file, 'w', encoding='utf-8') as f:
                json.dump(index, f, indent=2, ensure_ascii=False)
        except Exception as e:
            # 如果保存失败，至少打印错误
            import logging
            logging.error(f"[回收站:ERROR] 保存索引失败: {e}")

    def recycle_item(self, item_path: str, original_size: int,
                     description: str = '', risk_level: str = 'safe') -> bool:
        """
        将文件/文件夹添加到自定义回收站（压缩后保存）

        Args:
            item_path: 要删除的文件/文件夹路径
            original_size: 原始大小（字节）
            description: 项目描述
            risk_level: 风险等级

        Returns:
            bool: 是否成功添加到回收站
        """
        if not os.path.exists(item_path):
            return False

        try:
            # 生成唯一ID
            item_id = self._generate_item_id(item_path)
            timestamp = datetime.now().isoformat()

            # 创建临时压缩文件路径
            zip_name = f"{item_id}.zip"
            zip_path = os.path.join(self.recycle_path, zip_name)

            # 压缩文件
            item_name = os.path.basename(item_path)
            if os.path.isdir(item_path):
                # 压缩整个目录
                with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                    for root, dirs, files in os.walk(item_path):
                        for file in files:
                            file_path = os.path.join(root, file)
                            arcname = os.path.relpath(file_path, os.path.dirname(item_path))
                            zf.write(file_path, arcname)
            else:
                # 压缩单个文件
                with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                    zf.write(item_path, item_name)

            # 记录到索引
            index = self._load_index()
            item_info = {
                'id': item_id,
                'original_path': os.path.normpath(item_path),
                'original_name': item_name,
                'description': description,
                'risk_level': risk_level,
                'original_size': original_size,
                'zip_size': os.path.getsize(zip_path),
                'deleted_at': timestamp,
                'zip_file': zip_name
            }
            index['items'].append(item_info)
            self._save_index(index)

            # 删除原始文件/文件夹
            if os.path.isdir(item_path):
                shutil.rmtree(item_path)
            else:
                os.remove(item_path)

            return True

        except Exception as e:
            import logging
            logging.error(f"[回收站:ERROR] 回收项目失败 {item_path}: {e}")
            return False

    def restore_item(self, item_id: str, target_path: Optional[str] = None) -> bool:
        """
        恢复回收站中的项目

        Args:
            item_id: 项目ID
            target_path: 目标路径，如果为 None 则恢复到原始位置

        Returns:
            bool: 是否成功恢复
        """
        index = self._load_index()

        # 查找项目
        item_info = None
        item_index = -1
        for i, item in enumerate(index['items']):
            if item['id'] == item_id:
                item_info = item
                item_index = i
                break

        if not item_info:
            return False

        try:
            # 解压文件
            zip_path = os.path.join(self.recycle_path, item_info['zip_file'])
            if not os.path.exists(zip_path):
                return False

            # 确定目标路径
            if target_path is None:
                target_dir = os.path.dirname(item_info['original_path'])
                target_path = item_info['original_path']

                # 确保目标目录存在
                os.makedirs(target_dir, exist_ok=True)

            # 如果原始路径已存在同名文件/文件夹冲突
            if os.path.exists(target_path):
                # 添加时间戳后缀
                base, ext = os.path.splitext(target_path)
                timestamp = datetime.now().strftime('_%Y%m%d_%H%M%S')
                target_path = f"{base}{timestamp}{ext}"

            # 解压
            extract_dir = os.path.dirname(target_path)
            with zipfile.ZipFile(zip_path, 'r') as zf:
                zf.extractall(extract_dir)

            # 如果解压后的文件名不匹配，重命名
            extracted = os.path.join(extract_dir, item_info['original_name'])
            if extracted != target_path and os.path.exists(extracted):
                 shutil.move(extracted, target_path)

            # 从索引中移除
            index['items'].pop(item_index)
            self._save_index(index)

            # 删除压缩文件
            try:
                os.remove(zip_path)
            except:
                pass

            return True

        except Exception as e:
            import logging
            logging.error(f"[回收站:ERROR] 恢复项目失败 {item_id}: {e}")
            return False

    def list_items(self, risk_level: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        列出回收站中的项目

        Args:
            risk_level: 筛选风险等级，None 表示不筛选

        Returns:
            List[Dict[str, Any]]: 项目列表
        """
        index = self._load_index()

        items = []
        for item in index['items']:
            if risk_level is None or item.get('risk_level') == risk_level:
                # 检查压缩文件是否仍存在
                zip_path = os.path.join(self.recycle_path, item['zip_file'])
                item['exists'] = os.path.exists(zip_path)
                items.append(item)

        return items

    def scan_all_items(self) -> List[Dict[str, Any]]:
        """
        扫描回收站目录中的所有项目（包括未管理的）

        Returns:
            List[Dict[str, Any]]: 所有项目列表，包含：
            - managed: PurifyAI 管理的项目（有索引记录）
            - unmanaged_zip: 压缩文件但没有索引记录
            - regular: 普通文件或目录
        """
        index = self._load_index()
        indexed_zips = {item['zip_file'] for item in index['items']}
        indexed_ids = {item['id'] for item in index['items']}

        all_items = []

        # 扫描回收站目录中的所有文件
        try:
            for entry in os.scandir(self.recycle_path):
                entry_name = entry.name

                # 跳过索引文件
                if entry_name == 'recycle_index.json':
                    continue

                # 获取文件信息
                file_size = 0
                is_directory = entry.is_dir(follow_symlinks=False)

                if is_directory:
                    # 计算目录大小
                    try:
                        for root, dirs, files in os.walk(entry.path):
                            for file in files:
                                try:
                                    file_size += os.path.getsize(os.path.join(root, file))
                                except:
                                    pass
                    except:
                        pass

                    # 目录项
                    item_data = {
                        'id': f'dir_{entry_name}',
                        'type': 'regular',
                        'name': entry_name,
                        'path': entry.path,
                        'is_directory': True,
                        'size': file_size,
                        'modified_at': datetime.fromtimestamp(entry.stat().st_mtime).isoformat(),
                        'is_managed': False
                    }
                    all_items.append(item_data)
                else:
                    # 文件项
                    file_size = entry.stat(follow_symlinks=False).st_size

                    if entry_name.endswith('.zip'):
                        # 压缩文件
                        if entry_name in indexed_zips:
                            # 已管理的压缩文件，从索引获取信息
                            for item in index['items']:
                                if item['zip_file'] == entry_name:
                                    item['exists'] = True
                                    item['is_managed'] = True
                                    item['type'] = 'managed'
                                    all_items.append(item.copy())
                                    break
                        else:
                            # 未管理的压缩文件
                            item_data = {
                                'id': f'unzip_{entry_name}',
                                'type': 'unmanaged_zip',
                                'name': entry_name,
                                'path': entry.path,
                                'original_path': '',
                                'original_name': entry_name.replace('.zip', ''),
                                'description': '用户添加',
                                'risk_level': 'unknown',
                                'original_size': file_size,
                                'deleted_at': datetime.fromtimestamp(entry.stat().st_mtime).isoformat(),
                                'zip_file': entry_name,
                                'zip_size': file_size,
                                'is_managed': False
                            }
                            all_items.append(item_data)
                    else:
                        # 普通文件
                        item_data = {
                            'id': f'file_{entry_name}',
                            'type': 'regular',
                            'name': entry_name,
                            'path': entry.path,
                            'size': file_size,
                            'modified_at': datetime.fromtimestamp(entry.stat().st_mtime).isoformat(),
                            'is_managed': False
                        }
                        all_items.append(item_data)
        except Exception as e:
            import logging
            logging.error(f"[回收站:ERROR] 扫描目录失败: {e}")

        # 按删除时间排序（管理的按删除时间，未管理的按修改时间）
        all_items.sort(key=lambda x: x.get('deleted_at') or x.get('modified_at') or '', reverse=True)

        return all_items

    def restore_by_path(self, file_path: str, target_path: Optional[str] = None) -> bool:
        """通过文件路径恢复（用于未管理的压缩文件）"""
        if not os.path.exists(file_path):
            return False

        try:
            if file_path.endswith('.zip'):
                # 解压压缩文件
                if target_path is None:
                    # 默认解压到当前目录
                    extract_dir = os.path.dirname(file_path)
                    with zipfile.ZipFile(file_path, 'r') as zf:
                        zf.extractall(extract_dir)
                    return True
                else:
                    # 解压到指定位置
                    with zipfile.ZipFile(file_path, 'r') as zf:
                        zf.extractall(target_path)
                    return True
            else:
                # 普通文件，移动到指定位置
                if target_path is None:
                    target_dir = os.path.expanduser('~')
                    target_path = os.path.join(target_dir, os.path.basename(file_path))

                if os.path.isdir(target_path):
                    # 如果目标是目录，移动到目录内
                    shutil.move(file_path, os.path.join(target_dir, os.path.basename(file_path)))
                else:
                    shutil.move(file_path, target_path)
                return True

        except Exception as e:
            import logging
            logging.error(f"[回收站:ERROR] 从路径恢复失败 {file_path}: {e}")
            return False

    def delete_file_by_path(self, file_path: str) -> bool:
        """通过文件路径删除（用于未管理的文件）"""
        try:
            if os.path.isdir(file_path):
                shutil.rmtree(file_path)
            else:
                os.remove(file_path)
            return True
        except Exception as e:
            import logging
            logging.error(f"[回收站:ERROR] 删除文件失败 {file_path}: {e}")
            return False

    def delete_item(self, item_id: str) -> bool:
        """
        从回收站中永久删除项目

        Args:
            item_id: 项目ID

        Returns:
            bool: 是否成功删除
        """
        index = self._load_index()

        # 查找并移除项目
        for i, item in enumerate(index['items']):
            if item['id'] == item_id:
                # 删除压缩文件
                zip_path = os.path.join(self.recycle_path, item['zip_file'])
                try:
                    os.remove(zip_path)
                except:
                    pass

                # 从索引移除
                index['items'].pop(i)
                self._save_index(index)
                return True

        return False

    def clear_all(self) -> int:
        """
        清空回收站

        Returns:
            int: 清除的项目数
        """
        index = self._load_index()
        count = len(index['items'])

        # 删除所有压缩文件
        for item in index['items']:
            zip_path = os.path.join(self.recycle_path, item['zip_file'])
            try:
                os.remove(zip_path)
            except:
                pass

        # 清空索引
        index['items'] = []
        self._save_index(index)

        return count

    def get_stats(self) -> Dict[str, Any]:
        """
        获取回收站统计信息

        Returns:
            Dict[str, Any]: 统计信息
        """
        items = self.list_items()
        total_size = sum(item.get('original_size', 0) for item in items)
        zip_size = sum(item.get('zip_size', 0) for item in items)

        # 按风险等级统计
        by_risk = {}
        for item in items:
            risk = item.get('risk_level', 'unknown')
            by_risk[risk] = by_risk.get(risk, 0) + 1

        return {
            'total_items': len(items),
            'total_size': total_size,
            'zip_size': zip_size,
            'by_risk': by_risk,
            'saved_space': total_size - zip_size
        }

    def _generate_item_id(self, path: str) -> str:
        """生成唯一项目ID"""
        import hashlib
        m = hashlib.md5()
        m.update(path.encode('utf-8'))
        m.update(str(datetime.now().timestamp()).encode('utf-8'))
        return m.hexdigest()[:12]

    def cleanup_old_items(self, days: int = 30) -> int:
        """
        清理指定天数前的项目

        Args:
            days: 天数

        Returns:
            int: 清除的旧项目数
        """
        from datetime import timedelta
        cutoff = datetime.now() - timedelta(days=days)
        cutoff_str = cutoff.isoformat()

        index = self._load_index()
        removed_count = 0
        new_items = []

        for item in index['items']:
            if item.get('deleted_at', '') < cutoff_str:
                # 删除压缩文件
                zip_path = os.path.join(self.recycle_path, item['zip_file'])
                try:
                    os.remove(zip_path)
                except:
                    pass
                removed_count += 1
            else:
                new_items.append(item)

        if removed_count > 0:
            index['items'] = new_items
            self._save_index(index)

        return removed_count


# 全局实例
_global_recycle_bin: Optional[CustomRecycleBin] = None


def get_custom_recycle_bin(recycle_path: Optional[str] = None) -> CustomRecycleBin:
    """获取自定义回收站单例实例"""
    global _global_recycle_bin
    if _global_recycle_bin is None or (recycle_path is not None and _global_recycle_bin.recycle_path != recycle_path):
        _global_recycle_bin = CustomRecycleBin(recycle_path)
    return _global_recycle_bin


def is_custom_recycle_enabled(config_mgr) -> bool:
    """检查是否启用自定义回收站功能"""
    try:
        return config_mgr.get('recycle_enabled', False)
    except:
        return False


def get_custom_recycle_path(config_mgr) -> str:
    """获取自定义回收站路径"""
    try:
        path = config_mgr.get('recycle_path', '')
        if not path:
            # 尝试从旧格式读取
            recycle_config = config_mgr.get('recycle', {})
            path = recycle_config.get('folder_path', '')
        if not path:
            # 使用默认路径
            path = os.path.join(os.path.expanduser('~'), 'PurifyAI_RecycleBin')
        return os.path.normpath(path)
    except:
        return os.path.join(os.path.expanduser('~'), 'PurifyAI_RecycleBin')
