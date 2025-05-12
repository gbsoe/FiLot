#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Client for interacting with the FiLotSense Public API for real-time 
sentiment and price signals.
"""

import os
import time
import json
import logging
import asyncio
from typing import Dict, List, Any, Optional, Tuple

import aiohttp
from functools import lru_cache

# Import mock data functions for fallback when API is unavailable
from api_mock_data import (
    get_mock_sentiment_simple,
    get_mock_prices_latest,
    get_mock_sentiment_topics,
    get_mock_realdata,
    get_mock_token_sentiment_history
)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
logger = logging.getLogger('filotsense_client')

# Flag to control when to use mock data
USE_MOCK_DATA = os.environ.get("USE_MOCK_DATA", "true").lower() in ("true", "1", "yes")

# Singleton instance
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
        if endpoint == "/health" and ('online' in text.lower() or 'success' in text.lower()):
            logger.info("Detected positive health status from HTML response")
            return {"status": "success"}
        
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

    # Cached sentiment fetch to minimize API calls
    @lru_cache(maxsize=8)
    async def _fetch_sentiment_simple_cached(self, symbols: Optional[str], timestamp: int) -> Dict[str, Any]:
        """Cached version of fetch_sentiment_simple to minimize API calls."""
        endpoint = "/sentiment/simple"
        params = {}
        
        if symbols:
            params["symbols"] = symbols
        
        return await self._make_request(endpoint, params=params)

    async def fetch_sentiment_simple(self, symbols: Optional[List[str]] = None) -> Dict[str, float]:
        """
        Fetch simple sentiment scores for tokens.
        
        Args:
            symbols: Optional list of token symbols to get sentiment for
            
        Returns:
            Dictionary mapping token symbols to sentiment scores (-1.0 to 1.0)
        """
        # Check if we should use mock data based on environment setting or API health
        if USE_MOCK_DATA or not await self.check_health():
            logger.info("Using mock data for fetch_sentiment_simple")
            return get_mock_sentiment_simple(symbols)
        
        symbols_str = None
        if symbols:
            symbols_str = ",".join(symbols)
        
        # Round to nearest minute to improve cache hits
        timestamp = int(time.time()) // 60
        
        response = await self._fetch_sentiment_simple_cached(symbols_str, timestamp)
        
        if "error" in response:
            logger.error(f"Error fetching simple sentiment: {response['error']}")
            logger.info("Falling back to mock data for fetch_sentiment_simple due to API error")
            return get_mock_sentiment_simple(symbols)
            
        sentiment_data = {}
        try:
            # New API format
            if "sentiment" in response and isinstance(response["sentiment"], dict):
                for symbol, data in response["sentiment"].items():
                    if isinstance(data, dict) and "score" in data:
                        sentiment_data[symbol] = data["score"]
                    elif isinstance(data, (int, float)):
                        sentiment_data[symbol] = data
            # Legacy API format
            elif "data" in response and isinstance(response["data"], dict):
                for symbol, score in response["data"].items():
                    if isinstance(score, (int, float)):
                        sentiment_data[symbol] = score
                    elif isinstance(score, dict) and "score" in score:
                        sentiment_data[symbol] = score["score"]
                        
            # If we still don't have any data, use mock
            if not sentiment_data:
                logger.warning("Failed to extract sentiment data from API response")
                logger.info("Falling back to mock data for fetch_sentiment_simple due to parsing failure")
                return get_mock_sentiment_simple(symbols)
                
        except Exception as e:
            logger.error(f"Error processing sentiment data: {e}")
            logger.info("Falling back to mock data for fetch_sentiment_simple due to processing error")
            return get_mock_sentiment_simple(symbols)
            
        return sentiment_data

    # Cached prices fetch to minimize API calls
    @lru_cache(maxsize=8)
    async def _fetch_prices_latest_cached(self, symbols: Optional[str], timestamp: int) -> Dict[str, Any]:
        """Cached version of fetch_prices_latest to minimize API calls."""
        endpoint = "/prices/latest"
        params = {}
        
        if symbols:
            params["symbols"] = symbols
        
        return await self._make_request(endpoint, params=params)

    async def fetch_prices_latest(self, symbols: Optional[List[str]] = None) -> Dict[str, Dict[str, Any]]:
        """
        Fetch latest price information for tokens.
        
        Args:
            symbols: Optional list of token symbols to get prices for
            
        Returns:
            Dictionary mapping token symbols to price information
        """
        # Check if we should use mock data based on environment setting or API health
        if USE_MOCK_DATA or not await self.check_health():
            logger.info("Using mock data for fetch_prices_latest")
            return get_mock_prices_latest(symbols)
        
        symbols_str = None
        if symbols:
            symbols_str = ",".join(symbols)
        
        # Round to nearest minute to improve cache hits
        timestamp = int(time.time()) // 60
        
        response = await self._fetch_prices_latest_cached(symbols_str, timestamp)
        
        if "error" in response:
            logger.error(f"Error fetching latest prices: {response['error']}")
            logger.info("Falling back to mock data for fetch_prices_latest due to API error")
            return get_mock_prices_latest(symbols)
            
        price_data = {}
        try:
            # New API format
            if "prices" in response and isinstance(response["prices"], dict):
                return response["prices"]
            # Legacy API format
            elif "data" in response and isinstance(response["data"], dict):
                return response["data"]
                
            # If we still don't have any data, use mock
            if not price_data:
                logger.warning("Failed to extract price data from API response")
                logger.info("Falling back to mock data for fetch_prices_latest due to parsing failure")
                return get_mock_prices_latest(symbols)
                
        except Exception as e:
            logger.error(f"Error processing price data: {e}")
            logger.info("Falling back to mock data for fetch_prices_latest due to processing error")
            return get_mock_prices_latest(symbols)
            
        return price_data

    # Cached sentiment topics fetch to minimize API calls
    @lru_cache(maxsize=4)
    async def _fetch_sentiment_topics_cached(self, timestamp: int) -> Dict[str, Any]:
        """Cached version of fetch_sentiment_topics to minimize API calls."""
        endpoint = "/sentiment/topics"
        return await self._make_request(endpoint)

    async def fetch_sentiment_topics(self) -> List[Dict[str, Any]]:
        """
        Fetch trending sentiment topics in the crypto market.
        
        Returns:
            List of topic dictionaries with sentiment information
        """
        # Check if we should use mock data based on environment setting or API health
        if USE_MOCK_DATA or not await self.check_health():
            logger.info("Using mock data for fetch_sentiment_topics")
            return get_mock_sentiment_topics()
        
        # Round to nearest hour to improve cache hits
        timestamp = int(time.time()) // 3600
        
        response = await self._fetch_sentiment_topics_cached(timestamp)
        
        if "error" in response:
            logger.error(f"Error fetching sentiment topics: {response['error']}")
            logger.info("Falling back to mock data for fetch_sentiment_topics due to API error")
            return get_mock_sentiment_topics()
            
        topics = []
        try:
            # New API format
            if "topics" in response and isinstance(response["topics"], list):
                topics = response["topics"]
            # Alternative format
            elif "data" in response and isinstance(response["data"], list):
                topics = response["data"]
            # Legacy format
            elif "data" in response and isinstance(response["data"], dict) and "topics" in response["data"]:
                topics = response["data"]["topics"]
                
            # If we still don't have any data, use mock
            if not topics:
                logger.warning("Failed to extract topics from API response")
                logger.info("Falling back to mock data for fetch_sentiment_topics due to parsing failure")
                return get_mock_sentiment_topics()
                
        except Exception as e:
            logger.error(f"Error processing sentiment topics: {e}")
            logger.info("Falling back to mock data for fetch_sentiment_topics due to processing error")
            return get_mock_sentiment_topics()
            
        return topics

    # Cached realdata fetch to minimize API calls
    @lru_cache(maxsize=8)
    async def _fetch_realdata_cached(self, symbols: Optional[str], timestamp: int) -> Dict[str, Any]:
        """Cached version of fetch_realdata to minimize API calls."""
        endpoint = "/realdata"
        params = {}
        
        if symbols:
            params["symbols"] = symbols
        
        return await self._make_request(endpoint, params=params)

    async def fetch_realdata(self, symbols: Optional[List[str]] = None) -> Dict[str, Dict[str, Any]]:
        """
        Fetch comprehensive real-time data including price, sentiment, and volume.
        
        Args:
            symbols: Optional list of token symbols to get data for
            
        Returns:
            Dictionary mapping token symbols to comprehensive data
        """
        # Check if we should use mock data based on environment setting or API health
        if USE_MOCK_DATA or not await self.check_health():
            logger.info("Using mock data for fetch_realdata")
            return get_mock_realdata(symbols)
        
        symbols_str = None
        if symbols:
            symbols_str = ",".join(symbols)
        
        # Round to nearest minute to improve cache hits
        timestamp = int(time.time()) // 60
        
        response = await self._fetch_realdata_cached(symbols_str, timestamp)
        
        if "error" in response:
            logger.error(f"Error fetching real-time data: {response['error']}")
            logger.info("Falling back to mock data for fetch_realdata due to API error")
            return get_mock_realdata(symbols)
            
        realdata = {}
        try:
            # New API format
            if "data" in response and isinstance(response["data"], dict):
                return response["data"]
            # Legacy format or direct data
            elif all(key not in ["status", "error", "message"] for key in response.keys()):
                return response
                
            # If we still don't have any data, use mock
            if not realdata:
                logger.warning("Failed to extract real-time data from API response")
                logger.info("Falling back to mock data for fetch_realdata due to parsing failure")
                return get_mock_realdata(symbols)
                
        except Exception as e:
            logger.error(f"Error processing real-time data: {e}")
            logger.info("Falling back to mock data for fetch_realdata due to processing error")
            return get_mock_realdata(symbols)
            
        return realdata

    async def fetch_token_sentiment_history(self, symbol: str, days: int = 7) -> List[Dict[str, Any]]:
        """
        Fetch historical sentiment data for a specific token.
        
        Args:
            symbol: Token symbol
            days: Number of days of history to fetch (1-30)
            
        Returns:
            List of historical sentiment data points
        """
        # Check if we should use mock data based on environment setting or API health
        if USE_MOCK_DATA or not await self.check_health():
            logger.info("Using mock data for fetch_token_sentiment_history")
            return get_mock_token_sentiment_history(symbol, days)
        
        endpoint = f"/sentiment/history/{symbol}"
        params = {"days": min(max(1, days), 30)}  # Ensure days is between 1 and 30
        
        response = await self._make_request(endpoint, params=params)
        
        if "error" in response:
            logger.error(f"Error fetching sentiment history: {response['error']}")
            logger.info("Falling back to mock data for fetch_token_sentiment_history due to API error")
            return get_mock_token_sentiment_history(symbol, days)
            
        try:
            # New API format
            if "history" in response and isinstance(response["history"], list):
                return response["history"]
            # Legacy API format
            elif "data" in response and isinstance(response["data"], list):
                return response["data"]
                
            # If we still don't have any data, use mock
            logger.warning("Failed to extract sentiment history from API response")
            logger.info("Falling back to mock data for fetch_token_sentiment_history due to parsing failure")
            return get_mock_token_sentiment_history(symbol, days)
                
        except Exception as e:
            logger.error(f"Error in fetch_token_sentiment_history: {e}")
            logger.info("Falling back to mock data for fetch_token_sentiment_history due to processing error")
            return get_mock_token_sentiment_history(symbol, days)
            
    async def check_health(self) -> bool:
        """
        Check if the FiLotSense API is healthy and accessible.
        
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
            self.api_healthy = status in ["success", "online", "ok"]
            return self.api_healthy
        except Exception as e:
            logger.error(f"API health check failed: {e}")
            self.api_healthy = False
            return False