"""Bee API client for fetching conversations, facts, locations, and todos.

This module provides the BeeAPIClient class for interacting with
the Bee API to fetch conversations, facts, locations, and todo data.
"""

from typing import Any, Dict, List, Optional, Set

from loguru import logger

from .api_client import APIClient, APIError, log_api_call
from .constants import BEE_API_BASE_URL, DEFAULT_API_DELAY, DEFAULT_MAX_RETRIES


class BeeAPIClient(APIClient):
    """
    Manage Bee API interactions for conversations, facts, locations, and todos.

    This class handles all communication with the Bee API, including authentication,
    pagination, and response parsing for multiple endpoints.

    Attributes:
        api_key: Bee API authentication key
        base_url: Bee API base URL
        default_delay: Delay between requests in seconds
        max_retries: Maximum retry attempts for failed requests

    Example:
        >>> client = BeeAPIClient(api_key="your-key")
        >>> conversations = client.fetch_conversations()
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = BEE_API_BASE_URL,
        default_delay: float = DEFAULT_API_DELAY,
        max_retries: int = DEFAULT_MAX_RETRIES,
    ) -> None:
        """
        Initialize Bee API client with configuration.

        Args:
            api_key: Bee API authentication key
            base_url: Bee API base URL (default: https://api.bee.computer/v1/me)
            default_delay: Delay between requests in seconds
            max_retries: Maximum retry attempts for failed requests

        Example:
            >>> client = BeeAPIClient(api_key="your-key")
            >>> conversations = client.fetch_conversations()
        """
        super().__init__(api_key, base_url, default_delay, max_retries)
        logger.info("Initialized BeeAPIClient")

    def _setup_headers(self) -> None:
        """Set up Bee API specific headers.

        Configures the x-api-key header required for Bee API authentication.
        """
        self.session.headers.update(
            {"x-api-key": self.api_key, "Content-Type": "application/json"}
        )
        logger.debug("Set up Bee API headers")

    def _extract_items_from_response(
        self, response_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Extract items list from Bee API response.

        Args:
            response_data: Raw Bee API response

        Returns:
            List of items from the response

        Raises:
            APIError: When response format is unexpected
        """
        # Bee API responses have different top-level keys for different endpoints
        possible_keys = ["conversations", "facts", "locations", "todos"]

        for key in possible_keys:
            if key in response_data:
                items = response_data[key]
                logger.debug(f"Extracted {len(items)} {key} from response")
                return items

        logger.error(f"Unexpected response format: {list(response_data.keys())}")
        raise APIError(f"Invalid response format: expected one of {possible_keys}")

    def _has_more_pages(
        self,
        response_data: Dict[str, Any],
        current_page_size: int,
        current_params: Dict[str, Any],
    ) -> bool:
        """Check if more pages are available using Bee page-based pagination.

        Args:
            response_data: Current page response data
            current_page_size: Number of items in current page
            current_params: Current request parameters

        Returns:
            True if more pages are available, False otherwise
        """
        current_page = response_data.get("currentPage", 1)
        total_pages = response_data.get("totalPages", 1)

        has_more = current_page < total_pages
        logger.debug(f"Has more pages: {has_more} (page {current_page}/{total_pages})")
        return has_more

    def _extract_next_cursor(self, response_data: Dict[str, Any]) -> Optional[str]:
        """Extract next cursor from Bee API response.

        Bee API uses page-based pagination, not cursor-based.

        Args:
            response_data: Current page response data

        Returns:
            None (Bee API doesn't use cursors)
        """
        return None

    @log_api_call
    def fetch_conversations(
        self,
        limit: Optional[int] = None,
        max_pages: Optional[int] = None,
        existing_ids: Optional[Set[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Fetch conversations from Bee API with pagination and duplicate detection.

        Args:
            limit: Items per page (optional, if not specified uses API default)
            max_pages: Maximum number of pages to fetch (for testing)
            existing_ids: Set of existing conversation IDs to avoid duplicates

        Returns:
            List of all conversation entries

        Raises:
            APIError: When API requests fail

        Example:
            >>> client = BeeAPIClient("your-key")
            >>> conversations = client.fetch_conversations()
        """
        params = {}
        if limit is not None:
            params["limit"] = limit

        logger.info(f"Fetching conversations with params: {params}")
        logger.info(f"Existing IDs count: {len(existing_ids) if existing_ids else 0}")

        return self.fetch_paginated_data(
            endpoint="/conversations",
            pagination_strategy="page",
            params=params,
            existing_ids=existing_ids,
            id_field="id",
            max_pages=max_pages,
        )

    @log_api_call
    def fetch_conversation_details(self, conversation_id: int) -> Dict[str, Any]:
        """Fetch detailed conversation data including transcriptions.

        Args:
            conversation_id: ID of the conversation to fetch

        Returns:
            Detailed conversation data with transcriptions

        Raises:
            APIError: When API request fails

        Example:
            >>> details = client.fetch_conversation_details(12345)
        """
        logger.info(f"Fetching conversation details for ID: {conversation_id}")

        response_data = self._make_request(f"/conversations/{conversation_id}")

        if "conversation" not in response_data:
            raise APIError("Invalid response format: missing 'conversation' field")

        conversation_data = response_data["conversation"]
        logger.info(f"Fetched conversation details (ID: {conversation_id})")
        return conversation_data

    @log_api_call
    def fetch_facts(
        self,
        limit: Optional[int] = None,
        confirmed: bool = True,
        max_pages: Optional[int] = None,
        existing_ids: Optional[Set[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Fetch facts from Bee API with pagination and duplicate detection.

        Args:
            limit: Items per page (optional, if not specified uses API default)
            confirmed: Whether to fetch only confirmed facts
            max_pages: Maximum number of pages to fetch (for testing)
            existing_ids: Set of existing fact IDs to avoid duplicates

        Returns:
            List of all fact entries

        Raises:
            APIError: When API requests fail

        Example:
            >>> facts = client.fetch_facts(confirmed=True)
        """
        params = {"confirmed": confirmed}
        if limit is not None:
            params["limit"] = limit

        logger.info(f"Fetching facts with params: {params}")
        logger.info(f"Existing IDs count: {len(existing_ids) if existing_ids else 0}")

        return self.fetch_paginated_data(
            endpoint="/facts",
            pagination_strategy="page",
            params=params,
            existing_ids=existing_ids,
            id_field="id",
            max_pages=max_pages,
        )

    @log_api_call
    def fetch_fact_details(self, fact_id: int) -> Dict[str, Any]:
        """Fetch detailed fact data by ID.

        Args:
            fact_id: ID of the fact to fetch

        Returns:
            Detailed fact data

        Raises:
            APIError: When API request fails

        Example:
            >>> fact = client.fetch_fact_details(67890)
        """
        logger.info(f"Fetching fact details for ID: {fact_id}")

        response_data = self._make_request(f"/facts/{fact_id}")

        if "fact" not in response_data:
            raise APIError("Invalid response format: missing 'fact' field")

        fact_data = response_data["fact"]
        logger.info(f"Fetched fact details (ID: {fact_id})")
        return fact_data

    @log_api_call
    def fetch_locations(
        self,
        limit: Optional[int] = None,
        conversation_id: Optional[int] = None,
        max_pages: Optional[int] = None,
        existing_ids: Optional[Set[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Fetch locations from Bee API with pagination and duplicate detection.

        Args:
            limit: Items per page (optional, if not specified uses API default)
            conversation_id: Optional conversation ID to filter locations
            max_pages: Maximum number of pages to fetch (for testing)
            existing_ids: Set of existing location IDs to avoid duplicates

        Returns:
            List of all location entries

        Raises:
            APIError: When API requests fail

        Example:
            >>> locations = client.fetch_locations()
        """
        params = {}
        if limit is not None:
            params["limit"] = limit

        if conversation_id:
            params["conversationId"] = conversation_id

        logger.info(f"Fetching locations with params: {params}")
        logger.info(f"Existing IDs count: {len(existing_ids) if existing_ids else 0}")

        return self.fetch_paginated_data(
            endpoint="/locations",
            pagination_strategy="page",
            params=params,
            existing_ids=existing_ids,
            id_field="id",
            max_pages=max_pages,
        )

    @log_api_call
    def fetch_todos(
        self,
        limit: Optional[int] = None,
        max_pages: Optional[int] = None,
        existing_ids: Optional[Set[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Fetch todos from Bee API with pagination and duplicate detection.

        Note: Todos are very dynamic and may not be suitable for JSON storage
        as mentioned in the development plan.

        Args:
            limit: Items per page (optional, if not specified uses API default)
            max_pages: Maximum number of pages to fetch (for testing)
            existing_ids: Set of existing todo IDs to avoid duplicates

        Returns:
            List of all todo entries

        Raises:
            APIError: When API requests fail

        Example:
            >>> todos = client.fetch_todos()
        """
        params = {}
        if limit is not None:
            params["limit"] = limit

        logger.info(f"Fetching todos with params: {params}")
        logger.info(f"Existing IDs count: {len(existing_ids) if existing_ids else 0}")

        return self.fetch_paginated_data(
            endpoint="/todos",
            pagination_strategy="page",
            params=params,
            existing_ids=existing_ids,
            id_field="id",
            max_pages=max_pages,
        )

    @log_api_call
    def fetch_todo_details(self, todo_id: int) -> Dict[str, Any]:
        """Fetch detailed todo data by ID.

        Args:
            todo_id: ID of the todo to fetch

        Returns:
            Detailed todo data

        Raises:
            APIError: When API request fails

        Example:
            >>> todo = client.fetch_todo_details(11111)
        """
        logger.info(f"Fetching todo details for ID: {todo_id}")

        response_data = self._make_request(f"/todos/{todo_id}")

        if "todo" not in response_data:
            raise APIError("Invalid response format: missing 'todo' field")

        todo_data = response_data["todo"]
        logger.info(f"Fetched todo details (ID: {todo_id})")
        return todo_data

    @log_api_call
    def get_total_count(self) -> int:
        """Get total count of items from Bee API.

        Returns:
            Total number of items available

        Raises:
            APIError: When API request fails
        """
        logger.info("Getting total count from Bee API")
        
        try:
            response_data = self._make_request("/conversations", params={"limit": 1})
            
            # Check for totalCount in response
            if "totalCount" in response_data:
                total_count = response_data["totalCount"]
                logger.info(f"Total count: {total_count}")
                return total_count
                
            # If totalCount not found, try to get count from conversations array
            if "conversations" in response_data:
                conversations = response_data["conversations"]
                if isinstance(conversations, list):
                    # Make another request with a larger limit to get total count
                    response_data = self._make_request("/conversations", params={"limit": 1000})
                    if "conversations" in response_data:
                        total_count = len(response_data["conversations"])
                        logger.info(f"Total count from conversations array: {total_count}")
                        return total_count
            
            raise APIError("Could not determine total count from response")
            
        except Exception as e:
            logger.error(f"Error getting total count: {e}")
            raise APIError(f"Failed to get total count: {str(e)}")

    @log_api_call
    def fetch_batch(
        self,
        offset: int,
        limit: int,
    ) -> List[Dict[str, Any]]:
        """Fetch a batch of conversations from Bee API.

        Args:
            offset: Starting offset for pagination
            limit: Number of items to fetch

        Returns:
            List of conversation entries in the batch

        Raises:
            APIError: When API request fails
        """
        params = {
            "offset": offset,
            "limit": limit
        }
        
        logger.info(f"Fetching batch with params: {params}")
        
        try:
            response_data = self._make_request("/conversations", params=params)
            
            # Check for conversations in response
            if "conversations" not in response_data:
                raise APIError("Invalid response format: missing 'conversations' field")
                
            conversations = response_data["conversations"]
            if not isinstance(conversations, list):
                raise APIError("Invalid response format: 'conversations' is not a list")
                
            logger.info(f"Fetched {len(conversations)} conversations")
            return conversations
            
        except Exception as e:
            logger.error(f"Error fetching batch: {e}")
            raise APIError(f"Failed to fetch batch: {str(e)}")
