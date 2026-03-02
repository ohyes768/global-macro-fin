"""日志配置模块"""
import logging
from pathlib import Path


def setup_logger(name: str = "global-macro-fin", log_dir: str = "logs") -> logging.Logger:
    """配置日志记录器

    Args:
        name: 日志记录器名称
        log_dir: 日志目录

    Returns:
        配置好的日志记录器
    """
    log_path = Path(log_dir)
    log_path.mkdir(exist_ok=True)

    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    # 避免重复添加处理器
    if logger.handlers:
        return logger

    # 文件处理器
    file_handler = logging.FileHandler(log_path / "service.log", encoding="utf-8")
    file_handler.setLevel(logging.INFO)

    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    # 格式化器
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger
