"""
Logging decorators for easy and consistent application throughout the codebase.

This module provides decorators that can be applied to functions and methods
to automatically add logging functionality including:
- Function entry/exit logging
- Performance timing
- Exception handling with full tracebacks
- Parameter and return value logging
- Retry attempt logging

Usage Examples:
    @log_function_calls
    def my_function(param1, param2):
        return result
    
    @log_performance
    def slow_operation():
        time.sleep(1)
        return "done"
    
    @log_exceptions("Critical operation failed")
    def risky_operation():
        might_fail()
"""

import functools
import time
import traceback
from typing import Any, Callable, Optional, Dict, List
from logging_config import get_logger, log_exception


def log_function_calls(
    include_params: bool = True,
    include_result: bool = True,
    log_level: str = "DEBUG"
):
    """
    Decorator to log function entry, exit, parameters, and return values.
    
    Args
    ----
    include_params: Whether to log function parameters
    include_result: Whether to log return value
    log_level: Logging level to use (DEBUG, INFO, WARNING, ERROR)
    
    Example
    -------
        @log_function_calls(include_params=True, include_result=False)
        def process_data(data, options=None):
            return processed_data
    """
    def decorator(func: Callable) -> Callable:
        logger = get_logger(func.__module__)
        log_method = getattr(logger, log_level.lower())
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            func_name = f"{func.__module__}.{func.__qualname__}"
            
            # Log function entry
            entry_msg = f"ENTERING: {func_name}"
            if include_params and (args or kwargs):
                params = []
                if args:
                    params.extend([f"arg{i}={repr(arg)}" for i, arg in enumerate(args)])
                if kwargs:
                    params.extend([f"{k}={repr(v)}" for k, v in kwargs.items()])
                entry_msg += f" | Parameters: {', '.join(params)}"
            
            log_method(entry_msg)
            
            try:
                # Execute function
                result = func(*args, **kwargs)
                
                # Log function exit
                exit_msg = f"EXITING: {func_name}"
                if include_result:
                    exit_msg += f" | Result: {repr(result)}"
                
                log_method(exit_msg)
                return result
                
            except Exception as e:
                logger.error(f"EXCEPTION in {func_name}: {str(e)}")
                log_exception(logger, e, f"Function: {func_name}")
                raise
        
        return wrapper
    return decorator


def log_performance(
    threshold_seconds: float = 0.0,
    log_level: str = "INFO",
    include_params: bool = False
):
    """
    Decorator to log function performance timing.
    
    Args
    ----
    threshold_seconds: Only log if execution time exceeds this threshold
    log_level: Logging level to use
    include_params: Whether to include function parameters in log
    
    Example
    -------
        @log_performance(threshold_seconds=1.0, log_level="WARNING")
        def potentially_slow_function():
            time.sleep(2)
    """
    def decorator(func: Callable) -> Callable:
        logger = get_logger('performance')
        log_method = getattr(logger, log_level.lower())
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            func_name = f"{func.__module__}.{func.__qualname__}"
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time
                
                if execution_time >= threshold_seconds:
                    perf_msg = f"PERFORMANCE: {func_name} | Duration: {execution_time:.4f}s"
                    
                    if include_params and (args or kwargs):
                        params = []
                        if args:
                            params.extend([f"arg{i}={repr(arg)}" for i, arg in enumerate(args)])
                        if kwargs:
                            params.extend([f"{k}={repr(v)}" for k, v in kwargs.items()])
                        perf_msg += f" | Parameters: {', '.join(params)}"
                    
                    log_method(perf_msg)
                
                return result
                
            except Exception as e:
                execution_time = time.time() - start_time
                logger.error(f"PERFORMANCE: {func_name} | Duration: {execution_time:.4f}s | FAILED: {str(e)}")
                raise
        
        return wrapper
    return decorator


def log_exceptions(
    context: str = "",
    reraise: bool = True,
    log_level: str = "ERROR"
):
    """
    Decorator to log exceptions with full tracebacks.
    
    Args
    ----
    context: Additional context information for the exception
    reraise: Whether to reraise the exception after logging
    log_level: Logging level to use
    
    Example
    -------
        @log_exceptions("Database operation failed", reraise=True)
        def database_operation():
            risky_db_call()
    """
    def decorator(func: Callable) -> Callable:
        logger = get_logger(func.__module__)
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            func_name = f"{func.__module__}.{func.__qualname__}"
            
            try:
                return func(*args, **kwargs)
                
            except Exception as e:
                full_context = f"Function: {func_name}"
                if context:
                    full_context += f" | Context: {context}"
                
                log_exception(logger, e, full_context)
                
                if reraise:
                    raise
                else:
                    return None
        
        return wrapper
    return decorator


def log_retry_attempts(
    max_attempts: int = 3,
    delay_seconds: float = 1.0,
    backoff_multiplier: float = 2.0,
    exceptions: tuple = (Exception,)
):
    """
    Decorator to add retry logic with comprehensive logging.
    
    Args
    ----
    max_attempts: Maximum number of retry attempts
    delay_seconds: Initial delay between attempts
    backoff_multiplier: Multiplier for delay on each retry
    exceptions: Tuple of exceptions to catch and retry
    
    Example
    -------
        @log_retry_attempts(max_attempts=3, delay_seconds=1.0)
        def unreliable_network_call():
            make_api_request()
    """
    def decorator(func: Callable) -> Callable:
        logger = get_logger(func.__module__)
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            func_name = f"{func.__module__}.{func.__qualname__}"
            
            for attempt in range(1, max_attempts + 1):
                try:
                    if attempt > 1:
                        logger.info(f"RETRY: {func_name} | Attempt {attempt}/{max_attempts}")
                    
                    result = func(*args, **kwargs)
                    
                    if attempt > 1:
                        logger.info(f"RETRY SUCCESS: {func_name} | Succeeded on attempt {attempt}")
                    
                    return result
                    
                except exceptions as e:
                    if attempt == max_attempts:
                        logger.error(f"RETRY FAILED: {func_name} | All {max_attempts} attempts failed")
                        log_exception(logger, e, f"Final attempt failed for {func_name}")
                        raise
                    else:
                        delay = delay_seconds * (backoff_multiplier ** (attempt - 1))
                        logger.warning(f"RETRY: {func_name} | Attempt {attempt} failed: {str(e)} | Retrying in {delay:.2f}s")
                        time.sleep(delay)
                
                except Exception as e:
                    # Don't retry for exceptions not in the exceptions tuple
                    logger.error(f"NON-RETRYABLE ERROR: {func_name} | {str(e)}")
                    log_exception(logger, e, f"Non-retryable exception in {func_name}")
                    raise
        
        return wrapper
    return decorator


def log_method_calls(cls):
    """
    Class decorator to automatically log all method calls.
    
    Args
    ----
    cls: Class to decorate
    
    Example
    -------
        @log_method_calls
        class MyClass:
            def method1(self):
                pass
            
            def method2(self):
                pass
    """
    logger = get_logger(cls.__module__)
    
    for attr_name in dir(cls):
        attr = getattr(cls, attr_name)
        if callable(attr) and not attr_name.startswith('_'):
            # Apply logging decorator to public methods
            decorated_method = log_function_calls(
                include_params=True,
                include_result=False,
                log_level="DEBUG"
            )(attr)
            setattr(cls, attr_name, decorated_method)
    
    logger.debug(f"CLASS DECORATED: {cls.__module__}.{cls.__qualname__} | All public methods will be logged")
    return cls


# Convenience decorators with common configurations
def log_entry_exit(func: Callable) -> Callable:
    """Simple decorator for logging function entry and exit."""
    return log_function_calls(include_params=False, include_result=False, log_level="DEBUG")(func)


def log_slow_operations(threshold: float = 1.0):
    """Decorator for logging operations that take longer than threshold."""
    return log_performance(threshold_seconds=threshold, log_level="WARNING")


def log_critical_errors(context: str = "Critical operation"):
    """Decorator for logging critical errors with context."""
    return log_exceptions(context=context, reraise=True, log_level="CRITICAL")
