# -*- coding: utf-8 -*-
"""
AOP Integration - PurifyAI 与 AOP 的集成模块

此模块提供 PurifyAI 与 AOP (Agent Orchestration Platform) 的集成功能：
- 假设驱动开发 (HDD)
- 学习捕获
- 多 Agent 任务执行
- 项目评估
"""

from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable
import json
import yaml

# AOP 集成状态
@dataclass
class AOPStatus:
    """AOP 集成状态"""
    available: bool = False
    version: Optional[str] = None
    config_path: Optional[Path] = None
    providers: List[str] = field(default_factory=list)


class AOPIntegration:
    """AOP 集成管理器
    
    提供 PurifyAI 与 AOP 平台的集成功能：
    - 检查 AOP 可用性
    - 执行多 Agent 任务
    - 假设管理
    - 学习捕获
    """
    
    def __init__(self, project_root: Optional[Path] = None):
        self.project_root = project_root or Path.cwd()
        self._status: Optional[AOPStatus] = None
        self._config: Optional[Dict[str, Any]] = None
    
    @property
    def status(self) -> AOPStatus:
        """获取 AOP 状态"""
        if self._status is None:
            self._status = self._check_availability()
        return self._status
    
    @property
    def config(self) -> Dict[str, Any]:
        """获取 AOP 配置"""
        if self._config is None:
            self._config = self._load_config()
        return self._config
    
    def _check_availability(self) -> AOPStatus:
        """检查 AOP 是否可用"""
        status = AOPStatus()
        
        # 检查 aop 命令
        try:
            result = subprocess.run(
                ["aop", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                status.available = True
                status.version = result.stdout.strip()
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        
        # 检查配置文件
        config_path = self.project_root / ".aop.yaml"
        if config_path.exists():
            status.config_path = config_path
        
        return status
    
    def _load_config(self) -> Dict[str, Any]:
        """加载 AOP 配置"""
        if self.status.config_path and self.status.config_path.exists():
            with open(self.status.config_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        return {}
    
    def doctor(self) -> Dict[str, Any]:
        """运行 AOP doctor 检查环境
        
        Returns:
            包含检查结果的字典
        """
        if not self.status.available:
            return {
                "success": False,
                "error": "AOP not installed. Run: pip install aop-agent",
                "providers": []
            }
        
        try:
            result = subprocess.run(
                ["aop", "doctor", "--json"],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=self.project_root
            )
            
            if result.returncode == 0:
                return json.loads(result.stdout)
            else:
                return {
                    "success": False,
                    "error": result.stderr,
                    "providers": []
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "providers": []
            }
    
    def review(
        self,
        prompt: str,
        providers: Optional[List[str]] = None,
        timeout: int = 300
    ) -> Dict[str, Any]:
        """运行多 Agent 代码审查
        
        Args:
            prompt: 审查提示
            providers: 使用的 Provider 列表
            timeout: 超时时间（秒）
        
        Returns:
            审查结果
        """
        if not self.status.available:
            return {
                "success": False,
                "error": "AOP not installed",
                "findings": []
            }
        
        cmd = ["aop", "review", "-p", prompt]
        
        if providers:
            cmd.extend(["-P", ",".join(providers)])
        else:
            # 使用配置中的 providers
            config_providers = self.config.get("providers", [])
            if config_providers:
                cmd.extend(["-P", ",".join(config_providers)])
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=self.project_root
            )
            
            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr if result.returncode else None,
                "findings": self._parse_findings(result.stdout)
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": f"Timeout after {timeout} seconds",
                "findings": []
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "findings": []
            }
    
    def run_task(
        self,
        prompt: str,
        providers: Optional[List[str]] = None,
        timeout: int = 300
    ) -> Dict[str, Any]:
        """执行多 Agent 任务
        
        Args:
            prompt: 任务提示
            providers: 使用的 Provider 列表
            timeout: 超时时间（秒）
        
        Returns:
            任务结果
        """
        if not self.status.available:
            return {
                "success": False,
                "error": "AOP not installed"
            }
        
        cmd = ["aop", "run", "-p", prompt]
        
        if providers:
            cmd.extend(["-P", ",".join(providers)])
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=self.project_root
            )
            
            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr if result.returncode else None
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": f"Timeout after {timeout} seconds"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def create_hypothesis(
        self,
        statement: str,
        priority: str = "quick_win",
        phase: str = "explore"
    ) -> Dict[str, Any]:
        """创建假设
        
        Args:
            statement: 假设陈述
            priority: 优先级 (quick_win/experiment/strategic)
            phase: 阶段 (explore/build/validate/learn)
        
        Returns:
            创建结果
        """
        if not self.status.available:
            # 本地创建
            return self._create_local_hypothesis(statement, priority, phase)
        
        try:
            result = subprocess.run(
                ["aop", "hypothesis", "create", statement, "-p", priority],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=self.project_root
            )
            
            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr if result.returncode else None
            }
        except Exception as e:
            return self._create_local_hypothesis(statement, priority, phase)
    
    def _create_local_hypothesis(
        self,
        statement: str,
        priority: str,
        phase: str
    ) -> Dict[str, Any]:
        """本地创建假设（不需要 AOP CLI）"""
        runs_dir = self.project_root / "runs"
        runs_dir.mkdir(exist_ok=True)
        
        # 查找或创建最新的 run 目录
        run_dirs = sorted(runs_dir.glob("run-*"))
        if run_dirs:
            run_dir = run_dirs[-1]
        else:
            run_dir = runs_dir / "run-001"
            run_dir.mkdir(exist_ok=True)
        
        hypotheses_file = run_dir / "hypotheses.md"
        
        # 生成假设 ID
        hypothesis_id = f"H-{datetime.now().strftime('%Y%m%d%H%M')}"
        
        # 追加假设
        content = f"""
## {hypothesis_id}

### 假设陈述
{statement}

### 元数据
- 优先级: {priority}
- 阶段: {phase}
- 创建时间: {datetime.now().isoformat()}
- 状态: 待验证

### 验证方法
- [ ] 待定义

### 结果
- [ ] 待验证

---
"""
        
        with open(hypotheses_file, "a", encoding="utf-8") as f:
            f.write(content)
        
        return {
            "success": True,
            "hypothesis_id": hypothesis_id,
            "file": str(hypotheses_file)
        }
    
    def capture_learning(
        self,
        phase: str,
        worked: Optional[str] = None,
        failed: Optional[str] = None,
        insight: Optional[str] = None
    ) -> Dict[str, Any]:
        """捕获学习
        
        Args:
            phase: 阶段 (explore/build/validate/learn)
            worked: 什么有效
            failed: 什么失败
            insight: 洞察
        
        Returns:
            捕获结果
        """
        if not self.status.available:
            return self._capture_local_learning(phase, worked, failed, insight)
        
        cmd = ["aop", "learning", "capture", "--phase", phase]
        
        if worked:
            cmd.extend(["--worked", worked])
        if failed:
            cmd.extend(["--failed", failed])
        if insight:
            cmd.extend(["--insight", insight])
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                cwd=self.project_root
            )
            
            return {
                "success": result.returncode == 0,
                "output": result.stdout
            }
        except Exception as e:
            return self._capture_local_learning(phase, worked, failed, insight)
    
    def _capture_local_learning(
        self,
        phase: str,
        worked: Optional[str],
        failed: Optional[str],
        insight: Optional[str]
    ) -> Dict[str, Any]:
        """本地捕获学习"""
        runs_dir = self.project_root / "runs"
        run_dirs = sorted(runs_dir.glob("run-*"))
        
        if not run_dirs:
            return {"success": False, "error": "No run directory found"}
        
        run_dir = run_dirs[-1]
        learn_dir = run_dir / "learn"
        learn_dir.mkdir(exist_ok=True)
        
        learning_file = learn_dir / "learning-log.md"
        
        content = f"""
## 学习记录 - {datetime.now().isoformat()}

### 阶段: {phase}

"""
        if worked:
            content += f"**✅ 有效**: {worked}\n\n"
        if failed:
            content += f"**❌ 失败**: {failed}\n\n"
        if insight:
            content += f"**💡 洞察**: {insight}\n\n"
        
        content += "---\n"
        
        with open(learning_file, "a", encoding="utf-8") as f:
            f.write(content)
        
        return {
            "success": True,
            "file": str(learning_file)
        }
    
    def _parse_findings(self, output: str) -> List[Dict[str, Any]]:
        """解析 AOP review 输出中的 findings"""
        findings = []
        
        # 简单解析：查找 [HIGH], [MEDIUM], [LOW] 标记
        import re
        
        pattern = r'\[(HIGH|MEDIUM|LOW|CRITICAL)\]\s*(.+)'
        
        for match in re.finditer(pattern, output):
            findings.append({
                "severity": match.group(1).lower(),
                "title": match.group(2).strip()
            })
        
        return findings


# 便捷函数
_aop_instance: Optional[AOPIntegration] = None


def get_aop(project_root: Optional[Path] = None) -> AOPIntegration:
    """获取 AOP 集成实例"""
    global _aop_instance
    if _aop_instance is None:
        _aop_instance = AOPIntegration(project_root)
    return _aop_instance


def is_aop_available() -> bool:
    """检查 AOP 是否可用"""
    return get_aop().status.available