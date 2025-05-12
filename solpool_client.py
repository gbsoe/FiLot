#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Client for interacting with the SolPool Insight API for on-chain analytics 
and ML-powered pool predictions.
"""

import os
import time
import json
import logging
import asyncio
from typing import Dict, List, Any, Optional

import aiohttp
from functools import lru_cache

# Import mock data functions for fallback when API is unavailable
from api_mock_data import (
    get_mock_pools, 
    get_mock_pool_detail,
    get_mock_pool_history,
    get_mock_predictions,
    get_mock_forecast
)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
logger = logging.getLogger('solpool_client')

# Flag to control when to use mock data
USE_MOCK_DATA = os.environ.get("USE_MOCK_DATA", "true").lower() in ("true", "1", "yes")

# Singleton instance
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
            "pools": 300,           # 5 minutes
            "pool_detail": 300,     # 5 minutes
            "pool_history": 3600,   # 1 hour
            "predictions": 1800,    # 30 minutes
            "forecast": 1800        # 30 minutes
        }
        
        # Track API health
        self.api_healthy = False
        self.last_health_check = 0
        self.health_check_interval = 300  # Check health every 5 minutes
        
        # aiohttp session
        self._session = None

    async def ensure_session(self) -> aiohttp.ClientSession:
        """Ensure an aiohttp session exists for making requests."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self) -> None:
        """Close the aiohttp session."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
            
    async def _handle_html_response(self, response: aiohttp.ClientResponse, endpoint: str) -> Dict[str, Any]:
        """
        Handle HTML responses from the API which should return JSON.
        
        Args:
            response: aiohttp response object
            endpoint: The API endpoint that was requested
            
        Returns:
            Extracted data if possible, error dict otherwise
        """
        text = await response.text()
        logger.warning(f"Received HTML instead of JSON from API. Endpoint: {endpoint}")
        
        # Special case for health endpoint
        if endpoint == "/health" and ('online' in text.lower() or 'healthy' in text.lower() or 'success' in text.lower()):
            logger.info("Detected positive health status from HTML response")
            return {"status": "healthy"}
        
        # Try to extract JSON from HTML if it exists
        try:
            if '{' in text and '}' in text:
                start_idx = text.find('{')
                end_idx = text.rfind('}') + 1
                if start_idx >= 0 and end_idx > start_idx:
                    json_str = text[start_idx:end_idx]
                    logger.info(f"Attempting to extract JSON from HTML")
                    return json.loads(json_str)
        except json.JSONDecodeError:
            logger.warning("Could not extract valid JSON from HTML response")
        
        return {"error": "Received HTML instead of JSON", "details": text[:200]}

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
                        
                        # Check content type for HTML instead of JSON
                        content_type = response.headers.get('Content-Type', '')
                        if 'text/html' in content_type:
                            return await self._handle_html_response(response, endpoint)
                            
                        try:
                            return await response.json()
                        except json.JSONDecodeError as e:
                            text = await response.text()
                            logger.error(f"Failed to decode JSON response: {e}. Response text: {text[:200]}")
                            
                            # Try to extract JSON if embedded in HTML
                            return await self._handle_html_response(response, endpoint)
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
                        
                        # Check content type for HTML instead of JSON
                        content_type = response.headers.get('Content-Type', '')
                        if 'text/html' in content_type:
                            return await self._handle_html_response(response, endpoint)
                            
                        try:
                            return await response.json()
                        except json.JSONDecodeError as e:
                            text = await response.text()
                            logger.error(f"Failed to decode JSON response: {e}. Response text: {text[:200]}")
                            
                            # Try to extract JSON if embedded in HTML
                            return await self._handle_html_response(response, endpoint)
            
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
        
        return await self._make_request("/pools", params=params)

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
        # Check if we should use mock data based on environment setting or API health
        if USE_MOCK_DATA or not await self.check_health():
            logger.info("Using mock data for fetch_pools")
            return get_mock_pools(dex, min_tvl, min_apr, min_prediction)
        
        # Round to nearest 5 minutes to improve cache hits
        timestamp = int(time.time()) // 300
        
        response = await self._fetch_pools_cached(dex, min_tvl, min_apr, min_prediction, timestamp)
        
        if "error" in response:
            logger.error(f"Error fetching pools: {response['error']}")
            logger.info("Falling back to mock data for fetch_pools due to API error")
            return get_mock_pools(dex, min_tvl, min_apr, min_prediction)
            
        # Handle different response formats
        if "data" in response and isinstance(response["data"], list):
            return response["data"]
        elif "pools" in response and isinstance(response["pools"], list):
            return response["pools"]
        else:
            # Check if the response itself is a list
            if isinstance(response, list):
                return response
            
            logger.warning(f"Unexpected response format from fetch_pools: {response}")
            logger.info("Falling back to mock data for fetch_pools due to unexpected response format")
            return get_mock_pools(dex, min_tvl, min_apr, min_prediction)

    # Cache decorated function for pool detail by id
    @lru_cache(maxsize=32)
    async def _fetch_pool_detail_cached(self, pool_id: str, timestamp: int) -> Dict[str, Any]:
        """Cached version of fetch_pool_detail to minimize API calls."""
        return await self._make_request(f"/pools/{pool_id}")

    async def fetch_pool_detail(self, pool_id: str) -> Dict[str, Any]:
        """
        Fetch detailed information about a specific pool.
        
        Args:
            pool_id: ID of the pool to fetch details for
            
        Returns:
            Dictionary with pool details
        """
        # Check if we should use mock data based on environment setting or API health
        if USE_MOCK_DATA or not await self.check_health():
            logger.info("Using mock data for fetch_pool_detail")
            return get_mock_pool_detail(pool_id)
        
        # Round to nearest 5 minutes to improve cache hits
        timestamp = int(time.time()) // 300
        
        response = await self._fetch_pool_detail_cached(pool_id, timestamp)
        
        if "error" in response:
            logger.error(f"Error fetching pool detail: {response['error']}")
            logger.info("Falling back to mock data for fetch_pool_detail due to API error")
            return get_mock_pool_detail(pool_id)
            
        # Handle different response formats
        if "data" in response and isinstance(response["data"], dict):
            return response["data"]
        else:
            # Check if the response contains pool data directly
            if "id" in response and isinstance(response["id"], str):
                return response
                
            logger.warning(f"Unexpected response format from fetch_pool_detail: {response}")
            logger.info("Falling back to mock data for fetch_pool_detail due to unexpected response format")
            return get_mock_pool_detail(pool_id)

    # Cache decorated function for pool history
    @lru_cache(maxsize=16)
    async def _fetch_pool_history_cached(self, pool_id: str, days: int, interval: str, timestamp: int) -> Dict[str, Any]:
        """Cached version of fetch_pool_history to minimize API calls."""
        params = {
            "days": days,
            "interval": interval
        }
        
        return await self._make_request(f"/pools/{pool_id}/history", params=params)

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
        # Check if we should use mock data based on environment setting or API health
        if USE_MOCK_DATA or not await self.check_health():
            logger.info("Using mock data for fetch_pool_history")
            return get_mock_pool_history(pool_id, days, interval)
        
        # Ensure valid interval
        if interval not in ["hour", "day", "week"]:
            interval = "day"
            
        # Limit days to a reasonable range
        days = max(1, min(days, 90))
        
        # Round to nearest hour to improve cache hits
        timestamp = int(time.time()) // 3600
        
        response = await self._fetch_pool_history_cached(pool_id, days, interval, timestamp)
        
        if "error" in response:
            logger.error(f"Error fetching pool history: {response['error']}")
            logger.info("Falling back to mock data for fetch_pool_history due to API error")
            return get_mock_pool_history(pool_id, days, interval)
            
        # Handle different response formats
        if "data" in response and isinstance(response["data"], list):
            return response["data"]
        elif "history" in response and isinstance(response["history"], list):
            return response["history"]
        else:
            # Check if the response itself is a list
            if isinstance(response, list):
                return response
                
            logger.warning(f"Unexpected response format from fetch_pool_history: {response}")
            logger.info("Falling back to mock data for fetch_pool_history due to unexpected response format")
            return get_mock_pool_history(pool_id, days, interval)

    # Cache decorated function for predictions with min score
    @lru_cache(maxsize=8)
    async def _fetch_predictions_cached(self, min_score: float, timestamp: int) -> Dict[str, Any]:
        """Cached version of fetch_predictions to minimize API calls."""
        params = {}
        
        if min_score is not None and min_score > 0:
            params["min_score"] = min_score
        
        return await self._make_request("/predictions", params=params)

    async def fetch_predictions(self, min_score: Optional[float] = None) -> List[Dict[str, Any]]:
        """
        Fetch ML-powered predictions for pool performance.
        
        Args:
            min_score: Minimum prediction score threshold (0.0 to 1.0)
            
        Returns:
            List of prediction dictionaries
        """
        # Check if we should use mock data based on environment setting or API health
        if USE_MOCK_DATA or not await self.check_health():
            logger.info("Using mock data for fetch_predictions")
            return get_mock_predictions(min_score)
        
        # Round to nearest 30 minutes to improve cache hits
        timestamp = int(time.time()) // 1800
        
        response = await self._fetch_predictions_cached(min_score, timestamp)
        
        if "error" in response:
            logger.error(f"Error fetching predictions: {response['error']}")
            logger.info("Falling back to mock data for fetch_predictions due to API error")
            return get_mock_predictions(min_score)
            
        # Handle different response formats
        if "data" in response and isinstance(response["data"], list):
            return response["data"]
        elif "predictions" in response and isinstance(response["predictions"], list):
            return response["predictions"]
        else:
            # Check if the response itself is a list
            if isinstance(response, list):
                return response
                
            logger.warning(f"Unexpected response format from fetch_predictions: {response}")
            logger.info("Falling back to mock data for fetch_predictions due to unexpected response format")
            return get_mock_predictions(min_score)

    async def fetch_forecast(self, pool_id: str, days: int = 7) -> Dict[str, Any]:
        """
        Fetch APR forecast for a specific pool.
        
        Args:
            pool_id: ID of the pool
            days: Number of days to forecast (1-30)
            
        Returns:
            Dictionary with forecast data
        """
        # Check if we should use mock data based on environment setting or API health
        if USE_MOCK_DATA or not await self.check_health():
            logger.info("Using mock data for fetch_forecast")
            return get_mock_forecast(pool_id, days)
        
        # Limit days to a reasonable range
        days = max(1, min(days, 30))
        
        params = {"days": days}
        
        response = await self._make_request(f"/pools/{pool_id}/forecast", params=params)
        
        if "error" in response:
            logger.error(f"Error fetching pool forecast: {response['error']}")
            logger.info("Falling back to mock data for fetch_forecast due to API error")
            return get_mock_forecast(pool_id, days)
            
        # Handle different response formats
        if "data" in response and isinstance(response["data"], dict):
            return response["data"]
        elif "forecast" in response and isinstance(response["forecast"], dict):
            return response["forecast"]
        else:
            # Check if the response contains forecast data directly
            if "apr_forecast" in response or "tvl_forecast" in response:
                return response
                
            logger.warning(f"Unexpected response format from fetch_forecast: {response}")
            logger.info("Falling back to mock data for fetch_forecast due to unexpected response format")
            return get_mock_forecast(pool_id, days)

    async def check_health(self) -> bool:
        """
        Check if the SolPool API is healthy and accessible.
        
        Returns:
            True if the API is healthy, False otherwise
        """
        # Only check health periodically to avoid excessive API calls
        current_time = time.time()
        if current_time - self.last_health_check < self.health_check_interval and self.last_health_check > 0:
            return self.api_healthy
            
        self.last_health_check = current_time
        
        try:
            response = await self._make_request("/health")
            status = response.get("status", "").lower()
            self.api_healthy = status in ["healthy", "success", "online", "ok"]
            return self.api_healthy
        except Exception as e:
            logger.error(f"API health check failed: {e}")
            self.api_healthy = False
            return False