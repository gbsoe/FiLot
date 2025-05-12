#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Client for interacting with the SolPool Insight API for on-chain analytics 
and ML-powered pool predictions.
"""

import os
import logging
import aiohttp
import time
import json
from typing import Dict, Any, Optional, List, Union
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
logger = logging.getLogger('solpool_client')

# Initialize a singleton instance
_instance = None

def get_client() -> 'SolPoolClient':
    """Get the singleton SolPoolClient instance."""
    global _instance
    if _instance is None:
        try:
            _instance = SolPoolClient()
        except Exception as e:
            logger.error(f"Failed to initialize SolPoolClient: {e}")
            raise
    return _instance

class SolPoolClient:
    """Client for interacting with the SolPool Insight API."""

    def __init__(self):
        """Initialize the client with configuration from environment variables."""
        # Use the correct API URL, ensuring it doesn't end with a slash
        base_url = os.environ.get("SOLPOOL_API_URL", "https://filotanalytics.replit.app/api")
        # Remove trailing slash if it exists to avoid double slash issues
        self.base_url = base_url.rstrip('/')
        self.api_key = os.environ.get("SOLPOOL_API_KEY", "")

        # Cache TTLs (in seconds)
        self.cache_ttl = {
            "pools": 300,  # 5 minutes
            "predictions": 1800,  # 30 minutes
            "pool_detail": 300,  # 5 minutes
            "pool_history": 600   # 10 minutes
        }
        
        # Initialize request session
        self._session = None
        
        logger.info(f"Initialized SolPool client with API URL: {self.base_url}")

    async def ensure_session(self) -> aiohttp.ClientSession:
        """Ensure an aiohttp session exists for making requests."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(headers={
                "X-API-Key": self.api_key,
                "Content-Type": "application/json"
            })
        return self._session

    async def close(self) -> None:
        """Close the aiohttp session."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    async def _make_request(
        self, 
        endpoint: str, 
        method: str = 'GET', 
        params: Optional[Dict[str, Any]] = None, 
        data: Optional[Dict[str, Any]] = None, 
        max_retries: int = 3
    ) -> Dict[str, Any]:
        """Make a request to the SolPool API with retry logic."""
        session = await self.ensure_session()
        
        url = f"{self.base_url}{endpoint}"
        retries = 0
        backoff_factor = 2
        
        while retries < max_retries:
            try:
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

    # Cache decorated function for pools by DEX with min prediction score
    @lru_cache(maxsize=16)
    async def _fetch_pools_cached(self, dex: str, min_tvl: float, min_apr: float, min_prediction: float, timestamp: int) -> Dict[str, Any]:
        """Cached version of fetch_pools to minimize API calls."""
        params = {}
        
        if dex:
            params["dex"] = dex
            
        if min_tvl is not None and min_tvl > 0:
            params["min_tvl"] = min_tvl
            
        if min_apr is not None and min_apr > 0:
            params["min_apr"] = min_apr
            
        if min_prediction is not None and min_prediction > 0:
            params["min_prediction"] = min_prediction
            
        response = await self._make_request("/pools", params=params)
        return response

    async def fetch_pools(
        self, 
        dex: Optional[str] = "Raydium", 
        min_tvl: Optional[float] = None,
        min_apr: Optional[float] = None,
        min_prediction: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch pools from the SolPool API, with optional filtering.
        
        Args:
            dex: The DEX to filter pools by (default: "Raydium")
            min_tvl: Minimum TVL threshold
            min_apr: Minimum APR threshold (percentage)
            min_prediction: Minimum prediction score threshold (0-100)
            
        Returns:
            List of pool dictionaries
        """
        # Create a timestamp that changes every self.cache_ttl["pools"] seconds
        # This ensures the cache is invalidated after the TTL expires
        timestamp = int(time.time() / self.cache_ttl["pools"])
        
        try:
            response = await self._fetch_pools_cached(dex, min_tvl, min_apr, min_prediction, timestamp)
            
            if "error" in response:
                logger.error(f"Error fetching pools: {response['error']}")
                return []
                
            if response.get("status") == "success":
                return response.get("data", [])
            else:
                logger.error(f"Unsuccessful response fetching pools: {response}")
                return []
        except Exception as e:
            logger.error(f"Error in fetch_pools: {e}")
            return []

    @lru_cache(maxsize=32)
    async def _fetch_pool_detail_cached(self, pool_id: str, timestamp: int) -> Dict[str, Any]:
        """Cached version of fetch_pool_detail to minimize API calls."""
        response = await self._make_request(f"/pools/{pool_id}")
        return response

    async def fetch_pool_detail(self, pool_id: str) -> Dict[str, Any]:
        """
        Fetch detailed information about a specific pool.
        
        Args:
            pool_id: ID of the pool to fetch details for
            
        Returns:
            Dictionary with pool details
        """
        # Create a timestamp that changes every self.cache_ttl["pool_detail"] seconds
        timestamp = int(time.time() / self.cache_ttl["pool_detail"])
        
        try:
            response = await self._fetch_pool_detail_cached(pool_id, timestamp)
            
            if "error" in response:
                logger.error(f"Error fetching pool detail: {response['error']}")
                return {}
                
            if response.get("status") == "success":
                return response.get("data", {})
            else:
                logger.error(f"Unsuccessful response fetching pool detail: {response}")
                return {}
        except Exception as e:
            logger.error(f"Error in fetch_pool_detail: {e}")
            return {}
            
    @lru_cache(maxsize=32)
    async def _fetch_pool_history_cached(self, pool_id: str, days: int, interval: str, timestamp: int) -> Dict[str, Any]:
        """Cached version of fetch_pool_history to minimize API calls."""
        params = {
            "days": days,
            "interval": interval
        }
        response = await self._make_request(f"/pools/{pool_id}/history", params=params)
        return response
        
    async def fetch_pool_history(self, pool_id: str, days: int = 30, interval: str = "day") -> List[Dict[str, Any]]:
        """
        Fetch historical data for a specific pool.
        
        Args:
            pool_id: ID of the pool to fetch history for
            days: Number of days of history to retrieve (default: 30)
            interval: Time interval ('hour', 'day', 'week') (default: 'day')
            
        Returns:
            List of historical data points
        """
        # Create a timestamp that changes every self.cache_ttl["pool_history"] seconds
        timestamp = int(time.time() / self.cache_ttl["pool_history"])
        
        try:
            response = await self._fetch_pool_history_cached(pool_id, days, interval, timestamp)
            
            if "error" in response:
                logger.error(f"Error fetching pool history: {response['error']}")
                return []
                
            if response.get("status") == "success":
                return response.get("data", [])
            else:
                logger.error(f"Unsuccessful response fetching pool history: {response}")
                return []
        except Exception as e:
            logger.error(f"Error in fetch_pool_history: {e}")
            return []

    @lru_cache(maxsize=8)
    async def _fetch_predictions_cached(self, min_score: float, timestamp: int) -> Dict[str, Any]:
        """Cached version of fetch_predictions to minimize API calls."""
        params = {}
        if min_score is not None:
            params["min_score"] = min_score
            
        response = await self._make_request("/predictions", params=params)
        return response

    async def fetch_predictions(self, min_score: Optional[float] = None) -> List[Dict[str, Any]]:
        """
        Fetch ML-powered predictions for pool performance.
        
        Args:
            min_score: Minimum prediction score threshold (0.0 to 1.0)
            
        Returns:
            List of prediction dictionaries
        """
        # Create a timestamp that changes every self.cache_ttl["predictions"] seconds
        timestamp = int(time.time() / self.cache_ttl["predictions"])
        
        try:
            response = await self._fetch_predictions_cached(min_score, timestamp)
            
            if "error" in response:
                logger.error(f"Error fetching predictions: {response['error']}")
                return []
                
            if response.get("status") == "success":
                return response.get("data", [])
            else:
                logger.error(f"Unsuccessful response fetching predictions: {response}")
                return []
        except Exception as e:
            logger.error(f"Error in fetch_predictions: {e}")
            return []
            
    async def fetch_forecast(self, pool_id: str, days: int = 7) -> Dict[str, Any]:
        """
        Fetch APR forecast for a specific pool.
        
        Args:
            pool_id: ID of the pool
            days: Number of days to forecast (1-30)
            
        Returns:
            Dictionary with forecast data
        """
        params = {"days": days}
        
        try:
            response = await self._make_request(f"/pools/{pool_id}/forecast", params=params)
            
            if "error" in response:
                logger.error(f"Error fetching pool forecast: {response['error']}")
                return {}
                
            if response.get("status") == "success":
                return response.get("data", {})
            else:
                logger.error(f"Unsuccessful response fetching pool forecast: {response}")
                return {}
        except Exception as e:
            logger.error(f"Error in fetch_forecast: {e}")
            return {}
            
    async def check_health(self) -> bool:
        """
        Check if the SolPool API is healthy and accessible.
        
        Returns:
            True if the API is healthy, False otherwise
        """
        try:
            response = await self._make_request("/health")
            return response.get("status") == "success" or response.get("status") == "online"
        except Exception as e:
            logger.error(f"API health check failed: {e}")
            return False