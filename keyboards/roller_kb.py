from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from typing import Union

def get_dice_keyboard(mode: str = "normal", is_persistent: bool = False) -> ReplyKeyboardMarkup:
    """
    Создает выдвигаемую (Reply) клавиатуру с кнопками быстрого броска дайсов,
    выбором режима броска (Преимущество / Помеха) и кнопками управления.
    """
    builder = ReplyKeyboardBuilder()
    
    # Все стандартные дайсы на первой строке
    standard_dices = [4, 6, 8, 10, 12, 20, 100]
    dice_buttons = [KeyboardButton(text=f"🎲 d{sides}") for sides in standard_dices]
    builder.row(*dice_buttons)
    
    # Кнопки выбора режима броска на второй строке (с отметкой активного)
    adv_label = "🟢 Преимущество"
    norm_label = "⚪️ Обычный"
    dis_label = "🔴 Помеха"
    
    if mode == "advantage":
        adv_label = "🟢 Преимущество ✅"
    elif mode == "disadvantage":
        dis_label = "🔴 Помеха ✅"
    else:
        norm_label = "⚪️ Обычный ✅"
        
    builder.row(
        KeyboardButton(text=adv_label),
        KeyboardButton(text=norm_label),
        KeyboardButton(text=dis_label)
    )
    
    # Кнопка персонажей, кастомного ввода и справки на третьей строке
    import config
    from aiogram.types import WebAppInfo
    builder.row(
        KeyboardButton(text="👥 Персонажи"),
        KeyboardButton(text="🌐 Лист героя (App)", web_app=WebAppInfo(url=config.WEBAPP_URL)),
        KeyboardButton(text="✍️ Кастомный дайс"),
        KeyboardButton(text="ℹ️ Справка")
    )
    
    return builder.as_markup(
        resize_keyboard=True,
        is_persistent=is_persistent,
        selective=True,
        input_field_placeholder="Выберите кубик или режим броска..."
    )

async def get_dice_keyboard_for_user(user_id: int, mode: str = "normal") -> Union[ReplyKeyboardMarkup, ReplyKeyboardRemove]:
    """Асинхронный хелпер для загрузки настройки пользователя и генерации клавиатуры."""
    from services.db import DatabaseService
    mode_val = await DatabaseService.get_keyboard_mode(user_id)
    if mode_val == 2:
        return ReplyKeyboardRemove(selective=True)
    is_pers = (mode_val == 1)
    return get_dice_keyboard(mode, is_persistent=is_pers)
