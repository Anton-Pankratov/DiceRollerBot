import time
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery
from config import THROTTLING_RATE

class ThrottlingMiddleware(BaseMiddleware):
    """
    Middleware для ограничения частоты запросов от пользователей (Rate Limiting / Throttling).
    Предотвращает перегрузку бота при частых кликах по кнопкам или спаме сообщениями.
    """

    def __init__(self, rate_limit: float = THROTTLING_RATE):
        super().__init__()
        self.rate_limit = rate_limit
        # Хранилище времени последних запросов {user_id: timestamp}
        self.cache: Dict[int, float] = {}
        # Лимит размера кэша в памяти для предотвращения утечек
        self.max_cache_size = 50000

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        # Извлекаем пользователя из данных события
        user = data.get("event_from_user")
        if not user:
            return await handler(event, data)

        user_id = user.id
        current_time = time.time()
        
        # Периодическая очистка кэша от старых записей при превышении лимита размера
        if len(self.cache) > self.max_cache_size:
            self._clean_cache(current_time)

        last_request_time = self.cache.get(user_id, 0.0)

        # Если лимит времени не превышен
        if current_time - last_request_time < self.rate_limit:
            # Игнорируем запрос для сбережения лимитов Telegram API.
            # Если это CallbackQuery (нажатие на кнопку), можно ответить всплывающим сообщением.
            if isinstance(event, CallbackQuery):
                await event.answer(
                    text="⚠️ Не кликайте так часто!",
                    show_alert=False
                )
            return

        # Обновляем время последнего запроса
        self.cache[user_id] = current_time
        return await handler(event, data)

    def _clean_cache(self, current_time: float):
        """Очищает устаревшие записи из кэша для предотвращения утечек памяти."""
        expired_keys = [
            uid for uid, last_time in self.cache.items()
            if current_time - last_time > self.rate_limit
        ]
        for uid in expired_keys:
            self.cache.pop(uid, None)
