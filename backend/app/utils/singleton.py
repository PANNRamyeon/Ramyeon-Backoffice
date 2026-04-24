"""
Universal Singleton Service Manager
Provides thread-safe singleton instances for service classes

Usage:
    from app.utils.singleton import get_singleton
    from app.services.inventory.category_service import CategoryService
    
    category_service = get_singleton(CategoryService)
"""
import threading
import logging
from typing import Type, TypeVar, Dict, Any

logger = logging.getLogger(__name__)

# Type variable for generic service class
T = TypeVar('T')

# Global singleton cache
_singleton_cache: Dict[str, Any] = {}

# Thread lock for safe concurrent access
_lock = threading.Lock()


def get_singleton(service_class: Type[T], *args, **kwargs) -> T:
    """
    Get or create a singleton instance of a service class.
    Thread-safe implementation using double-checked locking pattern.
    
    Args:
        service_class: The class to instantiate (e.g., CategoryService)
        *args: Positional arguments to pass to the class constructor
        **kwargs: Keyword arguments to pass to the class constructor
    
    Returns:
        Singleton instance of the service class
    
    Example:
        category_service = get_singleton(CategoryService)
        product_service = get_singleton(ProductService, config={'debug': True})
    """
    class_name = service_class.__name__
    
    # First check (no lock) - fast path for already created instances
    if class_name not in _singleton_cache:
        # Acquire lock for thread-safe creation
        with _lock:
            # Double-check pattern - another thread might have created it
            if class_name not in _singleton_cache:
                logger.info(f"Creating singleton instance: {class_name}")
                try:
                    _singleton_cache[class_name] = service_class(*args, **kwargs)
                    logger.info(f"Singleton created successfully: {class_name}")
                except Exception as e:
                    logger.error(f"Failed to create singleton {class_name}: {e}")
                    raise
    
    return _singleton_cache[class_name]


def clear_singletons():
    """
    Clear all singleton instances from cache.
    Useful for testing or when you need to reset all services.
    
    Warning: This will force recreation of all singletons on next access.
    Only use in testing or controlled scenarios.
    """
    global _singleton_cache
    with _lock:
        count = len(_singleton_cache)
        _singleton_cache.clear()
        logger.info(f"Cleared {count} singleton instance(s)")


def get_cached_singletons() -> Dict[str, Any]:
    """
    Get a dictionary of all currently cached singleton instances.
    Useful for debugging or monitoring.
    
    Returns:
        Dictionary mapping class names to singleton instances
    """
    with _lock:
        return dict(_singleton_cache)


def is_singleton_cached(service_class: Type) -> bool:
    """
    Check if a singleton instance exists for a given service class.
    
    Args:
        service_class: The class to check
    
    Returns:
        True if singleton exists, False otherwise
    """
    class_name = service_class.__name__
    return class_name in _singleton_cache


# Export public API
__all__ = [
    'get_singleton',
    'clear_singletons',
    'get_cached_singletons',
    'is_singleton_cached',
]
