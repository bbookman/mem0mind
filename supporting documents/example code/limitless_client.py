"""Limitless API client for fetching lifelog data.

This module provides the LimitlessAPIClient class for interacting with
the Limitless API to fetch conversation transcripts and lifelog entries.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set

from loguru import logger

from .api_client import APIClient, APIError, log_api_call
from .constants import (
    LIMITLESS_API_BASE_URL,
    DEFAULT_API_DELAY,
    DEFAULT_MAX_RETRIES,
)


@dataclass
class LifelogQuery:
    """Parameter object for lifelog queries.

    Groups related parameters together to reduce method complexity
    and improve maintainability.

    Attributes:
        timezone: IANA timezone specifier
        date: Specific date in YYYY-MM-DD format
        start: Start datetime (YYYY-MM-DD or YYYY-MM-DD HH:mm:SS)
        end: End datetime (YYYY-MM-DD or YYYY-MM-DD HH:mm:SS)
        direction: Sort direction "asc" or "desc"
        includeMarkdown: Include markdown content
        includeHeadings: Include headings
        limit: Items per page (default is 10, max is 10)

    Example:
        >>> query = LifelogQuery(date="2024-01-15", timezone="America/New_York")
        >>> lifelogs = client.fetch_lifelogs(query)
    """

    timezone: str = "UTC"
    date: Optional[str] = None
    start: Optional[str] = None
    end: Optional[str] = None
    direction: str = "desc"
    includeMarkdown: bool = True
    includeHeadings: bool = True
    limit: int = 10


class LimitlessAPIClient(APIClient):
    """
    Manage Limitless API interactions for lifelogs and related data.

    This class handles all communication with the Limitless API, including authentication,
    cursor-based pagination, and response parsing for lifelog data.

    Attributes:
        api_key: Limitless API authentication key
        base_url: Limitless API base URL
        default_delay: Delay between requests in seconds
        max_retries: Maximum retry attempts for failed requests

    Example:
        >>> client = LimitlessAPIClient(api_key="your-key")
        >>> lifelogs = client.fetch_lifelogs()
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = LIMITLESS_API_BASE_URL,
        default_delay: float = DEFAULT_API_DELAY,
        max_retries: int = DEFAULT_MAX_RETRIES,
    ) -> None:
        """
        Initialize Limitless API client with configuration.

        Args:
            api_key: Limitless API authentication key
            base_url: Limitless API base URL (default: https://api.limitless.ai)
            default_delay: Delay between requests in seconds
            max_retries: Maximum retry attempts for failed requests

        Example:
            >>> client = LimitlessAPIClient(api_key="your-key")
            >>> lifelogs = client.fetch_lifelogs()
        """
        super().__init__(api_key, base_url, default_delay, max_retries)
        logger.info("Initialized LimitlessAPIClient")

    def _setup_headers(self) -> None:
        """Set up Limitless API specific headers.

        Configures the X-API-Key header required for Limitless API authentication.
        """
        self.session.headers.update(
            {"X-API-Key": self.api_key, "Content-Type": "application/json"}
        )
        logger.debug("Set up Limitless API headers")

    def _extract_items_from_response(
        self, response_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Extract lifelogs list from Limitless API response.

        Args:
            response_data: Raw Limitless API response

        Returns:
            List of lifelog entries from the response

        Raises:
            APIError: When response format is unexpected
        """
        if "data" not in response_data:
            logger.error(f"Unexpected response format: {list(response_data.keys())}")
            raise APIError("Invalid response format: missing 'data' field")

        if "lifelogs" not in response_data["data"]:
            logger.error(
                f"Unexpected data format: {list(response_data['data'].keys())}"
            )
            raise APIError("Invalid response format: missing 'lifelogs' field in data")

        lifelogs = response_data["data"]["lifelogs"]
        logger.debug(f"Extracted {len(lifelogs)} lifelogs from response")
        return lifelogs

    def _has_more_pages(
        self,
        response_data: Dict[str, Any],
        current_page_size: int,
        current_params: Dict[str, Any],
    ) -> bool:
        """Check if more pages are available using Limitless cursor pagination.

        Args:
            response_data: Current page response data
            current_page_size: Number of items in current page
            current_params: Current request parameters

        Returns:
            True if nextCursor is present, False otherwise
        """
        meta = response_data.get("meta", {})
        lifelogs_meta = meta.get("lifelogs", {})
        next_cursor = lifelogs_meta.get("nextCursor")

        has_more = bool(next_cursor)
        logger.debug(f"Has more pages: {has_more} (nextCursor: {next_cursor})")
        return has_more

    def _extract_next_cursor(self, response_data: Dict[str, Any]) -> Optional[str]:
        """Extract next cursor from Limitless API response.

        Args:
            response_data: Current page response data

        Returns:
            Next cursor value or None if not available
        """
        meta = response_data.get("meta", {})
        lifelogs_meta = meta.get("lifelogs", {})
        next_cursor = lifelogs_meta.get("nextCursor")

        logger.debug(f"Next cursor: {next_cursor}")
        return next_cursor

    def _build_query_params(self, query: LifelogQuery) -> Dict[str, Any]:
        """Build API query parameters from LifelogQuery object.

        Args:
            query: LifelogQuery object with parameters

        Returns:
            Dictionary of API parameters with non-default values

        Example:
            >>> query = LifelogQuery(date="2024-01-15", timezone="America/New_York")
            >>> params = client._build_query_params(query)
            >>> # Returns: {"date": "2024-01-15", "timezone": "America/New_York", "limit": 10}
        """
        params = {}

        # Always include limit, but cap at API maximum of 10
        api_limit = min(query.limit, 10)
        params["limit"] = api_limit

        # Include timezone if not default UTC
        if query.timezone != "UTC":
            params["timezone"] = query.timezone

        # Include date if specified (takes precedence over start/end)
        if query.date is not None:
            params["date"] = query.date
        else:
            # Include start/end if specified and no date
            if query.start is not None:
                params["start"] = query.start
            if query.end is not None:
                params["end"] = query.end

        # Include direction if not default desc
        if query.direction != "desc":
            params["direction"] = query.direction

        # Include includeMarkdown if not default True
        if not query.includeMarkdown:
            params["includeMarkdown"] = query.includeMarkdown

        # Include includeHeadings if not default True
        if not query.includeHeadings:
            params["includeHeadings"] = query.includeHeadings

        logger.debug(f"Built query params: {params}")
        return params

    @log_api_call
    def fetch_lifelogs(
        self,
        query: Optional[LifelogQuery] = None,
        existing_ids: Optional[Set[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Fetch lifelogs from Limitless API with pagination and duplicate detection.

        Args:
            query: Lifelog query parameters (uses defaults if None)
            existing_ids: Set of existing lifelog IDs to avoid duplicates

        Returns:
            List of all lifelog entries

        Raises:
            APIError: When API requests fail

        Example:
            >>> client = LimitlessAPIClient("your-key")
            >>> query = LifelogQuery(date="2024-01-15")
            >>> lifelogs = client.fetch_lifelogs(query)
        """
        if query is None:
            query = LifelogQuery()

        # Build parameters from query object
        params = self._build_query_params(query)

        logger.info(f"Fetching lifelogs with params: {params}")
        logger.info(f"Existing IDs count: {len(existing_ids) if existing_ids else 0}")

        return self.fetch_paginated_data(
            endpoint="/v1/lifelogs",
            pagination_strategy="cursor",
            params=params,
            existing_ids=existing_ids,
            id_field="id",
        )

    @log_api_call
    def fetch_lifelogs_by_date_range(
        self,
        start_date: str,
        end_date: str,
        timezone: str = "UTC",
        existing_ids: Optional[Set[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Fetch lifelogs for a specific date range.

        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            timezone: IANA timezone specifier
            existing_ids: Set of existing lifelog IDs to avoid duplicates

        Returns:
            List of lifelog entries in the date range

        Example:
            >>> lifelogs = client.fetch_lifelogs_by_date_range("2024-01-01", "2024-01-31")
        """
        query = LifelogQuery(start=start_date, end=end_date, timezone=timezone)
        return self.fetch_lifelogs(query=query, existing_ids=existing_ids)

    @log_api_call
    def fetch_recent_lifelogs(
        self,
        days: int = 7,
        timezone: str = "UTC",
        existing_ids: Optional[Set[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Fetch lifelogs from the last N days.

        Args:
            days: Number of days to look back
            timezone: IANA timezone specifier
            existing_ids: Set of existing lifelog IDs to avoid duplicates

        Returns:
            List of recent lifelog entries

        Example:
            >>> recent_logs = client.fetch_recent_lifelogs(days=3)
        """
        from datetime import datetime, timedelta

        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        query = LifelogQuery(
            start=start_date.strftime("%Y-%m-%d"),
            end=end_date.strftime("%Y-%m-%d"),
            timezone=timezone,
        )
        return self.fetch_lifelogs(query=query, existing_ids=existing_ids)

    @log_api_call
    def get_total_count(self) -> int:
        """Get total count of lifelogs from Limitless API.
        
        Note: Limitless API doesn't provide total count directly.
        This method makes a small request to check if data exists,
        and returns a reasonable estimate for progress tracking.

        Returns:
            Estimated total number of lifelogs (or 1 if any exist)

        Raises:
            APIError: When API request fails
        """
        logger.info("Getting total count estimate from Limitless API")
        
        # Make a request with limit=1 to see if any data exists
        response_data = self._make_request("/v1/lifelogs", params={"limit": 1})
        
        if "meta" not in response_data:
            raise APIError("Invalid response format: missing 'meta' field")
            
        meta = response_data["meta"]
        if "lifelogs" not in meta:
            raise APIError("Invalid response format: missing 'lifelogs' in meta")
            
        # Check if we have any data at all
        data = response_data.get("data", {})
        lifelogs = data.get("lifelogs", [])
        
        if not lifelogs:
            logger.info("No lifelogs found in account")
            return 0
            
        # We have data, but Limitless API doesn't provide total count
        # Return a reasonable estimate for progress tracking
        # We'll update this as we fetch more data
        count = len(lifelogs)
        has_more = meta["lifelogs"].get("nextCursor") is not None
        
        if has_more:
            # Estimate there might be more pages
            estimated_total = 50  # Conservative estimate for progress bar
            logger.info(f"Found {count} lifelogs in first page, estimating ~{estimated_total} total")
            return estimated_total
        else:
            # Only one page of data
            logger.info(f"Found {count} total lifelogs")
            return count

    @log_api_call
    def fetch_batch(
        self,
        offset: int,
        limit: int,
    ) -> List[Dict[str, Any]]:
        """Fetch a batch of lifelogs from Limitless API.

        Args:
            offset: Starting offset for pagination
            limit: Number of items to fetch

        Returns:
            List of lifelog entries in the batch

        Raises:
            APIError: When API request fails
        """
        params = {
            "offset": offset,
            "limit": limit
        }
        
        logger.info(f"Fetching batch with params: {params}")
        
        response_data = self._make_request("/v1/lifelogs", params=params)
        
        if "data" not in response_data or "lifelogs" not in response_data["data"]:
            raise APIError("Invalid response format: missing 'lifelogs' in data")
            
        lifelogs = response_data["data"]["lifelogs"]
        logger.info(f"Fetched {len(lifelogs)} lifelogs")
        return lifelogs
