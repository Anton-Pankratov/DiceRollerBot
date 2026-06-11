import urllib.request
import urllib.parse
import json
import random
import logging
import asyncio
import re
from typing import Optional
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

router = Router(name="meme")
logger = logging.getLogger(__name__)

def escape_memegen_text(text: str) -> str:
    """
    Экранирует специальные символы в тексте для соответствия правилам memegen.link.
    """
    if not text:
        return "_"
    # Замена спецсимволов согласно спецификации memegen.link
    text = text.replace("?", "~q").replace("%", "~p").replace("/", "~s").replace("\\", "~b").replace("\"", "''")
    # Пробелы заменяем на нижние подчеркивания
    text = text.replace(" ", "_")
    return urllib.parse.quote(text)

async def translate_to_english(text: str) -> str:
    """
    Переводит русский текст на английский с помощью свободного Google Translate API.
    Если в тексте нет русских букв, возвращает его без изменений.
    """
    if not text:
        return ""
    
    # Проверяем наличие кириллицы
    if not re.search('[а-яА-ЯёЁ]', text):
        return text
        
    url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=ru&tl=en&dt=t&q={urllib.parse.quote(text)}"
    req = urllib.request.Request(
        url,
        headers={'User-Agent': 'Mozilla/5.0'}
    )
    
    try:
        loop = asyncio.get_event_loop()
        def fetch():
            with urllib.request.urlopen(req, timeout=3) as response:
                return json.loads(response.read().decode('utf-8'))
        
        data = await loop.run_in_executor(None, fetch)
        if data and len(data) > 0 and len(data[0]) > 0 and len(data[0][0]) > 0:
            return data[0][0][0]
    except Exception as e:
        logger.warning(f"Translation failed: {e}. Using original text.")
        
    return text

async def translate_to_russian(text: str) -> str:
    """
    Переводит английский текст на русский с помощью свободного Google Translate API.
    Если в тексте есть кириллица, возвращает его без изменений.
    """
    if not text:
        return ""
    
    # Если уже есть кириллица, перевод не нужен
    if re.search('[а-яА-ЯёЁ]', text):
        return text
        
    url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=en&tl=ru&dt=t&q={urllib.parse.quote(text)}"
    req = urllib.request.Request(
        url,
        headers={'User-Agent': 'Mozilla/5.0'}
    )
    
    try:
        loop = asyncio.get_event_loop()
        def fetch():
            with urllib.request.urlopen(req, timeout=3) as response:
                return json.loads(response.read().decode('utf-8'))
        
        data = await loop.run_in_executor(None, fetch)
        if data and len(data) > 0 and len(data[0]) > 0 and len(data[0][0]) > 0:
            return data[0][0][0]
    except Exception as e:
        logger.warning(f"Translation to Russian failed: {e}. Using original text.")
        
    return text

async def fetch_russian_memes(keyword: str = "") -> list[dict]:
    """
    Сканирует публичные веб-превью Telegram-каналов dndhub и dnd_memes,
    парсит сообщения с картинками и фильтрует их по ключевому слову.
    """
    channels = ["dndhub", "dnd_memes"]
    keywords_list = keyword.lower().split() if keyword else []
    matches = []
    
    loop = asyncio.get_event_loop()
    
    def fetch_channel(channel: str):
        url = f"https://t.me/s/{channel}"
        req = urllib.request.Request(
            url,
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
        )
        try:
            with urllib.request.urlopen(req, timeout=5) as response:
                html = response.read().decode('utf-8')
            
            blocks = html.split('class="tgme_widget_message ')
            channel_matches = []
            for block in blocks[1:]:
                # Находим ссылки на картинки во фрейме
                photo_urls = re.findall(r"background-image:\s*url\s*\(\s*['\"]([^'\"]+)['\"]\s*\)", block)
                valid_photos = []
                for p_url in photo_urls:
                    if "emoji" not in p_url and "website_icon" not in p_url and "favicon" not in p_url and "telesco.pe" in p_url:
                        valid_photos.append(p_url)
                
                photo_url = valid_photos[0] if valid_photos else None
                if not photo_url:
                    continue
                
                # Парсим текст
                text = ""
                idx = block.find('class="tgme_widget_message_text')
                if idx != -1:
                    sub = block[idx:]
                    first_idx = len(sub)
                    for truncate_marker in ['<div class="tgme_widget_message_reactions', '<div class="tgme_widget_message_footer', '<div class="tgme_widget_message_info']:
                        t_idx = sub.find(truncate_marker)
                        if t_idx != -1 and t_idx < first_idx:
                            first_idx = t_idx
                    sub = sub[:first_idx]
                    
                    cleaned = re.sub(r'<[^>]+>', '', sub)
                    cleaned = cleaned.replace("&quot;", '"').replace("&amp;", '&').replace("&lt;", '<').replace("&gt;", '>').replace("&#33;", '!').replace("&#39;", "'")
                    cleaned = re.sub(r'^class="tgme_widget_message_text[^>]*>\s*', '', cleaned)
                    text = cleaned.strip()
                
                # Фильтруем по ключевому слову
                if keywords_list:
                    text_lower = text.lower()
                    if all(kw in text_lower for kw in keywords_list):
                        channel_matches.append({
                            "url": photo_url,
                            "title": text[:80] + "..." if len(text) > 80 else text,
                            "full_text": text,
                            "source": f"t.me/{channel}"
                        })
                else:
                    # Без ключевого слова добавляем всё с фото
                    channel_matches.append({
                        "url": photo_url,
                        "title": text[:80] + "..." if len(text) > 80 else text,
                        "full_text": text,
                        "source": f"t.me/{channel}"
                    })
            return channel_matches
        except Exception as e:
            logger.warning(f"Error fetching Russian memes from @{channel}: {e}")
            return []

    # Запускаем запросы ко всем каналам
    tasks = [loop.run_in_executor(None, fetch_channel, ch) for ch in channels]
    results = await asyncio.gather(*tasks)
    
    for r in results:
        matches.extend(r)
        
    return matches

async def query_memegen_templates(query: str) -> Optional[str]:
    """
    Запрашивает список шаблонов memegen.link с фильтром по названию и возвращает ID первого совпадения.
    """
    url = f"https://api.memegen.link/templates?filter={urllib.parse.quote(query)}"
    req = urllib.request.Request(url, headers={'User-Agent': 'DiceRollerBot/1.0'})
    try:
        loop = asyncio.get_event_loop()
        def fetch():
            with urllib.request.urlopen(req, timeout=3) as response:
                return json.loads(response.read().decode('utf-8'))
        templates = await loop.run_in_executor(None, fetch)
        if templates:
            return templates[0].get("id")
    except Exception as e:
        logger.warning(f"Error querying memegen templates for '{query}': {e}")
    return None

async def find_memegen_template(name: str) -> str:
    """
    Сопоставляет имя шаблона из AI-генератора с ID шаблона в memegen.link,
    используя нечеткий поиск и очистку названий.
    """
    # 1. Полнотекстовый поиск
    template_id = await query_memegen_templates(name)
    if template_id:
        return template_id
        
    # 2. Поиск с заменой дефисов на пробелы
    cleaned = name.replace("-", " ")
    template_id = await query_memegen_templates(cleaned)
    if template_id:
        return template_id
        
    # 3. Поиск по первому слову в названии
    words = name.replace("-", " ").split()
    if words:
        template_id = await query_memegen_templates(words[0])
        if template_id:
            return template_id
            
    # Фолбэк на дефолтный популярный шаблон
    return "drake"

async def generate_ai_meme(prompt: str) -> Optional[tuple[str, str]]:
    """
    Вызывает AI генератор JustMeme для получения шаблона и текста,
    затем сопоставляет шаблон с memegen.link и возвращает ссылку на картинку и подпись.
    """
    url = "https://justmeme.wtf/api/v1/ai-generate"
    payload = json.dumps({"prompt": f"dnd meme {prompt}"}).encode('utf-8')
    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            'Content-Type': 'application/json',
            'User-Agent': 'DiceRollerBot/1.0'
        },
        method='POST'
    )
    
    try:
        loop = asyncio.get_event_loop()
        def fetch():
            with urllib.request.urlopen(req, timeout=10) as response:
                return json.loads(response.read().decode('utf-8'))
                
        ai_res = await loop.run_in_executor(None, fetch)
        if not ai_res or not ai_res.get("success"):
            return None
            
        template_name = ai_res.get("template", "drake")
        top_text = ai_res.get("top_text", "").strip()
        bottom_text = ai_res.get("bottom_text", "").strip()
        
        # Сопоставляем шаблон с memegen.link
        template_id = await find_memegen_template(template_name)
        
        # Экранируем тексты для ссылки
        top_esc = escape_memegen_text(top_text)
        bottom_esc = escape_memegen_text(bottom_text)
        
        # Строим итоговую ссылку на сгенерированный мем
        image_url = f"https://api.memegen.link/images/{template_id}/{top_esc}/{bottom_esc}.png"
        
        # Формируем подпись
        caption_title = f"{top_text} | {bottom_text}" if top_text and bottom_text else (top_text or bottom_text or "AI Meme")
        return image_url, caption_title
        
    except Exception as e:
        logger.error(f"Failed to generate AI meme for prompt '{prompt}': {e}")
        return None

@router.message(Command("meme"))
async def cmd_meme(message: Message):
    """
    Обработчик команды /meme.
    1. Ищет мемы в русскоязычных D&D Telegram-каналах.
    2. Если не находит, переводит на английский и ищет в свежих постах dndmemes (Reddit).
    3. Если не находит и там, запускает ИИ-генератор мема.
    4. Показывает и удаляет временный статус поиска.
    """
    args = message.text.split(maxsplit=1)
    raw_keyword = args[1].strip() if len(args) > 1 else ""
    
    # Отправляем временный статус
    status_msg = await message.reply("🔍 <i>Ищу подходящие D&D мемы в тавернах интернета...</i>")

    try:
        chosen_meme_url = None
        chosen_meme_caption = None
        is_ai_generated = False
        
        # Шаг 1. Поиск в русскоязычных источниках
        ru_matches = []
        if raw_keyword:
            # Если запрос на английском, пробуем перевести его на русский для поиска в ру-каналах
            # Но также ищем по оригинальному ключевому слову (вдруг там английский тег вроде #dnd)
            has_cyrillic = bool(re.search('[а-яА-ЯёЁ]', raw_keyword))
            if has_cyrillic:
                ru_matches = await fetch_russian_memes(raw_keyword)
            else:
                translated_ru = await translate_to_russian(raw_keyword)
                ru_matches = await fetch_russian_memes(raw_keyword)
                if translated_ru != raw_keyword:
                    translated_matches = await fetch_russian_memes(translated_ru)
                    # Объединяем результаты без дубликатов
                    existing_urls = {m["url"] for m in ru_matches}
                    for m in translated_matches:
                        if m["url"] not in existing_urls:
                            ru_matches.append(m)
        else:
            # Без ключевого слова — с вероятностью 50% пробуем взять случайный русский мем
            if random.random() < 0.5:
                ru_matches = await fetch_russian_memes()

        # Шаг 2. Если нашли совпадения на русском, выбираем одно
        if ru_matches:
            chosen = random.choice(ru_matches)
            chosen_meme_url = chosen["url"]
            source_info = f"«{raw_keyword}»" if raw_keyword else "случайный"
            # Формируем красивую подпись с оригинальным текстом поста (если есть)
            caption_parts = [f"🎲 <b>Мем по запросу:</b> {source_info}"]
            if chosen["full_text"]:
                caption_parts.append(f"\n📝 <b>Текст:</b> {chosen['full_text']}")
            caption_parts.append(f"\n📡 <b>Источник:</b> {chosen['source']}")
            chosen_meme_caption = "\n".join(caption_parts)
            
        else:
            # Шаг 3. Перевод русского ключевого слова на английский для глобального поиска
            keyword_en = await translate_to_english(raw_keyword)
            
            # Запрашиваем 50 свежих мемов из dndmemes (Reddit)
            url = "https://meme-api.com/gimme/dndmemes/50"
            req = urllib.request.Request(
                url,
                headers={'User-Agent': 'DiceRollerBotMemeFetcher/1.0'}
            )
            
            memes = []
            try:
                loop = asyncio.get_event_loop()
                def fetch():
                    with urllib.request.urlopen(req, timeout=5) as response:
                        return json.loads(response.read().decode('utf-8'))
                
                data = await loop.run_in_executor(None, fetch)
                memes = data.get("memes", [])
            except Exception as api_err:
                logger.warning(f"Failed to fetch hot memes from API: {api_err}")
                
            search_info = f"«{raw_keyword}»"
            if raw_keyword and raw_keyword.lower() != keyword_en.lower():
                search_info += f" (en: {keyword_en})"
                
            if raw_keyword:
                # 3.1 Пытаемся найти совпадение в заголовках свежих Reddit-мемов
                matches = []
                if memes:
                    keywords_list = keyword_en.lower().split()
                    for m in memes:
                        title_lower = m.get("title", "").lower()
                        if all(kw in title_lower for kw in keywords_list):
                            matches.append(m)
                    
                    # Мягкий поиск (хотя бы одно совпадение)
                    if not matches and len(keywords_list) > 1:
                        for m in memes:
                            title_lower = m.get("title", "").lower()
                            if any(kw in title_lower for kw in keywords_list):
                                matches.append(m)
                                
                if matches:
                    chosen = random.choice(matches)
                    chosen_meme_url = chosen.get("url")
                    chosen_meme_caption = f"🎲 <b>Мем по запросу:</b> {search_info}\n\n📌 <b>{chosen['title']}</b>"
                else:
                    # 3.2 Если ничего не нашли в свежих, генерируем кастомный мем через ИИ
                    logger.info(f"Meme search query '{keyword_en}' not found in hot batch. Running AI Generator...")
                    ai_result = await generate_ai_meme(keyword_en)
                    if ai_result:
                        chosen_meme_url, ai_caption = ai_result
                        chosen_meme_caption = f"🤖 <b>ИИ сгенерировал мем по запросу:</b> {search_info}\n\n📌 <i>{ai_caption}</i>"
                        is_ai_generated = True
                    elif memes:
                        # Фолбэк на случай ошибки ИИ: берем случайный мем из базы
                        chosen = random.choice(memes)
                        chosen_meme_url = chosen.get("url")
                        chosen_meme_caption = f"🔍 Мем по запросу {search_info} не найден.\n\n🎲 <b>Случайный D&D мем:</b>\n📌 <b>{chosen['title']}</b>"
            else:
                # Запрос без ключевых слов — отдаем случайный мем из Reddit
                if memes:
                    chosen = random.choice(memes)
                    chosen_meme_url = chosen.get("url")
                    chosen_meme_caption = f"🎲 <b>Случайный D&D мем:</b>\n📌 <b>{chosen['title']}</b>"

        # Удаляем статус поиска
        try:
            await status_msg.delete()
        except Exception:
            pass

        if not chosen_meme_url:
            await message.reply("😔 Не удалось получить или сгенерировать мем. Пожалуйста, попробуйте позже!")
            return
            
        try:
            await message.reply_photo(photo=chosen_meme_url, caption=chosen_meme_caption)
        except Exception as e:
            logger.warning(f"Failed to send image directly: {e}. Falling back to text link.")
            await message.reply(f"{chosen_meme_caption}\n\n🔗 <a href='{chosen_meme_url}'>Посмотреть мем в браузере</a>")
            
    except Exception as e:
        logger.error(f"General error in cmd_meme: {e}")
        try:
            await status_msg.delete()
        except Exception:
            pass
        await message.reply("⚠️ Произошла ошибка при поиске мема. Пожалуйста, попробуйте позже.")
