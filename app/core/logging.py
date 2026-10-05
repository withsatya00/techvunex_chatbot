import logging
import sys
import json
import time
from typing import Optional, Dict, Any

class StructuredJsonFormatter(logging.Formatter):
    """
    Format logs as JSON objects for production observability.
    Masks sensitive keys like passwords, api keys, and tokens.
    """
    SENSITIVE_KEYS = {"password", "token", "secret", "api_key", "authorization", "key"}

    def format(self, record: logging.LogRecord) -> str:
        log_obj: Dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add extra attributes
        for key, val in record.__dict__.items():
            if key not in ("args", "asctime", "created", "exc_info", "exc_text", 
                           "filename", "funcName", "id", "levelname", "levelno", 
                           "lineno", "module", "msecs", "message", "msg", 
                           "name", "pathname", "process", "processName", 
                           "relativeCreated", "stack_info", "thread", "threadName"):
                if any(sens in key.lower() for sens in self.SENSITIVE_KEYS):
                    log_obj[key] = "***REDACTED***"
                else:
                    log_obj[key] = val

        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_obj)

def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(StructuredJsonFormatter())
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger

logger = get_logger("techvunex_chatbot")
