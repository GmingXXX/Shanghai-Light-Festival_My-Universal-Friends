"""
结构化日志工具
"""
import structlog
import logging
import sys
from typing import Any, Dict


def setup_logger(service_name: str = "alphavid-converter") -> structlog.stdlib.BoundLogger:
    """
    设置结构化日志
    
    Args:
        service_name: 服务名称
        
    Returns:
        配置好的 logger 实例
    """
    
    # 配置标准库日志
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.INFO,
    )
    
    # 配置 structlog
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.JSONRenderer()
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=False,
    )
    
    # 创建 logger 实例并绑定服务信息
    logger = structlog.get_logger()
    logger = logger.bind(service=service_name)
    
    return logger


def log_request(logger: structlog.stdlib.BoundLogger, 
                method: str, 
                path: str, 
                **kwargs) -> None:
    """记录请求日志"""
    logger.info(
        "HTTP request",
        method=method,
        path=path,
        **kwargs
    )


def log_task_start(logger: structlog.stdlib.BoundLogger,
                   task_id: str,
                   file_id: str,
                   **kwargs) -> None:
    """记录任务开始"""
    logger.info(
        "Task started",
        task_id=task_id,
        file_id=file_id,
        **kwargs
    )


def log_task_complete(logger: structlog.stdlib.BoundLogger,
                      task_id: str,
                      file_id: str,
                      duration_seconds: float,
                      **kwargs) -> None:
    """记录任务完成"""
    logger.info(
        "Task completed",
        task_id=task_id,
        file_id=file_id,
        duration_seconds=duration_seconds,
        **kwargs
    )


def log_task_error(logger: structlog.stdlib.BoundLogger,
                   task_id: str,
                   file_id: str,
                   error_code: str,
                   error_message: str,
                   **kwargs) -> None:
    """记录任务错误"""
    logger.error(
        "Task failed",
        task_id=task_id,
        file_id=file_id,
        error_code=error_code,
        error_message=error_message,
        **kwargs
    )
