"""LMS API client for fetching labs and scores."""

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


@dataclass
class Lab:
    """Represents a lab assignment."""

    id: str
    name: str
    description: str
    max_score: int
    deadline: Optional[str] = None


@dataclass
class TaskPassRate:
    """Represents pass rate for a task."""

    task_name: str
    pass_rate: float
    attempts: int


@dataclass
class Score:
    """Represents a student's score for a lab."""

    lab_id: str
    score: int
    max_score: int
    status: str
    feedback: Optional[str] = None


class LMSClient:
    """Client for interacting with the LMS API."""

    def __init__(self, base_url: str, api_key: str):
        """Initialize the LMS client.

        Args:
            base_url: Base URL of the LMS API.
            api_key: API key for authentication.
        """
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self._headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def get_labs(self) -> List[Lab]:
        """Fetch all available labs from /items/ endpoint.

        Returns:
            List of Lab objects.

        Raises:
            httpx.RequestError: If the API request fails.
        """
        url = f"{self.base_url}/items/"
        logger.info(f"Fetching labs from {url}")

        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=self._headers, timeout=10.0)
            response.raise_for_status()
            data = response.json()

        labs = []
        for item in data:
            # Only include items of type "lab"
            if item.get("type") != "lab":
                continue

            # Extract lab info from item structure
            item_id = item.get("id", "")
            title = item.get("title", item.get("name", "Unknown Lab"))

            # Generate lab ID from title if not present
            if isinstance(item_id, int):
                lab_id = f"lab-{item_id:02d}"
            else:
                lab_id = str(item_id).lower().replace(" ", "-")

            lab = Lab(
                id=lab_id,
                name=title,
                description=item.get("description", ""),
                max_score=item.get("max_score", 100),
                deadline=item.get("deadline"),
            )
            labs.append(lab)

        return labs

    async def get_pass_rates(self, lab_id: str) -> List[TaskPassRate]:
        """Fetch pass rates for a specific lab from /analytics/pass-rates endpoint.

        Args:
            lab_id: The lab ID to fetch pass rates for.

        Returns:
            List of TaskPassRate objects.

        Raises:
            httpx.RequestError: If the API request fails.
        """
        url = f"{self.base_url}/analytics/pass-rates"
        logger.info(f"Fetching pass rates for {lab_id} from {url}")

        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                headers=self._headers,
                params={"lab": lab_id},
                timeout=10.0,
            )
            response.raise_for_status()
            data = response.json()

        pass_rates = []
        for item in data:
            # The API returns avg_score (0-100) as the pass rate
            avg_score = item.get("avg_score", item.get("average", 0.0))
            # avg_score is already 0-100, not 0-1
            pass_rate = avg_score if avg_score <= 100 else avg_score * 100

            task = TaskPassRate(
                task_name=item.get("task_name", item.get("task", "Unknown Task")),
                pass_rate=pass_rate,
                attempts=item.get("attempts", item.get("submissions", 0)),
            )
            pass_rates.append(task)

        return pass_rates

    async def health_check(self) -> tuple[bool, int, Optional[str]]:
        """Check if the LMS API is healthy by calling /items/.

        Returns:
            Tuple of (is_healthy, item_count, error_message).
            error_message is None if healthy, or contains the actual error.
        """
        url = f"{self.base_url}/items/"
        logger.info(f"Checking LMS API health at {url}")

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=self._headers, timeout=10.0)

                if response.status_code == 200:
                    data = response.json()
                    item_count = len(data) if isinstance(data, list) else 0
                    return True, item_count, None
                else:
                    error_msg = f"HTTP {response.status_code} {response.reason_phrase}"
                    logger.warning(f"Health check failed: {error_msg}")
                    return False, 0, error_msg

        except httpx.ConnectError as e:
            error_msg = f"connection refused ({self.base_url}). Check that the services are running."
            logger.warning(f"Health check connection error: {error_msg}")
            return False, 0, error_msg

        except httpx.TimeoutException as e:
            error_msg = f"timeout connecting to {self.base_url}"
            logger.warning(f"Health check timeout: {error_msg}")
            return False, 0, error_msg

        except httpx.HTTPStatusError as e:
            error_msg = f"HTTP {e.response.status_code} {e.response.reason_phrase}"
            logger.warning(f"Health check HTTP error: {error_msg}")
            return False, 0, error_msg

        except Exception as e:
            error_msg = f"{type(e).__name__}: {str(e)}"
            logger.warning(f"Health check unexpected error: {error_msg}")
            return False, 0, error_msg
