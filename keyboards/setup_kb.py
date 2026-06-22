from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from typing import List, Dict

# Списки всех доступных вариантов для создания персонажа
ALL_SAVING_THROWS = [
    "Сила", "Ловкость", "Телосложение", 
    "Интеллект", "Мудрость", "Харизма"
]

ALL_SKILLS = [
    "Атлетика", "Акробатика", "Ловкость рук", "Скрытность",
    "Анализ", "История", "Магия", "Природа", "Религия",
    "Уход за животными", "Внимательность", "Проницательность", "Медицина", "Выживание",
    "Обман", "Запугивание", "Выступление", "Убеждение"
]

ALL_TOOLS = [
    # Основные инструменты и наборы
    "Воровские инструменты", "Инструменты навигатора", "Инструменты отравителя",
    "Набор травника", "Набор для грима", "Набор для фальсификации",
    
    # Транспорт
    "Сухопутный транспорт", "Водный транспорт",
    
    # Игровые наборы
    "Игровой набор: Драконьи шахматы", "Игровой набор: Карты", 
    "Игровой набор: Кости", "Игровой набор: Ставка трёх драконов",
    
    # Музыкальные инструменты
    "Музыкальный инструмент: Барабан", "Музыкальный инструмент: Виола", 
    "Музыкальный инструмент: Волынка", "Музыкальный инструмент: Лира", 
    "Музыкальный инструмент: Лютня", "Музыкальный инструмент: Рожок", 
    "Музыкальный инструмент: Свирель", "Музыкальный инструмент: Флейта", 
    "Музыкальный инструмент: Цимбалы", "Музыкальный инструмент: Шалмей",
    
    # Инструменты ремесленников
    "Инструменты алхимика", "Инструменты пивовара", "Инструменты каллиграфа",
    "Инструменты плотника", "Инструменты картографа", "Инструменты сапожника",
    "Инструменты повара", "Инструменты стеклодува", "Инструменты ювелира",
    "Инструменты кожевника", "Инструменты каменщика", "Инструменты художника",
    "Инструменты гончара", "Инструменты резчика по дереву", "Инструменты кузнеца",
    "Инструменты ткача", "Инструменты ремонтника"
]

def get_saving_throws_keyboard(selected: List[str]) -> InlineKeyboardMarkup:
    """Генерирует клавиатуру со спасбросками (отмеченными галочками ✅)."""
    builder = InlineKeyboardBuilder()
    
    for item in ALL_SAVING_THROWS:
        status = "✅" if item in selected else "❌"
        builder.add(
            InlineKeyboardButton(
                text=f"{status} {item}",
                callback_data=f"toggle_save:{item}"
            )
        )
        
    builder.adjust(2)  # Размещаем по 2 в ряд
    
    # Кнопка завершения
    builder.row(
        InlineKeyboardButton(
            text="Сохранить и продолжить ➡️",
            callback_data="done_save"
        )
    )
    return builder.as_markup()

def get_skills_keyboard(selected: List[str]) -> InlineKeyboardMarkup:
    """Генерирует клавиатуру с навыками (отмеченными галочками ✅)."""
    builder = InlineKeyboardBuilder()
    
    for item in ALL_SKILLS:
        status = "✅" if item in selected else "❌"
        builder.add(
            InlineKeyboardButton(
                text=f"{status} {item}",
                callback_data=f"toggle_skill:{item}"
            )
        )
        
    builder.adjust(2)  # Размещаем по 2 в ряд
    
    # Кнопка завершения
    builder.row(
        InlineKeyboardButton(
            text="Сохранить и продолжить ➡️",
            callback_data="done_skills"
        )
    )
    return builder.as_markup()

def get_tools_keyboard(selected: List[str]) -> InlineKeyboardMarkup:
    """Генерирует клавиатуру со всеми инструментами, игровыми наборами, музыкой и транспортом."""
    builder = InlineKeyboardBuilder()
    
    for idx, item in enumerate(ALL_TOOLS):
        status = "✅" if item in selected else "❌"
        # Сократим визуальный префикс для кнопок, чтобы они влезали в 2 колонки
        btn_text = item.replace("Музыкальный инструмент: ", "🎵 ").replace("Игровой набор: ", "🎲 ")
        builder.add(
            InlineKeyboardButton(
                text=f"{status} {btn_text}",
                callback_data=f"toggle_tool:{idx}"  # Используем индекс во избежание лимита 64 байт Telegram
            )
        )
        
    builder.adjust(2)  # Размещаем по 2 в ряд
    
    # Кнопка завершения
    builder.row(
        InlineKeyboardButton(
            text="Сохранить и продолжить ➡️",
            callback_data="done_tools"
        )
    )
    return builder.as_markup()

def get_expertise_keyboard(skills: List[str], tools: List[str], selected_exp: List[str]) -> InlineKeyboardMarkup:
    """Генерирует клавиатуру для выбора компетентности (Expertise) из владений."""
    builder = InlineKeyboardBuilder()
    
    # Добавляем навыки
    for skill in skills:
        if skill in ALL_SKILLS:
            idx = ALL_SKILLS.index(skill)
            status = "✅" if skill in selected_exp else "❌"
            builder.add(
                InlineKeyboardButton(
                    text=f"{status} 📜 {skill}",
                    callback_data=f"toggle_exp:s:{idx}"
                )
            )
            
    # Добавляем инструменты
    for tool in tools:
        if tool in ALL_TOOLS:
            idx = ALL_TOOLS.index(tool)
            status = "✅" if tool in selected_exp else "❌"
            btn_text = tool.replace("Музыкальный инструмент: ", "🎵 ").replace("Игровой набор: ", "🎲 ")
            builder.add(
                InlineKeyboardButton(
                    text=f"{status} 🛠️ {btn_text}",
                    callback_data=f"toggle_exp:t:{idx}"
                )
            )
            
    builder.adjust(2)
    
    builder.row(
        InlineKeyboardButton(
            text="Завершить создание персонажа 🎓",
            callback_data="done_expertise"
        )
    )
    return builder.as_markup()

def get_minimum_rolls_keyboard(skills: List[str], min_rolls: Dict[str, int]) -> InlineKeyboardMarkup:
    """Генерирует клавиатуру для выбора минимального значения на кубе d20 для навыков."""
    builder = InlineKeyboardBuilder()
    
    for skill in skills:
        if skill in ALL_SKILLS:
            idx = ALL_SKILLS.index(skill)
            val = min_rolls.get(skill, 0)
            status_text = f"Минимум: {val}" if val > 0 else "Нет"
            builder.add(
                InlineKeyboardButton(
                    text=f"📜 {skill} ({status_text})",
                    callback_data=f"cycle_min:{idx}"
                )
            )
            
    builder.adjust(1) # По 1 навыку в строке
    
    builder.row(
        InlineKeyboardButton(
            text="Сохранить и продолжить ➡️",
            callback_data="done_min_rolls"
        )
    )
    return builder.as_markup()

def get_classes_keyboard() -> InlineKeyboardMarkup:
    """Генерирует клавиатуру со списком 12 базовых классов D&D 2014."""
    builder = InlineKeyboardBuilder()
    classes = [
        ("⚔️ Воин", "Воин"), ("🛡️ Жрец", "Жрец"),
        ("🪄 Волшебник", "Волшебник"), ("🗡️ Плут", "Плут"),
        ("🌲 Друид", "Друид"), ("🎵 Бард", "Бард"),
        ("🩸 Варвар", "Варвар"), ("🥋 Монах", "Монах"),
        ("☀️ Паладин", "Паладин"), ("🏹 Следопыт", "Следопыт"),
        ("🔮 Колдун", "Колдун"), ("✨ Чародей", "Чародей")
    ]
    
    for label, callback_val in classes:
        builder.add(
            InlineKeyboardButton(
                text=label,
                callback_data=f"select_class:{callback_val}"
            )
        )
    builder.adjust(2)  # По 2 класса в строке
    builder.row(
        InlineKeyboardButton(text="✍️ Свой класс (ввести вручную)", callback_data="select_class_custom")
    )
    return builder.as_markup()

def get_review_keyboard() -> InlineKeyboardMarkup:
    """Создает клавиатуру подтверждения/правки для экрана обзора."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Подтвердить данные", callback_data="review_confirm"),
        InlineKeyboardButton(text="✏️ Нужны правки", callback_data="review_edit")
    )
    return builder.as_markup()

def get_edit_menu_keyboard() -> InlineKeyboardMarkup:
    """Создает меню выбора полей для редактирования."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="👤 Имя", callback_data="edit_field:name"),
        InlineKeyboardButton(text="🛡️ Класс", callback_data="edit_field:class"),
        InlineKeyboardButton(text="🎓 Бонус мастерства", callback_data="edit_field:pb")
    )
    builder.row(
        InlineKeyboardButton(text="⚔️ Характеристики", callback_data="edit_field:stats"),
        InlineKeyboardButton(text="🛡️ Спасброски", callback_data="edit_field:saves")
    )
    builder.row(
        InlineKeyboardButton(text="📜 Навыки", callback_data="edit_field:skills"),
        InlineKeyboardButton(text="🛠️ Инструменты", callback_data="edit_field:tools"),
        InlineKeyboardButton(text="🎓 Компетентность", callback_data="edit_field:expertise")
    )
    builder.row(
        InlineKeyboardButton(text="🎲 Минимальный куб", callback_data="edit_field:min_rolls")
    )
    builder.row(
        InlineKeyboardButton(text="⬅️ Назад к обзору", callback_data="edit_back_to_review")
    )
    return builder.as_markup()

def get_characters_management_keyboard(characters: List[dict], bound_char_name = None) -> InlineKeyboardMarkup:
    """Генерирует клавиатуру управления персонажами с подсветкой привязанного к текущему чату/теме."""
    builder = InlineKeyboardBuilder()
    
    bound_set = set()
    if bound_char_name:
        if isinstance(bound_char_name, str):
            bound_set.add(bound_char_name.lower())
        else:
            try:
                bound_set = {name.lower() for name in bound_char_name}
            except Exception:
                bound_set.add(str(bound_char_name).lower())
            
    # Список персонажей пользователя
    for char in characters:
        status = "👤"
        if char['name'].lower() in bound_set:
            status = "⚔️ [ПРИВЯЗАН]"
        elif char.get("is_active") == 1:
            status = "✨"
            
        builder.add(
            InlineKeyboardButton(
                text=f"{status} {char['name']}",
                callback_data=f"select_char:{char['name']}"
            )
        )
    builder.adjust(1)  # Персонажи в один столбик
    
    # Кнопки действий
    builder.row(
        InlineKeyboardButton(text="➕ Создать нового", callback_data="create_new_char")
    )
    builder.row(
        InlineKeyboardButton(text="📋 Карточка", callback_data="show_active_char_card"),
        InlineKeyboardButton(text="✏️ Редактировать", callback_data="edit_active_char")
    )
    builder.row(
        InlineKeyboardButton(text="🧪 Формулы", callback_data="active_char_formulas"),
        InlineKeyboardButton(text="❌ Удалить", callback_data="delete_char_menu")
    )
    builder.row(
        InlineKeyboardButton(text="🔗 Управление привязками", callback_data="manage_bindings_menu")
    )
    return builder.as_markup()

def get_character_card_keyboard() -> InlineKeyboardMarkup:
    """Генерирует клавиатуру для просмотра карточки персонажа."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="⬅️ Назад к списку", callback_data="back_to_chars_list")
    )
    return builder.as_markup()


def get_characters_delete_keyboard(characters: List[dict]) -> InlineKeyboardMarkup:
    """Генерирует клавиатуру для удаления персонажей."""
    builder = InlineKeyboardBuilder()
    
    for char in characters:
        builder.add(
            InlineKeyboardButton(
                text=f"🗑️ {char['name']}",
                callback_data=f"delete_char_select:{char['name']}"
            )
        )
    builder.adjust(1)
    
    # Кнопка назад
    builder.row(
        InlineKeyboardButton(text="⬅️ Назад", callback_data="delete_char_back")
    )
    return builder.as_markup()

def get_delete_confirm_keyboard(char_name: str) -> InlineKeyboardMarkup:
    """Генерирует клавиатуру подтверждения удаления."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🗑️ Да, удалить", callback_data=f"delete_char_confirm:{char_name}"),
        InlineKeyboardButton(text="❌ Отмена", callback_data="delete_char_cancel")
    )
    return builder.as_markup()

def get_formulas_keyboard(formulas: dict) -> InlineKeyboardMarkup:
    """Генерирует клавиатуру со списком кастомных формул активного персонажа."""
    builder = InlineKeyboardBuilder()
    
    # Каждая формула — кнопка быстрого броска
    for name, expr in formulas.items():
        builder.add(
            InlineKeyboardButton(
                text=f"🧪 {name} ({expr})",
                callback_data=f"roll_formula:{name}"
            )
        )
    builder.adjust(1)
    
    # Действия
    builder.row(
        InlineKeyboardButton(text="➕ Добавить формулу", callback_data="formula_add")
    )
    builder.row(
        InlineKeyboardButton(text="🗑️ Удалить формулу", callback_data="formula_delete_menu"),
        InlineKeyboardButton(text="⬅️ Назад", callback_data="formula_back_to_char_menu")
    )
    return builder.as_markup()

def get_formulas_delete_keyboard(formulas: dict) -> InlineKeyboardMarkup:
    """Генерирует клавиатуру со списком формул для удаления."""
    builder = InlineKeyboardBuilder()
    
    for name, expr in formulas.items():
        builder.add(
            InlineKeyboardButton(
                text=f"🗑️ Удалить: {name} ({expr})",
                callback_data=f"formula_delete_select:{name}"
            )
        )
    builder.adjust(1)
    
    builder.row(
        InlineKeyboardButton(text="⬅️ Назад", callback_data="formula_delete_cancel")
    )
    return builder.as_markup()

def get_chat_topics_keyboard(topics: List[dict], show_back: bool = True) -> InlineKeyboardMarkup:
    """Генерирует клавиатуру со списком разделов (тем) чата для инлайн-привязки."""
    builder = InlineKeyboardBuilder()
    
    for topic in topics:
        # thread_id в БД является хэшем (SHA-256). Так как лимит callback_data составляет 64 байта,
        # мы передаем только первые 8 символов хэша.
        short_hash = topic['thread_id'][:8]
        builder.add(
            InlineKeyboardButton(
                text=f"💬 {topic['name']}",
                callback_data=f"select_topic_bind:{short_hash}"
            )
        )
    builder.adjust(1)
    
    # Добавляем привязку к общему чату
    builder.row(
        InlineKeyboardButton(
            text="🌐 Общий раздел / Вся группа",
            callback_data="select_topic_bind:None"
        )
    )
    
    if show_back:
        builder.row(
            InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data="bind_menu"
            )
        )
    return builder.as_markup()

def get_bind_options_keyboard(chat_type: str) -> InlineKeyboardMarkup:
    """Генерирует клавиатуру с опциями привязки (Тема или Еще один чат)."""
    builder = InlineKeyboardBuilder()
    
    if chat_type != "private":
        builder.row(
            InlineKeyboardButton(text="💬 Тема", callback_data="bind_current_chat_topics")
        )
        
    builder.row(
        InlineKeyboardButton(text="🔗 Еще один чат", callback_data="bind_by_link")
    )
    
    builder.row(
        InlineKeyboardButton(text="⬅️ Назад", callback_data="manage_bindings_menu")
    )
    
    return builder.as_markup()

def get_bindings_management_keyboard(bindings: List[dict]) -> InlineKeyboardMarkup:
    """Генерирует клавиатуру управления привязками персонажа."""
    builder = InlineKeyboardBuilder()
    
    # Кнопки для отвязки
    for b in bindings:
        name = b.get("topic_name") or f"Чат {b['chat_id'][:8]}"
        chat_prefix = b['chat_id'][:8]
        thread_prefix = b['thread_id'][:8]
        builder.row(
            InlineKeyboardButton(
                text=f"❌ Отвязать: {name}",
                callback_data=f"unbind:{chat_prefix}:{thread_prefix}"
            )
        )
        
    # Кнопка перехода к выбору привязки
    builder.row(
        InlineKeyboardButton(text="➕ Привязать", callback_data="bind_menu")
    )
    
    builder.row(
        InlineKeyboardButton(text="⬅️ Назад к персонажам", callback_data="back_to_chars")
    )
    
    return builder.as_markup()


def get_chats_keyboard(user_chats: List[dict]) -> InlineKeyboardMarkup:
    """Генерирует клавиатуру со списком доступных чатов для привязки."""
    builder = InlineKeyboardBuilder()
    
    for chat in user_chats:
        chat_prefix = chat["chat_id"][:8]
        builder.row(
            InlineKeyboardButton(
                text=f"💬 {chat['name']}",
                callback_data=f"bind_chat_select:{chat_prefix}"
            )
        )
        
    builder.row(
        InlineKeyboardButton(
            text="🔗 Привязать по ссылке/ID",
            callback_data="bind_by_link"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="⬅️ Назад",
            callback_data="manage_bindings_menu"
        )
    )
    return builder.as_markup()


def get_multi_topic_selection_keyboard(
    topics: List[dict],
    selected_topic_hashes: List[str],
    chat_prefix: str
) -> InlineKeyboardMarkup:
    """Генерирует клавиатуру для множественного выбора тем с чекбоксами."""
    builder = InlineKeyboardBuilder()
    
    for topic in topics:
        thread_hash = topic["thread_id"]
        short_hash = thread_hash[:8]
        
        is_selected = thread_hash in selected_topic_hashes
        check_symbol = "✅" if is_selected else "◻️"
        
        from services.db import _hash_thread_id
        is_general = thread_hash == _hash_thread_id(None)
        display_name = "🌐 Общий раздел / Вся группа" if is_general else f"💬 {topic['name']}"
        
        builder.row(
            InlineKeyboardButton(
                text=f"{check_symbol} {display_name}",
                callback_data=f"bind_topic_toggle:{chat_prefix}:{short_hash}"
            )
        )
        
    builder.row(
        InlineKeyboardButton(
            text="✅ Готово",
            callback_data=f"bind_topics_done:{chat_prefix}"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="⬅️ Назад",
            callback_data="bind_menu"
        )
    )
    return builder.as_markup()


