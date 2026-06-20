import json
import logging
import hmac
import hashlib
from urllib.parse import parse_qsl
from pathlib import Path
from typing import Optional

from aiohttp import web
from aiogram import Bot

import config
from services.db import DatabaseService
from handlers.roller import roll_custom_formula, format_roll_report, get_check_emoji_and_title

logger = logging.getLogger(__name__)

# Верификация подписи данных WebApp от Telegram
def verify_telegram_webapp_data(token: str, init_data: str) -> bool:
    try:
        parsed_data = dict(parse_qsl(init_data))
        if "hash" not in parsed_data:
            return False
        
        received_hash = parsed_data.pop("hash")
        # Формируем строку проверки данных (сортируем ключи алфавитно)
        data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(parsed_data.items()))
        
        # Получаем секретный ключ
        secret_key = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
        # Считаем хэш
        calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
        
        return hmac.compare_digest(calculated_hash, received_hash)
    except Exception:
        return False

# Middleware для аутентификации пользователя через заголовок X-Telegram-Init-Data
@web.middleware
async def auth_middleware(request: web.Request, handler):
    # Разрешаем свободный доступ к статическим файлам
    if not request.path.startswith('/api/'):
        return await handler(request)
        
    init_data = request.headers.get('X-Telegram-Init-Data', '')
    
    # Режим тестирования в браузере
    if config.BOT_MODE == "test" and not init_data:
        request['user'] = {"id": 999999999, "first_name": "Тестовый Герой", "username": "test_hero"}
        return await handler(request)
        
    if not init_data:
        return web.json_response({"error": "Отсутствует X-Telegram-Init-Data заголовок"}, status=401)
        
    bot_token = config.BOT_TOKEN
    if not verify_telegram_webapp_data(bot_token, init_data):
        return web.json_response({"error": "Неверная подпись данных Telegram"}, status=403)
        
    try:
        parsed = dict(parse_qsl(init_data))
        user_info = json.loads(parsed.get('user', '{}'))
        if not user_info or 'id' not in user_info:
            return web.json_response({"error": "Данные пользователя пусты"}, status=400)
        request['user'] = user_info
    except Exception as e:
        return web.json_response({"error": f"Ошибка парсинга пользователя: {e}"}, status=400)
        
    return await handler(request)

# --- Обработчики API ---

async def get_characters(request: web.Request) -> web.Response:
    user = request['user']
    user_id = user['id']
    try:
        characters = await DatabaseService.get_all_characters(user_id)
        return web.json_response(characters)
    except Exception as e:
        logger.error(f"Ошибка получения персонажей: {e}")
        return web.json_response({"error": "Ошибка получения списка персонажей"}, status=500)

async def save_character(request: web.Request) -> web.Response:
    user = request['user']
    user_id = user['id']
    try:
        data = await request.json()
        
        name = data.get("name", "").strip()
        char_class = data.get("class", "").strip()
        
        if not name or not char_class:
            return web.json_response({"error": "Имя и класс обязательны"}, status=400)
            
        char_id = data.get("id")
        if char_id is not None:
            try:
                char_id = int(char_id)
            except ValueError:
                char_id = None

        char_id = await DatabaseService.save_character(
            user_id=user_id,
            name=name,
            char_class=char_class,
            proficiency_bonus=int(data.get("proficiency_bonus", 2)),
            mod_strength=int(data.get("mod_strength", 0)),
            mod_dexterity=int(data.get("mod_dexterity", 0)),
            mod_constitution=int(data.get("mod_constitution", 0)),
            mod_intelligence=int(data.get("mod_intelligence", 0)),
            mod_wisdom=int(data.get("mod_wisdom", 0)),
            mod_charisma=int(data.get("mod_charisma", 0)),
            saving_throws=data.get("saving_throws", []),
            skills=data.get("skills", []),
            tools=data.get("tools", []),
            custom_formulas=data.get("custom_formulas", {}),
            full_data=json.dumps(data, ensure_ascii=False),
            char_id=char_id
        )
        return web.json_response({"status": "success", "message": "Персонаж успешно сохранен", "id": char_id})
    except Exception as e:
        logger.exception(f"Ошибка сохранения персонажа: {e}")
        return web.json_response({"error": f"Ошибка сохранения: {str(e)}"}, status=500)

async def delete_character(request: web.Request) -> web.Response:
    user = request['user']
    user_id = user['id']
    name = request.query.get("name", "").strip()
    
    if not name:
        return web.json_response({"error": "Укажите имя персонажа для удаления"}, status=400)
        
    try:
        await DatabaseService.delete_character_by_name(user_id, name)
        return web.json_response({"status": "success", "message": "Персонаж удален"})
    except Exception as e:
        logger.error(f"Ошибка удаления персонажа: {e}")
        return web.json_response({"error": "Ошибка удаления персонажа"}, status=500)

async def select_character(request: web.Request) -> web.Response:
    user = request['user']
    user_id = user['id']
    try:
        data = await request.json()
        name = data.get("name", "").strip()
        if not name:
            return web.json_response({"error": "Имя не указано"}, status=400)
            
        await DatabaseService.set_active_character(user_id, name)
        return web.json_response({"status": "success", "message": f"Персонаж {name} выбран активным"})
    except Exception as e:
        logger.error(f"Ошибка выбора активного персонажа: {e}")
        return web.json_response({"error": "Ошибка выбора активного персонажа"}, status=500)

async def roll_formula_endpoint(request: web.Request) -> web.Response:
    user = request['user']
    user_id = user['id']
    bot: Bot = request.app['bot']
    
    try:
        data = await request.json()
        char_name = data.get("name", "")
        formula_name = data.get("formula_name", "")
        formula_expr = data.get("formula_expr", "")
        
        if not formula_expr:
            return web.json_response({"error": "Формула не указана"}, status=400)
            
        # Бросаем кубики с учетом минимального куба для навыков
        min_d20_val = 0
        if formula_name.startswith("Проверка навыка:"):
            skill_name = formula_name.replace("Проверка навыка:", "").strip()
            character = await DatabaseService.get_character(user_id)
            if character:
                full_data = character.get("full_data", {})
                if isinstance(full_data, str):
                    try:
                        full_data = json.loads(full_data)
                    except Exception:
                        full_data = {}
                if isinstance(full_data, dict):
                    min_rolls = full_data.get("min_rolls", {}) or full_data.get("minRolls", {})
                    min_d20_val = min_rolls.get(skill_name, 0)
                    
        total, rolls, mod, formula_str = roll_custom_formula(formula_expr, min_d20_val=min_d20_val)
        
        # Оформляем красивый отчет
        mention = f"@{user['username']}" if user.get('username') else user.get('first_name', 'Игрок')
        report = format_roll_report(
            user_mention=mention,
            char_name=char_name,
            check_icon="🧪",
            check_title=f"Формула: {formula_name}",
            formula_exp=formula_str,
            total=total,
            raw_d20=rolls[0] if (len(rolls) == 1) else None
        )
        
        # Отправляем сообщение пользователю в личку от лица бота
        try:
            await bot.send_message(chat_id=user_id, text=report, parse_mode="HTML")
        except Exception as telegram_err:
            logger.warning(f"Не удалось отправить бросок в Telegram: {telegram_err}")
            
        return web.json_response({
            "status": "success", 
            "total": total,
            "rolls": rolls,
            "formula_str": formula_str,
            "report": report
        })
    except Exception as e:
        logger.error(f"Ошибка совершения броска: {e}")
        return web.json_response({"error": f"Ошибка совершения броска: {str(e)}"}, status=500)

async def show_index(request: web.Request) -> web.FileResponse:
    return web.FileResponse(Path(__file__).resolve().parent.parent / 'webapp' / 'index.html')

# --- Инициализация сервера ---

async def start_webapp_server(bot: Bot) -> web.AppRunner:
    app = web.Application(middlewares=[auth_middleware])
    app['bot'] = bot
    
    # Роуты API
    app.router.add_get('/api/characters', get_characters)
    app.router.add_post('/api/characters', save_character)
    app.router.add_delete('/api/characters', delete_character)
    app.router.add_post('/api/characters/select', select_character)
    app.router.add_post('/api/roll', roll_formula_endpoint)
    
    # Роут главной страницы
    app.router.add_get('/', show_index)
    
    # Статические файлы
    webapp_path = Path(__file__).resolve().parent.parent / 'webapp'
    app.router.add_static('/', path=webapp_path, name='static')
    
    runner = web.AppRunner(app)
    await runner.setup()
    
    site = web.TCPSite(runner, config.WEBAPP_HOST, config.WEBAPP_PORT)
    await site.start()
    
    logger.info(f"Служба WebApp запущена на http://{config.WEBAPP_HOST}:{config.WEBAPP_PORT}")
    logger.info(f"Публичный URL WebApp настроен как: {config.WEBAPP_URL}")
    
    return runner
