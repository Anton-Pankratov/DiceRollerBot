import re
import random
from typing import Optional
from aiogram import Router, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from services.roller import DiceRollerService
from services.db import DatabaseService, _hash_thread_id, _hash_chat_id
from keyboards.roller_kb import get_dice_keyboard, get_dice_keyboard_for_user

async def _get_kb(msg_or_cb, mode: str = "normal"):
    user_id = msg_or_cb.from_user.id
    return await get_dice_keyboard_for_user(user_id, mode)

async def _send_dice_sticker(message: Message, sides: int, result: Optional[int] = None):
    """Отправляет анимированный стикер броска дайса, учитывая выпавший результат, если настроен."""
    import config
    
    # 1. Проверяем, есть ли стикер под конкретный результат (например, грань d20 с нужной цифрой)
    if result is not None:
        result_map = config.DICE_RESULT_STICKERS.get(sides)
        if result_map:
            sticker_id = result_map.get(result)
            if sticker_id:
                try:
                    await message.answer_sticker(sticker_id)
                    return
                except Exception:
                    pass
                    
    # 2. Если конкретный результат не настроен, отправляем общий стикер броска кубика данного типа
    sticker_id = config.DICE_STICKERS.get(sides)
    if sticker_id:
        try:
            await message.answer_sticker(sticker_id)
        except Exception:
            pass

router = Router(name="roller")

DUMMY_CHARACTER = {
    "name": "Без персонажа",
    "class": "Обычный бросок",
    "proficiency_bonus": 0,
    "mod_strength": 0,
    "mod_dexterity": 0,
    "mod_constitution": 0,
    "mod_intelligence": 0,
    "mod_wisdom": 0,
    "mod_charisma": 0,
    "saving_throws": [],
    "skills": [],
    "tools": [],
    "custom_formulas": {}
}

# Регулярное выражение для обычного броска дайса (d20, d100, 15, d4)
DICE_PATTERN = re.compile(r'^(🎲\s*d|[dд])?\d+$', re.IGNORECASE)

# Регулярное выражение для формул бросков типа 2d6, 1d20+5, 8d6-1, d12
FORMULA_PATTERN = re.compile(r'^(\d*)[dд](\d+)(?:([+-])(\d+))?$', re.IGNORECASE)

# Маппинги 6 стандартных характеристик D&D 5e
ATTR_MAPPING = {
    "сила": {"name": "Сила", "db_field": "mod_strength"},
    "ловкость": {"name": "Ловкость", "db_field": "mod_dexterity"},
    "телосложение": {"name": "Телосложение", "db_field": "mod_constitution"},
    "интеллект": {"name": "Интеллект", "db_field": "mod_intelligence"},
    "мудрость": {"name": "Мудрость", "db_field": "mod_wisdom"},
    "харизма": {"name": "Харизма", "db_field": "mod_charisma"}
}

# Маппинги 18 стандартных навыков D&D 5e на их базовые характеристики
SKILL_MAPPING = {
    "атлетика": {"name": "Атлетика", "attr": "сила"},
    "акробатика": {"name": "Акробатика", "attr": "ловкость"},
    "ловкость рук": {"name": "Ловкость рук", "attr": "ловкость"},
    "скрытность": {"name": "Скрытность", "attr": "ловкость"},
    "анализ": {"name": "Анализ", "attr": "интеллект"},
    "история": {"name": "История", "attr": "интеллект"},
    "магия": {"name": "Магия", "attr": "интеллект"},
    "природа": {"name": "Природа", "attr": "интеллект"},
    "религия": {"name": "Религия", "attr": "интеллект"},
    "уход за животными": {"name": "Уход за животными", "attr": "мудрость"},
    "внимательность": {"name": "Внимательность", "attr": "мудрость"},
    "проницательность": {"name": "Проницательность", "attr": "мудрость"},
    "медицина": {"name": "Медицина", "attr": "мудрость"},
    "выживание": {"name": "Выживание", "attr": "мудрость"},
    "обман": {"name": "Обман", "attr": "харизма"},
    "запугивание": {"name": "Запугивание", "attr": "харизма"},
    "выступление": {"name": "Выступление", "attr": "харизма"},
    "убеждение": {"name": "Убеждение", "attr": "харизма"}
}

from keyboards.setup_kb import ALL_TOOLS

# Построим словарь соответствий вводимых пользователем слов каноничным названиям инструментов
TOOL_MATCH_MAP = {}
for tool in ALL_TOOLS:
    TOOL_MATCH_MAP[tool.lower()] = tool
    
    # Также добавляем сокращенные названия без префиксов "игровой набор: " и "музыкальный инструмент: "
    if "игровой набор: " in tool.lower():
        short = tool.lower().replace("игровой набор: ", "")
        TOOL_MATCH_MAP[short] = tool
    elif "музыкальный инструмент: " in tool.lower():
        short = tool.lower().replace("музыкальный инструмент: ", "")
        TOOL_MATCH_MAP[short] = tool

def roll_custom_formula(formula_expr: str) -> tuple[int, list[int], int, str]:
    """
    Парсит формулу вида "2d6+4", "d20-1", "8d6" и совершает бросок.
    Возвращает: (итоговый_результат, список_бросков_кубиков, модификатор, текстовая_формула)
    """
    clean = formula_expr.replace(" ", "").lower()
    
    # Регулярка для разбора: ([кол-во])d([грани])([+-][модификатор])?
    match = re.match(r'^(\d*)[dд](\d+)(?:([+-])(\d+))?$', clean)
    if not match:
        raise ValueError("Некорректный формат формулы.")
        
    num_dice_str, sides_str, sign, mod_str = match.groups()
    
    num_dice = int(num_dice_str) if num_dice_str else 1
    sides = int(sides_str)
    
    mod = 0
    if sign and mod_str:
        val = int(mod_str)
        mod = val if sign == '+' else -val
        
    # Бросаем кубики
    rolls = [random.randint(1, sides) for _ in range(num_dice)]
    sum_rolls = sum(rolls)
    total = sum_rolls + mod
    
    # Формируем красивую формулу
    rolls_str = " + ".join(map(str, rolls))
    if num_dice > 1:
        formula_str = f"({rolls_str})"
    else:
        formula_str = f"{sum_rolls}"
        
    if sign and mod_str:
        formula_str += f" {sign} {mod_str}"
        
    return total, rolls, mod, formula_str

# =====================================================================
# ОБРАБОТЧИКИ РЕЖИМОВ БРОСКА (ПРЕИМУЩЕСТВО / ПОМЕХА) НА REPLY-КЛАВИАТУРЕ
# =====================================================================

@router.message(F.text.startswith("🟢 Преимущество"))
async def set_advantage_mode(message: Message, state: FSMContext):
    await state.update_data(roll_mode="advantage")
    markup = await _get_kb(message, "advantage")
    await message.reply(
        "🟢 <b>Режим бросков: Преимущество</b>\n"
        "Следующий бросок будет совершен с преимуществом (бросок двух d20 и выбор максимального).",
        reply_markup=markup
    )

@router.message(F.text.startswith("⚪️ Обычный"))
async def set_normal_mode(message: Message, state: FSMContext):
    await state.update_data(roll_mode="normal")
    markup = await _get_kb(message, "normal")
    await message.reply(
        "⚪️ <b>Режим бросков: Обычный</b>\n"
        "Броски совершаются по стандартным правилам.",
        reply_markup=markup
    )

@router.message(F.text.startswith("🔴 Помеха"))
async def set_disadvantage_mode(message: Message, state: FSMContext):
    await state.update_data(roll_mode="disadvantage")
    markup = await _get_kb(message, "disadvantage")
    await message.reply(
        "🔴 <b>Режим бросков: Помеха</b>\n"
        "Следующий бросок будет совершен с помехой (бросок двух d20 и выбор минимального).",
        reply_markup=markup
    )

# =====================================================================
# ОБРАБОТЧИК КНОПОК РОЛЛА КАСТОМНЫХ ФОРМУЛ (CALLBACK)
# =====================================================================

@router.callback_query(F.data.startswith("roll_formula:"))
async def handle_roll_formula_callback(callback: CallbackQuery, state: FSMContext):
    formula_name = callback.data.split(":", 1)[1]
    user_id = callback.from_user.id
    
    character = await DatabaseService.get_character(user_id)
    if not character:
        await callback.answer("⚠️ Персонаж не найден!", show_alert=True)
        return
        
    formulas = character.get("custom_formulas", {})
    if formula_name not in formulas:
        await callback.answer(f"⚠️ Формула {formula_name} не найдена!", show_alert=True)
        return
        
    expr = formulas[formula_name]
    
    # Парсим и бросаем
    try:
        total, rolls, mod, formula_str = roll_custom_formula(expr)
    except Exception as e:
        await callback.answer(f"⚠️ Ошибка броска формулы: {e}", show_alert=True)
        return
        
    await callback.answer(f"Бросок: {formula_name}")
    await state.update_data(roll_mode="normal")  # Сбрасываем временный режим на всякий случай
    
    # Пытаемся определить количество граней и выпавший результат для отправки стикера
    sides_val = 0
    num_dice = 0
    try:
        match = FORMULA_PATTERN.match(expr.replace(" ", "").lower())
        if match:
            num_dice_str, sides_str, sign, mod_str = match.groups()
            num_dice = int(num_dice_str) if num_dice_str else 1
            sides_val = int(sides_str)
            result_val = rolls[0] if len(rolls) == 1 else None
            await _send_dice_sticker(callback.message, sides_val, result_val)
    except Exception:
        pass
        
    user_name = f"@{callback.from_user.username}" if callback.from_user.username else callback.from_user.mention_html()
    char_name_val = character["name"] if (character and character != DUMMY_CHARACTER) else None
    raw_d20 = rolls[0] if (sides_val == 20 and num_dice == 1) else None
    
    report = format_roll_report(
        user_mention=user_name,
        char_name=char_name_val,
        check_icon="🧪",
        check_title=f"Формула: {formula_name}",
        formula_exp=formula_str,
        total=total,
        raw_d20=raw_d20
    )
    markup = await _get_kb(callback, "normal")
    if callback.message.reply_to_message:
        await callback.message.reply_to_message.reply(report, reply_markup=markup)
    else:
        mention = callback.from_user.mention_html()
        await callback.message.answer(f"{mention}\n\n{report}", reply_markup=markup)

# =====================================================================
# ОСНОВНОЙ ОБРАБОТЧИК ТЕКСТОВОГО ВВОДА
# =====================================================================


def get_check_emoji_and_title(check_type: str) -> tuple[str, str]:
    clean = check_type.lower().strip()
    # Очищаем от преимущества/помехи
    clean = clean.replace("преимущество", "").replace("преимуществом", "").replace("преи", "")
    clean = clean.replace("помеха", "").replace("помехой", "").replace("пом", "")
    clean = re.sub(r'\s+', ' ', clean).strip()
    
    is_passive = "пассивн" in clean
    clean = clean.replace("пассивный", "").replace("пассивная", "").replace("пассивное", "").replace("пассивн", "").strip()
    
    # 1. Спасбросок
    if "спас" in clean:
        attr_name = "Спасбросок"
        for key, info in ATTR_MAPPING.items():
            if key in clean:
                attr_name = f"Спасбросок {info['name']}"
                break
        prefix = "👁️ Пассивный " if is_passive else ""
        return "🛡️", f"{prefix}{attr_name}"
        
    # 2. Навык
    for key, info in SKILL_MAPPING.items():
        if key in clean:
            prefix = "👁️ Пассивный " if is_passive else ""
            return "📜", f"{prefix}Навык: {info['name']}"
            
    # 3. Инструмент
    for key, val in TOOL_MATCH_MAP.items():
        if key in clean:
            prefix = "👁️ Пассивная " if is_passive else ""
            return "🛠️", f"{prefix}Инструмент: {val}"
            
    # 4. Характеристика
    for key, info in ATTR_MAPPING.items():
        if key in clean:
            prefix = "👁️ Пассивная " if is_passive else ""
            return "⚔️", f"{prefix}Характеристика: {info['name']}"
            
    return "🎲", f"{check_type}"

def format_roll_report(
    user_mention: str,
    char_name: str,
    check_icon: str,
    check_title: str,
    formula_exp: str,
    total: int,
    raw_d20: int = None,
    is_passive: bool = False
) -> str:
    crit_suffix = ""
    if not is_passive and raw_d20 is not None:
        if raw_d20 == 1:
            crit_suffix = " 🔴 Критический провал!"
        elif raw_d20 == 20:
            crit_suffix = " 🟢 Критический успех!"
            
    identity = f"{user_mention}"
    if char_name and char_name != "DUMMY":
        identity = f"{user_mention} | {char_name}"
            
    return (
        f"{check_icon} <b>{check_title}</b>\n"
        f"👤 {identity}\n"
        f"🎲 {formula_exp} ➔ <b>{total}</b>{crit_suffix}"
    )

@router.message(Command("roll"))
async def cmd_roll(message: Message, state: FSMContext):
    """Команда /roll <число> для быстрого броска кастомного дайса."""
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer(
            "⚠️ Укажите количество граней.\n"
            "Пример: <code>/roll 20</code>"
        )
        return
        
    sides_str = args[1]
    result_data = DiceRollerService.parse_and_roll(sides_str)
    await state.update_data(roll_mode="normal")
    await _send_roll_result(message, result_data)

async def evaluate_check_for_character(
    character: dict,
    raw_text: str, # Текст БЕЗ префикса "!"
    session_mode: str,
    state: FSMContext,
    message: Message
):
    kb_markup = await _get_kb(message, "normal")
    clean_text = raw_text.lower()
    
    # Парсинг Преимущества / Помехи (из текста или FSM)
    has_advantage = "преи" in clean_text or session_mode == "advantage"
    has_disadvantage = "пом" in clean_text or session_mode == "disadvantage"
    
    # Вырезаем ключевые слова преимущества и помехи
    clean_text = clean_text.replace("преимущество", "").replace("преимуществом", "").replace("преи", "")
    clean_text = clean_text.replace("помеха", "").replace("помехой", "").replace("пом", "")
    clean_text = re.sub(r'\s+', ' ', clean_text).strip()

    user_name = f"@{message.from_user.username}" if message.from_user.username else message.from_user.mention_html()
    identity = f"{user_name} ({character['name']})" if (character and character != DUMMY_CHARACTER) else user_name

    # 1. Проверяем, не является ли сообщение стандартным броском дайса (например, "20" или "d20")
    if DICE_PATTERN.match(clean_text):
        sides = 20
        digits = re.sub(r'[^\d]', '', clean_text)
        try:
            sides = int(digits)
        except ValueError:
            pass
            
        if sides == 20 and (has_advantage or has_disadvantage):
            # Если это бросок d20 и выбран специальный режим броска
            r1 = random.randint(1, 20)
            r2 = random.randint(1, 20)
            if has_advantage and not has_disadvantage:
                chosen = max(r1, r2)
                if chosen == r1:
                    roll_desc = f"<b>{r1}</b> и ~~{r2}~~"
                else:
                    roll_desc = f"~~{r1}~~ и <b>{r2}</b>"
                mode_str = "Преимущество"
            else:
                chosen = min(r1, r2)
                if chosen == r1:
                    roll_desc = f"<b>{r1}</b> и ~~{r2}~~"
                else:
                    roll_desc = f"~~{r1}~~ и <b>{r2}</b>"
                mode_str = "Помеха"
                
            char_name_val = character["name"] if (character and character != DUMMY_CHARACTER) else None
            report = format_roll_report(
                user_mention=user_name,
                char_name=char_name_val,
                check_icon="🎲",
                check_title=f"d20 + {mode_str.lower()}",
                formula_exp=roll_desc,
                total=chosen,
                raw_d20=chosen
            )
            await state.update_data(roll_mode="normal")
            await message.reply(report, reply_markup=kb_markup)
            return
            
        result_data = DiceRollerService.parse_and_roll(raw_text)
        await state.update_data(roll_mode="normal")
        await _send_roll_result(message, result_data, character)
        return

    # 2.5. Проверяем, не является ли это кастомной именованной формулой персонажа
    formulas = character.get("custom_formulas", {})
    matched_formula_name = None
    for f_name in formulas.keys():
        if f_name.lower() == clean_text:
            matched_formula_name = f_name
            break
            
    if matched_formula_name:
        expr = formulas[matched_formula_name]
        try:
            total, rolls, mod, formula_str = roll_custom_formula(expr)
            # Пытаемся определить количество граней и выпавший результат для отправки стикера
            try:
                match = FORMULA_PATTERN.match(expr.replace(" ", "").lower())
                if match:
                    sides_val = int(match.group(2))
                    result_val = rolls[0] if len(rolls) == 1 else None
                    await _send_dice_sticker(message, sides_val, result_val)
            except Exception:
                pass
            char_name_val = character["name"] if (character and character != DUMMY_CHARACTER) else None
            raw_d20 = rolls[0] if (sides_val == 20 and num_dice == 1) else None
            report = format_roll_report(
                user_mention=user_name,
                char_name=char_name_val,
                check_icon="🧪",
                check_title=f"Формула: {matched_formula_name}",
                formula_exp=formula_str,
                total=total,
                raw_d20=raw_d20
            )
            await state.update_data(roll_mode="normal") # Сбрасываем временный режим преимущества/помехи
            await message.reply(report, reply_markup=kb_markup)
            return
        except Exception as e:
            await message.reply(f"⚠️ Ошибка броска формулы: {e}", reply_markup=kb_markup)
            return

    # Вспомогательное форматирование чисел (+3, -1)
    format_mod = lambda v: f"+{v}" if v >= 0 else str(v)

    # 3. Парсинг дополнительного модификатора (+2, -3)
    custom_mod = 0
    mod_match = re.search(r'([+-])\s*(\d+)', clean_text)
    if mod_match:
        sign = mod_match.group(1)
        val = int(mod_match.group(2))
        custom_mod = val if sign == '+' else -val
        clean_text = re.sub(r'([+-])\s*(\d+)', '', clean_text).strip()

    # 5. Парсинг Пассивной проверки
    is_passive = "пассивн" in clean_text
    clean_text = clean_text.replace("пассивный", "").replace("пассивная", "").replace("пассивное", "").replace("пассивн", "")
    clean_text = re.sub(r'\s+', ' ', clean_text).strip()

    # 6. Парсинг Альтернативной/Взаимозаменяемой характеристики
    override_attr = None
    for attr_key in ATTR_MAPPING.keys():
        if attr_key in clean_text:
            # Если вся строка состоит только из названия характеристики, то это прямая проверка, а не альтернативная
            if clean_text == attr_key:
                break
            override_attr = attr_key
            clean_text = clean_text.replace(attr_key, "").strip()
            clean_text = re.sub(r'\s+', ' ', clean_text).strip()
            break

    # Функция генерации броска d20 с учетом преимущества/помехи/пассивности
    async def make_d20_roll() -> tuple[int, str]:
        if is_passive:
            return 10, "<b>10</b> (d20, пассивно)"
        
        await _send_dice_sticker(message, 20)
        
        if has_advantage and not has_disadvantage:
            r1 = random.randint(1, 20)
            r2 = random.randint(1, 20)
            chosen = max(r1, r2)
            if chosen == r1:
                return chosen, f"<b>{r1}</b> и ~~{r2}~~ (d20 с преимуществом)"
            else:
                return chosen, f"~~{r1}~~ и <b>{r2}</b> (d20 с преимуществом)"
            
        if has_disadvantage and not has_advantage:
            r1 = random.randint(1, 20)
            r2 = random.randint(1, 20)
            chosen = min(r1, r2)
            if chosen == r1:
                return chosen, f"<b>{r1}</b> и ~{r2}~ (d20 с помехой)"
            else:
                return chosen, f"~{r1}~ и <b>{r2}</b> (d20 с помехой)"
            
        r = random.randint(1, 20)
        return r, f"<b>{r}</b> (d20)"

    # Дополнительные строки вывода
    custom_mod_text = f"\n➕ Временный модификатор: <b>{format_mod(custom_mod)}</b>" if custom_mod != 0 else ""

    # Сбрасываем временный режим
    await state.update_data(roll_mode="normal")

    # 7. Проверяем Спасброски
    if clean_text.startswith("спасбросок ") or clean_text.endswith("спасбросок") or "спас" in clean_text:
        attr_key = None
        if override_attr:
            attr_key = override_attr
        else:
            for key in ATTR_MAPPING.keys():
                if key in clean_text or key in raw_text.lower():
                    attr_key = key
                    break
        
        if attr_key in ATTR_MAPPING:
            attr_info = ATTR_MAPPING[attr_key]
            attr_name = attr_info["name"]
            db_field = attr_info["db_field"]
            
            modifier = character[db_field]
            is_proficient = attr_name in character["saving_throws"]
            pb = character["proficiency_bonus"] if is_proficient else 0
            
            d20_roll, roll_text = await make_d20_roll()
            total = d20_roll + modifier + pb + custom_mod
            
            pb_text = f"\n🎓 Бонус мастерства: <b>+{pb}</b> (Владение)" if is_proficient else ""
            title_prefix = "Пассивный спасбросок" if is_passive else "Спасбросок"
            
            formula_parts = [roll_text]
            if modifier: formula_parts.append(f"{format_mod(modifier)} (мод)")
            if pb: formula_parts.append(f"+{pb} (мастерство)")
            if custom_mod: formula_parts.append(f"{format_mod(custom_mod)} (врем)")
            formula_exp = " + ".join(formula_parts).replace(" + -", " - ").replace(" + +", " + ")

            char_name_val = character["name"] if (character and character != DUMMY_CHARACTER) else None
            report = format_roll_report(
                user_mention=user_name,
                char_name=char_name_val,
                check_icon="🛡️",
                check_title=f"{title_prefix}: {attr_name}",
                formula_exp=formula_exp,
                total=total,
                raw_d20=d20_roll,
                is_passive=is_passive
            )
            
            # Интеграция с GM-проверками
            detail_str = f"{d20_roll} {format_mod(modifier)} (мод)"
            if pb: detail_str += f" + {pb} (мастерство)"
            if custom_mod: detail_str += f" {format_mod(custom_mod)} (врем)"
            sent_msg = await message.reply(report, reply_markup=kb_markup)
            await check_and_update_gm_request(message, character, f"Спасбросок {attr_name}", total, detail_str, sent_msg.message_id)
            return

    # 8. Проверяем Навыки
    matched_skill_key = None
    for skill_key in SKILL_MAPPING.keys():
        if skill_key in clean_text:
            matched_skill_key = skill_key
            break
            
    if matched_skill_key:
        skill_info = SKILL_MAPPING[matched_skill_key]
        skill_name = skill_info["name"]
        
        if override_attr:
            attr_key = override_attr
            display_name = f"{skill_name} ({ATTR_MAPPING[attr_key]['name']})"
        else:
            attr_key = skill_info["attr"]
            display_name = skill_name
            
        attr_info = ATTR_MAPPING[attr_key]
        db_field = attr_info["db_field"]
        
        modifier = character[db_field]
        is_proficient = skill_name in character["skills"]
        pb = character["proficiency_bonus"] if is_proficient else 0
        
        d20_roll, roll_text = await make_d20_roll()
        total = d20_roll + modifier + pb + custom_mod
        
        pb_text = f"\n🎓 Бонус мастерства: <b>+{pb}</b> (Владение)" if is_proficient else ""
        title_prefix = "Пассивная проверка навыка" if is_passive else "Проверка навыка"
        
        formula_parts = [roll_text]
        if modifier: formula_parts.append(f"{format_mod(modifier)} (мод)")
        if pb: formula_parts.append(f"+{pb} (мастерство)")
        if custom_mod: formula_parts.append(f"{format_mod(custom_mod)} (врем)")
        formula_exp = " + ".join(formula_parts).replace(" + -", " - ").replace(" + +", " + ")

        char_name_val = character["name"] if (character and character != DUMMY_CHARACTER) else None
        report = format_roll_report(
            user_mention=user_name,
            char_name=char_name_val,
            check_icon="📜",
            check_title=f"{title_prefix}: {display_name}",
            formula_exp=formula_exp,
            total=total,
            raw_d20=d20_roll,
            is_passive=is_passive
        )
        
        # Интеграция с GM-проверками
        detail_str = f"{d20_roll} {format_mod(modifier)} ({attr_info['name']})"
        if pb: detail_str += f" + {pb} (мастерство)"
        if custom_mod: detail_str += f" {format_mod(custom_mod)} (врем)"
        sent_msg = await message.reply(report, reply_markup=kb_markup)
        await check_and_update_gm_request(message, character, skill_name, total, detail_str, sent_msg.message_id)
        return

    # 9. Проверяем Владение Инструментами
    matched_tool_key = None
    for term in TOOL_MATCH_MAP.keys():
        if term in clean_text:
            matched_tool_key = term
            break
            
    if matched_tool_key:
        tool_name = TOOL_MATCH_MAP[matched_tool_key]
        
        is_proficient = any(t.lower() == tool_name.lower() for t in character["tools"])
        pb = character["proficiency_bonus"] if is_proficient else 0
        
        d20_roll, roll_text = await make_d20_roll()
        total = d20_roll + pb + custom_mod
        
        pb_text = f"\n🎓 Бонус мастерства: <b>+{pb}</b> (Владение)" if is_proficient else "\n❌ Бонус мастерства: <b>+0</b> (Нет владения)"
        title_prefix = "Пассивная проверка" if is_passive else "Проверка инструментов"
        
        formula_parts = [roll_text]
        if pb: formula_parts.append(f"+{pb} (мастерство)")
        if custom_mod: formula_parts.append(f"{format_mod(custom_mod)} (врем)")
        formula_exp = " + ".join(formula_parts).replace(" + -", " - ").replace(" + +", " + ")

        char_name_val = character["name"] if (character and character != DUMMY_CHARACTER) else None
        report = format_roll_report(
            user_mention=user_name,
            char_name=char_name_val,
            check_icon="🛠️",
            check_title=f"{title_prefix}: {tool_name}",
            formula_exp=formula_exp,
            total=total,
            raw_d20=d20_roll,
            is_passive=is_passive
        )
        
        # Интеграция с GM-проверками
        detail_str = f"{d20_roll}"
        if pb: detail_str += f" + {pb} (мастерство)"
        if custom_mod: detail_str += f" {format_mod(custom_mod)} (врем)"
        sent_msg = await message.reply(report, reply_markup=kb_markup)
        await check_and_update_gm_request(message, character, tool_name, total, detail_str, sent_msg.message_id)
        return

    # 10. Проверяем Характеристики напрямую
    attr_key = None
    for key in ATTR_MAPPING.keys():
        if key in clean_text:
            attr_key = key
            break
            
    if attr_key:
        attr_info = ATTR_MAPPING[attr_key]
        attr_name = attr_info["name"]
        db_field = attr_info["db_field"]
        
        modifier = character[db_field]
        
        d20_roll, roll_text = await make_d20_roll()
        total = d20_roll + modifier + custom_mod
        
        title_prefix = "Пассивная проверка" if is_passive else "Проверка характеристики"
        
        formula_parts = [roll_text]
        if modifier: formula_parts.append(f"{format_mod(modifier)} (мод)")
        if custom_mod: formula_parts.append(f"{format_mod(custom_mod)} (врем)")
        formula_exp = " + ".join(formula_parts).replace(" + -", " - ").replace(" + +", " + ")

        char_name_val = character["name"] if (character and character != DUMMY_CHARACTER) else None
        report = format_roll_report(
            user_mention=user_name,
            char_name=char_name_val,
            check_icon="⚔️",
            check_title=f"{title_prefix}: {attr_name}",
            formula_exp=formula_exp,
            total=total,
            raw_d20=d20_roll,
            is_passive=is_passive
        )
        
        # Интеграция с GM-проверками
        detail_str = f"{d20_roll} {format_mod(modifier)} (мод)"
        if custom_mod: detail_str += f" {format_mod(custom_mod)} (врем)"
        sent_msg = await message.reply(report, reply_markup=kb_markup)
        await check_and_update_gm_request(message, character, attr_name, total, detail_str, sent_msg.message_id)
        return

    # 11. Если сообщение не подошло ни под один паттерн
    await message.reply(
        "Не понял команду 🧐\n"
        "Отправьте в чат:\n"
        "• Число или выражение для броска (например, <code>15</code>, <code>2d6</code>, <code>1d20+5</code>)\n"
        "• Название проверки с префиксом <code>!</code> (например, <code>!Сила</code>, <code>!Спасбросок Мудрости</code>, <code>!Скрытность +2</code>)\n"
        "• Воспользуйтесь переключателями преимуществ/помех на клавиатуре!",
        reply_markup=kb_markup
    )

@router.message(F.text == "✍️ Кастомный дайс")
async def cmd_custom_dice_hint(message: Message):
    await message.answer(
        "✍️ <b>Как сделать кастомный бросок:</b>\n\n"
        "Вы можете вводить любые формулы кубиков прямо в чат с префиксом <code>!</code>. Например:\n"
        "• <code>!2d6+4</code> — бросок двух d6 и прибавление 4.\n"
        "• <code>!8d6</code> — бросок восьми d6 (заклинание Огненный шар).\n"
        "• <code>!1d20-2</code> — бросок d20 с вычитанием 2.\n\n"
        "Также вы можете добавлять постоянные именованные формулы (например, ваше оружие) в меню вашего активного персонажа (кнопка 👥 <b>Персонажи</b> ➡️ выберите героя ➡️ 🧪 <b>Формулы</b>) и вызывать их одной кнопкой или текстовой командой вида <code>!ИмяФормулы</code>."
    )

@router.message(F.text)
async def handle_direct_text_input(message: Message, state: FSMContext):
    """
    Основной обработчик текстового ввода.
    Распознает обычные броски дайсов (d20) и проверки D&D характеристик, навыков,
    спасбросков или инструментов по названию.
    """
    raw_text = message.text.strip()
    clean_text = raw_text.lower()
    
    # Игнорируем сервисные кнопки, у них свои обработчики
    if clean_text.startswith("👥 персонажи") or clean_text.startswith("✍️ кастомный дайс") or clean_text.startswith("ℹ️ справка"):
        return
        
    # Проверяем наличие обязательного префикса "!" или значка кубика "🎲" с клавиатуры
    is_check_command = raw_text.startswith("!")
    is_keyboard_dice = raw_text.startswith("🎲")
    
    if not (is_check_command or is_keyboard_dice):
        # Без знака "!" или значка кубика 🎲 бот полностью и тихо игнорирует сообщения, чтобы не флудить в чате
        return
        
    # Срезаем префикс "!" для дальнейшего разбора (только если он есть)
    if is_check_command:
        raw_text = raw_text[1:].strip()
        
    clean_text = raw_text.lower()
            
    user_id = message.from_user.id
    chat_id = message.chat.id
    thread_id = message.message_thread_id
    
    # Загружаем character и identity заранее, чтобы исправить NameError в d20/формулах
    user_name = f"@{message.from_user.username}" if message.from_user.username else message.from_user.mention_html()
    character = await DatabaseService.get_bound_character(user_id, chat_id, thread_id)
    if not character:
        all_chars = await DatabaseService.get_all_characters(user_id)
        character = next((c for c in all_chars if c["is_active"] == 1), None)
    if not character:
        character = DUMMY_CHARACTER
    identity = f"{user_name} ({character['name']})" if (character and character != DUMMY_CHARACTER) else user_name
        
    # Получаем сессионный режим броска
    fsm_data = await state.get_data()
    session_mode = fsm_data.get("roll_mode", "normal")
    has_advantage = "преи" in clean_text or session_mode == "advantage"
    has_disadvantage = "пом" in clean_text or session_mode == "disadvantage"
    
    # Очищаем временные слова преимущества/помехи
    temp_clean = clean_text.replace("преимущество", "").replace("преимуществом", "").replace("преи", "")
    temp_clean = temp_clean.replace("помеха", "").replace("помехой", "").replace("пом", "")
    temp_clean = re.sub(r'\s+', ' ', temp_clean).strip()
    
    is_standard_dice = DICE_PATTERN.match(temp_clean)
    is_formula = FORMULA_PATTERN.match(temp_clean)
    
    if is_standard_dice or is_formula:
        # Это стандартный бросок дайса или формулы! Персонаж не требуется.
        kb_markup = await _get_kb(message, "normal")
        
        # Сбрасываем временный режим броска
        await state.update_data(roll_mode="normal")
        
        # Проверяем, d20 ли это (для преимуществ/помех)
        sides = 0
        if is_standard_dice:
            digits = re.sub(r'[^\d]', '', temp_clean)
            try:
                sides = int(digits)
            except ValueError:
                sides = 20
        elif is_formula:
            match = FORMULA_PATTERN.match(temp_clean)
            num_dice_str, sides_str, sign, mod_str = match.groups()
            num_dice = int(num_dice_str) if num_dice_str else 1
            try:
                sides_val = int(sides_str)
            except ValueError:
                sides_val = 0
            if num_dice == 1 and sides_val == 20 and not sign:
                sides = 20
                
        if sides == 20 and (has_advantage or has_disadvantage):
            await _send_dice_sticker(message, 20)
            r1 = random.randint(1, 20)
            r2 = random.randint(1, 20)
            if has_advantage and not has_disadvantage:
                chosen = max(r1, r2)
                if chosen == r1:
                    roll_desc = f"<b>{r1}</b> и ~~{r2}~~"
                else:
                    roll_desc = f"~~{r1}~~ и <b>{r2}</b>"
                mode_str = "Преимущество"
            else:
                chosen = min(r1, r2)
                if chosen == r1:
                    roll_desc = f"<b>{r1}</b> и ~~{r2}~~"
                else:
                    roll_desc = f"~~{r1}~~ и <b>{r2}</b>"
                mode_str = "Помеха"
                
            char_name_val = character["name"] if (character and character != DUMMY_CHARACTER) else None
            report = format_roll_report(
                user_mention=user_name,
                char_name=char_name_val,
                check_icon="🎲",
                check_title=f"d20 + {mode_str.lower()}",
                formula_exp=roll_desc,
                total=chosen,
                raw_d20=chosen
            )
            await message.reply(report, reply_markup=kb_markup)
            return
            
        try:
            if is_formula:
                match = FORMULA_PATTERN.match(temp_clean)
                num_dice_str, sides_str, sign, mod_str = match.groups()
                try:
                    sides_val = int(sides_str)
                    await _send_dice_sticker(message, sides_val)
                except Exception:
                    pass
                
                total, rolls, mod, formula_str = roll_custom_formula(temp_clean)
                char_name_val = character["name"] if (character and character != DUMMY_CHARACTER) else None
                raw_d20 = rolls[0] if (sides_val == 20 and num_dice == 1) else None
                report = format_roll_report(
                    user_mention=user_name,
                    char_name=char_name_val,
                    check_icon="🧪",
                    check_title=f"Формула: {temp_clean}",
                    formula_exp=formula_str,
                    total=total,
                    raw_d20=raw_d20
                )
                await message.reply(report, reply_markup=kb_markup)
            else:
                result_data = DiceRollerService.parse_and_roll(raw_text)
                await _send_roll_result(message, result_data, character)
            return
        except Exception as e:
            await message.reply(f"⚠️ Ошибка броска: {e}", reply_markup=kb_markup)
            return

    # Сначала кэшируем тему, если это форум и тема не сохранена
    if thread_id is not None:
        topics = await DatabaseService.get_chat_topics(chat_id)
        hashed_thread = _hash_thread_id(thread_id)
        exists = any(t["thread_id"] == hashed_thread for t in topics)
        if not exists:
            await DatabaseService.save_chat_topic(
                chat_id=chat_id,
                thread_id=thread_id,
                name=f"Тема №{thread_id}"
            )
            
    # Получаем привязанного к этому чату и теме персонажа
    character = await DatabaseService.get_bound_character(user_id, chat_id, thread_id)
    
    if not character:
        # Персонажа нет (не привязан к текущему чату/топику или вообще не создан)
        # Совершаем обычный бросок без персонажа!
        character = DUMMY_CHARACTER
        
    # Выполняем бросок!
    await evaluate_check_for_character(character, raw_text, session_mode, state, message)

@router.callback_query(F.data.startswith("bind_roll:"))
async def handle_bind_roll_callback(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    raw_idx = callback.data.split(":", 1)[1]
    try:
        idx = int(raw_idx)
    except ValueError:
        await callback.answer("⚠️ Ошибка: неверный индекс персонажа.")
        return
        
    fsm_data = await state.get_data()
    pending_cmd = fsm_data.get("pending_roll_command")
    chat_id = fsm_data.get("pending_roll_chat_id")
    thread_id = fsm_data.get("pending_roll_thread_id")
    session_mode = fsm_data.get("pending_roll_mode", "normal")
    
    if not pending_cmd or chat_id is None:
        await callback.answer("⚠️ Это не ваш выбор или сессия броска истекла!", show_alert=True)
        return
        
    all_chars = await DatabaseService.get_all_characters(user_id)
    if idx < 0 or idx >= len(all_chars):
        await callback.answer("⚠️ Ошибка: выбранный персонаж не найден.")
        return
        
    character = all_chars[idx]
    
    # Привязываем!
    await DatabaseService.bind_character(user_id, chat_id, thread_id, character["name"])
    
    # Сохраняем имя чата (общего раздела)
    chat_title = callback.message.chat.title or callback.message.chat.full_name or "Групповой чат"
    await DatabaseService.save_chat_topic(chat_id, None, chat_title)
    
    # Если это тема, убедимся, что название темы есть в БД
    if thread_id is not None:
        topics = await DatabaseService.get_chat_topics(chat_id)
        hashed_thread = _hash_thread_id(thread_id)
        if not any(t["thread_id"] == hashed_thread for t in topics):
            await DatabaseService.save_chat_topic(chat_id, thread_id, f"Тема №{thread_id}")
            
    # Оповещаем о привязке
    await callback.answer(f"Персонаж {character['name']} успешно привязан!")
    
    # Удаляем сообщение с предложением выбора
    try:
        await callback.message.delete()
    except Exception:
        pass
    
    # Теперь выполняем оригинальный бросок!
    await evaluate_check_for_character(character, pending_cmd, session_mode, state, callback.message)

@router.message(F.forum_topic_created)
async def handle_topic_created(message: Message):
    chat_id = message.chat.id
    thread_id = message.message_thread_id or message.message_id
    name = message.forum_topic_created.name
    await DatabaseService.save_chat_topic(chat_id, thread_id, name)

@router.message(F.forum_topic_edited)
async def handle_topic_edited(message: Message):
    chat_id = message.chat.id
    thread_id = message.message_thread_id
    name = message.forum_topic_edited.name
    if name:
        await DatabaseService.save_chat_topic(chat_id, thread_id, name)

async def _send_roll_result(message: Message, result_data: dict, character: Optional[dict] = None):
    """Вспомогательный метод для отправки результатов броска стандартных дайсов."""
    markup = await _get_kb(message, "normal")
    if result_data["success"]:
        sides = result_data["sides"]
        import config
        sticker_id = config.DICE_STICKERS.get(sides)
        if sticker_id:
            try:
                await message.answer_sticker(sticker_id)
            except Exception:
                pass
                
        if not character:
            user_id = message.from_user.id
            chat_id = message.chat.id
            thread_id = message.message_thread_id
            character = await DatabaseService.get_bound_character(user_id, chat_id, thread_id)
            if not character:
                all_chars = await DatabaseService.get_all_characters(user_id)
                character = next((c for c in all_chars if c["is_active"] == 1), None)
                
        user_mention = f"@{message.from_user.username}" if message.from_user.username else message.from_user.first_name
        char_name_val = character['name'] if (character and character != DUMMY_CHARACTER) else None
        
        crit_suffix = ""
        if sides == 20:
            if result_data['result'] == 1:
                crit_suffix = " 🔴 Критический провал!"
            elif result_data['result'] == 20:
                crit_suffix = " 🟢 Критический успех!"
                
        text = format_roll_report(
            user_mention=user_mention,
            char_name=char_name_val,
            check_icon="🎲",
            check_title=f"d{sides}",
            formula_exp=f"d{sides}",
            total=result_data['result'],
            raw_d20=result_data['result'] if sides == 20 else None
        )
        await message.reply(text, reply_markup=markup)
    else:
        await message.reply(
            f"⚠️ {result_data['error']}",
            reply_markup=markup
        )

def perform_dnd_check_roll(character: dict, check_text: str, roll_mode: str = "normal") -> dict:
    """Выполняет вычисления D&D броска для указанного персонажа и типа проверки."""
    clean_text = check_text.lower().strip()
    
    # 1. Считываем преимущество/помеху
    has_advantage = "преи" in clean_text or roll_mode == "advantage"
    has_disadvantage = "пом" in clean_text or roll_mode == "disadvantage"
    
    # Вырезаем ключевые слова режима
    clean_text = clean_text.replace("преимущество", "").replace("преимуществом", "").replace("преи", "")
    clean_text = clean_text.replace("помеха", "").replace("помехой", "").replace("пом", "")
    clean_text = re.sub(r'\s+', ' ', clean_text).strip()
    
    # Считываем временный модификатор (+2, -1)
    custom_mod = 0
    mod_match = re.search(r'([+-])\s*(\d+)', clean_text)
    if mod_match:
        sign = mod_match.group(1)
        val = int(mod_match.group(2))
        custom_mod = val if sign == '+' else -val
        clean_text = re.sub(r'([+-])\s*(\d+)', '', clean_text).strip()
        
    is_passive = "пассивн" in clean_text
    clean_text = clean_text.replace("пассивный", "").replace("пассивная", "").replace("пассивное", "").replace("пассивн", "").strip()
    
    override_attr = None
    for attr_key in ATTR_MAPPING.keys():
        if attr_key in clean_text and clean_text != attr_key:
            override_attr = attr_key
            clean_text = clean_text.replace(attr_key, "").strip()
            clean_text = re.sub(r'\s+', ' ', clean_text).strip()
            break
            
    # Совершаем d20 броски
    if is_passive:
        chosen_roll = 10
        roll_desc = "Пассивное значение: 10"
    else:
        r1 = random.randint(1, 20)
        r2 = random.randint(1, 20)
        if has_advantage and not has_disadvantage:
            chosen_roll = max(r1, r2)
            if chosen_roll == r1:
                roll_desc = f"<b>{r1}</b> и ~{r2}~ (d20 с преимуществом)"
            else:
                roll_desc = f"~{r1}~ и <b>{r2}</b> (d20 с преимуществом)"
        elif has_disadvantage and not has_advantage:
            chosen_roll = min(r1, r2)
            if chosen_roll == r1:
                roll_desc = f"<b>{r1}</b> и ~{r2}~ (d20 с помехой)"
            else:
                roll_desc = f"~{r1}~ и <b>{r2}</b> (d20 с помехой)"
        else:
            chosen_roll = r1
            roll_desc = f"{chosen_roll} (d20)"
            
    # Сопоставляем проверку
    format_mod = lambda v: f"+{v}" if v >= 0 else str(v)
    
    # A. Спасбросок
    if "спас" in clean_text:
        attr_key = None
        if override_attr:
            attr_key = override_attr
        else:
            for key in ATTR_MAPPING.keys():
                if key in clean_text:
                    attr_key = key
                    break
        if attr_key in ATTR_MAPPING:
            attr_info = ATTR_MAPPING[attr_key]
            attr_name = attr_info["name"]
            db_field = attr_info["db_field"]
            
            modifier = character[db_field]
            is_proficient = attr_name in character["saving_throws"]
            pb = character["proficiency_bonus"] if is_proficient else 0
            
            total = chosen_roll + modifier + pb + custom_mod
            
            detail_str = f"{roll_desc} {format_mod(modifier)} (мод)"
            if pb: detail_str += f" + {pb} (мастерство)"
            if custom_mod: detail_str += f" {format_mod(custom_mod)} (врем)"
            
            return {
                "total": total,
                "detail_str": detail_str,
                "sides": 20,
                "result": chosen_roll if not is_passive else None
            }
            
    # B. Навыки
    matched_skill_key = None
    for skill_key in SKILL_MAPPING.keys():
        if skill_key in clean_text:
            matched_skill_key = skill_key
            break
            
    if matched_skill_key:
        skill_info = SKILL_MAPPING[matched_skill_key]
        skill_name = skill_info["name"]
        
        if override_attr:
            attr_key = override_attr
        else:
            attr_key = skill_info["attr"]
            
        attr_info = ATTR_MAPPING[attr_key]
        db_field = attr_info["db_field"]
        
        modifier = character[db_field]
        is_proficient = skill_name in character["skills"]
        pb = character["proficiency_bonus"] if is_proficient else 0
        
        total = chosen_roll + modifier + pb + custom_mod
        
        detail_str = f"{roll_desc} {format_mod(modifier)} ({attr_info['name']})"
        if pb: detail_str += f" + {pb} (мастерство)"
        if custom_mod: detail_str += f" {format_mod(custom_mod)} (врем)"
        
        return {
            "total": total,
            "detail_str": detail_str,
            "sides": 20,
            "result": chosen_roll if not is_passive else None
        }
        
    # C. Инструменты
    matched_tool_key = None
    for term in TOOL_MATCH_MAP.keys():
        if term in clean_text:
            matched_tool_key = term
            break
            
    if matched_tool_key:
        tool_name = TOOL_MATCH_MAP[matched_tool_key]
        is_proficient = any(t.lower() == tool_name.lower() for t in character["tools"])
        pb = character["proficiency_bonus"] if is_proficient else 0
        
        total = chosen_roll + pb + custom_mod
        
        detail_str = f"{roll_desc}"
        if pb: detail_str += f" + {pb} (мастерство)"
        if custom_mod: detail_str += f" {format_mod(custom_mod)} (врем)"
        
        return {
            "total": total,
            "detail_str": detail_str,
            "sides": 20,
            "result": chosen_roll if not is_passive else None
        }
        
    # D. Прямая характеристика
    attr_key = None
    for key in ATTR_MAPPING.keys():
        if key in clean_text:
            attr_key = key
            break
            
    if attr_key:
        attr_info = ATTR_MAPPING[attr_key]
        db_field = attr_info["db_field"]
        modifier = character[db_field]
        
        total = chosen_roll + modifier + custom_mod
        
        detail_str = f"{roll_desc} {format_mod(modifier)} (мод)"
        if custom_mod: detail_str += f" {format_mod(custom_mod)} (врем)"
        
        return {
            "total": total,
            "detail_str": detail_str,
            "sides": 20,
            "result": chosen_roll if not is_passive else None
        }
        
    # E. Кастомная формула
    try:
        total, rolls, mod, formula_str = roll_custom_formula(clean_text)
        return {
            "total": total,
            "detail_str": formula_str,
            "sides": 20,
            "result": rolls[0] if len(rolls) == 1 else None
        }
    except Exception:
        pass
        
    # F. Дефолтный бросок d20
    total = chosen_roll + custom_mod
    detail_str = f"{roll_desc}"
    if custom_mod: detail_str += f" {format_mod(custom_mod)} (врем)"
    return {
        "total": total,
        "detail_str": detail_str,
        "sides": 20,
        "result": chosen_roll if not is_passive else None
    }

async def check_and_update_gm_request(message: Message, character: dict, check_name_key: str, total: int, detail_str: str, bot_message_id: Optional[int] = None):
    """Проверяет наличие активной GM-заявки в чате и обновляет ее, если бросок игрока совпал с типом проверки."""
    chat_id = message.chat.id
    thread_id = message.message_thread_id
    user_id = message.from_user.id
    
    req = await DatabaseService.get_active_check_request(chat_id, thread_id)
    if not req:
        return
        
    req_check_type = req["check_type"].lower().strip()
    check_name_key = check_name_key.lower().strip()
    
    match = False
    if req_check_type == check_name_key:
        match = True
    elif "спас" in req_check_type and "спас" in check_name_key:
        for key in ATTR_MAPPING.keys():
            if key in req_check_type and key in check_name_key:
                match = True
                break
                
    if not match:
        return
        
    char_name = character["name"]
    if character == DUMMY_CHARACTER:
        char_name = f"Без персонажа ({message.from_user.first_name})"
        
    target_characters = req["target_characters"]
    if target_characters != ["all"]:
        target_set = {t.lower() for t in target_characters}
        
        # Проверяем, привязан ли проверяемый персонаж к текущему пользователю в этом чате/теме
        # и входит ли его имя в список целей.
        bound_chars = await DatabaseService.get_bound_characters_in_chat(chat_id, thread_id)
        from services.db import _hash_user_id
        hashed_user = _hash_user_id(user_id)
        
        user_bound_chars = [bc for bc in bound_chars if bc["user_id"] == hashed_user and bc["char_name"].lower() in target_set]
        if not user_bound_chars:
            return
            
        if char_name.lower() not in {bc["char_name"].lower() for bc in user_bound_chars}:
            return
            
    success = await DatabaseService.add_passed_character(
        request_id=req["id"],
        char_name=char_name,
        result=total,
        user_id=user_id,
        roll_detail=detail_str,
        message_id=bot_message_id
    )
    if not success:
        return
        
    req_updated = await DatabaseService.get_check_request_by_id(req["id"])
    if req_updated:
        from handlers.gm_handlers import format_check_request_text, get_check_request_keyboard, get_mention_prefix_for_request
        is_active = (req_updated["is_active"] == 1)
        
        # Load bound characters to show owner tags in the list
        bound_chars = await DatabaseService.get_bound_characters_in_chat(chat_id, thread_id)
        
        updated_text = format_check_request_text(
            check_type=req_updated["check_type"],
            dc=req_updated["dc"],
            description=req_updated["description"],
            target_characters=req_updated["target_characters"],
            passed_characters=req_updated["passed_characters"],
            is_closed=not is_active,
            bound_characters=bound_chars
        )
        mention_prefix = await get_mention_prefix_for_request(
            chat_id=chat_id,
            thread_id=thread_id,
            target_characters=req_updated["target_characters"]
        )
        try:
            await message.bot.edit_message_text(
                chat_id=chat_id,
                message_id=req_updated["message_id"],
                text=f"{mention_prefix}{updated_text}",
                reply_markup=get_check_request_keyboard(req["id"], is_active=is_active)
            )
        except Exception:
            pass
            
        # Если все участники прошли проверку (is_active стало 0), удаляем сообщения бота с результатами бросков
        if req_updated["is_active"] == 0:
            for p in req_updated["passed_characters"]:
                p_msg_id = p.get("message_id")
                if p_msg_id:
                    try:
                        await message.bot.delete_message(chat_id=chat_id, message_id=p_msg_id)
                    except Exception:
                        pass

@router.callback_query(F.data.startswith("run_request_check:"))
async def handle_run_request_check_callback(callback: CallbackQuery, state: FSMContext):
    """Callback-обработчик для кнопки '🎲 Пройти проверку'."""
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
        
    if req["is_active"] == 0:
        await callback.answer("⚠️ Эта проверка уже завершена!", show_alert=True)
        return
        
    user_id = callback.from_user.id
    chat_id = callback.message.chat.id
    thread_id = callback.message.message_thread_id
    
    target_characters = req["target_characters"]
    
    character = None
    if target_characters != ["all"]:
        target_set = {t.lower() for t in target_characters}
        
        # Получаем привязанных персонажей в чате
        bound_chars = await DatabaseService.get_bound_characters_in_chat(chat_id, thread_id)
        from services.db import _hash_user_id
        hashed_user = _hash_user_id(user_id)
        
        # Находим привязанных персонажей пользователя, которые входят в цели проверки
        user_bound_chars = [bc for bc in bound_chars if bc["user_id"] == hashed_user and bc["char_name"].lower() in target_set]
        
        if not user_bound_chars:
            await callback.answer(
                "⚠️ Эта заявка не предназначена для вас!",
                show_alert=True
            )
            return
            
        # Определяем, какие из них еще не проходили эту проверку
        passed_names = {p["char_name"].lower() for p in req["passed_characters"]}
        user_eligible_chars = [bc for bc in user_bound_chars if bc["char_name"].lower() not in passed_names]
        
        if not user_eligible_chars:
            await callback.answer("⚠️ Все ваши персонажи уже прошли эту проверку!", show_alert=True)
            return
            
        # Загружаем активного персонажа пользователя
        active_char = await DatabaseService.get_character(user_id)
        eligible_names = {bc["char_name"].lower() for bc in user_eligible_chars}
        
        if active_char and active_char["name"].lower() in eligible_names:
            # Если активный персонаж входит в список непрошедших целей, берем его
            character = active_char
        else:
            # Иначе берем первого из непрошедших
            char_name_to_roll = user_eligible_chars[0]["char_name"]
            character = await DatabaseService.get_character_by_name(user_id, char_name_to_roll)
            if not character:
                await callback.answer("⚠️ Ваш персонаж не найден!", show_alert=True)
                return
    else:
        # Для обратной совместимости
        character = await DatabaseService.get_bound_character(user_id, chat_id, thread_id)
        if not character:
            all_chars = await DatabaseService.get_all_characters(user_id)
            active_char = next((c for c in all_chars if c["is_active"] == 1), None)
            if active_char:
                character = active_char
                await DatabaseService.bind_character(user_id, chat_id, thread_id, character["name"])
            else:
                character = DUMMY_CHARACTER
                
    char_name = character["name"]
    if character == DUMMY_CHARACTER:
        char_name = f"Без персонажа ({callback.from_user.first_name})"
        
    passed_characters = req["passed_characters"]
    if any(p["char_name"].lower() == char_name.lower() for p in passed_characters):
        await callback.answer(f"⚠️ Ваш персонаж {char_name} уже прошел эту проверку!", show_alert=True)
        return
        
    fsm_data = await state.get_data()
    roll_mode = fsm_data.get("roll_mode", "normal")
    await state.update_data(roll_mode="normal")
    
    roll_result = perform_dnd_check_roll(character, req["check_type"], roll_mode)
    
    if roll_result["sides"] and roll_result["result"] is not None:
        await _send_dice_sticker(callback.message, roll_result["sides"], roll_result["result"])
    else:
        await _send_dice_sticker(callback.message, 20)
        
    user_name = f"@{callback.from_user.username}" if callback.from_user.username else callback.from_user.mention_html()
    if character == DUMMY_CHARACTER:
        identity = f"{user_name} (без персонажа)"
    else:
        identity = f"{user_name} ({char_name})"
    
    char_name_val = character["name"] if (character and character != DUMMY_CHARACTER) else None
    check_icon, check_title = get_check_emoji_and_title(req['check_type'])
    raw_d20 = roll_result['result']
    is_passive = "пассивн" in req['check_type'].lower()
    
    report = format_roll_report(
        user_mention=user_name,
        char_name=char_name_val,
        check_icon=check_icon,
        check_title=check_title,
        formula_exp=roll_result['detail_str'],
        total=roll_result['total'],
        raw_d20=raw_d20,
        is_passive=is_passive
    )
    
    markup = await _get_kb(callback, "normal")
    bot_msg = await callback.message.answer(report, reply_markup=markup)
    await callback.answer("Бросок выполнен!")
    
    await DatabaseService.add_passed_character(
        request_id=request_id,
        char_name=char_name,
        result=roll_result["total"],
        user_id=user_id,
        roll_detail=roll_result["detail_str"],
        message_id=bot_msg.message_id
    )
    
    req_updated = await DatabaseService.get_check_request_by_id(request_id)
    if req_updated:
        from handlers.gm_handlers import format_check_request_text, get_check_request_keyboard, get_mention_prefix_for_request
        is_active = (req_updated["is_active"] == 1)
        
        # Load bound characters to show owner tags in the list
        bound_chars = await DatabaseService.get_bound_characters_in_chat(chat_id, thread_id)
        
        updated_text = format_check_request_text(
            check_type=req_updated["check_type"],
            dc=req_updated["dc"],
            description=req_updated["description"],
            target_characters=req_updated["target_characters"],
            passed_characters=req_updated["passed_characters"],
            is_closed=not is_active,
            bound_characters=bound_chars
        )
        mention_prefix = await get_mention_prefix_for_request(
            chat_id=chat_id,
            thread_id=thread_id,
            target_characters=req_updated["target_characters"]
        )
        try:
            await callback.message.edit_text(
                f"{mention_prefix}{updated_text}",
                reply_markup=get_check_request_keyboard(request_id, is_active=is_active)
            )
        except Exception:
            pass

        # Если все участники прошли проверку (is_active стало 0), удаляем сообщения бота с результатами бросков
        if req_updated["is_active"] == 0:
            for p in req_updated["passed_characters"]:
                p_msg_id = p.get("message_id")
                if p_msg_id:
                    try:
                        await callback.message.bot.delete_message(chat_id=chat_id, message_id=p_msg_id)
                    except Exception:
                        pass
