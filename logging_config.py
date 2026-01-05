#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
QBot v2.0 - Centralized Logging Configuration
Tất cả modules sẽ log vào:
- log_info.txt: Tất cả logs (INFO, WARNING, ERROR, CRITICAL)
- log_error.txt: Chỉ ERROR và CRITICAL
"""

import logging
import os
from logging.handlers import RotatingFileHandler
from datetime import datetime

# Đường dẫn thư mục logs
LOG_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_INFO_FILE = os.path.join(LOG_DIR, "log_info.txt")
LOG_ERROR_FILE = os.path.join(LOG_DIR, "log_error.txt")

# Format cho log messages
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)-25s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

def setup_logger(module_name):
    """
    Setup logger cho mỗi module với 2 file handlers:
    - log_info.txt: Tất cả logs (INFO+)
    - log_error.txt: Chỉ ERROR và CRITICAL
    
    Args:
        module_name (str): Tên module (VD: "hd_order", "hd_update_all")
    
    Returns:
        logging.Logger: Logger đã config
    """
    logger = logging.getLogger(module_name)
    
    # Nếu logger đã được setup rồi, return luôn
    if logger.handlers:
        return logger
    
    logger.setLevel(logging.INFO)
    
    # Formatter
    formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)
    
    # Handler 1: log_info.txt - Tất cả logs (INFO, WARNING, ERROR, CRITICAL)
    info_handler = RotatingFileHandler(
        LOG_INFO_FILE,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    info_handler.setLevel(logging.INFO)
    info_handler.setFormatter(formatter)
    
    # Handler 2: log_error.txt - Chỉ ERROR và CRITICAL
    error_handler = RotatingFileHandler(
        LOG_ERROR_FILE,
        maxBytes=5*1024*1024,   # 5MB
        backupCount=3,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    
    # Handler 3: Console output (optional, có thể comment nếu không cần)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    
    # Add handlers
    logger.addHandler(info_handler)
    logger.addHandler(error_handler)
    logger.addHandler(console_handler)
    
    return logger


def log_startup(module_name):
    """
    Log startup message khi module bắt đầu chạy
    
    Args:
        module_name (str): Tên module
    """
    logger = logging.getLogger(module_name)
    logger.info("=" * 70)
    logger.info(f"{module_name.upper()} - STARTED")
    logger.info(f"PID: {os.getpid()}")
    logger.info(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 70)


def log_shutdown(module_name, reason="Normal shutdown"):
    """
    Log shutdown message khi module dừng
    
    Args:
        module_name (str): Tên module
        reason (str): Lý do shutdown
    """
    logger = logging.getLogger(module_name)
    logger.info("=" * 70)
    logger.info(f"{module_name.upper()} - STOPPED")
    logger.info(f"Reason: {reason}")
    logger.info(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 70)


def log_error_with_context(module_name, error, context=None):
    """
    Log error với context chi tiết
    
    Args:
        module_name (str): Tên module
        error (Exception): Exception object
        context (dict): Context information (symbol, order_id, etc.)
    """
    logger = logging.getLogger(module_name)
    logger.error(f"ERROR: {type(error).__name__}: {str(error)}")
    
    if context:
        logger.error(f"Context: {context}")
    
    # Log traceback nếu có
    import traceback
    logger.error(f"Traceback:\n{traceback.format_exc()}")


# Test function
if __name__ == "__main__":
    # Test logging
    test_logger = setup_logger("TEST_MODULE")
    log_startup("TEST_MODULE")
    
    test_logger.info("This is an INFO message")
    test_logger.warning("This is a WARNING message")
    test_logger.error("This is an ERROR message")
    test_logger.critical("This is a CRITICAL message")
    
    # Test error with context
    try:
        1 / 0
    except Exception as e:
        log_error_with_context("TEST_MODULE", e, context={
            "symbol": "BTC/USDT",
            "order_id": "12345678"
        })
    
    log_shutdown("TEST_MODULE", reason="Test completed")
    
    print(f"\n✅ Logs written to:")
    print(f"   - {LOG_INFO_FILE}")
    print(f"   - {LOG_ERROR_FILE}")

