import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

import config
from handlers import register_all_routers
from middlewares import ThrottlingMiddleware

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

async def main():
    # Проверка на наличие токена
    if not config.BOT_TOKEN or config.BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN_HERE":
        logger.error(
            "КРИТИЧЕСКАЯ ОШИБКА: Укажите корректный BOT_TOKEN в файле .env "
            "для запуска бота!"
        )
        return

    # Инициализация бота с поддержкой HTML-разметки (используем DefaultBotProperties для aiogram >= 3.7.0)
    bot = Bot(
        token=config.BOT_TOKEN, 
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    from handlers.setup import CreationPrefixRequestMiddleware
    bot.session.middleware.register(CreationPrefixRequestMiddleware())

    welcome_description = (
        "🎲 Добро пожаловать в DiceRollerBot! 🧙‍♂️\n\n"
        "Я — ваш цифровой помощник по D&D 5e!\n\n"
        "🛡️ Что я умею:\n"
        "• Хранить листы персонажей любого класса.\n"
        "• Делать авто-проверки характеристик, навыков, спасбросков и инструментов с учетом модификаторов.\n"
        "• Бросать с преимуществом 🟢 или помехой 🔴 с клавиатуры.\n"
        "• Сохранять кастомные формулы бросков (оружие, магия).\n"
        "• Работать в группах без флуда через префикс !.\n\n"
        "Нажмите «Запустить», создайте героя и пусть кубики будут благосклонны! 🌟"
    )
    try:
        await bot.set_my_description(description=welcome_description)
        await bot.set_my_short_description(
            short_description="🎲 Хранитель листов персонажей D&D 5e и мастер автоматических проверок кубиков!"
        )
        logger.info("Приветственное описание бота успешно установлено в Telegram.")
        
        # Регистрация меню команд бота в Telegram
        from aiogram.types import BotCommand
        bot_commands = [
            BotCommand(command="start", description="Запустить бота и получить приветственное сообщение"),
            BotCommand(command="help", description="Открыть справочное руководство по броскам и проверкам"),
            BotCommand(command="keyboard", description="Настроить закрепление или скрытие игровой клавиатуры"),
            BotCommand(command="characters", description="Управление списком ваших персонажей"),
            BotCommand(command="create_character", description="Создать нового персонажа (мастер создания)"),
            BotCommand(command="roll", description="Сделать быстрый бросок кубиков (например: /roll 2d6)"),
            BotCommand(command="gm_check", description="Призвать игроков пройти проверку (заявка от Мастера)"),
            BotCommand(command="meme", description="Найти DnD мем по ключевым словам или получить случайный"),
            BotCommand(command="stop", description="Скрыть игровую Reply-клавиатуру и приостановить сессию")
        ]
        await bot.set_my_commands(commands=bot_commands)
        logger.info("Меню команд бота успешно зарегистрировано в Telegram.")
    except Exception as e:
        logger.warning(f"Не удалось установить описание или команды бота в Telegram: {e}")
    
    # Инициализация диспетчера с хранилищем состояний в памяти (MemoryStorage).
    # При сверхвысоких нагрузках на несколько серверов MemoryStorage заменяется на RedisStorage.
    dp = Dispatcher(storage=MemoryStorage())

    # Подключение Throttling (Rate Limiting) Middleware для защиты от спама
    throttling_middleware = ThrottlingMiddleware()
    dp.message.outer_middleware(throttling_middleware)
    dp.callback_query.outer_middleware(throttling_middleware)

    # Регистрация всех обработчиков (роутеров)
    register_all_routers(dp)

    # Инициализация базы данных SQLite
    from services.db import DatabaseService
    await DatabaseService.init_db()
    logger.info("База данных SQLite успешно инициализирована.")

    logger.info("Запуск бота в режиме Long Polling...")
    
    try:
        # Пропускаем накопившиеся обновления перед стартом, чтобы бот не отвечал на старые сообщения
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    except Exception as e:
        logger.exception(f"Произошла ошибка во время работы бота: {e}")
    finally:
        # Корректное закрытие сессии бота
        await bot.session.close()
        logger.info("Бот успешно остановлен.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот принудительно остановлен пользователем.")
