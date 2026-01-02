"""
Compatibility layer for zgw-consumers 1.x test utilities.

zgw-consumers 1.x removed OAS schema support and the test utilities that came with it.
This module imports them from the official zgw-consumers-oas package.

See: https://pypi.org/project/zgw-consumers-oas/
"""

# Import from the official zgw-consumers-oas package
from zgw_consumers_oas import generate_oas_component
from zgw_consumers_oas.mocks import mock_service_oas_get

# Re-export for backward compatibility
__all__ = [
    "mock_service_oas_get",
    "generate_oas_component",
    "install_schema_fetcher_cache",
]


def install_schema_fetcher_cache():
    """
    No-op replacement for zgw_consumers.cache.install_schema_fetcher_cache.

    In zgw-consumers <1.0, this installed a cache for OAS schema fetching.
    Since zgw-consumers 1.x no longer uses OAS schemas internally, this is now a no-op.
    The zgw-consumers-oas package handles schema loading differently.
    """
    # No-op: zgw-consumers 1.x doesn't use schema fetcher cache
    pass
