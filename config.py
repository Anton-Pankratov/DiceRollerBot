import os
from pathlib import Path
from dotenv import load_dotenv

# Определяем базовую директорию проекта для поиска файла .env
BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"

# Загружаем переменные окружения
if ENV_PATH.exists():
    load_dotenv(dotenv_path=ENV_PATH)
else:
    load_dotenv()

# Настройки бота
BOT_TOKEN = os.getenv("BOT_TOKEN")
THROTTLING_RATE = float(os.getenv("THROTTLING_RATE", "1.0"))
DB_SALT = os.getenv("DB_SALT", "default_dice_roller_salt_value")

# Валидация критических настроек
if not BOT_TOKEN or BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN_HERE":
    # Для демонстрационных целей или локальных тестов не кидаем критическое исключение сразу при импорте,
    # но предупреждаем пользователя при запуске
    pass

# Анимированные/статические стикеры бросков дайсов в стиле Telegram.
# Добавьте File ID из вашего Telegram стикер-пака в файл .env или оставьте пустыми для отключения.
DICE_STICKERS = {
    4: os.getenv("STICKER_D4", ""),
    6: os.getenv("STICKER_D6", ""),
    8: os.getenv("STICKER_D8", ""),
    10: os.getenv("STICKER_D10", ""),
    12: os.getenv("STICKER_D12", ""),
    20: os.getenv("STICKER_D20", ""),
    100: os.getenv("STICKER_D100", "")
}

# Маппинг конкретных результатов бросков на стикеры (например, чтобы d20 при выпадении 20 падал на грань 20).
# Поддерживает d6 (1-6) и d20 (1-20). Прописывается в .env в формате STICKER_D20_20=...
DICE_RESULT_STICKERS = {
    6: {i: os.getenv(f"STICKER_D6_{i}", "") for i in range(1, 7)},
    20: {i: os.getenv(f"STICKER_D20_{i}", "") for i in range(1, 21)}
}
