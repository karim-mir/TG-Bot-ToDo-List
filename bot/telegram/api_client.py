import logging
import os
from typing import Any, Dict, List

import aiohttp

logger = logging.getLogger(__name__)


class DjangoAPIClient:
    def __init__(self):
        self.base_url = os.getenv("DJANGO_API_URL", "http://localhost:8000/api")
        self.timeout = aiohttp.ClientTimeout(total=30)
        logger.info(f"API Client initialized with base URL: {self.base_url}")

    async def _make_request(
        self, method: str, endpoint: str, **kwargs
    ) -> Dict[str, Any]:
        """Базовый метод для запросов к API"""
        url = f"{self.base_url}/{endpoint}"
        logger.info(f"API Request: {method} {url}")

        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            try:
                async with session.request(method, url, **kwargs) as response:
                    response_text = await response.text()
                    logger.info(
                        f"API Response {response.status}: {response_text[:200]}..."
                    )

                    if response.status == 200 or response.status == 201:
                        try:
                            return await response.json()
                        except:
                            return {"text": response_text}
                    else:
                        logger.error(f"API Error {response.status}: {response_text}")
                        return {
                            "error": f"API Error {response.status}: {response_text}"
                        }
            except Exception as e:
                logger.error(f"Network error: {e}")
                return {"error": f"Network error: {str(e)}"}

    async def get_user_tasks(self, django_user_id):
        """Получить задачи пользователя - ИСПРАВЛЕННАЯ ВЕРСИЯ"""
        # Пробуем разные варианты параметров
        urls_to_try = [
            f"{self.base_url}/tasks/?user={django_user_id}",
            f"{self.base_url}/tasks/?user_id={django_user_id}",
            f"{self.base_url}/tasks/?user__id={django_user_id}",
        ]

        for url in urls_to_try:
            logger.info(f"API GET tasks: {url}")
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, timeout=30) as response:
                        logger.info(f"Tasks API response status: {response.status}")

                        if response.status == 200:
                            try:
                                data = await response.json()
                                logger.info(
                                    f"Got {len(data) if isinstance(data, list) else 0} tasks via {url}"
                                )
                                return data if isinstance(data, list) else []
                            except Exception as e:
                                text = await response.text()
                                logger.error(
                                    f"JSON parse error: {e}, text: {text[:100]}"
                                )
                        elif response.status == 400:
                            # Пробуем следующий URL
                            continue
                        else:
                            error = await response.text()
                            logger.error(f"API Error {response.status}: {error}")
            except Exception as e:
                logger.error(f"Network error with {url}: {e}")
                continue

        logger.warning(f"Все URL вернули ошибку для user_id={django_user_id}")
        return []

    async def create_task(self, task_data: Dict) -> Dict:
        """Создать новую задачу"""
        return await self._make_request("POST", "tasks/", json=task_data)

    async def get_user_categories(self, user_id: int) -> List[Dict]:
        """Получить категории пользователя"""
        result = await self._make_request("GET", f"categories/?user_id={user_id}")
        if isinstance(result, list):
            return result
        elif isinstance(result, dict) and "error" in result:
            logger.error(f"Error getting categories: {result['error']}")
            return []
        else:
            return []
