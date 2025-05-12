#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Client for interacting with the FiLotSense Public API for real-time 
sentiment and price signals.
"""

import os
import logging
import aiohttp
import time
import json
from typing import Dict, Any, Optional, List, Union, Tuple
from functools import lru_cache
import asyncio

try:
    from dotenv import load_dotenv
    # Load environment variables
    load_dotenv()
except ImportError:
    # Ignore if dotenv is not installed
    pass

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('filotsense_client')

# Initialize a singleton instance
_instance = None

def get_client() -> 'FiLotSenseClient':
    """Get the singleton FiLotSenseClient instance."""
    global _instance
    if _instance is None:
        try:
            _instance = FiLotSenseClient()
        except Exception as e:
            logger.error(f"Failed to initialize FiLotSenseClient: {e}")
            raise
    return _instance

class FiLotSenseClient:
    """Client for interacting with the FiLotSense Public API."""

    def __init__(self):
        """Initialize the client with configuration from environment variables."""
        # Use the correct API URL, ensuring it doesn't end with a slash
        base_url = os.environ.get("FILOTSENSE_API_URL", "https://filotsense.replit.app/api")
        # Remove trailing slash if it exists to avoid double slash issues
        self.base_url = base_url.rstrip('/')
        
        # Current rate limits: 100 requests per hour
        self.rate_limit = 100
        self.rate_limit_window = 3600  # 1 hour in seconds
        self.request_timestamps = []
        
        # Cache TTLs (in seconds)
        self.cache_ttl = {
            "sentiment": 300,  # 5 minutes
            "prices": 120,     # 2 minutes
            "topics": 900,     # 15 minutes
            "realdata": 300    # 5 minutes
        }
        
        # Initialize request session
        self._session = None
        
        logger.info(f"Initialized FiLotSense client with API URL: {self.base_url}")

    async def ensure_session(self) -> aiohttp.ClientSession:
        """Ensure an aiohttp session exists for making requests."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(headers={
                "Content-Type": "application/json"
            })
        return self._session

    async def close(self) -> None:
        """Close the aiohttp session."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    def _check_rate_limit(self) -> Tuple[bool, Optional[float]]:
        """
        Check if we're within rate limits.
        
        Returns:
            Tuple of (is_allowed, wait_time)
            where is_allowed is True if request can proceed
            and wait_time is seconds to wait if not allowed (None if allowed)
        """
        current_time = time.time()
        
        # Remove timestamps older than the rate limit window
        self.request_timestamps = [ts for ts in self.request_timestamps 
                                 if current_time - ts < self.rate_limit_window]
        
        # Check if we've reached the rate limit
        if len(self.request_timestamps) >= self.rate_limit:
            # Calculate time until oldest request expires
            oldest = min(self.request_timestamps)
            wait_time = oldest + self.rate_limit_window - current_time
            return False, max(0, wait_time)
            
        return True, None
        
    async def _make_request(
        self, 
        endpoint: str, 
        method: str = 'GET', 
        params: Optional[Dict[str, Any]] = None, 
        data: Optional[Dict[str, Any]] = None, 
        max_retries: int = 3
    ) -> Dict[str, Any]:
        """Make a request to the FiLotSense API with retry logic and rate limiting."""
        session = await self.ensure_session()
        
        url = f"{self.base_url}{endpoint}"
        retries = 0
        backoff_factor = 2
        
        while retries < max_retries:
            # Check rate limits before making request
            is_allowed, wait_time = self._check_rate_limit()
            if not is_allowed and wait_time is not None:
                logger.warning(f"Rate limit exceeded. Waiting {wait_time:.2f} seconds before retry.")
                await asyncio.sleep(wait_time)
                continue
                
            try:
                # Record this request timestamp for rate limiting
                self.request_timestamps.append(time.time())
                
                if method.upper() == 'GET':
                    async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as response:
                        if response.status == 429:  # Rate limit exceeded
                            retry_after = int(response.headers.get('Retry-After', backoff_factor ** retries))
                            logger.warning(f"Rate limit exceeded. Retrying after {retry_after} seconds.")
                            await asyncio.sleep(retry_after)
                            retries += 1
                            continue
                        
                        if response.status >= 500:  # Server error
                            logger.warning(f"Server error {response.status}. Retrying after {backoff_factor ** retries} seconds.")
                            await asyncio.sleep(backoff_factor ** retries)
                            retries += 1
                            continue
                            
                        if response.status != 200:
                            error_text = await response.text()
                            logger.error(f"API error {response.status}: {error_text}")
                            return {"error": f"API error {response.status}", "details": error_text}
                            
                        return await response.json()
                else:  # POST, PUT, etc.
                    async with session.request(method, url, params=params, json=data, timeout=aiohttp.ClientTimeout(total=10)) as response:
                        if response.status == 429:  # Rate limit exceeded
                            retry_after = int(response.headers.get('Retry-After', backoff_factor ** retries))
                            logger.warning(f"Rate limit exceeded. Retrying after {retry_after} seconds.")
                            await asyncio.sleep(retry_after)
                            retries += 1
                            continue
                        
                        if response.status >= 500:  # Server error
                            logger.warning(f"Server error {response.status}. Retrying after {backoff_factor ** retries} seconds.")
                            await asyncio.sleep(backoff_factor ** retries)
                            retries += 1
                            continue
                            
                        if response.status != 200:
                            error_text = await response.text()
                            logger.error(f"API error {response.status}: {error_text}")
                            return {"error": f"API error {response.status}", "details": error_text}
                            
                        return await response.json()
            
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                logger.warning(f"Request failed: {e}. Retrying ({retries+1}/{max_retries})")
                await asyncio.sleep(backoff_factor ** retries)
                retries += 1
        
        logger.error(f"Failed to make request after {max_retries} retries")
        return {"error": "Maximum retries exceeded"}

    # Cache decorated function for simple sentiment
    @lru_cache(maxsize=16)
    async def _fetch_sentiment_simple_cached(self, symbols: Optional[str], timestamp: int) -> Dict[str, Any]:
        """Cached version of fetch_sentiment_simple to minimize API calls."""
        params = {}
        if symbols:
            params["symbols"] = symbols
            
        response = await self._make_request("/sentiment/simple", params=params)
        return response

    async def fetch_sentiment_simple(self, symbols: Optional[List[str]] = None) -> Dict[str, float]:
        """
        Fetch simple sentiment scores for tokens.
        
        Args:
            symbols: Optional list of token symbols to get sentiment for
            
        Returns:
            Dictionary mapping token symbols to sentiment scores (-1.0 to 1.0)
        """
        # Create a timestamp that changes every self.cache_ttl["sentiment"] seconds
        timestamp = int(time.time() / self.cache_ttl["sentiment"])
        
        try:
            symbols_str = None
            if symbols:
                symbols_str = ",".join(symbols)
                
            response = await self._fetch_sentiment_simple_cached(symbols_str, timestamp)
            
            if "error" in response:
                logger.error(f"Error fetching sentiment: {response['error']}")
                return {}
                
            if response.get("status") == "success":
                return response.get("sentiment", {})
            else:
                logger.error(f"Unsuccessful response fetching sentiment: {response}")
                return {}
        except Exception as e:
            logger.error(f"Error in fetch_sentiment_simple: {e}")
            return {}

    @lru_cache(maxsize=16)
    async def _fetch_prices_latest_cached(self, symbols: Optional[str], timestamp: int) -> Dict[str, Any]:
        """Cached version of fetch_prices_latest to minimize API calls."""
        params = {}
        if symbols:
            params["symbols"] = symbols
            
        response = await self._make_request("/prices/latest", params=params)
        return response

    async def fetch_prices_latest(self, symbols: Optional[List[str]] = None) -> Dict[str, Dict[str, Any]]:
        """
        Fetch latest price information for tokens.
        
        Args:
            symbols: Optional list of token symbols to get prices for
            
        Returns:
            Dictionary mapping token symbols to price information
        """
        # Create a timestamp that changes every self.cache_ttl["prices"] seconds
        timestamp = int(time.time() / self.cache_ttl["prices"])
        
        try:
            symbols_str = None
            if symbols:
                symbols_str = ",".join(symbols)
                
            response = await self._fetch_prices_latest_cached(symbols_str, timestamp)
            
            if "error" in response:
                logger.error(f"Error fetching prices: {response['error']}")
                return {}
            
            if response.get("status") == "success":
                return response.get("data", {})
            else:
                logger.error(f"Unsuccessful response fetching prices: {response}")
                return {}
        except Exception as e:
            logger.error(f"Error in fetch_prices_latest: {e}")
            return {}

    @lru_cache(maxsize=8)
    async def _fetch_sentiment_topics_cached(self, timestamp: int) -> Dict[str, Any]:
        """Cached version of fetch_sentiment_topics to minimize API calls."""
        response = await self._make_request("/sentiment/topics")
        return response

    async def fetch_sentiment_topics(self) -> List[Dict[str, Any]]:
        """
        Fetch trending sentiment topics in the crypto market.
        
        Returns:
            List of topic dictionaries with sentiment information
        """
        # Create a timestamp that changes every self.cache_ttl["topics"] seconds
        timestamp = int(time.time() / self.cache_ttl["topics"])
        
        try:
            response = await self._fetch_sentiment_topics_cached(timestamp)
            
            if "error" in response:
                logger.error(f"Error fetching sentiment topics: {response['error']}")
                return []
            
            if response.get("status") == "success":
                return response.get("data", [])
            else:
                logger.error(f"Unsuccessful response fetching sentiment topics: {response}")
                return []
        except Exception as e:
            logger.error(f"Error in fetch_sentiment_topics: {e}")
            return []

    @lru_cache(maxsize=8)
    async def _fetch_realdata_cached(self, symbols: Optional[str], timestamp: int) -> Dict[str, Any]:
        """Cached version of fetch_realdata to minimize API calls."""
        params = {}
        if symbols:
            params["symbols"] = symbols
            
        response = await self._make_request("/realdata", params=params)
        return response

    async def fetch_realdata(self, symbols: Optional[List[str]] = None) -> Dict[str, Dict[str, Any]]:
        """
        Fetch comprehensive real-time data including price, sentiment, and volume.
        
        Args:
            symbols: Optional list of token symbols to get data for
            
        Returns:
            Dictionary mapping token symbols to comprehensive data
        """
        # Create a timestamp that changes every self.cache_ttl["realdata"] seconds
        timestamp = int(time.time() / self.cache_ttl["realdata"])
        
        try:
            symbols_str = None
            if symbols:
                symbols_str = ",".join(symbols)
                
            response = await self._fetch_realdata_cached(symbols_str, timestamp)
            
            if "error" in response:
                logger.error(f"Error fetching realdata: {response['error']}")
                return {}
            
            if response.get("status") == "success":
                return response.get("data", {})
            else:
                logger.error(f"Unsuccessful response fetching realdata: {response}")
                return {}
        except Exception as e:
            logger.error(f"Error in fetch_realdata: {e}")
            return {}
            
    async def fetch_token_sentiment_history(self, symbol: str, days: int = 7) -> List[Dict[str, Any]]:
        """
        Fetch historical sentiment data for a specific token.
        
        Args:
            symbol: Token symbol
            days: Number of days of history to fetch (1-30)
            
        Returns:
            List of historical sentiment data points
        """
        params = {"days": days}
        try:
            response = await self._make_request(f"/sentiment/history/{symbol}", params=params)
            
            if "error" in response:
                logger.error(f"Error fetching sentiment history: {response['error']}")
                return []
            
            if response.get("status") == "success":
                return response.get("data", [])
            else:
                logger.error(f"Unsuccessful response fetching sentiment history: {response}")
                return []
        except Exception as e:
            logger.error(f"Error in fetch_token_sentiment_history: {e}")
            return []
            
    async def check_health(self) -> bool:
        """
        Check if the FiLotSense API is healthy and accessible.
        
        Returns:
            True if the API is healthy, False otherwise
        """
        try:
            response = await self._make_request("/health")
            return response.get("status") == "success" or response.get("status") == "online"
        except Exception as e:
            logger.error(f"API health check failed: {e}")
            return False