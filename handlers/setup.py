import re
import json
import uuid
import asyncio
import contextvars
from typing import Optional, List, Dict, Any
from aiogram import Router, F, Bot, BaseMiddleware
from aiogram.client.session.middlewares.base import BaseRequestMiddleware
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from services.db import DatabaseService, _hash_thread_id, _hash_chat_id
from keyboards.setup_kb import (
    get_saving_throws_keyboard,
    get_skills_keyboard,
    get_tools_keyboard,
    get_expertise_keyboard,
    get_review_keyboard,
    get_edit_menu_keyboard,
    get_characters_management_keyboard,
    get_characters_delete_keyboard,
    get_delete_confirm_keyboard,
    get_classes_keyboard,
    get_formulas_keyboard,
    get_formulas_delete_keyboard,
    get_chat_topics_keyboard,
    get_bindings_management_keyboard,
    get_bind_options_keyboard,
    get_character_card_keyboard,
    ALL_TOOLS,
    ALL_SKILLS
)
from keyboards.roller_kb import get_dice_keyboard, get_dice_keyboard_for_user

router = Router(name="setup")

class CharacterSetupStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_class = State()       # Шаг выбора класса
    waiting_for_pb = State()          # Proficiency bonus (Бонус мастерства)
    waiting_for_strength = State()
    waiting_for_dexterity = State()
    waiting_for_constitution = State() # Телосложение
    waiting_for_intelligence = State()
    waiting_for_wisdom = State()
    waiting_for_charisma = State()
    selecting_saving_throws = State()
    selecting_skills = State()
    selecting_tools = State()
    selecting_expertise = State()     # Выбор компетентности (навыки/инструменты)
    reviewing_data = State()          # Просмотр и подтверждение данных
    editing_menu = State()            # Выбор поля для изменения
    adding_custom_formula_name = State() # Шаг добавления названия формулы
    adding_custom_formula_expr = State() # Шаг добавления самой формулы
    waiting_for_binding_link = State()   # Шаг ожидания ссылки или ID для привязки персонажа

CREATION_STATES = {
    CharacterSetupStates.waiting_for_name.state,
    CharacterSetupStates.waiting_for_class.state,
    CharacterSetupStates.waiting_for_pb.state,
    CharacterSetupStates.waiting_for_strength.state,
    CharacterSetupStates.waiting_for_dexterity.state,
    CharacterSetupStates.waiting_for_constitution.state,
    CharacterSetupStates.waiting_for_intelligence.state,
    CharacterSetupStates.waiting_for_wisdom.state,
    CharacterSetupStates.waiting_for_charisma.state,
    CharacterSetupStates.selecting_saving_throws.state,
    CharacterSetupStates.selecting_skills.state,
    CharacterSetupStates.selecting_tools.state,
    CharacterSetupStates.selecting_expertise.state,
    CharacterSetupStates.reviewing_data.state,
}

def get_user_mention(user) -> str:
    if user.username:
        return f"@{user.username}"
    return user.mention_html(user.first_name)

creation_context = contextvars.ContextVar("creation_context", default=None)

class CreationPrefixRequestMiddleware(BaseRequestMiddleware):
    async def __call__(
        self,
        make_request,
        bot,
        method
    ):
        ctx = creation_context.get()
        if ctx:
            mention, chat_type = ctx
            
            async def get_hint():
                try:
                    bot_user = await bot.get_me()
                    username = bot_user.username
                except Exception:
                    username = None
                if username:
                    return f"\n\n💬 <i>Отвечайте (reply) на это сообщение или упоминайте @{username}, чтобы продолжить.</i>"
                return f"\n\n💬 <i>Отвечайте (reply) на это сообщение, чтобы продолжить.</i>"

            from aiogram.methods import SendMessage, EditMessageText
            if isinstance(method, SendMessage):
                hint = await get_hint()
                method.text = f"👤 Игрок: {mention}\n\n{method.text}{hint}"
            elif isinstance(method, EditMessageText):
                hint = await get_hint()
                method.text = f"👤 Игрок: {mention}\n\n{method.text}{hint}"
                
        return await make_request(bot, method)

class SetupMessageMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler,
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        state: FSMContext = data.get("state")
        current_state = await state.get_state() if state else None
        
        is_starting = False
        if event.text:
            text_lower = event.text.lower()
            is_starting = "/create_character" in text_lower
            
        is_in_creation = current_state in CREATION_STATES or is_starting
        
        if is_in_creation and event.chat.type != "private":
            if event.text:
                bot: Bot = data.get("bot") or event.bot
                try:
                    bot_user = await bot.get_me()
                    username = bot_user.username
                    if username:
                        mention = f"@{username}"
                        if mention.lower() in event.text.lower():
                            import re
                            cleaned_text = re.sub(rf"(?i)\s*{re.escape(mention)}\s*", " ", event.text).strip()
                            event.text = cleaned_text
                except Exception:
                    pass

            mention = get_user_mention(event.from_user)
            token = creation_context.set((mention, event.chat.type))
            try:
                return await handler(event, data)
            finally:
                creation_context.reset(token)
                
        return await handler(event, data)

class SetupCallbackMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler,
        event: CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        state: FSMContext = data.get("state")
        current_state = await state.get_state() if state else None
        
        is_starting = event.data in ["create_new_char", "continue_creation", "reset_creation"]
        is_in_creation = current_state in CREATION_STATES or is_starting
        
        if is_in_creation and event.message and event.message.chat.type != "private":
            mention = get_user_mention(event.from_user)
            token = creation_context.set((mention, event.message.chat.type))
            try:
                return await handler(event, data)
            finally:
                creation_context.reset(token)
                
        return await handler(event, data)

router.message.outer_middleware(SetupMessageMiddleware())
router.callback_query.outer_middleware(SetupCallbackMiddleware())


async def delete_previous_messages(message: Message, state: FSMContext):
    """Удаляет входящее сообщение пользователя и предыдущее сообщение бота, если его ID сохранен."""
    try:
        await message.delete()
    except Exception:
        pass
        
    data = await state.get_data()
    last_bot_msg_id = data.get("last_bot_msg_id")
    if last_bot_msg_id:
        try:
            await message.bot.delete_message(chat_id=message.chat.id, message_id=last_bot_msg_id)
        except Exception:
            pass

async def send_reminder_after_delay(bot: Bot, chat_id: int, user_id: int, state: FSMContext, session_id: str, delay: int = 300):
    """Фоновая задача, отправляющая напоминание, если создание персонажа не завершено."""
    await asyncio.sleep(delay)
    current_state = await state.get_state()
    if current_state in CREATION_STATES:
        data = await state.get_data()
        if data.get("creation_session_id") == session_id:
            try:
                await bot.send_message(
                    chat_id=chat_id,
                    text="🔔 <b>Напоминание:</b> Вы начали создание персонажа, но не закончили его.\n\n"
                         "Пожалуйста, завершите процесс создания (команда /create_character), чтобы иметь возможность совершать D&D проверки!"
                )
            except Exception:
                pass

async def prompt_for_creation_state(chat_id: int, bot: Bot, state: FSMContext, state_name: str):
    """Генерирует и отправляет сообщение-подсказку для продолжения создания на текущем шаге."""
    data = await state.get_data()
    
    if state_name == CharacterSetupStates.waiting_for_name.state:
        sent_msg = await bot.send_message(
            chat_id=chat_id,
            text="🧙‍♂️ <b>Мастер создания персонажа</b>\n\n"
                 "Шаг 1: <b>Введите имя вашего нового персонажа</b>:",
            reply_markup=ReplyKeyboardRemove(selective=True)
        )
    elif state_name == CharacterSetupStates.waiting_for_class.state:
        sent_msg = await bot.send_message(
            chat_id=chat_id,
            text="Шаг 2: <b>Выберите класс вашего персонажа</b> или введите его вручную в чат:",
            reply_markup=get_classes_keyboard()
        )
    elif state_name == CharacterSetupStates.waiting_for_pb.state:
        sent_msg = await bot.send_message(
            chat_id=chat_id,
            text="Шаг 3: <b>Введите бонус мастерства</b> своего персонажа (например: <code>+2</code>, <code>+3</code>, <code>2</code>):"
        )
    elif state_name == CharacterSetupStates.waiting_for_strength.state:
        sent_msg = await bot.send_message(
            chat_id=chat_id,
            text="Шаг 4: Введите модификатор <b>Силы</b> (например, +3, 0, -1):"
        )
    elif state_name == CharacterSetupStates.waiting_for_dexterity.state:
        sent_msg = await bot.send_message(
            chat_id=chat_id,
            text="Шаг 5: Введите модификатор <b>Ловкости</b>:"
        )
    elif state_name == CharacterSetupStates.waiting_for_constitution.state:
        sent_msg = await bot.send_message(
            chat_id=chat_id,
            text="Шаг 6: Введите модификатор <b>Телосложения</b>:"
        )
    elif state_name == CharacterSetupStates.waiting_for_intelligence.state:
        sent_msg = await bot.send_message(
            chat_id=chat_id,
            text="Шаг 7: Введите модификатор <b>Интеллекта</b>:"
        )
    elif state_name == CharacterSetupStates.waiting_for_wisdom.state:
        sent_msg = await bot.send_message(
            chat_id=chat_id,
            text="Шаг 8: Введите модификатор <b>Мудрости</b>:"
        )
    elif state_name == CharacterSetupStates.waiting_for_charisma.state:
        sent_msg = await bot.send_message(
            chat_id=chat_id,
            text="Шаг 9: Введите модификатор <b>Харизмы</b>:"
        )
    elif state_name == CharacterSetupStates.selecting_saving_throws.state:
        saves = data.get("saving_throws", [])
        sent_msg = await bot.send_message(
            chat_id=chat_id,
            text="Шаг 10: Отметьте <b>спасброски</b>, которыми владеет ваш персонаж (кликните для переключения ✅/❌):\n"
                 "<i>Когда закончите, нажмите кнопку внизу.</i>",
            reply_markup=get_saving_throws_keyboard(saves)
        )
    elif state_name == CharacterSetupStates.selecting_skills.state:
        skills = data.get("skills", [])
        sent_msg = await bot.send_message(
            chat_id=chat_id,
            text="Шаг 11: Отметьте <b>навыки</b>, которыми владеет ваш персонаж:\n"
                 "<i>Когда закончите, нажмите кнопку внизу.</i>",
            reply_markup=get_skills_keyboard(skills)
        )
    elif state_name == CharacterSetupStates.selecting_tools.state:
        tools = data.get("tools", [])
        sent_msg = await bot.send_message(
            chat_id=chat_id,
            text="Шаг 12: Отметьте <b>инструменты</b>, которыми владеет ваш персонаж:\n"
                 "<i>Когда закончите, нажмите кнопку внизу.</i>",
            reply_markup=get_tools_keyboard(tools)
        )
    elif state_name == CharacterSetupStates.selecting_expertise.state:
        skills = data.get("skills", [])
        tools = data.get("tools", [])
        expertise = data.get("expertise", [])
        sent_msg = await bot.send_message(
            chat_id=chat_id,
            text="Шаг 13: Выберите <b>навыки и инструменты</b>, в которых ваш персонаж имеет <b>компетентность</b>:\n"
                 "<i>Когда закончите, нажмите кнопку внизу.</i>",
            reply_markup=get_expertise_keyboard(skills, tools, expertise)
        )
    elif state_name == CharacterSetupStates.reviewing_data.state:
        sent_msg = await bot.send_message(
            chat_id=chat_id,
            text=_get_character_review_text(data),
            reply_markup=get_review_keyboard()
        )
    elif state_name == CharacterSetupStates.editing_menu.state:
        sent_msg = await bot.send_message(
            chat_id=chat_id,
            text="✏️ <b>Редактирование персонажа</b>\n\nВыберите, какой раздел вы хотите изменить:",
            reply_markup=get_edit_menu_keyboard()
        )
    else:
        sent_msg = await bot.send_message(
            chat_id=chat_id,
            text="🧙‍♂️ Нажмите /create_character чтобы начать создание персонажа."
        )
        
    await state.update_data(last_bot_msg_id=sent_msg.message_id)

async def check_incomplete_creation(chat_id: int, bot: Bot, state: FSMContext) -> bool:
    """Проверяет, есть ли незаконченное создание персонажа, и выводит предупреждение."""
    current_state = await state.get_state()
    fsm_data = await state.get_data()
    
    if fsm_data.get("is_new_creation") and current_state in CREATION_STATES:
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(text="➕ Продолжить создание", callback_data="continue_creation"),
            InlineKeyboardButton(text="🗑️ Сбросить и начать заново", callback_data="reset_creation")
        )
        
        sent_msg = await bot.send_message(
            chat_id=chat_id,
            text="⚠️ <b>У вас есть незавершенный процесс создания персонажа!</b>\n\n"
                 "Необходимо досоздать персонажа или сбросить прогресс и создать заново.",
            reply_markup=builder.as_markup()
        )
        await state.update_data(last_bot_msg_id=sent_msg.message_id)
        return True
    return False

@router.callback_query(F.data == "continue_creation")
async def handle_continue_creation(callback: CallbackQuery, state: FSMContext):
    """Callback-обработчик для продолжения создания с прерванного шага."""
    await callback.answer()
    try:
        await callback.message.delete()
    except Exception:
        pass
        
    await state.update_data(
        creator_mention=get_user_mention(callback.from_user),
        creation_chat_type=callback.message.chat.type
    )
    current_state = await state.get_state()
    await prompt_for_creation_state(callback.message.chat.id, callback.bot, state, current_state)

@router.callback_query(F.data == "reset_creation")
async def handle_reset_creation(callback: CallbackQuery, state: FSMContext):
    """Callback-обработчик для сброса создания персонажа и запуска заново."""
    await callback.answer("Прогресс сброшен")
    try:
        await callback.message.delete()
    except Exception:
        pass
        
    await state.clear()
    await state.set_state(CharacterSetupStates.waiting_for_name)
    
    session_id = str(uuid.uuid4())
    await state.update_data(
        is_new_creation=True,
        creation_session_id=session_id,
        creator_mention=get_user_mention(callback.from_user),
        creation_chat_type=callback.message.chat.type
    )
    
    sent_msg = await callback.message.answer(
        "🧙‍♂️ <b>Мастер создания персонажа</b>\n\n"
        "Давайте создадим вашего персонажа для игры в D&D!\n"
        "Шаг 1: <b>Введите имя вашего персонажа</b>:",
        reply_markup=ReplyKeyboardRemove(selective=True)
    )
    await state.update_data(last_bot_msg_id=sent_msg.message_id)
    
    # Запускаем фоновое напоминание
    asyncio.create_task(
        send_reminder_after_delay(
            callback.bot, callback.message.chat.id, callback.from_user.id, state, session_id
        )
    )

async def parse_telegram_link(text: str, bot: Bot) -> tuple[Optional[int], Optional[int], Optional[str]]:
    """
    Парсит ссылку на чат/тему Telegram или ID в формате chat_id:thread_id.
    Возвращает (chat_id, thread_id, error_message).
    """
    text = text.strip()
    
    # 1. Формат chat_id:thread_id или просто chat_id
    # e.g., -100123456789:105 или -100123456789
    match_ids = re.match(r"^([-+]?\d+)(?::(\d+))?$", text)
    if match_ids:
        chat_id = int(match_ids.group(1))
        thread_id = int(match_ids.group(2)) if match_ids.group(2) else None
        return chat_id, thread_id, None

    # 2. Ссылка закрытой группы/канала t.me/c/XXXXX/YYYYY
    # e.g. https://t.me/c/1234567890/105 или t.me/c/1234567890
    match_private = re.search(r"t\.me/c/(\d+)(?:/(\d+))?", text)
    if match_private:
        raw_chat_id = match_private.group(1)
        thread_id = int(match_private.group(2)) if match_private.group(2) else None
        # Для закрытых супергрупп/каналов в Telegram Bot API ID начинается с -100
        chat_id_str = raw_chat_id if raw_chat_id.startswith("-100") else f"-100{raw_chat_id}"
        return int(chat_id_str), thread_id, None

    # 3. Ссылка публичной группы/канала t.me/username/YYYYY
    # e.g. https://t.me/public_group/105
    match_public = re.search(r"t\.me/([a-zA-Z0-9_]+)(?:/(\d+))?", text)
    if match_public:
        username = match_public.group(1)
        thread_id = int(match_public.group(2)) if match_public.group(2) else None
        # Проверяем, что это не '/c/', который матчится в п.2
        if username.lower() != 'c':
            try:
                chat = await bot.get_chat(f"@{username}")
                return chat.id, thread_id, None
            except Exception as e:
                return None, None, f"Не удалось найти чат с юзернеймом @{username}: {str(e)}"

    return None, None, "Неизвестный формат ссылки. Убедитесь, что ссылка правильная (например, https://t.me/c/123456789/105)."

def parse_modifier(text: str) -> int:
    """Удаляет лишние пробелы и знак плюс, приводя ввод к числу."""
    cleaned = text.strip()
    if cleaned.startswith("+"):
        cleaned = cleaned[1:]
    return int(cleaned)

def _format_items_with_expertise(items: List[str], expertise: List[str]) -> str:
    if not items:
        return "нет"
    formatted = []
    for item in items:
        if item in expertise:
            formatted.append(f"{item} (компетентность)")
        else:
            formatted.append(item)
    return ", ".join(formatted)

def _get_character_review_text(data: dict) -> str:
    """Форматирует красивое резюме персонажа для экрана проверки."""
    saves_str = ", ".join(data.get("saving_throws", [])) if data.get("saving_throws") else "нет"
    
    expertise = data.get("expertise", [])
    skills_str = _format_items_with_expertise(data.get("skills", []), expertise)
    tools_str = _format_items_with_expertise(data.get("tools", []), expertise)
    
    format_mod = lambda v: f"+{v}" if v >= 0 else str(v)
    
    return (
        f"📝 <b>Проверка данных вашего персонажа</b>\n\n"
        f"Пожалуйста, убедитесь, что всё введено верно:\n\n"
        f"👤 <b>Имя:</b> {data.get('name', 'Не введено')}\n"
        f"🛡️ <b>Класс:</b> {data.get('char_class', 'Не выбран')}\n"
        f"🎓 <b>Бонус мастерства:</b> {format_mod(data.get('pb', 0))}\n\n"
        f"⚔️ <b>Характеристики:</b>\n"
        f"• Сила: <code>{format_mod(data.get('mod_strength', 0))}</code>\n"
        f"• Ловкость: <code>{format_mod(data.get('mod_dexterity', 0))}</code>\n"
        f"• Телосложение: <code>{format_mod(data.get('mod_constitution', 0))}</code>\n"
        f"• Интеллект: <code>{format_mod(data.get('mod_intelligence', 0))}</code>\n"
        f"• Мудрость: <code>{format_mod(data.get('mod_wisdom', 0))}</code>\n"
        f"• Харизма: <code>{format_mod(data.get('mod_charisma', 0))}</code>\n\n"
        f"🛡️ <b>Владение спасбросками:</b> {saves_str}\n"
        f"📜 <b>Владение навыками:</b> {skills_str}\n"
        f"🛠️ <b>Владение инструментами:</b> {tools_str}\n\n"
        f"<i>Вы можете подтвердить эти данные или изменить любой из разделов.</i>"
    )

def format_character_card(character: dict) -> str:
    """Форматирует красивую карточку персонажа (характеристики и владения) одним сообщением."""
    full_data = character.get("full_data", {})
    expertise = []
    if isinstance(full_data, dict):
        fd_skills = full_data.get("skills", {})
        if isinstance(fd_skills, dict):
            for k, v in fd_skills.items():
                if v == "expert":
                    expertise.append(k)
        fd_tools = full_data.get("tools", {})
        if isinstance(fd_tools, dict):
            for k, v in fd_tools.items():
                if v == "expert":
                    expertise.append(k)

    saves_str = ", ".join(character.get("saving_throws", [])) if character.get("saving_throws") else "нет"
    skills_str = _format_items_with_expertise(character.get("skills", []), expertise)
    tools_str = _format_items_with_expertise(character.get("tools", []), expertise)
    
    format_mod = lambda v: f"+{v}" if v >= 0 else str(v)
    
    # Имя и класс
    name = character.get("name", "Без имени")
    char_class = character.get("class", "Обычный бросок")
    pb = character.get("proficiency_bonus", 0)
    
    # Формулы кастомные
    formulas = character.get("custom_formulas", {})
    formulas_str = ""
    if formulas:
        formulas_list = [f"• <code>{k}</code>: {v}" for k, v in formulas.items()]
        formulas_str = "\n🧪 <b>Кастомные формулы:</b>\n" + "\n".join(formulas_list) + "\n"
        
    return (
        f"📋 <b>Лист персонажа: {name}</b>\n"
        f"🛡️ <b>Класс:</b> {char_class} | 🎓 <b>БМ:</b> {format_mod(pb)}\n\n"
        f"⚔️ <b>Характеристики D&D 5e:</b>\n"
        f"• Сила: <code>{format_mod(character.get('mod_strength', 0))}</code>\n"
        f"• Ловкость: <code>{format_mod(character.get('mod_dexterity', 0))}</code>\n"
        f"• Телосложение: <code>{format_mod(character.get('mod_constitution', 0))}</code>\n"
        f"• Интеллект: <code>{format_mod(character.get('mod_intelligence', 0))}</code>\n"
        f"• Мудрость: <code>{format_mod(character.get('mod_wisdom', 0))}</code>\n"
        f"• Харизма: <code>{format_mod(character.get('mod_charisma', 0))}</code>\n\n"
        f"🛡️ <b>Владение спасбросками:</b> {saves_str}\n"
        f"📜 <b>Владение навыками:</b> {skills_str}\n"
        f"🛠️ <b>Владение инструментами:</b> {tools_str}\n"
        f"{formulas_str}"
    )

@router.message(Command("sheet", "character", "my_character"))
async def cmd_show_sheet(message: Message, state: FSMContext):
    """Показывает карточку активного персонажа пользователя."""
    user_id = message.from_user.id
    chat_id = message.chat.id
    thread_id = message.message_thread_id
    
    character = await DatabaseService.get_bound_character(user_id, chat_id, thread_id)
    if not character:
        all_chars = await DatabaseService.get_all_characters(user_id)
        character = next((c for c in all_chars if c["is_active"] == 1), None)
        
    if not character:
        await message.reply(
            "⚠️ У вас нет активного персонажа. Создайте его с помощью /create_character или выберите в /characters."
        )
        return
        
    card_text = format_character_card(character)
    await message.reply(card_text)


# =====================================================================
# УПРАВЛЕНИЕ СПИСКОМ ПЕРСОНАЖЕЙ (ВЫБОР, СОЗДАНИЕ, УДАЛЕНИЕ, РЕДАКТИРОВАНИЕ)
# =====================================================================

@router.message(F.text == "👥 Персонажи")
@router.message(Command("characters"))
async def list_characters_menu(message: Message, state: FSMContext):
    """Выводит меню управления персонажами игрока."""
    await state.clear()
    user_id = message.from_user.id
    characters = await DatabaseService.get_all_characters(user_id)
    
    if not characters:
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text="➕ Создать первого персонажа", callback_data="create_new_char"))
        await message.answer(
            "👥 <b>У вас еще нет созданных персонажей!</b>\n\n"
            "Давайте создадим вашего первого героя для игры в D&D 5e.",
            reply_markup=builder.as_markup()
        )
        return
        
    active_char = next((c for c in characters if c.get("is_active") == 1), None)
    active_name = active_char["name"] if active_char else "не выбран"
    
    chat_id = message.chat.id
    thread_id = message.message_thread_id
    bound_names = await DatabaseService.get_user_bound_character_names(user_id, chat_id, thread_id)
    
    await message.answer(
        f"👥 <b>Ваши персонажи:</b>\n"
        f"Текущий активный персонаж: <b>{active_name}</b>\n\n"
        f"<i>Кликните на имя персонажа, чтобы сделать его активным для проверок.</i>",
        reply_markup=get_characters_management_keyboard(characters, bound_char_name=bound_names)
    )

@router.callback_query(F.data.startswith("select_char:"))
async def handle_select_character(callback: CallbackQuery, state: FSMContext):
    """Переключает активного персонажа пользователя."""
    char_name = callback.data.split(":", 1)[1]
    user_id = callback.from_user.id
    
    await DatabaseService.set_active_character(user_id, char_name)
    await callback.answer(f"Выбран персонаж: {char_name}")
    
    # Обновляем меню
    characters = await DatabaseService.get_all_characters(user_id)
    active_char = next((c for c in characters if c.get("is_active") == 1), None)
    active_name = active_char["name"] if active_char else "не выбран"
    
    chat_id = callback.message.chat.id
    thread_id = callback.message.message_thread_id
    bound_names = await DatabaseService.get_user_bound_character_names(user_id, chat_id, thread_id)
    
    try:
        await callback.message.edit_text(
            f"👥 <b>Ваши персонажи:</b>\n"
            f"Текущий активный персонаж: <b>{active_name}</b>\n\n"
            f"<i>Кликните на имя персонажа, чтобы сделать его активным для проверок.</i>",
            reply_markup=get_characters_management_keyboard(characters, bound_char_name=bound_names)
        )
    except Exception:
        pass

@router.callback_query(F.data == "show_active_char_card")
async def handle_show_active_char_card(callback: CallbackQuery, state: FSMContext):
    """Отображает карточку активного персонажа со всеми характеристиками и владениями."""
    user_id = callback.from_user.id
    active_char = await DatabaseService.get_character(user_id)
    if not active_char:
        await callback.answer("⚠️ У вас нет активного персонажа!", show_alert=True)
        return
        
    card_text = format_character_card(active_char)
    await callback.message.edit_text(
        card_text,
        reply_markup=get_character_card_keyboard()
    )
    await callback.answer()

@router.callback_query(F.data == "back_to_chars_list")
async def handle_back_to_chars_list(callback: CallbackQuery, state: FSMContext):
    """Возвращает из карточки персонажа назад к меню списка персонажей."""
    user_id = callback.from_user.id
    characters = await DatabaseService.get_all_characters(user_id)
    active_char = next((c for c in characters if c.get("is_active") == 1), None)
    active_name = active_char["name"] if active_char else "не выбран"
    
    chat_id = callback.message.chat.id
    thread_id = callback.message.message_thread_id
    bound_names = await DatabaseService.get_user_bound_character_names(user_id, chat_id, thread_id)
    
    await callback.message.edit_text(
        f"👥 <b>Ваши персонажи:</b>\n"
        f"Текущий активный персонаж: <b>{active_name}</b>\n\n"
        f"<i>Кликните на имя персонажа, чтобы сделать его активным для проверок.</i>",
        reply_markup=get_characters_management_keyboard(characters, bound_char_name=bound_names)
    )
    await callback.answer()

@router.callback_query(F.data == "create_new_char")
async def handle_create_new_character_callback(callback: CallbackQuery, state: FSMContext):
    """Инициализирует мастер создания нового персонажа."""
    has_incomplete = await check_incomplete_creation(callback.message.chat.id, callback.bot, state)
    if has_incomplete:
        await callback.answer()
        return

    await state.clear()
    await state.set_state(CharacterSetupStates.waiting_for_name)
    await callback.answer("Запуск создания персонажа")
    try:
        await callback.message.delete()
    except Exception:
        pass
        
    session_id = str(uuid.uuid4())
    await state.update_data(
        is_new_creation=True,
        creation_session_id=session_id,
        creator_mention=get_user_mention(callback.from_user),
        creation_chat_type=callback.message.chat.type
    )
    
    sent_msg = await callback.message.answer(
        "🧙‍♂️ <b>Мастер создания персонажа</b>\n\n"
        "Шаг 1: <b>Введите имя вашего нового персонажа</b>:",
        reply_markup=ReplyKeyboardRemove(selective=True)
    )
    await state.update_data(last_bot_msg_id=sent_msg.message_id)
    
    asyncio.create_task(
        send_reminder_after_delay(
            callback.bot, callback.message.chat.id, callback.from_user.id, state, session_id
        )
    )

@router.callback_query(F.data == "edit_active_char")
async def handle_edit_active_character(callback: CallbackQuery, state: FSMContext):
    """Подгружает данные активного персонажа во FSM-сессию и открывает меню редактирования."""
    user_id = callback.from_user.id
    active_char = await DatabaseService.get_character(user_id)
    
    if not active_char:
        await callback.answer("⚠️ Нет активного персонажа для редактирования!", show_alert=True)
        return
        
    full_data = active_char.get("full_data", {})
    expertise = []
    if isinstance(full_data, dict):
        fd_skills = full_data.get("skills", {})
        if isinstance(fd_skills, dict):
            for k, v in fd_skills.items():
                if v == "expert":
                    expertise.append(k)
        fd_tools = full_data.get("tools", {})
        if isinstance(fd_tools, dict):
            for k, v in fd_tools.items():
                if v == "expert":
                    expertise.append(k)
                    
    await state.clear()
    # Подгружаем все данные в сессию FSM
    await state.update_data(
        char_id=active_char["id"],
        name=active_char["name"],
        char_class=active_char["class"],
        pb=active_char["proficiency_bonus"],
        mod_strength=active_char["mod_strength"],
        mod_dexterity=active_char["mod_dexterity"],
        mod_constitution=active_char["mod_constitution"],
        mod_intelligence=active_char["mod_intelligence"],
        mod_wisdom=active_char["mod_wisdom"],
        mod_charisma=active_char["mod_charisma"],
        saving_throws=active_char["saving_throws"],
        skills=active_char["skills"],
        tools=active_char["tools"],
        expertise=expertise,
        full_data=full_data
    )
    
    await state.set_state(CharacterSetupStates.editing_menu)
    await callback.answer("Режим редактирования")
    try:
        await callback.message.edit_text(
            f"✏️ <b>Редактирование персонажа: {active_char['name']}</b>\n\n"
            f"Выберите, какой раздел вы хотите изменить:",
            reply_markup=get_edit_menu_keyboard()
        )
    except Exception:
        pass

@router.callback_query(F.data.startswith("edit_field:"))
async def handle_edit_field(callback: CallbackQuery, state: FSMContext):
    """Обрабатывает выбор конкретного поля для редактирования в меню ✏️ Редактировать."""
    field = callback.data.split(":", 1)[1]
    await callback.answer()

    FIELD_TO_STATE = {
        "name":  CharacterSetupStates.waiting_for_name,
        "class": CharacterSetupStates.waiting_for_class,
        "pb":    CharacterSetupStates.waiting_for_pb,
        "stats": CharacterSetupStates.waiting_for_strength,
        "saves": CharacterSetupStates.selecting_saving_throws,
        "skills": CharacterSetupStates.selecting_skills,
        "tools": CharacterSetupStates.selecting_tools,
        "expertise": CharacterSetupStates.selecting_expertise,
    }

    FIELD_PROMPTS = {
        "name":  "✏️ Введите <b>новое имя</b> персонажа:",
        "class": "✏️ Введите <b>новый класс</b> или выберите из списка:",
        "pb":    "✏️ Введите <b>новый бонус мастерства</b> (например: <code>+3</code> или <code>3</code>):",
        "stats": "✏️ Введите <b>новый модификатор Силы</b> (например: <code>+2</code>, <code>-1</code>):",
        "saves": "✏️ Отметьте <b>спасброски</b> для вашего персонажа:",
        "skills": "✏️ Отметьте <b>навыки</b> для вашего персонажа:",
        "tools": "✏️ Отметьте <b>инструменты</b> для вашего персонажа:",
        "expertise": "✏️ Отметьте <b>навыки и инструменты</b>, в которых у персонажа компетентность:",
    }

    target_state = FIELD_TO_STATE.get(field)
    if not target_state:
        await callback.answer(f"⚠️ Неизвестное поле: {field}", show_alert=True)
        return

    await state.update_data(is_editing=True, edit_field=field)
    await state.set_state(target_state)

    data = await state.get_data()

    try:
        await callback.message.delete()
    except Exception:
        pass

    if field == "saves":
        saves = data.get("saving_throws", [])
        sent_msg = await callback.message.answer(
            FIELD_PROMPTS[field] + "\n<i>Когда закончите, нажмите кнопку внизу.</i>",
            reply_markup=get_saving_throws_keyboard(saves)
        )
    elif field == "skills":
        skills = data.get("skills", [])
        sent_msg = await callback.message.answer(
            FIELD_PROMPTS[field] + "\n<i>Когда закончите, нажмите кнопку внизу.</i>",
            reply_markup=get_skills_keyboard(skills)
        )
    elif field == "tools":
        tools = data.get("tools", [])
        sent_msg = await callback.message.answer(
            FIELD_PROMPTS[field] + "\n<i>Когда закончите, нажмите кнопку внизу.</i>",
            reply_markup=get_tools_keyboard(tools)
        )
    elif field == "expertise":
        skills = data.get("skills", [])
        tools = data.get("tools", [])
        expertise = data.get("expertise", [])
        sent_msg = await callback.message.answer(
            FIELD_PROMPTS[field] + "\n<i>Когда закончите, нажмите кнопку внизу.</i>",
            reply_markup=get_expertise_keyboard(skills, tools, expertise)
        )
    elif field == "class":
        sent_msg = await callback.message.answer(
            FIELD_PROMPTS[field],
            reply_markup=get_classes_keyboard()
        )
    else:
        sent_msg = await callback.message.answer(FIELD_PROMPTS[field])

    await state.update_data(last_bot_msg_id=sent_msg.message_id)

@router.callback_query(F.data == "delete_char_menu")
async def handle_delete_char_menu(callback: CallbackQuery, state: FSMContext):
    """Открывает список персонажей для удаления."""
    user_id = callback.from_user.id
    characters = await DatabaseService.get_all_characters(user_id)
    
    await callback.answer()
    try:
        await callback.message.edit_text(
            "🗑️ <b>Выберите персонажа для удаления:</b>\n"
            "<i>Внимание: это действие необратимо!</i>",
            reply_markup=get_characters_delete_keyboard(characters)
        )
    except Exception:
        pass

@router.callback_query(F.data == "delete_char_back")
async def handle_delete_char_back(callback: CallbackQuery, state: FSMContext):
    """Возвращает из меню удаления в меню управления персонажами."""
    user_id = callback.from_user.id
    characters = await DatabaseService.get_all_characters(user_id)
    active_char = next((c for c in characters if c.get("is_active") == 1), None)
    active_name = active_char["name"] if active_char else "не выбран"
    
    await callback.answer()
    try:
        await callback.message.edit_text(
            f"👥 <b>Ваши персонажи:</b>\n"
            f"Текущий активный персонаж: <b>{active_name}</b>\n\n"
            f"<i>Кликните на имя персонажа, чтобы сделать его активным для проверок.</i>",
            reply_markup=get_characters_management_keyboard(characters)
        )
    except Exception:
        pass

@router.callback_query(F.data.startswith("delete_char_select:"))
async def handle_delete_char_select(callback: CallbackQuery, state: FSMContext):
    """Запрашивает подтверждение удаления выбранного персонажа."""
    char_name = callback.data.split(":", 1)[1]
    await callback.answer()
    try:
        await callback.message.edit_text(
            f"⚠️ <b>Вы уверены, что хотите навсегда удалить персонажа {char_name}?</b>\n\n"
            f"Все его характеристики, навыки и инструменты будут стерты безвозвратно!",
            reply_markup=get_delete_confirm_keyboard(char_name)
        )
    except Exception:
        pass

@router.callback_query(F.data == "delete_char_cancel")
async def handle_delete_char_cancel(callback: CallbackQuery, state: FSMContext):
    """Отменяет удаление и возвращает в список персонажей на удаление."""
    user_id = callback.from_user.id
    characters = await DatabaseService.get_all_characters(user_id)
    await callback.answer("Удаление отменено")
    try:
        await callback.message.edit_text(
            "🗑️ <b>Выберите персонажа для удаления:</b>\n"
            "<i>Внимание: это действие необратимо!</i>",
            reply_markup=get_characters_delete_keyboard(characters)
        )
    except Exception:
        pass

@router.callback_query(F.data.startswith("delete_char_confirm:"))
async def handle_delete_char_confirm(callback: CallbackQuery, state: FSMContext):
    """Выполняет удаление персонажа из БД и возвращает в меню управления."""
    char_name = callback.data.split(":", 1)[1]
    user_id = callback.from_user.id
    
    await DatabaseService.delete_character_by_name(user_id, char_name)
    await callback.answer(f"Персонаж {char_name} удален!", show_alert=True)
    
    # Возвращаем на страницу списка персонажей
    characters = await DatabaseService.get_all_characters(user_id)
    if not characters:
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text="➕ Создать первого персонажа", callback_data="create_new_char"))
        try:
            await callback.message.edit_text(
                "👥 <b>У вас еще нет созданных персонажей!</b>\n\n"
                "Давайте создадим вашего первого героя для игры в D&D 5e.",
                reply_markup=builder.as_markup()
            )
        except Exception:
            pass
        return
        
    active_char = next((c for c in characters if c.get("is_active") == 1), None)
    active_name = active_char["name"] if active_char else "не выбран"
    
    try:
        await callback.message.edit_text(
            f"👥 <b>Ваши персонажи:</b>\n"
            f"Текущий активный персонаж: <b>{active_name}</b>\n\n"
            f"<i>Кликните на имя персонажа, чтобы сделать его активным для проверок.</i>",
            reply_markup=get_characters_management_keyboard(characters)
        )
    except Exception:
        pass

# =====================================================================
# УПРАВЛЕНИЕ КАСТОМНЫМИ ФОРМУЛАМИ
# =====================================================================

@router.callback_query(F.data == "active_char_formulas")
async def handle_active_char_formulas(callback: CallbackQuery, state: FSMContext):
    """Выводит список кастомных формул активного персонажа."""
    user_id = callback.from_user.id
    active_char = await DatabaseService.get_character(user_id)
    
    if not active_char:
        await callback.answer("⚠️ Нет активного персонажа для формул!", show_alert=True)
        return
        
    formulas = active_char.get("custom_formulas", {})
    await callback.answer()
    try:
        await callback.message.edit_text(
            f"🧪 <b>Кастомные формулы персонажа {active_char['name']}:</b>\n\n"
            f"Вы можете нажать на формулу, чтобы быстро пробросить ее, или воспользоваться кнопками ниже для управления.",
            reply_markup=get_formulas_keyboard(formulas)
        )
    except Exception:
        pass

@router.callback_query(F.data == "formula_back_to_char_menu")
async def handle_formula_back_to_char_menu(callback: CallbackQuery, state: FSMContext):
    """Возвращает из меню формул в список персонажей."""
    user_id = callback.from_user.id
    characters = await DatabaseService.get_all_characters(user_id)
    active_char = next((c for c in characters if c.get("is_active") == 1), None)
    active_name = active_char["name"] if active_char else "не выбран"
    
    await callback.answer()
    try:
        await callback.message.edit_text(
            f"👥 <b>Ваши персонажи:</b>\n"
            f"Текущий активный персонаж: <b>{active_name}</b>\n\n"
            f"<i>Кликните на имя персонажа, чтобы сделать его активным для проверок.</i>",
            reply_markup=get_characters_management_keyboard(characters)
        )
    except Exception:
        pass

@router.callback_query(F.data == "formula_add")
async def handle_formula_add(callback: CallbackQuery, state: FSMContext):
    """Запускает FSM добавления новой кастомной формулы."""
    await state.clear()
    await state.set_state(CharacterSetupStates.adding_custom_formula_name)
    await callback.answer()
    await callback.message.delete()
    await callback.message.answer(
        "🧪 <b>Добавление кастомной формулы</b>\n\n"
        "Введите <b>название</b> для вашей формулы (например: <code>Glamdring</code>, <code>Скрытая атака</code>, <code>Огненный шар</code>):",
        reply_markup=ReplyKeyboardRemove(selective=True)
    )

@router.message(StateFilter(CharacterSetupStates.adding_custom_formula_name))
async def process_formula_name(message: Message, state: FSMContext):
    name = message.text.strip()
    if not name:
        await message.answer("⚠️ Название не может быть пустым. Введите корректное название:")
        return
        
    await state.update_data(formula_name=name)
    await state.set_state(CharacterSetupStates.adding_custom_formula_expr)
    await message.answer(
        f"Отлично! Название: <b>{name}</b>.\n"
        f"Теперь введите <b>формулу броска</b> (например: <code>1d20+5</code>, <code>2d6+3</code>, <code>8d6</code>):"
    )

@router.message(StateFilter(CharacterSetupStates.adding_custom_formula_expr))
async def process_formula_expr(message: Message, state: FSMContext):
    expr = message.text.strip().lower()
    
    # Регулярка для валидации бросков D&D формул
    clean_expr = expr.replace(" ", "")
    formula_pattern = re.compile(r'^\d*[dд]\d+(?:([+-])\d+)?$', re.IGNORECASE)
    
    if not formula_pattern.match(clean_expr):
        await message.answer(
            "⚠️ Некорректный формат формулы.\n"
            "Пожалуйста, введите формулу в формате: <code>[кол-во]d[грани][+/-модификатор]</code>\n"
            "Примеры: <code>2d6+4</code>, <code>1d10</code>, <code>8d6-1</code>:"
        )
        return
        
    data = await state.get_data()
    name = data["formula_name"]
    user_id = message.from_user.id
    
    await DatabaseService.add_custom_formula(user_id, name, expr)
    await state.clear()
    
    markup = await get_dice_keyboard_for_user(user_id)
    await message.reply(
        f"✅ Формула <b>{name}</b> (<code>{expr}</code>) успешно сохранена!",
        reply_markup=markup
    )
    
    # Отправляем обновленное меню формул
    characters = await DatabaseService.get_all_characters(user_id)
    active_char = next((c for c in characters if c.get("is_active") == 1), None)
    if active_char:
        await message.answer(
            f"🧪 <b>Кастомные формулы персонажа {active_char['name']}:</b>\n\n"
            f"Вы можете нажать на формулу, чтобы быстро пробросить ее, или воспользоваться кнопками ниже для управления.",
            reply_markup=get_formulas_keyboard(active_char.get("custom_formulas", {}))
        )

@router.callback_query(F.data == "formula_delete_menu")
async def handle_formula_delete_menu(callback: CallbackQuery, state: FSMContext):
    """Показывает список формул для удаления."""
    user_id = callback.from_user.id
    active_char = await DatabaseService.get_character(user_id)
    
    if not active_char:
        await callback.answer("⚠️ Нет активного персонажа!", show_alert=True)
        return
        
    formulas = active_char.get("custom_formulas", {})
    await callback.answer()
    try:
        await callback.message.edit_text(
            "🗑️ <b>Выберите формулу для удаления:</b>",
            reply_markup=get_formulas_delete_keyboard(formulas)
        )
    except Exception:
        pass

@router.callback_query(F.data == "formula_delete_cancel")
async def handle_formula_delete_cancel(callback: CallbackQuery, state: FSMContext):
    """Отменяет удаление формулы и возвращает в список формул."""
    user_id = callback.from_user.id
    active_char = await DatabaseService.get_character(user_id)
    
    if not active_char:
        await callback.answer("⚠️ Нет активного персонажа!", show_alert=True)
        return
        
    formulas = active_char.get("custom_formulas", {})
    await callback.answer()
    try:
        await callback.message.edit_text(
            f"🧪 <b>Кастомные формулы персонажа {active_char['name']}:</b>\n\n"
            f"Вы можете нажать на формулу, чтобы быстро пробросить ее, или воспользоваться кнопками ниже для управления.",
            reply_markup=get_formulas_keyboard(formulas)
        )
    except Exception:
        pass

@router.callback_query(F.data.startswith("formula_delete_select:"))
async def handle_formula_delete_select(callback: CallbackQuery, state: FSMContext):
    """Удаляет выбранную формулу и возвращает в меню."""
    formula_name = callback.data.split(":", 1)[1]
    user_id = callback.from_user.id
    
    await DatabaseService.delete_custom_formula(user_id, formula_name)
    await callback.answer(f"Формула {formula_name} удалена!")
    
    active_char = await DatabaseService.get_character(user_id)
    formulas = active_char.get("custom_formulas", {}) if active_char else {}
    
    try:
        await callback.message.edit_text(
            f"🧪 <b>Кастомные формулы персонажа {active_char['name']}:</b>\n\n"
            f"Вы можете нажать на формулу, чтобы быстро пробросить ее, или воспользоваться кнопками ниже для управления.",
            reply_markup=get_formulas_keyboard(formulas)
        )
    except Exception:
        pass

# =====================================================================
# МАСТЕР ПОШАГОВОГО СОЗДАНИЯ И РЕДАКТИРОВАНИЯ ХАРАКТЕРИСТИК (FSM)
# =====================================================================

@router.message(Command("create_character"))
async def start_character_setup(message: Message, state: FSMContext):
    """Начало процесса создания персонажа."""
    has_incomplete = await check_incomplete_creation(message.chat.id, message.bot, state)
    if has_incomplete:
        try:
            await message.delete()
        except Exception:
            pass
        return

    await state.clear()
    await state.set_state(CharacterSetupStates.waiting_for_name)
    try:
        await message.delete()
    except Exception:
        pass
        
    session_id = str(uuid.uuid4())
    await state.update_data(
        is_new_creation=True,
        creation_session_id=session_id,
        creator_mention=get_user_mention(message.from_user),
        creation_chat_type=message.chat.type
    )
    
    sent_msg = await message.reply(
        "🧙‍♂️ <b>Мастер создания персонажа</b>\n\n"
        "Давайте создадим вашего персонажа для игры в D&D!\n"
        "Шаг 1: <b>Введите имя вашего персонажа</b>:",
        reply_markup=ReplyKeyboardRemove(selective=True)
    )
    await state.update_data(last_bot_msg_id=sent_msg.message_id)
    
    asyncio.create_task(
        send_reminder_after_delay(
            message.bot, message.chat.id, message.from_user.id, state, session_id
        )
    )

@router.message(StateFilter(CharacterSetupStates.waiting_for_name))
async def process_name(message: Message, state: FSMContext):
    await delete_previous_messages(message, state)
    
    name = message.text.strip()
    if not name:
        sent_msg = await message.answer("⚠️ Имя не может быть пустым. Введите корректное имя:")
        await state.update_data(last_bot_msg_id=sent_msg.message_id)
        return
        
    await state.update_data(name=name)
    data = await state.get_data()
    
    # Если мы находимся в режиме редактирования поля Name
    if data.get("is_editing") and data.get("edit_field") == "name":
        await state.update_data(is_editing=False, edit_field=None)
        await state.set_state(CharacterSetupStates.reviewing_data)
        sent_msg = await message.answer(
            _get_character_review_text(data),
            reply_markup=get_review_keyboard()
        )
        await state.update_data(last_bot_msg_id=sent_msg.message_id)
        return
        
    await state.set_state(CharacterSetupStates.waiting_for_class)
    sent_msg = await message.answer(
        f"Отлично, {name}!\n"
        "Шаг 2: <b>Выберите класс вашего персонажа</b> или введите его вручную в чат:",
        reply_markup=get_classes_keyboard()
    )
    await state.update_data(last_bot_msg_id=sent_msg.message_id)

@router.callback_query(StateFilter(CharacterSetupStates.waiting_for_class), F.data.startswith("select_class:"))
async def handle_select_class_callback(callback: CallbackQuery, state: FSMContext):
    char_class = callback.data.split(":", 1)[1]
    await state.update_data(char_class=char_class)
    await callback.answer(f"Выбран класс: {char_class}")
    try:
        await callback.message.delete()
    except Exception:
        pass
    
    data = await state.get_data()
    if data.get("is_editing") and data.get("edit_field") == "class":
        await state.update_data(is_editing=False, edit_field=None)
        await state.set_state(CharacterSetupStates.reviewing_data)
        sent_msg = await callback.message.answer(
            _get_character_review_text(data),
            reply_markup=get_review_keyboard()
        )
        await state.update_data(last_bot_msg_id=sent_msg.message_id)
        return
        
    await state.set_state(CharacterSetupStates.waiting_for_pb)
    sent_msg = await callback.message.answer(
        "Шаг 3: <b>Введите бонус мастерства</b> своего персонажа (например: <code>+2</code>, <code>+3</code>, <code>2</code>):"
    )
    await state.update_data(last_bot_msg_id=sent_msg.message_id)

@router.callback_query(StateFilter(CharacterSetupStates.waiting_for_class), F.data == "select_class_custom")
async def handle_select_class_custom(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    try:
        await callback.message.delete()
    except Exception:
        pass
    sent_msg = await callback.message.answer(
        "✍️ <b>Введите название класса вручную в чат:</b>"
    )
    await state.update_data(last_bot_msg_id=sent_msg.message_id)

@router.message(StateFilter(CharacterSetupStates.waiting_for_class))
async def process_class_text(message: Message, state: FSMContext):
    await delete_previous_messages(message, state)
    
    char_class = message.text.strip()
    if not char_class:
        sent_msg = await message.answer("⚠️ Название класса не может быть пустым. Введите название:")
        await state.update_data(last_bot_msg_id=sent_msg.message_id)
        return
        
    await state.update_data(char_class=char_class)
    data = await state.get_data()
    
    if data.get("is_editing") and data.get("edit_field") == "class":
        await state.update_data(is_editing=False, edit_field=None)
        await state.set_state(CharacterSetupStates.reviewing_data)
        sent_msg = await message.answer(
            _get_character_review_text(data),
            reply_markup=get_review_keyboard()
        )
        await state.update_data(last_bot_msg_id=sent_msg.message_id)
        return
        
    await state.set_state(CharacterSetupStates.waiting_for_pb)
    sent_msg = await message.answer(
        f"Класс <b>{char_class}</b> записан!\n"
        "Шаг 3: <b>Введите бонус мастерства</b> своего персонажа (например: <code>+2</code>, <code>+3</code>, <code>2</code>):"
    )
    await state.update_data(last_bot_msg_id=sent_msg.message_id)

@router.message(StateFilter(CharacterSetupStates.waiting_for_pb))
async def process_pb(message: Message, state: FSMContext):
    await delete_previous_messages(message, state)
    try:
        pb = parse_modifier(message.text)
        if pb < 1:
            sent_msg = await message.answer("⚠️ Бонус мастерства должен быть не менее 1. Попробуйте еще раз:")
            await state.update_data(last_bot_msg_id=sent_msg.message_id)
            return
    except ValueError:
        sent_msg = await message.answer("⚠️ Пожалуйста, введите целое число (например, +2 или 3):")
        await state.update_data(last_bot_msg_id=sent_msg.message_id)
        return

    await state.update_data(pb=pb)
    data = await state.get_data()
    
    # Если мы находимся в режиме редактирования поля pb
    if data.get("is_editing") and data.get("edit_field") == "pb":
        await state.update_data(is_editing=False, edit_field=None)
        await state.set_state(CharacterSetupStates.reviewing_data)
        sent_msg = await message.answer(
            _get_character_review_text(data),
            reply_markup=get_review_keyboard()
        )
        await state.update_data(last_bot_msg_id=sent_msg.message_id)
        return

    await state.set_state(CharacterSetupStates.waiting_for_strength)
    sent_msg = await message.answer("Шаг 4: Введите модификатор <b>Силы</b> (например, +3, 0, -1):")
    await state.update_data(last_bot_msg_id=sent_msg.message_id)

@router.message(StateFilter(CharacterSetupStates.waiting_for_strength))
async def process_strength(message: Message, state: FSMContext):
    await delete_previous_messages(message, state)
    try:
        val = parse_modifier(message.text)
    except ValueError:
        sent_msg = await message.answer("⚠️ Пожалуйста, введите корректное число для Силы:")
        await state.update_data(last_bot_msg_id=sent_msg.message_id)
        return

    await state.update_data(mod_strength=val)
    await state.set_state(CharacterSetupStates.waiting_for_dexterity)
    sent_msg = await message.answer("Шаг 5: Введите модификатор <b>Ловкости</b>:")
    await state.update_data(last_bot_msg_id=sent_msg.message_id)

@router.message(StateFilter(CharacterSetupStates.waiting_for_dexterity))
async def process_dexterity(message: Message, state: FSMContext):
    await delete_previous_messages(message, state)
    try:
        val = parse_modifier(message.text)
    except ValueError:
        sent_msg = await message.answer("⚠️ Пожалуйста, введите корректное число для Ловкости:")
        await state.update_data(last_bot_msg_id=sent_msg.message_id)
        return

    await state.update_data(mod_dexterity=val)
    await state.set_state(CharacterSetupStates.waiting_for_constitution)
    sent_msg = await message.answer("Шаг 6: Введите модификатор <b>Телосложения</b>:")
    await state.update_data(last_bot_msg_id=sent_msg.message_id)

@router.message(StateFilter(CharacterSetupStates.waiting_for_constitution))
async def process_constitution(message: Message, state: FSMContext):
    await delete_previous_messages(message, state)
    try:
        val = parse_modifier(message.text)
    except ValueError:
        sent_msg = await message.answer("⚠️ Пожалуйста, введите корректное число для Телосложения:")
        await state.update_data(last_bot_msg_id=sent_msg.message_id)
        return

    await state.update_data(mod_constitution=val)
    await state.set_state(CharacterSetupStates.waiting_for_intelligence)
    sent_msg = await message.answer("Шаг 7: Введите модификатор <b>Интеллекта</b>:")
    await state.update_data(last_bot_msg_id=sent_msg.message_id)

@router.message(StateFilter(CharacterSetupStates.waiting_for_intelligence))
async def process_intelligence(message: Message, state: FSMContext):
    await delete_previous_messages(message, state)
    try:
        val = parse_modifier(message.text)
    except ValueError:
        sent_msg = await message.answer("⚠️ Пожалуйста, введите корректное число для Интеллекта:")
        await state.update_data(last_bot_msg_id=sent_msg.message_id)
        return

    await state.update_data(mod_intelligence=val)
    await state.set_state(CharacterSetupStates.waiting_for_wisdom)
    sent_msg = await message.answer("Шаг 8: Введите модификатор <b>Мудрости</b>:")
    await state.update_data(last_bot_msg_id=sent_msg.message_id)

@router.message(StateFilter(CharacterSetupStates.waiting_for_wisdom))
async def process_wisdom(message: Message, state: FSMContext):
    await delete_previous_messages(message, state)
    try:
        val = parse_modifier(message.text)
    except ValueError:
        sent_msg = await message.answer("⚠️ Пожалуйста, введите корректное число для Мудрости:")
        await state.update_data(last_bot_msg_id=sent_msg.message_id)
        return

    await state.update_data(mod_wisdom=val)
    await state.set_state(CharacterSetupStates.waiting_for_charisma)
    sent_msg = await message.answer("Шаг 9: Введите модификатор <b>Харизмы</b>:")
    await state.update_data(last_bot_msg_id=sent_msg.message_id)

@router.message(StateFilter(CharacterSetupStates.waiting_for_charisma))
async def process_charisma(message: Message, state: FSMContext):
    await delete_previous_messages(message, state)
    try:
        val = parse_modifier(message.text)
    except ValueError:
        sent_msg = await message.answer("⚠️ Пожалуйста, введите корректное число для Харизмы:")
        await state.update_data(last_bot_msg_id=sent_msg.message_id)
        return

    await state.update_data(mod_charisma=val)
    data = await state.get_data()
    
    # Если мы редактировали характеристики последовательно
    if data.get("is_editing") and data.get("edit_field") == "stats":
        await state.update_data(is_editing=False, edit_field=None)
        await state.set_state(CharacterSetupStates.reviewing_data)
        sent_msg = await message.answer(
            _get_character_review_text(data),
            reply_markup=get_review_keyboard()
        )
        await state.update_data(last_bot_msg_id=sent_msg.message_id)
        return

    await state.update_data(saving_throws=[])
    await state.set_state(CharacterSetupStates.selecting_saving_throws)
    
    sent_msg = await message.answer(
        "Шаг 10: Отметьте <b>спасброски</b>, которыми владеет ваш персонаж (кликните для переключения ✅/❌):\n"
        "<i>Когда закончите, нажмите кнопку внизу.</i>",
        reply_markup=get_saving_throws_keyboard([])
    )
    await state.update_data(last_bot_msg_id=sent_msg.message_id)

# Обработка чекбоксов спасбросков
@router.callback_query(StateFilter(CharacterSetupStates.selecting_saving_throws), F.data.startswith("toggle_save:"))
async def toggle_saving_throw(callback: CallbackQuery, state: FSMContext):
    item = callback.data.split(":", 1)[1]
    data = await state.get_data()
    saves = list(data.get("saving_throws", []))
    
    if item in saves:
        saves.remove(item)
    else:
        saves.append(item)
        
    await state.update_data(saving_throws=saves)
    await callback.answer(f"Изменено: {item}")
    try:
        await callback.message.edit_reply_markup(reply_markup=get_saving_throws_keyboard(saves))
    except Exception:
        pass

@router.callback_query(StateFilter(CharacterSetupStates.selecting_saving_throws), F.data == "done_save")
async def finish_saving_throws(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    try:
        await callback.message.delete()
    except Exception:
        pass
    
    # Если редактировали спасброски
    if data.get("is_editing") and data.get("edit_field") == "saves":
        await state.update_data(is_editing=False, edit_field=None)
        await state.set_state(CharacterSetupStates.reviewing_data)
        await callback.answer("Спасброски сохранены!")
        sent_msg = await callback.message.answer(
            _get_character_review_text(data),
            reply_markup=get_review_keyboard()
        )
        await state.update_data(last_bot_msg_id=sent_msg.message_id)
        return

    await state.update_data(skills=[])
    await state.set_state(CharacterSetupStates.selecting_skills)
    await callback.answer("Спасброски сохранены!")
    sent_msg = await callback.message.answer(
        "Шаг 11: Отметьте <b>навыки</b>, которыми владеет ваш персонаж:\n"
        "<i>Когда закончите, нажмите кнопку внизу.</i>",
        reply_markup=get_skills_keyboard([])
    )
    await state.update_data(last_bot_msg_id=sent_msg.message_id)

# Обработка чекбоксов навыков
@router.callback_query(StateFilter(CharacterSetupStates.selecting_skills), F.data.startswith("toggle_skill:"))
async def toggle_skill(callback: CallbackQuery, state: FSMContext):
    item = callback.data.split(":", 1)[1]
    data = await state.get_data()
    skills = list(data.get("skills", []))
    
    if item in skills:
        skills.remove(item)
    else:
        skills.append(item)
        
    await state.update_data(skills=skills)
    await callback.answer(f"Изменено: {item}")
    try:
        await callback.message.edit_reply_markup(reply_markup=get_skills_keyboard(skills))
    except Exception:
        pass

@router.callback_query(StateFilter(CharacterSetupStates.selecting_skills), F.data == "done_skills")
async def finish_skills(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    try:
        await callback.message.delete()
    except Exception:
        pass
    
    # Если редактировали навыки
    if data.get("is_editing") and data.get("edit_field") == "skills":
        skills = data.get("skills", [])
        tools = data.get("tools", [])
        expertise = [item for item in data.get("expertise", []) if item in skills or item in tools]
        await state.update_data(expertise=expertise, is_editing=False, edit_field=None)
        await state.set_state(CharacterSetupStates.reviewing_data)
        await callback.answer("Навыки сохранены!")
        sent_msg = await callback.message.answer(
            _get_character_review_text(await state.get_data()),
            reply_markup=get_review_keyboard()
        )
        await state.update_data(last_bot_msg_id=sent_msg.message_id)
        return

    await state.update_data(tools=[])
    await state.set_state(CharacterSetupStates.selecting_tools)
    await callback.answer("Навыки сохранены!")
    sent_msg = await callback.message.answer(
        "Шаг 12: Отметьте <b>инструменты</b>, которыми владеет ваш персонаж:\n"
        "<i>Когда закончите, нажмите кнопку внизу.</i>",
        reply_markup=get_tools_keyboard([])
    )
    await state.update_data(last_bot_msg_id=sent_msg.message_id)

def _get_character_report_from_data(data: dict) -> str:
    """Форматирует красивое резюме персонажа после успешного сохранения."""
    saves_str = ", ".join(data.get("saving_throws", [])) if data.get("saving_throws") else "нет"
    skills_str = ", ".join(data.get("skills", [])) if data.get("skills") else "нет"
    tools_str = ", ".join(data.get("tools", [])) if data.get("tools") else "нет"
    
    format_mod = lambda v: f"+{v}" if v >= 0 else str(v)
    
    return (
        f"👤 <b>Имя:</b> {data.get('name', 'Не введено')}\n"
        f"🛡️ <b>Класс:</b> {data.get('char_class', 'Не выбран')}\n"
        f"🎓 <b>Бонус мастерства:</b> {format_mod(data.get('pb', 0))}\n\n"
        f"⚔️ <b>Характеристики:</b>\n"
        f"• Сила: <code>{format_mod(data.get('mod_strength', 0))}</code>\n"
        f"• Ловкость: <code>{format_mod(data.get('mod_dexterity', 0))}</code>\n"
        f"• Телосложение: <code>{format_mod(data.get('mod_constitution', 0))}</code>\n"
        f"• Интеллект: <code>{format_mod(data.get('mod_intelligence', 0))}</code>\n"
        f"• Мудрость: <code>{format_mod(data.get('mod_wisdom', 0))}</code>\n"
        f"• Харизма: <code>{format_mod(data.get('mod_charisma', 0))}</code>\n\n"
        f"🛡️ <b>Владение спасбросками:</b> {saves_str}\n"
        f"📜 <b>Владение навыками:</b> {skills_str}\n"
        f"🛠️ <b>Владение инструментами:</b> {tools_str}\n\n"
        f"💬 <i>Теперь вы можете проводить любые проверки, отправляя их название в чат с обязательным восклицательным знаком в начале! Например: \"!Атлетика +2\", \"!Спасбросок Мудрости преимущество\".</i>"
    )

@router.callback_query(F.data.startswith("unbind:"))
async def handle_unbind_callback(callback: CallbackQuery, state: FSMContext):
    """Удаляет существующую привязку персонажа."""
    parts = callback.data.split(":")
    if len(parts) != 3:
        await callback.answer("⚠️ Ошибка callback_data.", show_alert=True)
        return
        
    chat_prefix = parts[1]
    thread_prefix = parts[2]
    
    data = await state.get_data()
    char_name = data.get("binding_char_name")
    user_id = callback.from_user.id
    
    if not char_name:
        active_char = await DatabaseService.get_character(user_id)
        if active_char:
            char_name = active_char["name"]
            
    if not char_name:
        await callback.answer("⚠️ Не удалось определить персонажа.", show_alert=True)
        return
        
    # Ищем полную пару хешей по префиксам среди привязок персонажа
    bindings = await DatabaseService.get_character_bindings(user_id, char_name)
    target_binding = None
    for b in bindings:
        b_thread = b.get("thread_id") or ""
        b_chat = b.get("chat_id") or ""
        if b_chat.startswith(chat_prefix) and (b_thread == "" if thread_prefix == "None" or thread_prefix == "" else b_thread.startswith(thread_prefix)):
            target_binding = b
            break
            
    if not target_binding:
        await callback.answer("⚠️ Привязка не найдена или уже удалена.", show_alert=True)
        return
        
    # Удаляем привязку
    await DatabaseService.delete_binding(user_id, target_binding["chat_id"], target_binding["thread_id"], char_name)
    await callback.answer("Привязка удалена!")
    
    # Обновляем сообщение меню
    bindings = await DatabaseService.get_character_bindings(user_id, char_name)
    bindings_text = ""
    if bindings:
        for i, b in enumerate(bindings, 1):
            name = b.get("topic_name") or f"Чат {b['chat_id'][:8]}..."
            bindings_text += f"{i}. <b>{name}</b>\n"
    else:
        bindings_text = "<i>Привязки отсутствуют. Персонаж не привязан ни к одному чату/теме.</i>\n"
        
    text = (
        f"🔗 <b>Управление привязками персонажа {char_name}:</b>\n\n"
        f"Текущие привязки:\n{bindings_text}\n"
        f"Вы можете привязать персонажа к чату/разделу или удалить существующие привязки."
    )
    
    try:
        await callback.message.edit_text(
            text,
            reply_markup=get_bindings_management_keyboard(bindings)
        )
    except Exception:
        pass

# Обработка чекбоксов инструментов
@router.callback_query(StateFilter(CharacterSetupStates.selecting_tools), F.data.startswith("toggle_tool:"))
async def toggle_tool(callback: CallbackQuery, state: FSMContext):
    idx_str = callback.data.split(":", 1)[1]
    try:
        idx = int(idx_str)
        item = ALL_TOOLS[idx]
    except (ValueError, IndexError):
        await callback.answer("⚠️ Ошибка: инструмент не найден.")
        return
        
    data = await state.get_data()
    tools = list(data.get("tools", []))
    
    if item in tools:
        tools.remove(item)
    else:
        tools.append(item)
        
    await state.update_data(tools=tools)
    await callback.answer(f"Изменено: {item}")
    try:
        await callback.message.edit_reply_markup(reply_markup=get_tools_keyboard(tools))
    except Exception:
        pass

@router.callback_query(StateFilter(CharacterSetupStates.selecting_tools), F.data == "done_tools")
async def finish_character_creation(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    try:
        await callback.message.delete()
    except Exception:
        pass
    
    # Если редактировали инструменты
    if data.get("is_editing") and data.get("edit_field") == "tools":
        skills = data.get("skills", [])
        tools = data.get("tools", [])
        expertise = [item for item in data.get("expertise", []) if item in skills or item in tools]
        await state.update_data(expertise=expertise, is_editing=False, edit_field=None)
        await state.set_state(CharacterSetupStates.reviewing_data)
        await callback.answer("Инструменты сохранены!")
        sent_msg = await callback.message.answer(
            _get_character_review_text(await state.get_data()),
            reply_markup=get_review_keyboard()
        )
        await state.update_data(last_bot_msg_id=sent_msg.message_id)
        return

    # Переходим к шагу компетентности (если есть хотя бы один навык или инструмент)
    skills = data.get("skills", [])
    tools = data.get("tools", [])
    
    if skills or tools:
        await state.update_data(expertise=[])
        await state.set_state(CharacterSetupStates.selecting_expertise)
        await callback.answer("Инструменты сохранены!")
        sent_msg = await callback.message.answer(
            "Шаг 13: Выберите <b>навыки и инструменты</b>, в которых ваш персонаж имеет <b>компетентность</b>:\n"
            "<i>Компетентность удваивает бонус мастерства для проверок. Когда закончите, нажмите кнопку внизу.</i>",
            reply_markup=get_expertise_keyboard(skills, tools, [])
        )
        await state.update_data(last_bot_msg_id=sent_msg.message_id)
    else:
        await state.update_data(expertise=[])
        await state.set_state(CharacterSetupStates.reviewing_data)
        await callback.answer("Данные собраны!")
        sent_msg = await callback.message.answer(
            _get_character_review_text(data),
            reply_markup=get_review_keyboard()
        )
        await state.update_data(last_bot_msg_id=sent_msg.message_id)

# Обработка чекбоксов компетентности
@router.callback_query(StateFilter(CharacterSetupStates.selecting_expertise), F.data.startswith("toggle_exp:"))
async def toggle_expertise(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split(":")
    if len(parts) != 3:
        await callback.answer("⚠️ Неверный формат callback data.")
        return
        
    item_type = parts[1]
    idx_str = parts[2]
    
    try:
        idx = int(idx_str)
        if item_type == "s":
            item = ALL_SKILLS[idx]
        elif item_type == "t":
            item = ALL_TOOLS[idx]
        else:
            raise ValueError("Invalid item type")
    except (ValueError, IndexError):
        await callback.answer("⚠️ Ошибка: элемент не найден.")
        return
        
    data = await state.get_data()
    expertise = list(data.get("expertise", []))
    
    if item in expertise:
        expertise.remove(item)
    else:
        expertise.append(item)
        
    await state.update_data(expertise=expertise)
    await callback.answer(f"Изменено: {item}")
    try:
        skills = data.get("skills", [])
        tools = data.get("tools", [])
        await callback.message.edit_reply_markup(
            reply_markup=get_expertise_keyboard(skills, tools, expertise)
        )
    except Exception:
        pass

@router.callback_query(StateFilter(CharacterSetupStates.selecting_expertise), F.data == "done_expertise")
async def finish_expertise(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    try:
        await callback.message.delete()
    except Exception:
        pass
        
    if data.get("is_editing") and data.get("edit_field") == "expertise":
        await state.update_data(is_editing=False, edit_field=None)
        
    await state.set_state(CharacterSetupStates.reviewing_data)
    await callback.answer("Компетентность сохранена!")
    sent_msg = await callback.message.answer(
        _get_character_review_text(await state.get_data()),
        reply_markup=get_review_keyboard()
    )
    await state.update_data(last_bot_msg_id=sent_msg.message_id)

# =====================================================================
# ОБРАБОТЧИКИ ЭКРАНА ОБЗОРА И ПОДТВЕРЖДЕНИЯ ДАННЫХ (reviewing_data)
# =====================================================================

@router.callback_query(F.data == "review_edit")
async def handle_review_edit(callback: CallbackQuery, state: FSMContext):
    """Обрабатывает нажатие кнопки '✏️ Нужны правки' на экране обзора."""
    await state.set_state(CharacterSetupStates.editing_menu)
    await callback.answer()
    try:
        await callback.message.edit_text(
            "✏️ <b>Редактирование персонажа</b>\n\nВыберите, какой раздел вы хотите изменить:",
            reply_markup=get_edit_menu_keyboard()
        )
    except Exception:
        pass

@router.callback_query(F.data == "edit_back_to_review")
async def handle_edit_back_to_review(callback: CallbackQuery, state: FSMContext):
    """Обрабатывает нажатие кнопки '⬅️ Назад к обзору' в меню редактирования."""
    data = await state.get_data()
    await state.set_state(CharacterSetupStates.reviewing_data)
    await callback.answer()
    try:
        await callback.message.edit_text(
            _get_character_review_text(data),
            reply_markup=get_review_keyboard()
        )
    except Exception:
        pass

@router.callback_query(StateFilter(CharacterSetupStates.reviewing_data), F.data == "review_confirm")
async def confirm_character_data(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    user_id = callback.from_user.id
    
    # Формируем full_data с учетом выбранной компетентности
    existing_full_data = data.get("full_data", {})
    if not isinstance(existing_full_data, dict):
        existing_full_data = {}
        
    skills_list = data.get("skills", [])
    tools_list = data.get("tools", [])
    expertise_list = data.get("expertise", [])
    
    existing_full_data["skills"] = {s: ("expert" if s in expertise_list else "proficient") for s in skills_list}
    existing_full_data["tools"] = {t: ("expert" if t in expertise_list else "proficient") for t in tools_list}
    
    existing_full_data["name"] = data["name"]
    existing_full_data["class"] = data["char_class"]
    existing_full_data["proficiency_bonus"] = data["pb"]
    existing_full_data["mod_strength"] = data["mod_strength"]
    existing_full_data["mod_dexterity"] = data["mod_dexterity"]
    existing_full_data["mod_constitution"] = data["mod_constitution"]
    existing_full_data["mod_intelligence"] = data["mod_intelligence"]
    existing_full_data["mod_wisdom"] = data["mod_wisdom"]
    existing_full_data["mod_charisma"] = data["mod_charisma"]
    existing_full_data["saving_throws"] = data.get("saving_throws", [])
    
    full_data_str = json.dumps(existing_full_data, ensure_ascii=False)
    
    # Сохраняем в базу данных
    await DatabaseService.save_character(
        user_id=user_id,
        name=data["name"],
        char_class=data["char_class"],
        proficiency_bonus=data["pb"],
        mod_strength=data["mod_strength"],
        mod_dexterity=data["mod_dexterity"],
        mod_constitution=data["mod_constitution"],
        mod_intelligence=data["mod_intelligence"],
        mod_wisdom=data["mod_wisdom"],
        mod_charisma=data["mod_charisma"],
        saving_throws=data.get("saving_throws", []),
        skills=data.get("skills", []),
        tools=data.get("tools", []),
        full_data=full_data_str,
        char_id=data.get("char_id")
    )
    
    # Очищаем сессионный ID создания, так как персонаж создан и сохранен!
    await state.update_data(binding_char_name=data["name"], is_new_creation=False, creation_session_id=None)
    await state.set_state(None)
    
    try:
        await callback.message.delete()
    except Exception:
        pass
        
    await callback.answer("Персонаж успешно сохранен!")
    
    # Сразу переводим в меню управления привязками
    bindings = await DatabaseService.get_character_bindings(user_id, data["name"])
    bindings_text = "<i>Привязки отсутствуют. Персонаж не привязан ни к одному чату/теме.</i>\n"
    
    text = (
        f"🎉 <b>Персонаж {data['name']} успешно создан!</b>\n\n"
        f"🔗 <b>Управление привязками персонажа {data['name']}:</b>\n\n"
        f"Текущие привязки:\n{bindings_text}\n"
        f"Вы можете привязать персонажа к чату/разделу или завершить настройку."
    )
    
    sent_msg = await callback.message.answer(
        text,
        reply_markup=get_bindings_management_keyboard(bindings)
    )
    await state.update_data(last_bot_msg_id=sent_msg.message_id)

@router.callback_query(F.data == "manage_bindings_menu")
async def handle_manage_bindings_menu(callback: CallbackQuery, state: FSMContext):
    """Отображает список текущих привязок персонажа и позволяет управлять ими."""
    user_id = callback.from_user.id
    active_char = await DatabaseService.get_character(user_id)
    if not active_char:
        await callback.answer("⚠️ Сначала выберите или создайте активного персонажа!", show_alert=True)
        return
        
    char_name = active_char["name"]
    await state.update_data(binding_char_name=char_name)
    
    # Сбрасываем временные параметры привязки к другому чату, если они были сохранены
    await state.update_data(binding_chat_id=None, binding_chat_title=None)
    await state.set_state(None)
    
    bindings = await DatabaseService.get_character_bindings(user_id, char_name)
    bindings_text = ""
    if bindings:
        for i, b in enumerate(bindings, 1):
            name = b.get("topic_name") or f"Чат {b['chat_id'][:8]}..."
            bindings_text += f"{i}. <b>{name}</b>\n"
    else:
        bindings_text = "<i>Привязки отсутствуют. Персонаж не привязан ни к одному чату/теме.</i>\n"
        
    text = (
        f"🔗 <b>Управление привязками персонажа {char_name}:</b>\n\n"
        f"Текущие привязки:\n{bindings_text}\n"
        f"Вы можете привязать персонажа к чату/разделу или удалить существующие привязки."
    )
    
    await callback.message.edit_text(
        text,
        reply_markup=get_bindings_management_keyboard(bindings)
    )
    await callback.answer()

@router.callback_query(F.data == "bind_menu")
async def handle_bind_menu(callback: CallbackQuery, state: FSMContext):
    """Отображает опции привязки (к текущему чату/теме или по ссылке)."""
    user_id = callback.from_user.id
    data = await state.get_data()
    char_name = data.get("binding_char_name")
    
    if not char_name:
        active_char = await DatabaseService.get_character(user_id)
        if not active_char:
            await callback.answer("⚠️ Сначала выберите или создайте активного персонажа!", show_alert=True)
            return
        char_name = active_char["name"]
        await state.update_data(binding_char_name=char_name)

    await state.set_state(CharacterSetupStates.waiting_for_binding_link)
    
    chat_type = callback.message.chat.type
    await callback.message.edit_text(
        f"🔗 <b>Привязка персонажа {char_name}</b>\n\n"
        f"Выберите способ привязки:\n"
        f"• <b>Тема</b> — привязать к теме (разделу) текущего чата или к самому чату.\n"
        f"• <b>Еще один чат</b> — привязать к другому чату по ссылке/ID (бот должен быть участником).",
        reply_markup=get_bind_options_keyboard(chat_type)
    )
    await callback.answer()

@router.callback_query(StateFilter(CharacterSetupStates.waiting_for_binding_link), F.data == "bind_by_link")
async def handle_bind_by_link(callback: CallbackQuery, state: FSMContext):
    """Запрашивает ссылку/ID чата для привязки."""
    data = await state.get_data()
    char_name = data.get("binding_char_name")
    
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="bind_menu"))
    
    await callback.message.edit_text(
        f"🔗 <b>Привязка {char_name} по ссылке/ID чата</b>\n\n"
        f"Отправьте в этот чат:\n"
        f"• Ссылку на чат/тему (например, <code>t.me/c/123456789/105</code> или <code>https://t.me/public_chat/105</code>)\n"
        f"• Либо ID чата в формате <code>chat_id:thread_id</code> (например, <code>-100123456789:105</code>).\n\n"
        f"<i>Убедитесь, что бот добавлен в целевую группу!</i>",
        reply_markup=builder.as_markup()
    )
    await callback.answer()

@router.callback_query(StateFilter(CharacterSetupStates.waiting_for_binding_link), F.data == "bind_current_chat_topics")
async def handle_bind_current_chat_topics(callback: CallbackQuery, state: FSMContext):
    """Показывает список разделов текущего чата для быстрой привязки."""
    chat_id = callback.message.chat.id
    user_id = callback.from_user.id
    
    data = await state.get_data()
    char_name = data.get("binding_char_name")
    
    topics = await DatabaseService.get_chat_topics(chat_id)
    
    await callback.message.edit_text(
        f"💬 <b>Привязка {char_name} к теме текущего чата</b>\n\n"
        f"Выберите раздел чата, в котором этот персонаж будет активен по умолчанию:",
        reply_markup=get_chat_topics_keyboard(topics, show_back=True)
    )
    await callback.answer()

@router.callback_query(F.data == "back_to_chars")
async def handle_back_to_chars(callback: CallbackQuery, state: FSMContext):
    """Возвращает в основное меню списка персонажей."""
    await state.clear()
    user_id = callback.from_user.id
    characters = await DatabaseService.get_all_characters(user_id)
    
    if not characters:
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text="➕ Создать первого персонажа", callback_data="create_new_char"))
        await callback.message.edit_text(
            "👥 <b>У вас еще нет созданных персонажей!</b>\n\n"
            "Давайте создадим вашего первого героя для игры в D&D 5e.",
            reply_markup=builder.as_markup()
        )
        return
        
    active_char = next((c for c in characters if c.get("is_active") == 1), None)
    active_name = active_char["name"] if active_char else "не выбран"
    
    chat_id = callback.message.chat.id
    thread_id = callback.message.message_thread_id
    bound_names = await DatabaseService.get_user_bound_character_names(user_id, chat_id, thread_id)
    
    await callback.message.edit_text(
        f"👥 <b>Ваши персонажи:</b>\n"
        f"Текущий активный персонаж: <b>{active_name}</b>\n\n"
        f"<i>Кликните на имя персонажа, чтобы сделать его активным для проверок.</i>",
        reply_markup=get_characters_management_keyboard(characters, bound_char_name=bound_names)
    )
    await callback.answer()

@router.callback_query(StateFilter(CharacterSetupStates.waiting_for_binding_link), F.data == "skip_binding")
async def handle_skip_binding(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    report = _get_character_report_from_data(data)
    
    await state.clear()
    await callback.answer("Привязка пропущена")
    await callback.message.delete()
    markup = await get_dice_keyboard_for_user(callback.from_user.id)
    text = f"🎉 <b>Персонаж успешно сохранен!</b>\n\n{report}"
    if callback.message.reply_to_message:
        await callback.message.reply_to_message.reply(text, reply_markup=markup)
    else:
        mention = callback.from_user.mention_html()
        await callback.message.answer(f"{mention}, {text}", reply_markup=markup)

@router.callback_query(StateFilter(CharacterSetupStates.waiting_for_binding_link), F.data.startswith("select_topic_bind:"))
async def handle_select_topic_bind(callback: CallbackQuery, state: FSMContext):
    raw_thread_id = callback.data.split(":", 1)[1]
    
    # Разрешаем оригинальный thread_id
    if raw_thread_id == "None":
        thread_id = None
    else:
        # Находим полный хэш темы по первым 8 символам префикса
        chat_id = callback.message.chat.id
        topics = await DatabaseService.get_chat_topics(chat_id)
        full_hash = None
        for t in topics:
            if t["thread_id"].startswith(raw_thread_id):
                full_hash = t["thread_id"]
                break
        
        if full_hash:
            thread_id = DatabaseService.resolve_thread_id(full_hash)
        else:
            thread_id = None

    data = await state.get_data()
    char_name = data.get("binding_char_name")
    user_id = callback.from_user.id
    chat_id = callback.message.chat.id
    
    # Производим привязку!
    await DatabaseService.bind_character(
        user_id, chat_id, thread_id, char_name,
        tg_username=callback.from_user.username,
        tg_first_name=callback.from_user.first_name
    )
    
    # Сохраняем имя чата/темы для отображения в списке привязок
    chat_title = callback.message.chat.title or callback.message.chat.full_name or "Групповой чат"
    name_to_save = chat_title
    if thread_id is not None:
        topics = await DatabaseService.get_chat_topics(chat_id)
        hashed_thread = _hash_thread_id(thread_id)
        topic_name_str = f"Тема №{thread_id}"
        for t in topics:
            if t["thread_id"] == hashed_thread:
                topic_name_str = t["name"]
                break
        name_to_save = f"{chat_title} (раздел «{topic_name_str}»)"
    await DatabaseService.save_chat_topic(chat_id, thread_id, name_to_save)
    
    # Получаем красивое название темы
    topic_name = "Общий раздел / Вся группа"
    if thread_id is not None:
        topics = await DatabaseService.get_chat_topics(chat_id)
        hashed_thread = _hash_thread_id(thread_id)
        for t in topics:
            if t["thread_id"] == hashed_thread:
                topic_name = f"Раздел «{t['name']}»"
                break
                
    await callback.answer(f"Персонаж {char_name} успешно привязан!")
    try:
        await callback.message.delete()
    except Exception:
        pass
        
    # Показываем меню управления привязками
    bindings = await DatabaseService.get_character_bindings(user_id, char_name)
    bindings_text = ""
    if bindings:
        for i, b in enumerate(bindings, 1):
            name = b.get("topic_name") or f"Чат {b['chat_id'][:8]}..."
            bindings_text += f"{i}. <b>{name}</b>\n"
    else:
        bindings_text = "<i>Привязки отсутствуют. Персонаж не привязан ни к одному чату/теме.</i>\n"
        
    text = (
        f"✅ <b>Успешно привязано!</b>\n"
        f"Персонаж <b>{char_name}</b> привязан к разделу: <b>{topic_name}</b>\n\n"
        f"🔗 <b>Текущие привязки:</b>\n{bindings_text}\n"
        f"Выберите действие ниже:"
    )
    
    await state.clear()
    await callback.message.answer(
        text,
        reply_markup=get_bindings_management_keyboard(bindings)
    )

@router.message(StateFilter(CharacterSetupStates.waiting_for_binding_link))
async def process_binding_link(message: Message, state: FSMContext):
    # Защита от сообщений без текста (фото, стикеры и т.д.)
    if not message.text:
        await message.answer(
            "⚠️ Пожалуйста, отправьте текстовую ссылку/ID для привязки "
            "или нажмите кнопку пропуска под предыдущим сообщением."
        )
        return

    text = message.text.strip()
    
    # Если пользователь вводит команду отмены или пропуска
    if text.lower() in ["/cancel", "отмена", "пропустить", "/skip"]:
        await state.clear()
        markup = await get_dice_keyboard_for_user(message.from_user.id)
        await message.reply("❌ Привязка пропущена. Ваш персонаж сохранен!", reply_markup=markup)
        return
        
    # Если пользователь решил сделать бросок прямо во время привязки, автоматически завершаем создание
    if text.startswith("!") or text.startswith("🎲"):
        await state.clear()
        from handlers.roller import handle_direct_text_input
        await handle_direct_text_input(message, state)
        return
        
    # Если пользователь ввел любую другую команду
    if text.startswith("/"):
        await state.clear()
        if text.startswith("/start"):
            from handlers.common import cmd_start
            await cmd_start(message)
        elif text.startswith("/help"):
            from handlers.common import cmd_help
            await cmd_help(message)
        elif text.startswith("/keyboard"):
            from handlers.common import cmd_keyboard
            await cmd_keyboard(message)
        elif text.startswith("/characters"):
            await list_characters_menu(message, state)
        elif text.startswith("/create_character"):
            await start_character_setup(message, state)
        elif text.startswith("/stop"):
            from handlers.common import cmd_stop
            await cmd_stop(message)
        else:
            await message.answer("🧙‍♂️ Лист персонажа сохранен. Создание успешно завершено!")
        return

    data = await state.get_data()
    char_name = data.get("binding_char_name")
    user_id = message.from_user.id
    
    # Пытаемся распарсить ссылку
    chat_id, thread_id, error_msg = await parse_telegram_link(text, message.bot)
    
    if error_msg:
        await message.answer(
            f"⚠️ <b>Ошибка привязки:</b> {error_msg}\n\n"
            f"Пожалуйста, проверьте ссылку/ID и попробуйте еще раз, "
            f"или нажмите кнопку пропуска под предыдущим сообщением."
        )
        return
        
    # Проверяем доступность чата
    try:
        chat = await message.bot.get_chat(chat_id)
        chat_title = chat.title or chat.full_name or "Чат"
    except Exception as e:
        await message.answer(
            f"⚠️ <b>Не удалось получить доступ к чату!</b>\n\n"
            f"Бот должен быть участником чата/супергруппы, чтобы привязать к ней персонажа. "
            f"Убедитесь, что бот добавлен в этот чат, и пришлите ссылку заново."
        )
        return
        
    # Сохраняем привязку
    await DatabaseService.bind_character(
        user_id, chat_id, thread_id, char_name,
        tg_username=message.from_user.username,
        tg_first_name=message.from_user.first_name
    )
    
    # Получаем название темы, если есть thread_id
    topic_info = ""
    if thread_id is not None:
        topics = await DatabaseService.get_chat_topics(chat_id)
        hashed_thread = _hash_thread_id(thread_id)
        topic_name = f"Тема №{thread_id}"
        for t in topics:
            if t["thread_id"] == hashed_thread:
                topic_name = t["name"]
                break
        topic_info = f" (раздел «{topic_name}»)"
        
    report = _get_character_report_from_data(data)
    
    await state.clear()
    markup = await get_dice_keyboard_for_user(user_id)
    await message.reply(
        f"🔗 <b>Успешно привязано!</b>\n"
        f"Персонаж <b>{char_name}</b> привязан к чату <b>{chat_title}</b>{topic_info}.\n\n"
        f"{report}",
        reply_markup=markup
    )

@router.callback_query(F.data == "bind_active_to_chat")
async def handle_bind_active_to_chat(callback: CallbackQuery):
    user_id = callback.from_user.id
    chat_id = callback.message.chat.id
    chat_type = callback.message.chat.type
    
    if chat_type == "private":
        await callback.answer("⚠️ Привязать к текущему чату можно только находясь в групповом чате или теме форума!", show_alert=True)
        return
        
    active_char = await DatabaseService.get_character(user_id)
    if not active_char:
        await callback.answer("⚠️ У вас нет активного персонажа для привязки!", show_alert=True)
        return
        
    thread_id = callback.message.message_thread_id
    await DatabaseService.bind_character(
        user_id, chat_id, thread_id, active_char["name"],
        tg_username=callback.from_user.username,
        tg_first_name=callback.from_user.first_name
    )
    
    await callback.answer(f"🔗 Персонаж {active_char['name']} успешно привязан к этому разделу чата!", show_alert=True)
    
    # И обновим клавиатуру, чтобы подсветить изменения
    characters = await DatabaseService.get_all_characters(user_id)
    bound_names = await DatabaseService.get_user_bound_character_names(user_id, chat_id, thread_id)
    
    try:
        await callback.message.edit_reply_markup(
            reply_markup=get_characters_management_keyboard(characters, bound_char_name=bound_names)
        )
    except Exception:
        pass
