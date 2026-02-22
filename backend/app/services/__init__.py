# Lazy import to avoid circular dependencies
# Don't eagerly import services at module level
# Import them when needed instead

def get_batch_service():
    from .inventory.batch_service import BatchService
    return BatchService()

# For backwards compatibility
batch_service = None

def __getattr__(name):
    if name == 'batch_service':
        global batch_service
        if batch_service is None:
            batch_service = get_batch_service()
        return batch_service
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
