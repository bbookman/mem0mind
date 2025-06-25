"""
Tests for the comprehensive logging system.

This module tests the logging functionality including:
- LoggingConfig initialization and setup
- Log file creation and rotation
- Logger retrieval and usage
- Exception logging with tracebacks
- Decorator functionality for automatic logging
"""

import pytest
import tempfile
import shutil
import time
import os
from pathlib import Path
from unittest.mock import patch, Mock
import logging

from logging_config import LoggingConfig, get_logger, log_exception
from logging_decorators import (
    log_function_calls,
    log_performance,
    log_exceptions,
    log_retry_attempts,
    log_method_calls
)


class TestLoggingConfig:
    """Test LoggingConfig class functionality."""
    
    def test_singleton_pattern(self):
        """Test that LoggingConfig follows singleton pattern."""
        config1 = LoggingConfig()
        config2 = LoggingConfig()
        
        assert config1 is config2
        assert id(config1) == id(config2)
    
    def test_log_directory_creation(self):
        """Test that logs directory is created."""
        config = LoggingConfig()
        
        assert config.log_dir.exists()
        assert config.log_dir.is_dir()
        assert config.log_dir.name == "logs"
    
    def test_logger_retrieval(self):
        """Test getting logger instances."""
        config = LoggingConfig()
        
        logger1 = config.get_logger("test_module")
        logger2 = config.get_logger("test_module")
        logger3 = config.get_logger("different_module")
        
        assert logger1 is logger2  # Same module should return same logger
        assert logger1 is not logger3  # Different modules should have different loggers
        assert logger1.name == "test_module"
        assert logger3.name == "different_module"
    
    def test_specialized_loggers_exist(self):
        """Test that specialized loggers are created."""
        config = LoggingConfig()
        
        assert hasattr(config, 'app_logger')
        assert hasattr(config, 'performance_logger')
        assert hasattr(config, 'error_logger')
        
        assert config.app_logger.name == 'memory_app'
        assert config.performance_logger.name == 'performance'
        assert config.error_logger.name == 'errors'


class TestLoggerFunctions:
    """Test global logger functions."""
    
    def test_get_logger_function(self):
        """Test the global get_logger function."""
        logger = get_logger("test_module")
        
        assert isinstance(logger, logging.Logger)
        assert logger.name == "test_module"
    
    def test_log_exception_function(self):
        """Test the global log_exception function."""
        logger = get_logger("test_exception")
        
        # Create a test exception
        try:
            raise ValueError("Test exception message")
        except Exception as e:
            # Should not raise any errors
            log_exception(logger, e, "Test context")
            
        # Test passes if no exception is raised


class TestLogFunctionCallsDecorator:
    """Test the log_function_calls decorator."""
    
    def test_basic_function_logging(self):
        """Test basic function call logging."""
        logger = get_logger("test_decorator")
        
        @log_function_calls(include_params=True, include_result=True)
        def test_function(param1, param2="default"):
            return f"result: {param1}, {param2}"
        
        # Function should execute normally
        result = test_function("test", param2="value")
        assert result == "result: test, value"
    
    def test_function_logging_without_params(self):
        """Test function logging without parameter logging."""
        @log_function_calls(include_params=False, include_result=False)
        def test_function(param1, param2):
            return "success"
        
        result = test_function("arg1", "arg2")
        assert result == "success"
    
    def test_function_logging_with_exception(self):
        """Test function logging when exception occurs."""
        @log_function_calls()
        def failing_function():
            raise RuntimeError("Test error")
        
        with pytest.raises(RuntimeError, match="Test error"):
            failing_function()


class TestLogPerformanceDecorator:
    """Test the log_performance decorator."""
    
    def test_performance_logging_above_threshold(self):
        """Test performance logging for slow operations."""
        @log_performance(threshold_seconds=0.1, log_level="INFO")
        def slow_function():
            time.sleep(0.2)
            return "completed"
        
        result = slow_function()
        assert result == "completed"
    
    def test_performance_logging_below_threshold(self):
        """Test that fast operations don't trigger performance logging."""
        @log_performance(threshold_seconds=1.0, log_level="INFO")
        def fast_function():
            return "fast"
        
        result = fast_function()
        assert result == "fast"
    
    def test_performance_logging_with_exception(self):
        """Test performance logging when function raises exception."""
        @log_performance(threshold_seconds=0.0)
        def failing_function():
            time.sleep(0.1)
            raise ValueError("Performance test error")
        
        with pytest.raises(ValueError, match="Performance test error"):
            failing_function()


class TestLogExceptionsDecorator:
    """Test the log_exceptions decorator."""
    
    def test_exception_logging_with_reraise(self):
        """Test exception logging with reraise enabled."""
        @log_exceptions("Test operation failed", reraise=True)
        def failing_function():
            raise RuntimeError("Test exception")
        
        with pytest.raises(RuntimeError, match="Test exception"):
            failing_function()
    
    def test_exception_logging_without_reraise(self):
        """Test exception logging without reraise."""
        @log_exceptions("Test operation failed", reraise=False)
        def failing_function():
            raise RuntimeError("Test exception")
        
        # Should return None instead of raising
        result = failing_function()
        assert result is None
    
    def test_exception_logging_success_case(self):
        """Test that decorator doesn't interfere with successful execution."""
        @log_exceptions("Should not log", reraise=True)
        def successful_function():
            return "success"
        
        result = successful_function()
        assert result == "success"


class TestLogRetryAttemptsDecorator:
    """Test the log_retry_attempts decorator."""
    
    def test_retry_success_on_first_attempt(self):
        """Test retry decorator when function succeeds immediately."""
        @log_retry_attempts(max_attempts=3, delay_seconds=0.1)
        def successful_function():
            return "success"
        
        result = successful_function()
        assert result == "success"
    
    def test_retry_success_after_failures(self):
        """Test retry decorator with eventual success."""
        call_count = 0
        
        @log_retry_attempts(max_attempts=3, delay_seconds=0.1)
        def eventually_successful_function():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise RuntimeError("Temporary failure")
            return "success"
        
        result = eventually_successful_function()
        assert result == "success"
        assert call_count == 2
    
    def test_retry_final_failure(self):
        """Test retry decorator when all attempts fail."""
        @log_retry_attempts(max_attempts=2, delay_seconds=0.1)
        def always_failing_function():
            raise RuntimeError("Always fails")
        
        with pytest.raises(RuntimeError, match="Always fails"):
            always_failing_function()
    
    def test_retry_non_retryable_exception(self):
        """Test that non-retryable exceptions are not retried."""
        @log_retry_attempts(max_attempts=3, delay_seconds=0.1, exceptions=(ValueError,))
        def function_with_type_error():
            raise TypeError("Not retryable")
        
        with pytest.raises(TypeError, match="Not retryable"):
            function_with_type_error()


class TestLogMethodCallsDecorator:
    """Test the log_method_calls class decorator."""
    
    def test_class_method_logging(self):
        """Test that class decorator logs all public methods."""
        @log_method_calls
        class TestClass:
            def __init__(self, name):
                self.name = name
            
            def public_method(self):
                return f"public: {self.name}"
            
            def another_public_method(self, param):
                return f"another: {param}"
            
            def _private_method(self):
                return "private"
        
        obj = TestClass("test")
        
        # Public methods should work normally
        result1 = obj.public_method()
        assert result1 == "public: test"
        
        result2 = obj.another_public_method("value")
        assert result2 == "another: value"
        
        # Private method should not be affected
        result3 = obj._private_method()
        assert result3 == "private"


class TestLogFileCreation:
    """Test that log files are actually created."""
    
    def test_log_files_exist(self):
        """Test that log files are created in the logs directory."""
        # Initialize logging system
        config = LoggingConfig()
        logger = get_logger("test_file_creation")
        
        # Generate some log entries
        logger.info("Test info message")
        logger.error("Test error message")
        
        # Check that log files exist
        log_dir = Path("logs")
        assert log_dir.exists()
        
        # Check for timestamped log files
        app_logs = list(log_dir.glob("app_*.log"))
        error_logs = list(log_dir.glob("errors_*.log"))
        performance_logs = list(log_dir.glob("performance_*.log"))
        
        assert len(app_logs) > 0, "Application log file should exist"
        assert len(error_logs) > 0, "Error log file should exist"
        assert len(performance_logs) > 0, "Performance log file should exist"
    
    def test_log_content_written(self):
        """Test that log content is actually written to files."""
        logger = get_logger("test_content")
        test_message = "Test log content message"
        
        logger.info(test_message)
        
        # Find the current app log file
        log_dir = Path("logs")
        app_logs = list(log_dir.glob("app_*.log"))
        
        assert len(app_logs) > 0
        
        # Read the log file and check for our message
        with open(app_logs[0], 'r') as f:
            log_content = f.read()
        
        assert test_message in log_content


class TestIntegratedLogging:
    """Test logging integration with real usage scenarios."""
    
    def test_complete_logging_workflow(self):
        """Test a complete logging workflow with multiple decorators."""
        logger = get_logger("test_workflow")
        
        @log_function_calls(include_params=True, include_result=True)
        @log_performance(threshold_seconds=0.1)
        @log_exceptions("Workflow failed")
        def complex_function(data, process=True):
            logger.info(f"Processing {len(data)} items")
            
            if process:
                time.sleep(0.15)  # Trigger performance logging
                return {"processed": len(data), "status": "success"}
            else:
                raise ValueError("Processing disabled")
        
        # Test successful execution
        result = complex_function([1, 2, 3, 4, 5], process=True)
        assert result["processed"] == 5
        assert result["status"] == "success"
        
        # Test exception case
        with pytest.raises(ValueError, match="Processing disabled"):
            complex_function([1, 2, 3], process=False)
    
    def test_logger_hierarchy(self):
        """Test that loggers maintain proper hierarchy."""
        parent_logger = get_logger("parent")
        child_logger = get_logger("parent.child")
        
        assert parent_logger.name == "parent"
        assert child_logger.name == "parent.child"
        
        # Both should be Logger instances
        assert isinstance(parent_logger, logging.Logger)
        assert isinstance(child_logger, logging.Logger)
