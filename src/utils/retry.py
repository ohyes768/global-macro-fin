"""重试装饰器模块"""
import asyncio
import functools
from typing import Callable, TypeVar, ParamSpec
from src.utils.logger import setup_logger

logger = setup_logger("retry")

P = ParamSpec("P")
R = TypeVar("R")


def async_retry(max_retries: int = 3, delay: float = 1.0):
    """异步函数重试装饰器

    Args:
        max_retries: 最大重试次数
        delay: 重试延迟（秒）

    Returns:
        装饰器函数
    """

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @functools.wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        wait_time = delay * (2**attempt)
                        logger.warning(
                            f"{func.__name__} 失败 (尝试 {attempt + 1}/{max_retries}): {str(e)}，"
                            f"{wait_time:.1f}秒后重试..."
                        )
                        await asyncio.sleep(wait_time)
                    else:
                        logger.error(
                            f"{func.__name__} 失败，已达到最大重试次数 ({max_retries})"
                        )
            raise last_exception

        return wrapper

    return decorator
