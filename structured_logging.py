#!/usr/bin/env python3
"""
Модуль для структурированного логирования
"""

import logging
import json
import sys
from datetime import datetime
from typing import Any, Dict

class StructuredFormatter(logging.Formatter):
    """
    Форматтер для JSON логов с структурированными полями
    """
    
    def format(self, record: logging.LogRecord) -> str:
        # Базовые поля
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # Добавляем дополнительные поля если есть
        if hasattr(record, 'user_id'):
            log_entry['user_id'] = record.user_id
        if hasattr(record, 'browser_id'):
            log_entry['browser_id'] = record.browser_id
        if hasattr(record, 'batch_id'):
            log_entry['batch_id'] = record.batch_id
        if hasattr(record, 'execution_time'):
            log_entry['execution_time'] = record.execution_time
        if hasattr(record, 'memory_usage'):
            log_entry['memory_usage'] = record.memory_usage
            
        # Исключения
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_entry, ensure_ascii=False)

def setup_structured_logging():
    """
    Настройка структурированного логирования для production
    """
    # Корневой логгер
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # Очищаем существующие хендлеры
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # JSON хендлер для stdout
    json_handler = logging.StreamHandler(sys.stdout)
    json_handler.setFormatter(StructuredFormatter())
    json_handler.setLevel(logging.INFO)
    root_logger.addHandler(json_handler)
    
    # Настройка уровней для разных модулей
    logging.getLogger('werkzeug').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('selenium').setLevel(logging.WARNING)
    
    return root_logger

def get_logger(name: str) -> logging.Logger:
    """
    Получить логгер с именем
    """
    return logging.getLogger(name)

def log_browser_event(logger: logging.Logger, message: str, 
                     browser_id: int = None, user_id: str = None, 
                     batch_id: int = None, execution_time: float = None, 
                     level: str = "INFO"):
    """
    Логирование событий браузера с дополнительными метаданными
    """
    extra = {}
    if browser_id is not None:
        extra['browser_id'] = browser_id
    if user_id is not None:
        extra['user_id'] = user_id
    if batch_id is not None:
        extra['batch_id'] = batch_id
    if execution_time is not None:
        extra['execution_time'] = execution_time
    
    if level.upper() == "ERROR":
        logger.error(message, extra=extra)
    elif level.upper() == "WARNING":
        logger.warning(message, extra=extra)
    elif level.upper() == "DEBUG":
        logger.debug(message, extra=extra)
    else:
        logger.info(message, extra=extra)

def log_user_activity(logger: logging.Logger, user_id: str, 
                     username: str, nickname: str, ean_count: int, 
                     uploaded_file: str):
    """
    Логирование активности пользователя
    """
    extra = {
        'user_id': user_id,
        'username': username,
        'nickname': nickname,
        'ean_count': ean_count,
        'uploaded_file': uploaded_file,
        'event_type': 'user_activity'
    }
    logger.info(f"User activity: {username} uploaded {uploaded_file} with {ean_count} EANs", 
               extra=extra)