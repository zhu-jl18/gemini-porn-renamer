"""自定义异常类型 - 区分不同类型的错误."""

from __future__ import annotations


class VRenamerError(Exception):
    """基础异常类 - 所有自定义异常的基类."""

    pass


class ConfigError(VRenamerError):
    """配置错误 - 配置文件缺失、格式错误、参数无效等."""

    pass


class APIError(VRenamerError):
    """API 调用错误 - LLM API 调用失败、超时、响应格式错误等."""

    def __init__(self, message: str, status_code: int = None, response: str = None):
        """初始化 API 错误.

        Args:
            message: 错误消息
            status_code: HTTP 状态码（可选）
            response: 原始响应内容（可选）
        """
        super().__init__(message)
        self.status_code = status_code
        self.response = response


class VideoProcessingError(VRenamerError):
    """视频处理错误 - 视频抽帧、转码、分析失败等."""

    pass


class FileOperationError(VRenamerError):
    """文件操作错误 - 文件读写、重命名、权限问题等."""

    pass


class ValidationError(VRenamerError):
    """验证错误 - 数据验证失败、格式不符合要求等."""

    pass
