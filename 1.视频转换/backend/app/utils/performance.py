"""
性能优化工具
"""
import time
import functools
from typing import Callable, Any
from .logger import setup_logger

logger = setup_logger()


def timing_decorator(func: Callable) -> Callable:
    """
    计时装饰器 - 记录函数执行时间
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            duration = time.time() - start_time
            logger.info(
                "Function completed",
                function=func.__name__,
                duration_seconds=round(duration, 3)
            )
            return result
        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                "Function failed",
                function=func.__name__,
                duration_seconds=round(duration, 3),
                error=str(e)
            )
            raise
    return wrapper


def memory_usage_decorator(func: Callable) -> Callable:
    """
    内存使用装饰器 - 记录内存使用情况
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        try:
            import psutil
            import os
            
            process = psutil.Process(os.getpid())
            memory_before = process.memory_info().rss / 1024 / 1024  # MB
            
            result = func(*args, **kwargs)
            
            memory_after = process.memory_info().rss / 1024 / 1024  # MB
            memory_diff = memory_after - memory_before
            
            logger.info(
                "Memory usage",
                function=func.__name__,
                memory_before_mb=round(memory_before, 2),
                memory_after_mb=round(memory_after, 2),
                memory_diff_mb=round(memory_diff, 2)
            )
            
            return result
        except ImportError:
            # psutil 未安装，直接执行函数
            return func(*args, **kwargs)
    
    return wrapper


class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self):
        self.metrics = {}
    
    def record_metric(self, name: str, value: float, unit: str = 'seconds'):
        """记录性能指标"""
        if name not in self.metrics:
            self.metrics[name] = []
        
        self.metrics[name].append({
            'value': value,
            'unit': unit,
            'timestamp': time.time()
        })
        
        logger.info(
            "Performance metric recorded",
            metric_name=name,
            value=value,
            unit=unit
        )
    
    def get_average(self, name: str) -> float:
        """获取指标平均值"""
        if name not in self.metrics or not self.metrics[name]:
            return 0.0
        
        values = [m['value'] for m in self.metrics[name]]
        return sum(values) / len(values)
    
    def get_percentile(self, name: str, percentile: int = 95) -> float:
        """获取指标百分位数"""
        if name not in self.metrics or not self.metrics[name]:
            return 0.0
        
        values = sorted([m['value'] for m in self.metrics[name]])
        index = int(len(values) * percentile / 100)
        return values[min(index, len(values) - 1)]
    
    def clear_metrics(self, name: str = None):
        """清除指标数据"""
        if name:
            self.metrics.pop(name, None)
        else:
            self.metrics.clear()


# 全局性能监控器
performance_monitor = PerformanceMonitor()


def monitor_performance(metric_name: str):
    """性能监控装饰器"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                performance_monitor.record_metric(metric_name, duration)
                return result
            except Exception as e:
                duration = time.time() - start_time
                performance_monitor.record_metric(f"{metric_name}_error", duration)
                raise
        return wrapper
    return decorator


def optimize_video_processing():
    """视频处理优化建议"""
    return {
        'ffmpeg_threads': 'auto',  # 自动检测线程数
        'memory_limit': '512M',    # 内存限制
        'preset': 'medium',        # 编码预设（速度vs质量平衡）
        'crf': 23,                # 恒定质量因子
        'buffer_size': '2M'       # 缓冲区大小
    }


def get_system_resources():
    """获取系统资源信息"""
    try:
        import psutil
        
        return {
            'cpu_percent': psutil.cpu_percent(interval=1),
            'memory_percent': psutil.virtual_memory().percent,
            'disk_percent': psutil.disk_usage('/').percent,
            'cpu_count': psutil.cpu_count(),
            'memory_total_gb': round(psutil.virtual_memory().total / 1024 / 1024 / 1024, 2)
        }
    except ImportError:
        return {
            'cpu_percent': 0,
            'memory_percent': 0,
            'disk_percent': 0,
            'cpu_count': 1,
            'memory_total_gb': 0
        }
