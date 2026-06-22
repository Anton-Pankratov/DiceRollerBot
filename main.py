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
            BotCommand(command="webapp", description="Открыть интерактивный Mini App для листов персонажей"),
            BotCommand(command="roll", description="Сделать быстрый бросок кубиков (например: /roll 2d6)"),
            BotCommand(command="gm_check", description="Призвать игроков пройти проверку (заявка от Мастера)"),
            BotCommand(command="meme", description="Найти DnD мем по ключевым словам или получить случайный"),
            BotCommand(command="stop", description="Скрыть игровую Reply-клавиатуру и приостановить сессию")
        ]
        await bot.set_my_commands(commands=bot_commands)
        logger.info("Меню команд бота успешно зарегистрировано в Telegram.")

        # Настройка Menu Button для WebApp
        if config.WEBAPP_URL.startswith("https://"):
            from aiogram.types import MenuButtonWebApp, WebAppInfo
            await bot.set_chat_menu_button(
                menu_button=MenuButtonWebApp(
                    text="🎲 Лист героя",
                    web_app=WebAppInfo(url=config.WEBAPP_URL)
                )
            )
            logger.info("Menu Button для WebApp успешно настроен.")
        else:
            logger.warning(
                "Кнопка меню WebApp не была настроена, так как Telegram требует HTTPS ссылку. "
                "Пропишите HTTPS-адрес (например, от ngrok) в WEBAPP_URL в файле .env."
            )
    except Exception as e:
        logger.warning(f"Не удалось установить описание или команды бота в Telegram: {e}")
    
    # Инициализация диспетчера с хранилищем состояний в памяти (MemoryStorage).
    # При сверхвысоких нагрузках на несколько серверов MemoryStorage заменяется на RedisStorage.
    dp = Dispatcher(storage=MemoryStorage())

    @dp.update.outer_middleware()
    async def log_updates(handler, event, data):
        logger.info(f"!!! RECEIVED UPDATE: {event}")
        
        # Автоматическое сохранение чатов и тем при любой активности
        try:
            message = None
            if event.message:
                message = event.message
            elif event.edited_message:
                message = event.edited_message
            elif event.callback_query and event.callback_query.message:
                message = event.callback_query.message
                
            if message and message.chat and message.chat.type in ["group", "supergroup"]:
                chat_id = message.chat.id
                thread_id = message.message_thread_id
                chat_title = message.chat.title or "Групповой чат"
                from services.db import DatabaseService, _hash_thread_id
                await DatabaseService.save_chat_topic(chat_id, None, chat_title)
                if thread_id is not None:
                    topics = await DatabaseService.get_chat_topics(chat_id)
                    hashed_thread = _hash_thread_id(thread_id)
                    if not any(t["thread_id"] == hashed_thread for t in topics):
                        await DatabaseService.save_chat_topic(chat_id, thread_id, f"Тема №{thread_id}")
        except Exception as e:
            logger.warning(f"Ошибка при автоматическом сохранении чата/темы в middleware: {e}")

        try:
            return await handler(event, data)
        except Exception as e:
            logger.exception(f"!!! ERROR DURING UPDATE HANDLING: {e}")
            raise

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

    # Запуск WebApp сервера
    from services.webapp_server import start_webapp_server
    webapp_runner = await start_webapp_server(bot)

    logger.info(f"Запуск бота в режиме Long Polling (Окружение: {config.BOT_MODE.upper()})...")
    
    try:
        # Пропускаем накопившиеся обновления перед стартом, чтобы бот не отвечал на старые сообщения
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    except Exception as e:
        logger.exception(f"Произошла ошибка во время работы бота: {e}")
    finally:
        # Корректное закрытие сессии WebApp
        if 'webapp_runner' in locals() and webapp_runner:
            await webapp_runner.cleanup()
            logger.info("Сервер WebApp успешно остановлен.")
        # Корректное закрытие сессии бота
        await bot.session.close()
        logger.info("Бот успешно остановлен.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот принудительно остановлен пользователем.")
