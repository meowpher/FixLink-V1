"""
Centralized Cache Module for FixLink.
Provides a shared cache instance and invalidation helpers.
"""
from flask_caching import Cache

cache = Cache()


def init_cache(app):
    """Initialize the cache with the Flask app."""
    cache_config = {
        'CACHE_TYPE': 'SimpleCache',
        'CACHE_DEFAULT_TIMEOUT': 3600,  # 1 hour default
        'CACHE_THRESHOLD': 256,
    }
    app.config.from_mapping(cache_config)
    cache.init_app(app)
    return cache


def invalidate_floor_cache(floor_id):
    """Invalidate cached map data for a specific floor.
    Call this when a ticket is created/updated or an asset status changes.
    """
    # Keys match the patterns used in @cache.cached() decorators
    cache.delete(f'map_floor_{floor_id}')
    cache.delete(f'admin_floor_{floor_id}')


def invalidate_all_map_cache():
    """Nuclear option: clear all cached map data."""
    cache.clear()
