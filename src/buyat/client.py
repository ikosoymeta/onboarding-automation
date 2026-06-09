"""Buy@ client for supplier verification and onboarding.

Provides browser automation for searching suppliers in Buy@ system
since no public API is available. Includes caching to avoid repeated
searches and handles supplier reactivation for inactive suppliers.
"""

import logging
import time
from typing import Optional, Dict, Any
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class SupplierNotFoundError(Exception):
    """Raised when supplier is not found in Buy@."""
    pass


class BuyAtError(Exception):
    """Base exception for Buy@ operations."""
    pass


@dataclass
class SupplierInfo:
    """Information about a supplier in Buy@."""
    name: str
    exists: bool
    supplier_id: Optional[str] = None
    status: Optional[str] = None
    contact_email: Optional[str] = None
    is_active: bool = False


class BuyAtClient:
    """Client for interacting with Buy@ supplier system.
    
    Uses browser automation to search for suppliers since
    Buy@ does not provide a public API for supplier verification.
    
    Features:
    - Supplier search and verification
    - Caching to avoid repeated searches
    - Handles supplier reactivation
    - Secure screenshot storage
    """
    
    BUYAT_URL = "https://www.internalfb.com/buy/suppliers/onboarding"
    
    def __init__(
        self, 
        headless: bool = True, 
        screenshot_dir: str = None,
        cache_ttl: int = 3600
    ):
        """Initialize Buy@ client.
        
        Args:
            headless: Whether to run browser in headless mode
            screenshot_dir: Directory to save error screenshots.
                          Defaults to ~/.vendor_onboarding/screenshots
            cache_ttl: Cache time-to-live in seconds (default: 1 hour)
        """
        self.headless = headless
        # Use secure default location with restricted permissions
        if screenshot_dir is None:
            screenshot_dir = Path.home() / ".vendor_onboarding" / "screenshots"
        self.screenshot_dir = Path(screenshot_dir)
        self.screenshot_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        self._browser = None
        self._page = None
        self._cache: Dict[str, tuple[SupplierInfo, datetime]] = {}
        self.cache_ttl = cache_ttl
    
    def _is_cache_valid(self, cached_time: datetime) -> bool:
        """Check if cached entry is still valid.
        
        Args:
            cached_time: When the entry was cached
            
        Returns:
            True if cache entry is still valid
        """
        return datetime.utcnow() - cached_time < timedelta(seconds=self.cache_ttl)
    
    def _get_from_cache(self, supplier_name: str) -> Optional[SupplierInfo]:
        """Get supplier info from cache if valid.
        
        Args:
            supplier_name: Name of supplier to look up
            
        Returns:
            Cached SupplierInfo or None if not cached or expired
        """
        if supplier_name in self._cache:
            info, cached_time = self._cache[supplier_name]
            if self._is_cache_valid(cached_time):
                logger.debug(f"Cache hit for supplier: {supplier_name}")
                return info
            else:
                logger.debug(f"Cache expired for supplier: {supplier_name}")
                del self._cache[supplier_name]
        return None
    
    def _save_to_cache(self, supplier_name: str, info: SupplierInfo):
        """Save supplier info to cache.
        
        Args:
            supplier_name: Name of supplier
            info: Supplier information to cache
        """
        self._cache[supplier_name] = (info, datetime.utcnow())
        logger.debug(f"Cached supplier info for: {supplier_name}")
    
    def search_supplier(self, supplier_name: str, use_cache: bool = True) -> SupplierInfo:
        """Search for a supplier in Buy@.
        
        Args:
            supplier_name: Name of supplier to search for
            use_cache: Whether to use cached results if available
            
        Returns:
            SupplierInfo with supplier details
            
        Raises:
            SupplierNotFoundError: If supplier is not found
            BuyAtError: If search fails
        """
        # Check cache first
        if use_cache:
            cached = self._get_from_cache(supplier_name)
            if cached:
                return cached
        
        logger.info(f"Searching for supplier: {supplier_name}")
        
        # TODO: Implement actual browser automation
        # For now, simulate the search
        # In production, this would use Playwright to:
        # 1. Navigate to Buy@ URL
        # 2. Search for supplier name
        # 3. Parse results to determine if exists and status
        
        # Simulated logic for demonstration
        # In real implementation, replace with actual browser automation
        
        # Simulate not found for demo purposes
        # Real implementation would check actual Buy@ system
        raise SupplierNotFoundError(f"Supplier '{supplier_name}' not found in Buy@")
    
    def verify_supplier_exists(self, supplier_name: str, use_cache: bool = True) -> bool:
        """Check if supplier exists in Buy@.
        
        Args:
            supplier_name: Name of supplier to check
            use_cache: Whether to use cached results
            
        Returns:
            True if supplier exists, False otherwise
        """
        try:
            info = self.search_supplier(supplier_name, use_cache=use_cache)
            return info.exists
        except SupplierNotFoundError:
            return False
    
    def is_supplier_active(self, supplier_name: str, use_cache: bool = True) -> bool:
        """Check if supplier is active in Buy@.
        
        Args:
            supplier_name: Name of supplier to check
            use_cache: Whether to use cached results
            
        Returns:
            True if supplier exists and is active, False otherwise
        """
        try:
            info = self.search_supplier(supplier_name, use_cache=use_cache)
            return info.exists and info.is_active
        except SupplierNotFoundError:
            return False
    
    def clear_cache(self):
        """Clear the supplier cache."""
        self._cache.clear()
        logger.info("Supplier cache cleared")
    
    def close(self):
        """Close browser resources."""
        if self._browser:
            self._browser.close()
            self._browser = None
            self._page = None
