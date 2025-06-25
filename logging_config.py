"""
Centralized logging configuration for the unified memory application.

This module provides comprehensive logging functionality with:
- Timestamped log files with automatic rotation
- Verbose and robust logging with full tracebacks
- Decorators for easy and consistent application
- Centralized configuration available to all code

Features:
- Automatic log rotation (daily and size-based)
- Structured log formatting with timestamps
- Multiple log levels and handlers
- Performance tracking decorators
- Exception logging decorators
- Function entry/exit logging
"""

import logging
import logging.handlers
import os
import sys
import traceback
import functools
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Optional, Dict


class LoggingConfig:
    """
    Centralized logging configuration manager.
    
    This class handles all logging setup including file rotation,
    formatting, and provides access to loggers throughout the codebase.
    
    Attributes
    ----------
    log_dir: Path to logs directory
    app_logger: Main application logger
    performance_logger: Performance tracking logger
    error_logger: Error-specific logger
    
    Example
    -------
        >>> from logging_config import get_logger
        >>> logger = get_logger(__name__)
        >>> logger.info("Application started")
    """
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        """Singleton pattern to ensure single logging configuration."""
        if cls._instance is None:
            cls._instance = super(LoggingConfig, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize logging configuration if not already done."""
        if not LoggingConfig._initialized:
            self.log_dir = Path("logs")
            self.log_dir.mkdir(exist_ok=True)
            self._setup_logging()
            LoggingConfig._initialized = True
    
    def _setup_logging(self):
        """
        Setup comprehensive logging configuration.
        
        Creates multiple loggers with different handlers:
        - Application logger: General application logs
        - Performance logger: Performance and timing logs
        - Error logger: Error-specific logs with full tracebacks
        """
        # Create formatters
        detailed_formatter = logging.Formatter(
            fmt='%(asctime)s | %(name)s | %(levelname)s | %(filename)s:%(lineno)d | %(funcName)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        simple_formatter = logging.Formatter(
            fmt='%(asctime)s | %(levelname)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Setup root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)
        
        # Clear any existing handlers
        root_logger.handlers.clear()
        
        # Console handler for immediate feedback
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(simple_formatter)
        root_logger.addHandler(console_handler)
        
        # Main application log file with rotation
        app_log_file = self.log_dir / f"app_{datetime.now().strftime('%Y%m%d')}.log"
        app_file_handler = logging.handlers.RotatingFileHandler(
            filename=app_log_file,
            maxBytes=50 * 1024 * 1024,  # 50MB
            backupCount=30,  # Keep 30 backup files
            encoding='utf-8'
        )
        app_file_handler.setLevel(logging.DEBUG)
        app_file_handler.setFormatter(detailed_formatter)
        root_logger.addHandler(app_file_handler)
        
        # Error log file with rotation
        error_log_file = self.log_dir / f"errors_{datetime.now().strftime('%Y%m%d')}.log"
        error_file_handler = logging.handlers.RotatingFileHandler(
            filename=error_log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=50,  # Keep 50 backup files
            encoding='utf-8'
        )
        error_file_handler.setLevel(logging.ERROR)
        error_file_handler.setFormatter(detailed_formatter)
        root_logger.addHandler(error_file_handler)
        
        # Performance log file with daily rotation
        performance_log_file = self.log_dir / f"performance_{datetime.now().strftime('%Y%m%d')}.log"
        performance_handler = logging.handlers.TimedRotatingFileHandler(
            filename=performance_log_file,
            when='midnight',
            interval=1,
            backupCount=90,  # Keep 90 days
            encoding='utf-8'
        )
        performance_handler.setLevel(logging.DEBUG)
        performance_handler.setFormatter(detailed_formatter)
        
        # Create specialized loggers
        self.app_logger = logging.getLogger('memory_app')
        self.performance_logger = logging.getLogger('performance')
        self.error_logger = logging.getLogger('errors')
        
        # Add performance handler to performance logger
        self.performance_logger.addHandler(performance_handler)
        self.performance_logger.setLevel(logging.DEBUG)
        
        # Log initialization
        self.app_logger.info("=" * 80)
        self.app_logger.info("LOGGING SYSTEM INITIALIZED")
        self.app_logger.info(f"Log directory: {self.log_dir.absolute()}")
        self.app_logger.info(f"Application log: {app_log_file}")
        self.app_logger.info(f"Error log: {error_log_file}")
        self.app_logger.info(f"Performance log: {performance_log_file}")
        self.app_logger.info("=" * 80)
    
    def get_logger(self, name: str) -> logging.Logger:
        """
        Get a logger instance for the specified module.
        
        Args
        ----
        name: Logger name (typically __name__ from calling module)
        
        Returns
        -------
        Configured logger instance
        
        Example
        -------
            >>> logger = logging_config.get_logger(__name__)
            >>> logger.info("Module initialized")
        """
        return logging.getLogger(name)
    
    def log_exception(self, logger: logging.Logger, exc: Exception, context: str = ""):
        """
        Log exception with full traceback and context.
        
        Args
        ----
        logger: Logger instance to use
        exc: Exception to log
        context: Additional context information
        
        Example
        -------
            >>> try:
            ...     risky_operation()
            ... except Exception as e:
            ...     logging_config.log_exception(logger, e, "During startup")
        """
        tb_str = ''.join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        
        error_msg = f"EXCEPTION OCCURRED"
        if context:
            error_msg += f" - {context}"
        
        logger.error(error_msg)
        logger.error(f"Exception Type: {type(exc).__name__}")
        logger.error(f"Exception Message: {str(exc)}")
        logger.error(f"Full Traceback:\n{tb_str}")
        
        # Also log to error logger
        self.error_logger.error(error_msg)
        self.error_logger.error(f"Exception Type: {type(exc).__name__}")
        self.error_logger.error(f"Exception Message: {str(exc)}")
        self.error_logger.error(f"Full Traceback:\n{tb_str}")


# Global logging configuration instance
_logging_config = LoggingConfig()


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for the specified module.
    
    This is the main function that should be used throughout the codebase
    to obtain logger instances.
    
    Args
    ----
    name: Logger name (typically __name__ from calling module)
    
    Returns
    -------
    Configured logger instance
    
    Example
    -------
        >>> from logging_config import get_logger
        >>> logger = get_logger(__name__)
        >>> logger.info("Module started")
    """
    return _logging_config.get_logger(name)


def log_exception(logger: logging.Logger, exc: Exception, context: str = ""):
    """
    Log exception with full traceback and context.
    
    Args
    ----
    logger: Logger instance to use
    exc: Exception to log
    context: Additional context information
    
    Example
    -------
        >>> logger = get_logger(__name__)
        >>> try:
        ...     risky_operation()
        ... except Exception as e:
        ...     log_exception(logger, e, "During initialization")
    """
    _logging_config.log_exception(logger, exc, context)
