"""
Retry logic utilities for the Meme Coin Bot.
Provides exponential backoff retry and circuit breaker patterns.
"""
import asyncio
import logging
import time
from functools import wraps
from typing import Any, Callable, Dict, Optional, TypeVar, cast

# Setup logging
logger = logging.getLogger(__name__)

# Type variables for better type hinting
T = TypeVar('T')
F = TypeVar('F', bound=Callable[..., Any])

class CircuitBreaker:
    """Circuit breaker implementation to prevent cascading failures."""
    
    def __init__(self, name: str, failure_threshold: int = 5, reset_timeout: int = 60):
        """
        Initialize the circuit breaker.
        
        Args:
            name: Name of the circuit breaker for logging
            failure_threshold: Number of failures before opening the circuit
            reset_timeout: Time in seconds before trying to close the circuit again
        """
        self.name = name
        self.failure_count = 0
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.state = "closed"  # closed, open, half-open
        self.last_failure_time = 0
        logger.info(f"Circuit breaker '{name}' initialized")
    
    async def execute(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with circuit breaker pattern.
        
        Args:
            func: Function to execute
            *args: Arguments to pass to the function
            **kwargs: Keyword arguments to pass to the function
            
        Returns:
            Result of the function execution
            
        Raises:
            Exception: If circuit is open or function execution fails
        """
        # Check if circuit is open
        if self.state == "open":
            if time.time() - self.last_failure_time > self.reset_timeout:
                # Try half-open state
                logger.info(f"Circuit breaker '{self.name}' entering half-open state")
                self.state = "half-open"
            else:
                logger.warning(f"Circuit breaker '{self.name}' is open, request rejected")
                raise Exception(f"Circuit breaker '{self.name}' is open")
        
        try:
            # Check if function is a coroutine
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
            
            # Reset on success if in half-open state
            if self.state == "half-open":
                logger.info(f"Circuit breaker '{self.name}' closing after successful execution")
                self.failure_count = 0
                self.state = "closed"
                
            return result
            
        except Exception as e:
            # Record failure
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            # Open circuit if threshold reached
            if self.failure_count >= self.failure_threshold:
                logger.warning(f"Circuit breaker '{self.name}' opening after {self.failure_count} failures")
                self.state = "open"
            
            logger.error(f"Circuit breaker '{self.name}' execution failed: {str(e)}")
            raise e

def retry_with_backoff(max_retries: int = 3, initial_delay: float = 1.0, backoff_factor: float = 2.0):
    """
    Decorator to retry a function with exponential backoff.
    
    Args:
        max_retries: Maximum number of retries
        initial_delay: Initial delay in seconds
        backoff_factor: Factor to increase delay with each retry
        
    Returns:
        Decorated function with retry logic
    """
    def decorator(func: F) -> F:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            delay = initial_delay
            last_exception = None
            
            for retry in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if retry == max_retries:
                        logger.error(f"Failed after {max_retries} retries: {str(e)}")
                        raise
                    
                    # Log retry attempt
                    logger.warning(f"Retry {retry+1}/{max_retries} after error: {str(e)}")
                    
                    # Wait with exponential backoff
                    await asyncio.sleep(delay)
                    delay *= backoff_factor
            
            # This should never be reached, but just in case
            raise last_exception or Exception("Retry failed for unknown reason")
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            delay = initial_delay
            last_exception = None
            
            for retry in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if retry == max_retries:
                        logger.error(f"Failed after {max_retries} retries: {str(e)}")
                        raise
                    
                    # Log retry attempt
                    logger.warning(f"Retry {retry+1}/{max_retries} after error: {str(e)}")
                    
                    # Wait with exponential backoff
                    time.sleep(delay)
                    delay *= backoff_factor
            
            # This should never be reached, but just in case
            raise last_exception or Exception("Retry failed for unknown reason")
        
        # Return appropriate wrapper based on whether the function is async or not
        if asyncio.iscoroutinefunction(func):
            return cast(F, async_wrapper)
        return cast(F, sync_wrapper)
    
    return decorator
