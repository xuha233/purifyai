"""
AI 客户端模块
提供与兼容 OpenAI 格式的 API 进行交互的功能
支持详细的 API 请求/响应日志记录
"""
import json
import time
import requests
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass, field

from ..utils.logger import get_logger, log_api_event, log_performance


logger_AI = get_logger(__name__)


@dataclass
class AIConfig:
    """AI 配置"""
    api_url: str = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
    api_key: str = ""
    model: str = "glm-4-flash"  # 默认模型，但用户可以自由更改
    max_retries: int = 3
    retry_delay: int = 20

    def validate(self) -> Tuple[bool, str]:
        """验证配置有效性"""
        if not self.api_url.strip():
            return False, "API地址不能为空"
        if not self.api_key.strip():
            return False, "API密钥不能为空"
        if not self.model.strip():
            return False, "模型名称不能为空"
        return True, ""


class AIClient:
    """AI API 客户端"""

    def __init__(self, config: AIConfig):
        self.config = config
        self.session = requests.Session()
        logger_AI.debug(f"[AI:INIT] AI客户端初始化 - 模型: {config.model}, 端点: {config.api_url}")

    def _create_request(self, messages: List[Dict]) -> Dict:
        """创建 API 请求"""
        return {
            "messages": messages,
            "model": self.config.model
        }

    def _get_headers(self) -> Dict:
        """获取请求头"""
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.config.api_key}"
        }

    def _parse_response(self, response: requests.Response) -> str:
        """解析 API 响应"""
        try:
            data = response.json()
            if "choices" in data and len(data["choices"]) > 0:
                return data["choices"][0]["message"]["content"]
            return ""
        except Exception as e:
            raise ValueError(f"解析响应失败: {e}")

    def chat(self, messages: List[Dict]) -> Tuple[bool, str]:
        """发送聊天请求

        Args:
            messages: 消息列表，格式为 [{"role": "user", "content": "..."}]

        Returns:
            (success, result) - 成功状态和结果/错误信息
        """
        request_size = len(json.dumps(messages))
        logger_AI.info(f"[API:REQUEST] 开始API请求 - 消息数: {len(messages)}, 请求大小: {request_size} 字符")

        attempt = 0
        last_error = ""

        while attempt < self.config.max_retries:
            attempt += 1

            start_time = time.time()
            try:
                request_data = self._create_request(messages)
                headers = self._get_headers()

                logger_AI.debug(f"[API:DETAIL] 请求详情 - 端点: {self.config.api_url}, 模型: {self.config.model}, 重试: {attempt}/{self.config.max_retries}")

                response = self.session.post(
                    self.config.api_url,
                    json=request_data,
                    headers=headers,
                    timeout=30
                )

                duration_ms = int((time.time() - start_time) * 1000)
                status_code = response.status_code
                response_size = len(response.text)

                logger_AI.debug(f"[API:RESPONSE] 收到响应 - 状态码: {status_code}, 响应大小: {response_size} 字符, 耗时: {duration_ms}ms")

                # 记录API请求和响应
                log_api_event(
                    logger_AI,
                    'RESPONSE' if status_code == 200 else 'ERROR',
                    self.config.api_url,
                    status=str(status_code),
                    duration_ms=duration_ms,
                    request_size=request_size,
                    response_size=response_size
                )

                # 处理不同的状态码
                if status_code == 200:
                    try:
                        result = self._parse_response(response)
                        result_size = len(result)
                        logger_AI.info(f"[API:SUCCESS] API请求成功 - 响应内容长度: {result_size} 字符")
                        log_performance(logger_AI, "API调用成功", duration_ms, response_chars=result_size)
                        return True, result
                    except Exception as e:
                        last_error = str(e)
                        logger_AI.error(f"[API:PARSE_ERROR] 解析响应失败: {str(e)}")
                        if attempt >= self.config.max_retries:
                            return False, last_error
                elif status_code == 401:
                    log_api_event(logger_AI, 'FAILED', self.config.api_url, status='401', error='认证失败')
                    logger_AI.error("[API:AUTH_ERROR] 认证失败 (HTTP 401): API密钥无效或已过期")
                    return False, "认证失败 (HTTP 401): API密钥无效或已过期"
                elif status_code == 403:
                    log_api_event(logger_AI, 'FAILED', self.config.api_url, status='403', error='拒绝访问')
                    logger_AI.error("[API:AUTH_ERROR] 拒绝访问 (HTTP 403): 没有权限访问此资源")
                    return False, "拒绝访问 (HTTP 403): 没有权限访问此资源"
                elif status_code == 404:
                    log_api_event(logger_AI, 'FAILED', self.config.api_url, status='404', error='资源不存在')
                    logger_AI.error("[API:NOT Found] 资源不存在 (HTTP 404): API端点URL可能不正确")
                    return False, "资源不存在 (HTTP 404): API端点URL可能不正确"
                elif status_code == 429:
                    last_error = f"请求过于频繁 (HTTP 429): {response.text[:200]}"
                    log_api_event(logger_AI, 'RATE_LIMIT', self.config.api_url, status='429', error='请求过于频繁')
                    logger_AI.warning(f"[API:RATE_LIMIT] 请求过于频繁 (HTTP 429), 将重试...")
                elif status_code >= 500:
                    last_error = f"服务器错误 (HTTP {status_code}): {response.text[:200]}"
                    log_api_event(logger_AI, 'SERVER_ERROR', self.config.api_url, status=str(status_code), error='服务器错误')
                    logger_AI.warning(f"[API:SERVER_ERROR] 服务器错误 (HTTP {status_code}), 将重试...")
                else:
                    last_error = f"请求失败 (HTTP {status_code}): {response.text[:200]}"
                    log_api_event(logger_AI, 'FAILED', self.config.api_url, status=str(status_code), error=f'请求失败: {last_error[:50]}')

            except requests.Timeout:
                last_error = "连接超时: 请检查网络连接或API服务是否可用"
                logger_AI.error(f"[API:TIMEOUT] 连接超时 - 尝试 {attempt}/{self.config.max_retries}")
            except requests.ConnectionError as e:
                last_error = f"连接失败: 无法连接到API服务器 - {e}"
                logger_AI.error(f"[API:CONNECTION] 连接失败 - {str(e)}")
            except Exception as e:
                last_error = f"请求错误: {e}"
                logger_AI.error(f"[API:ERROR] 请求异常 - {type(e).__name__}: {str(e)}")

            # 重试前等待
            if attempt < self.config.max_retries:
                logger_AI.info(f"[API:RETRY] {self.config.retry_delay} 秒后重试...")
                log_performance(logger_AI, "API重试等待", self.config.retry_delay * 1000)
                time.sleep(self.config.retry_delay)

        log_api_event(logger_AI, 'ERROR', self.config.api_url, error=last_error[:100])
        logger_AI.error(f"[API:FAILED] 所有重试失败 - 最终错误: {last_error}")
        return False, last_error

    def test_connection(self) -> Tuple[bool, str]:
        """测试 API 连接

        Returns:
            (success, message) - 成功状态和消息
        """
        logger_AI.info(f"[API:TEST] 测试 API 连接 - 端点: {self.config.api_url}, 模型: {self.config.model}")
        messages = [{"role": "user", "content": "测试连接"}]
        success, result = self.chat(messages)
        if success:
            logger_AI.info("[API:TEST] API 连接测试成功")
        else:
            logger_AI.error(f"[API:TEST] API 连接测试失败: {result}")
        return success, result

    def classify_folder_risk(self, folder_name: str, folder_path: str,
                           folder_type: str, size: str) -> Tuple[bool, str, str]:
        """使用 AI 评估文件夹风险

        Args:
            folder_name: 文件夹名称
            folder_path: 文件夹路径
            folder_type: 文件夹类型 (Roaming/Local/LocalLow)
            size: 文件夹大小

        Returns:
            (success, risk_level, reason) - 成功状态、风险等级和原因
        """
        logger_AI.debug(f"[AI:CLASSIFY] 开始评估文件夹风险 - 名称: {folder_name}, 类型: {folder_type}, 大小: {size}")
        system_prompt = """# 角色：Windows AppData 安全评估专家

## 任务
评估以下 AppData 文件夹的安全性，将其分为三个风险等级。

## 评估标准

### 安全 - 可直接删除
1. 明确的缓存文件夹（cache, Cache）
2. 临时文件夹（temp, Temp, tmp）
3. 预取数据文件夹（Prefetch）
4. 日志文件夹（logs, Logs）
5. 下载缓存文件夹（Downloads）

### 疑似 - 需要用户确认
1. 配置文件文件夹（config, settings）
2. 用户数据文件夹（UserData, data）
3. 不确定用途的文件夹
4. 应用程序核心文件夹

### 危险 - 不建议删除
1. 系统关键数据
2. 用户重要数据
3. 删除会导致应用无法启动的数据

## 输出格式
请按照以下 JSON 格式输出（不要包含其他文字）：
```json
{
  "risk_level": "安全|疑似|危险",
  "reason": "评估原因",
  "confidence": "高|中|低"
}
```
"""

        user_prompt = f"""请评估以下 AppData 文件夹：

- 文件夹名称: {folder_name}
- 所属目录: {folder_type}
- 完整路径: {folder_path}
- 大小: {size}

请给出风险评估结果。"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        logger_AI.debug(f"[AI:CLASSIFY] 发送AI评估请求 - 文件夹: {folder_name}")
        success, result = self.chat(messages)

        if not success:
            logger_AI.error(f"[AI:CLASSIFY] AI评估失败 - {folder_name}: {result}")
            return False, "", result

        # 解析 JSON 响应
        try:
            # 尝试提取 JSON 代码块
            if "```json" in result:
                json_start = result.find("```json") + 7
                json_end = result.find("```", json_start)
                json_str = result[json_start:json_end].strip()
            else:
                json_str = result.strip()

            data = json.loads(json_str)
            risk_level = data.get("risk_level", "疑似")
            reason = data.get("reason", "AI评估完成")

            logger_AI.info(f"[AI:CLASSIFY] AI评估完成 - 文件夹: {folder_name}, 风险: {risk_level}, 原因: {reason}")
            return True, risk_level, reason
        except Exception as e:
            # 如果解析失败，尝试简单文本匹配
            if "危险" in result:
                return True, "危险", result
            elif "疑似" in result:
                return True, "疑似", result
            elif "安全" in result:
                return True, "安全", result
            else:
                return False, "", f"解析AI响应失败: {e}"

    def get_folder_description(self, folder_type: str, folder_name: str) -> Tuple[bool, str]:
        """获取文件夹描述

        Args:
            folder_type: 文件夹类型 (Local/LocalLow/Roaming)
            folder_name: 文件夹名称

        Returns:
            (success, description) - 成功状态和描述/错误信息
        """
        logger_AI.debug(f"[AI:DESC] 开始获取文件夹描述 - 类型: {folder_type}, 名称: {folder_name}")

        system_prompt = """# 角色：Windows AppData 分析专家

## 任务
分析用户提供的 AppData 文件夹信息并给出简要描述。

## 输出格式
请按照以下 JSON 格式输出：
```json
{
  "software_name": "软件名称",
  "data_category": "配置|缓存|用户数据|日志",
  "purpose": "应用用途（简短描述，50字以内）",
  "safe_to_delete": "是|否"
}
```
"""

        user_prompt = f"""请分析 Windows 系统中 AppData 下的 [{folder_type}] 文件夹中的 [{folder_name}] 子文件夹的用途。"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        logger_AI.debug(f"[AI:DESC] 发送AI描述请求 - 文件夹: {folder_name}")
        success, result = self.chat(messages)

        if not success:
            logger_AI.error(f"[AI:DESC] AI描述失败 - {folder_name}: {result}")
            return False, result

        logger_AI.info(f"[AI:DESC] AI描述完成 - 文件夹: {folder_name}")
        return True, result
