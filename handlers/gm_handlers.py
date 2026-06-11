import re
import json
from typing import Optional, List, Dict, Any
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from services.db import DatabaseService, _hash_user_id

router = Router(name="gm_handlers")

def format_check_request_text(
    check_type: str,
    dc: Optional[int],
    description: Optional[str],
    target_characters: List[str],
    passed_characters: List[Dict[str, Any]],
    is_closed: bool = False,
    bound_characters: Optional[List[Dict[str, Any]]] = None
) -> str:
    """Форматирует карточку проверки с результатами, тегами владельцев персонажей и значками ОК / Не ОК."""
    char_to_tag = {}
    if bound_characters:
        for bc in bound_characters:
            name_lower = bc["char_name"].lower()
            if bc["tg_username"]:
                char_to_tag[name_lower] = f"@{bc['tg_username']}"
            else:
                char_to_tag[name_lower] = bc["tg_first_name"] or bc["char_name"]

    targets_list = []
    for t in target_characters:
        name_title = t.title()
        tag = char_to_tag.get(t.lower())
        if tag:
            targets_list.append(f"{name_title} ({tag})")
        else:
            targets_list.append(name_title)
            
    targets_str = ", ".join(targets_list) if target_characters != ["all"] else "Все персонажи"
    desc_str = f"\n📝 <b>Описание</b>: {description}" if description else ""
    
    dc_str = f" (Сложность: {dc})" if dc is not None else ""
    
    text = (
        f"⚔️ <b>Заявка на проверку от Мастера</b>\n"
        f"🎯 <b>Проверка</b>: <code>{check_type}</code>{dc_str}"
        f"{desc_str}\n"
        f"👥 <b>Кому пройти</b>: {targets_str}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📊 <b>Статус проверки</b>:\n"
    )
    
    if target_characters == ["all"]:
        if not passed_characters:
            text += "⏳ Ожидание первых бросков...\n"
        else:
            for passed in passed_characters:
                status_icon = "✅"
                if dc is not None:
                    status_icon = "🟢 ОК" if passed["result"] >= dc else "🔴 Провал"
                
                passed_tag = char_to_tag.get(passed["char_name"].lower(), "")
                tag_suffix = f" ({passed_tag})" if passed_tag else ""
                text += f"{status_icon} <b>{passed['char_name']}</b>{tag_suffix}: <b>{passed['result']}</b> ({passed['roll_detail']})\n"
    else:
        for char in target_characters:
            passed_info = next((p for p in passed_characters if p["char_name"].lower() == char.lower()), None)
            tag = char_to_tag.get(char.lower(), "")
            tag_suffix = f" ({tag})" if tag else ""
            
            if passed_info:
                status_icon = "✅"
                if dc is not None:
                    status_icon = "🟢 ОК" if passed_info["result"] >= dc else "🔴 Провал"
                text += f"{status_icon} <b>{passed_info['char_name']}</b>{tag_suffix}: <b>{passed_info['result']}</b> ({passed_info['roll_detail']})\n"
            else:
                text += f"⏳ <b>{char.title()}</b>{tag_suffix}: Ожидает броска\n"
                
    if is_closed:
        text += f"\n⏹ <b>Проверка завершена Мастером!</b>"
    elif target_characters != ["all"] and len(passed_characters) >= len(target_characters):
        passed_names = {p["char_name"].lower() for p in passed_characters}
        if all(t in passed_names for t in target_characters):
            text += f"\n✨ <b>Все участники успешно прошли проверку!</b>"
        
    return text

def get_check_request_keyboard(request_id: int, is_active: bool = True):
    """Возвращает кнопки действий для карточки проверки."""
    builder = InlineKeyboardBuilder()
    if is_active:
        builder.row(
            InlineKeyboardButton(text="🎲 Пройти проверку", callback_data=f"run_request_check:{request_id}"),
            InlineKeyboardButton(text="⏹ Завершить проверку", callback_data=f"close_request_check:{request_id}")
        )
    return builder.as_markup()

async def get_mention_prefix_for_request(chat_id: int, thread_id: Optional[int], target_characters: List[str]) -> str:
    """Формирует строку упоминания игроков для выбранных персонажей."""
    if not target_characters or target_characters == ["all"]:
        return ""
    bound_chars = await DatabaseService.get_bound_characters_in_chat(chat_id, thread_id)
    tags = []
    selected_set = {n.lower() for n in target_characters}
    for bc in bound_chars:
        if bc["char_name"].lower() in selected_set:
            if bc["tg_username"]:
                tags.append(f"@{bc['tg_username']}")
            else:
                tags.append(bc["tg_first_name"] or bc["char_name"])
    tags_str = ", ".join(tags)
    return f"🔔 <b>Призываются:</b> {tags_str}\n\n" if tags else ""

def get_setup_keyboard(request_id: int, bound_chars: List[Dict[str, Any]], selected_names: List[str]):
    """Генерирует инлайн-клавиатуру настройки целей проверки для GM."""
    builder = InlineKeyboardBuilder()
    selected_set = {n.lower() for n in selected_names}
    
    # Кнопки для каждого привязанного персонажа
    for char in bound_chars:
        name = char["char_name"]
        is_selected = name.lower() in selected_set
        prefix = "✅" if is_selected else "❌"
        builder.row(InlineKeyboardButton(text=f"{prefix} {name}", callback_data=f"t_ch:{request_id}:{name}"))
        
    # Управление
    builder.row(
        InlineKeyboardButton(text="👥 Выбрать всех", callback_data=f"setup_all:{request_id}"),
        InlineKeyboardButton(text="🧹 Сбросить", callback_data=f"setup_clear:{request_id}")
    )
    builder.row(
        InlineKeyboardButton(text="🚀 Создать проверку", callback_data=f"setup_launch:{request_id}")
    )
    return builder.as_markup()

@router.message(Command("gm_check", "request_check"))
async def cmd_gm_check(message: Message):
    """Команда создания запроса на проверку от Мастера."""
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer(
            "✍️ <b>Мастер игры, чтобы создать проверку, используйте формат:</b>\n"
            "<code>/gm_check [проверка] | [Описание]</code>\n\n"
            "Примеры:\n"
            "• <code>/gm_check Атлетика кс 15 | Перелезть через забор</code>\n"
            "• <code>/gm_check Спасбросок Ловкости кс 12 | Избежать ловушки</code>"
        )
        return
        
    content = args[1].strip()
    
    # Парсим описание
    description = None
    if "|" in content:
        content_part, desc_part = content.split("|", 1)
        content = content_part.strip()
        description = desc_part.strip()
        
    check_type = content.strip()
    
    # Парсим DC/Сложность
    dc = None
    dc_match = re.search(r'(?:\s*\(?(?:кс|dc|сложность|дц)\s*(\d+)\)?)', check_type, re.IGNORECASE)
    if dc_match:
        dc = int(dc_match.group(1))
        # Очищаем название проверки от указания сложности
        check_type = check_type.replace(dc_match.group(0), "").strip()
        
    chat_id = message.chat.id
    thread_id = message.message_thread_id
    creator_id = message.from_user.id
    
    # Проверяем, есть ли привязанные персонажи в этом чате/теме
    bound_chars = await DatabaseService.get_bound_characters_in_chat(chat_id, thread_id)
    if not bound_chars:
        await message.answer(
            "⚠️ <b>В этой теме еще нет привязанных персонажей!</b>\n\n"
            "Игроки должны привязать своих персонажей через Reply-меню <code>👥 Персонажи</code> -> выбрать персонажа -> <code>🔗 Привязать к чату</code>, "
            "чтобы они отобразились в списке выбора Мастера."
        )
        return
        
    # Создаем черновик проверки (is_active = -1)
    request_id = await DatabaseService.create_check_request(
        chat_id=chat_id,
        thread_id=thread_id,
        check_type=check_type,
        dc=dc,
        description=description,
        target_characters=[], # Изначально пустой выбор
        creator_id=creator_id
    )
    
    # Принудительно устанавливаем черновику статус -1 в БД
    from services.db import DB_PATH
    import aiosqlite
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE check_requests SET is_active = -1 WHERE id = ?", (request_id,))
        await db.commit()
        
    # Отправляем меню настройки
    dc_display = f" (Сложность: {dc})" if dc is not None else ""
    desc_display = f"\n📝 Описание: {description}" if description else ""
    
    sent_msg = await message.answer(
        f"🛠️ <b>Настройка проверки от Мастера</b>\n"
        f"🎯 Проверка: <code>{check_type}</code>{dc_display}{desc_display}\n\n"
        f"Выберите персонажей, которые должны пройти проверку:",
        reply_markup=get_setup_keyboard(request_id, bound_chars, [])
    )
    
    # Временно сохраняем ID сообщения настройки
    await DatabaseService.set_check_request_message_id(request_id, sent_msg.message_id)
    
    try:
        await message.delete()
    except Exception:
        pass

@router.callback_query(F.data.startswith("t_ch:"))
async def handle_toggle_char(callback: CallbackQuery):
    """Переключение выбора персонажа в черновике проверки."""
    _, request_id_str, char_name = callback.data.split(":", 2)
    request_id = int(request_id_str)
    
    req = await DatabaseService.get_check_request_by_id(request_id)
    if not req or req["is_active"] != -1:
        await callback.answer("⚠️ Эта настройка устарела.")
        return
        
    hashed_user = _hash_user_id(callback.from_user.id)
    if hashed_user != req["creator_id"]:
        await callback.answer("⚠️ Только Мастер игры, запустивший настройку, может выбирать цели!", show_alert=True)
        return
        
    selected = list(req["target_characters"])
    char_name_lower = char_name.lower()
    
    if char_name_lower in selected:
        selected.remove(char_name_lower)
    else:
        selected.append(char_name_lower)
        
    from services.db import DB_PATH
    import aiosqlite
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE check_requests SET target_characters = ? WHERE id = ?",
            (json.dumps(selected, ensure_ascii=False), request_id)
        )
        await db.commit()
        
    bound_chars = await DatabaseService.get_bound_characters_in_chat(callback.message.chat.id, callback.message.message_thread_id)
    
    await callback.answer()
    try:
        await callback.message.edit_reply_markup(
            reply_markup=get_setup_keyboard(request_id, bound_chars, selected)
        )
    except Exception:
        pass

@router.callback_query(F.data.startswith("setup_all:") | F.data.startswith("setup_clear:"))
async def handle_setup_controls(callback: CallbackQuery):
    """Выбрать всех / Сбросить всех в черновике."""
    action, request_id_str = callback.data.split(":", 1)
    request_id = int(request_id_str)
    
    req = await DatabaseService.get_check_request_by_id(request_id)
    if not req or req["is_active"] != -1:
        await callback.answer("⚠️ Эта настройка устарела.")
        return
        
    hashed_user = _hash_user_id(callback.from_user.id)
    if hashed_user != req["creator_id"]:
        await callback.answer("⚠️ Только Мастер игры может изменять цели!", show_alert=True)
        return
        
    bound_chars = await DatabaseService.get_bound_characters_in_chat(callback.message.chat.id, callback.message.message_thread_id)
    
    if action == "setup_all":
        selected = [c["char_name"].lower() for c in bound_chars]
    else:
        selected = []
        
    from services.db import DB_PATH
    import aiosqlite
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE check_requests SET target_characters = ? WHERE id = ?",
            (json.dumps(selected, ensure_ascii=False), request_id)
        )
        await db.commit()
        
    await callback.answer()
    try:
        await callback.message.edit_reply_markup(
            reply_markup=get_setup_keyboard(request_id, bound_chars, selected)
        )
    except Exception:
        pass

@router.callback_query(F.data.startswith("setup_launch:"))
async def handle_setup_launch(callback: CallbackQuery):
    """Активация и публикация проверки."""
    request_id = int(callback.data.split(":", 1)[1])
    
    req = await DatabaseService.get_check_request_by_id(request_id)
    if not req or req["is_active"] != -1:
        await callback.answer("⚠️ Эта настройка устарела.")
        return
        
    hashed_user = _hash_user_id(callback.from_user.id)
    if hashed_user != req["creator_id"]:
        await callback.answer("⚠️ Только Мастер игры может запускать проверку!", show_alert=True)
        return
        
    selected = req["target_characters"]
    if not selected:
        await callback.answer("⚠️ Выберите хотя бы одного персонажа!", show_alert=True)
        return
        
    from services.db import DB_PATH
    import aiosqlite
    async with aiosqlite.connect(DB_PATH) as db:
        hashed_chat = req["chat_id"]
        hashed_thread = req["thread_id"]
        # Деактивируем любые другие активные
        await db.execute("""
            UPDATE check_requests 
            SET is_active = 0 
            WHERE chat_id = ? AND thread_id = ? AND is_active = 1
        """, (hashed_chat, hashed_thread))
        
        # Активируем текущую
        await db.execute(
            "UPDATE check_requests SET is_active = 1 WHERE id = ?",
            (request_id,)
        )
        await db.commit()
        
    await callback.answer("Проверка успешно запущена!")
    
    bound_chars = await DatabaseService.get_bound_characters_in_chat(callback.message.chat.id, callback.message.message_thread_id)
    
    mention_prefix = await get_mention_prefix_for_request(
        callback.message.chat.id, callback.message.message_thread_id, selected
    )
    
    card_text = format_check_request_text(
        check_type=req["check_type"],
        dc=req["dc"],
        description=req["description"],
        target_characters=selected,
        passed_characters=[],
        bound_characters=bound_chars
    )
    
    sent_msg = await callback.message.edit_text(
        f"{mention_prefix}{card_text}",
        reply_markup=get_check_request_keyboard(request_id, is_active=True)
    )
    
    await DatabaseService.set_check_request_message_id(request_id, sent_msg.message_id)

@router.callback_query(F.data.startswith("close_request_check:"))
async def handle_close_request_check(callback: CallbackQuery):
    """Callback для принудительного завершения проверки Мастером."""
    request_id_str = callback.data.split(":", 1)[1]
    try:
        request_id = int(request_id_str)
    except ValueError:
        await callback.answer("⚠️ Ошибка: неверный ID запроса.")
        return
        
    req = await DatabaseService.get_check_request_by_id(request_id)
    if not req:
        await callback.answer("⚠️ Проверка не найдена!")
        return
        
    user_id = callback.from_user.id
    hashed_user = _hash_user_id(user_id)
    
    is_allowed = (hashed_user == req["creator_id"])
    
    if not is_allowed:
        try:
            member = await callback.bot.get_chat_member(callback.message.chat.id, user_id)
            if member.status in ("administrator", "creator"):
                is_allowed = True
        except Exception:
            pass
            
    if not is_allowed:
        await callback.answer(
            "⚠️ Только Мастер игры, создавший проверку, или администраторы чата могут завершить ее!",
            show_alert=True
        )
        return
        
    await DatabaseService.close_check_request(request_id)
    await callback.answer("Проверка завершена")
    
    bound_chars = await DatabaseService.get_bound_characters_in_chat(callback.message.chat.id, callback.message.message_thread_id)
    
    updated_text = format_check_request_text(
        check_type=req["check_type"],
        dc=req["dc"],
        description=req["description"],
        target_characters=req["target_characters"],
        passed_characters=req["passed_characters"],
        is_closed=True,
        bound_characters=bound_chars
    )
    
    mention_prefix = await get_mention_prefix_for_request(
        callback.message.chat.id, callback.message.message_thread_id, req["target_characters"]
    )
    
    try:
        await callback.message.edit_text(
            f"{mention_prefix}{updated_text}",
            reply_markup=None
        )
    except Exception:
        pass
