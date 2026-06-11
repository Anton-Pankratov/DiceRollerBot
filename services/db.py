import aiosqlite
import json
import os
import hashlib
import hmac
from typing import Dict, Any, Optional, List, Union
from pathlib import Path
import base64
from config import DB_SALT
from cryptography.fernet import Fernet

# Derive a valid Fernet key from DB_SALT
_fernet_key = base64.urlsafe_b64encode(hashlib.sha256(DB_SALT.encode('utf-8')).digest())

def encrypt_val(val: Optional[str]) -> Optional[str]:
    if not val:
        return None
    f = Fernet(_fernet_key)
    return f.encrypt(val.encode('utf-8')).decode('utf-8')

def decrypt_val(val: Optional[str]) -> Optional[str]:
    if not val:
        return None
    f = Fernet(_fernet_key)
    try:
        return f.decrypt(val.encode('utf-8')).decode('utf-8')
    except Exception:
        # Fallback for plain-text / unencrypted legacy data
        return val

# Путь к файлу базы данных SQLite
DB_PATH = Path(os.getenv("DB_PATH", Path(__file__).resolve().parent.parent / "dnd_bot.db"))

def _hash_user_id(user_id: int) -> str:
    """
    Хеширует Telegram User ID с помощью криптографически стойкого алгоритма HMAC-SHA256 с солью.
    Это предотвращает восстановление реальных ID пользователей при утечке БД и защищает
    от атак типа 'длина-расширение' (Length Extension Attacks).
    """
    key = DB_SALT.encode('utf-8')
    msg = str(user_id).encode('utf-8')
    return hmac.new(key, msg, hashlib.sha256).hexdigest()

def _hash_chat_id(chat_id: int) -> str:
    """Хеширует Telegram Chat ID с помощью HMAC-SHA256 с солью."""
    key = DB_SALT.encode('utf-8')
    msg = str(chat_id).encode('utf-8')
    return hmac.new(key, msg, hashlib.sha256).hexdigest()

def _hash_thread_id(thread_id: Optional[int]) -> str:
    """Хеширует Telegram Thread ID (тему форума) с помощью HMAC-SHA256 с солью."""
    key = DB_SALT.encode('utf-8')
    msg = str(thread_id).encode('utf-8')
    return hmac.new(key, msg, hashlib.sha256).hexdigest()

class DatabaseService:
    """
    Асинхронный сервис для работы с базой данных SQLite.
    Хранит листы персонажей игроков (модификаторы, владения спасбросками, навыками и инструментами).
    """

    @staticmethod
    async def init_db():
        """Инициализация базы данных и создание таблиц, если они не существуют."""
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS characters (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,               -- Хешированный SHA-256 ID для безопасности
                    name TEXT NOT NULL,
                    class TEXT NOT NULL,                 -- Класс персонажа (D&D 2014 или кастомный)
                    proficiency_bonus INTEGER NOT NULL,
                    mod_strength INTEGER NOT NULL,
                    mod_dexterity INTEGER NOT NULL,
                    mod_constitution INTEGER NOT NULL,   -- Телосложение
                    mod_intelligence INTEGER NOT NULL,
                    mod_wisdom INTEGER NOT NULL,
                    mod_charisma INTEGER NOT NULL,
                    saving_throws TEXT NOT NULL,         -- JSON-список владений спасбросками
                    skills TEXT NOT NULL,                -- JSON-список владений навыками
                    tools TEXT NOT NULL,                 -- JSON-список владений инструментами
                    custom_formulas TEXT NOT NULL DEFAULT '{}', -- JSON-словарь именованных кастомных бросков
                    is_active INTEGER DEFAULT 0,         -- 1 для активного персонажа, 0 для неактивного
                    UNIQUE(user_id, name)
                )
            """)
            
            # Миграция таблицы char_bindings: переход к PRIMARY KEY (user_id, chat_id, thread_id, char_name)
            # Это позволяет привязывать несколько персонажей пользователя к одному чату/теме,
            # а также привязывать персонажа к нескольким чатам/темам.
            char_name_in_pk = False
            cursor_exists = await db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='char_bindings'")
            table_exists = await cursor_exists.fetchone()
            if table_exists:
                cursor_info = await db.execute("PRAGMA table_info(char_bindings)")
                cols = await cursor_info.fetchall()
                for col in cols:
                    # Кортеж: (cid, name, type, notnull, dflt_value, pk)
                    if col[1] == 'char_name' and col[5] > 0:
                        char_name_in_pk = True
                        break
            
            if table_exists and not char_name_in_pk:
                db.row_factory = aiosqlite.Row
                cursor_data = await db.execute("SELECT * FROM char_bindings")
                existing_bindings = await cursor_data.fetchall()
                bindings_list = [dict(r) for r in existing_bindings]
                
                await db.execute("DROP TABLE char_bindings")
                
                await db.execute("""
                    CREATE TABLE char_bindings (
                        user_id TEXT NOT NULL,               -- Хешированный User ID
                        chat_id TEXT NOT NULL,               -- Хешированный Chat ID
                        thread_id TEXT NOT NULL,             -- Хешированный Message Thread ID (или "None")
                        char_name TEXT NOT NULL,             -- Имя привязанного персонажа
                        tg_username TEXT,                    -- Telegram username владельца
                        tg_first_name TEXT,                  -- Telegram first_name владельца
                        PRIMARY KEY (user_id, chat_id, thread_id, char_name),
                        FOREIGN KEY (user_id, char_name) REFERENCES characters(user_id, name) ON DELETE CASCADE
                    )
                """)
                
                for b in bindings_list:
                    await db.execute("""
                        INSERT OR IGNORE INTO char_bindings (user_id, chat_id, thread_id, char_name, tg_username, tg_first_name)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (b["user_id"], b["chat_id"], b["thread_id"], b["char_name"], b.get("tg_username"), b.get("tg_first_name")))
            elif not table_exists:
                await db.execute("""
                    CREATE TABLE char_bindings (
                        user_id TEXT NOT NULL,               -- Хешированный User ID
                        chat_id TEXT NOT NULL,               -- Хешированный Chat ID
                        thread_id TEXT NOT NULL,             -- Хешированный Message Thread ID (или "None")
                        char_name TEXT NOT NULL,             -- Имя привязанного персонажа
                        tg_username TEXT,                    -- Telegram username владельца
                        tg_first_name TEXT,                  -- Telegram first_name владельца
                        PRIMARY KEY (user_id, chat_id, thread_id, char_name),
                        FOREIGN KEY (user_id, char_name) REFERENCES characters(user_id, name) ON DELETE CASCADE
                    )
                """)
            
            await db.execute("""
                CREATE TABLE IF NOT EXISTS chat_topics (
                    chat_id TEXT NOT NULL,               -- Хешированный Chat ID
                    thread_id TEXT NOT NULL,             -- Хешированный Message Thread ID (или "None")
                    name TEXT NOT NULL,                  -- Понятное название темы
                    PRIMARY KEY (chat_id, thread_id)
                )
            """)

            await db.execute("""
                CREATE TABLE IF NOT EXISTS user_settings (
                    user_id TEXT PRIMARY KEY,            -- Хешированный User ID
                    keyboard_persistent INTEGER DEFAULT 0 -- 1 для постоянной клавиатуры, 0 для скрываемой
                )
            """)

            await db.execute("DROP TABLE IF EXISTS check_requests")
            await db.execute("""
                CREATE TABLE IF NOT EXISTS check_requests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id TEXT NOT NULL,
                    thread_id TEXT NOT NULL,
                    check_type TEXT NOT NULL,
                    dc INTEGER,
                    description TEXT,
                    target_characters TEXT NOT NULL,
                    passed_characters TEXT NOT NULL DEFAULT '[]',
                    creator_id TEXT NOT NULL,
                    message_id INTEGER,
                    is_active INTEGER DEFAULT 1
                )
            """)
            await db.commit()

    @staticmethod
    async def save_character(
        user_id: int,
        name: str,
        char_class: str,
        proficiency_bonus: int,
        mod_strength: int,
        mod_dexterity: int,
        mod_constitution: int,
        mod_intelligence: int,
        mod_wisdom: int,
        mod_charisma: int,
        saving_throws: List[str],
        skills: List[str],
        tools: List[str],
        custom_formulas: Dict[str, str] = None
    ) -> bool:
        """Сохраняет или обновляет лист персонажа для пользователя (с автоматическим хешированием user_id)."""
        hashed_id = _hash_user_id(user_id)
        if custom_formulas is None:
            custom_formulas = {}
            
        async with aiosqlite.connect(DB_PATH) as db:
            # Сбрасываем активность всех остальных персонажей пользователя перед сохранением нового активным
            await db.execute(
                "UPDATE characters SET is_active = 0 WHERE user_id = ?",
                (hashed_id,)
            )
            
            # Получаем существующие кастомные формулы, если мы обновляем персонажа, чтобы не затереть их
            existing_formulas = "{}"
            cursor = await db.execute(
                "SELECT custom_formulas FROM characters WHERE user_id = ? AND name = ?",
                (hashed_id, name)
            )
            row = await cursor.fetchone()
            if row:
                existing_formulas = row[0]
                
            formulas_json = json.dumps(custom_formulas, ensure_ascii=False) if custom_formulas else existing_formulas
            
            # Используем INSERT OR REPLACE. У игрока не может быть двух персонажей с одинаковым именем.
            query = """
                INSERT OR REPLACE INTO characters (
                    user_id, name, class, proficiency_bonus, 
                    mod_strength, mod_dexterity, mod_constitution,
                    mod_intelligence, mod_wisdom, mod_charisma,
                    saving_throws, skills, tools, custom_formulas, is_active
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
            """
            await db.execute(
                query,
                (
                    hashed_id,
                    name,
                    char_class,
                    proficiency_bonus,
                    mod_strength,
                    mod_dexterity,
                    mod_constitution,
                    mod_intelligence,
                    mod_wisdom,
                    mod_charisma,
                    json.dumps(saving_throws, ensure_ascii=False),
                    json.dumps(skills, ensure_ascii=False),
                    json.dumps(tools, ensure_ascii=False),
                    formulas_json
                )
            )
            await db.commit()
        return True

    @staticmethod
    async def get_character(user_id: int) -> Optional[Dict[str, Any]]:
        """Возвращает активный лист персонажа пользователя (поиск по хешированному ID)."""
        hashed_id = _hash_user_id(user_id)
        query = "SELECT * FROM characters WHERE user_id = ? AND is_active = 1"
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(query, (hashed_id,)) as cursor:
                row = await cursor.fetchone()
                if not row:
                    return None
                
                character = dict(row)
                # Десериализуем списки и словари из JSON
                character["saving_throws"] = json.loads(character["saving_throws"])
                character["skills"] = json.loads(character["skills"])
                character["tools"] = json.loads(character["tools"])
                character["custom_formulas"] = json.loads(character["custom_formulas"])
                return character

    @staticmethod
    async def get_all_characters(user_id: int) -> List[Dict[str, Any]]:
        """Возвращает список всех персонажей пользователя."""
        hashed_id = _hash_user_id(user_id)
        query = "SELECT * FROM characters WHERE user_id = ? ORDER BY name ASC"
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(query, (hashed_id,)) as cursor:
                rows = await cursor.fetchall()
                characters = []
                for row in rows:
                    char_dict = dict(row)
                    char_dict["saving_throws"] = json.loads(char_dict["saving_throws"])
                    char_dict["skills"] = json.loads(char_dict["skills"])
                    char_dict["tools"] = json.loads(char_dict["tools"])
                    char_dict["custom_formulas"] = json.loads(char_dict["custom_formulas"])
                    characters.append(char_dict)
                return characters

    @staticmethod
    async def set_active_character(user_id: int, name: str) -> bool:
        """Делает персонажа с указанным именем активным, сбрасывая активность других."""
        hashed_id = _hash_user_id(user_id)
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "UPDATE characters SET is_active = 0 WHERE user_id = ?",
                (hashed_id,)
            )
            await db.execute(
                "UPDATE characters SET is_active = 1 WHERE user_id = ? AND name = ?",
                (hashed_id, name)
            )
            await db.commit()
        return True

    @staticmethod
    async def delete_character_by_name(user_id: int, name: str) -> bool:
        """Удаляет персонажа по имени. Если он был активным, делает активным другого первого попавшегося."""
        hashed_id = _hash_user_id(user_id)
        async with aiosqlite.connect(DB_PATH) as db:
            # Проверяем, был ли удаляемый персонаж активным
            cursor = await db.execute(
                "SELECT is_active FROM characters WHERE user_id = ? AND name = ?",
                (hashed_id, name)
            )
            row = await cursor.fetchone()
            was_active = row and row[0] == 1
            
            await db.execute(
                "DELETE FROM characters WHERE user_id = ? AND name = ?",
                (hashed_id, name)
            )
            await db.execute(
                "DELETE FROM char_bindings WHERE user_id = ? AND char_name = ?",
                (hashed_id, name)
            )
            
            # Если был активным, выберем любого другого и сделаем его активным
            if was_active:
                cursor_other = await db.execute(
                    "SELECT name FROM characters WHERE user_id = ? LIMIT 1",
                    (hashed_id,)
                )
                row_other = await cursor_other.fetchone()
                if row_other:
                    other_name = row_other[0]
                    await db.execute(
                        "UPDATE characters SET is_active = 1 WHERE user_id = ? AND name = ?",
                        (hashed_id, other_name)
                    )
            await db.commit()
        return True

    @staticmethod
    async def add_custom_formula(user_id: int, name: str, formula_expr: str) -> bool:
        """Добавляет/обновляет кастомную формулу броска для активного персонажа."""
        hashed_id = _hash_user_id(user_id)
        async with aiosqlite.connect(DB_PATH) as db:
            # Находим активного персонажа
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT name, custom_formulas FROM characters WHERE user_id = ? AND is_active = 1",
                (hashed_id,)
            )
            row = await cursor.fetchone()
            if not row:
                return False
                
            char_name = row["name"]
            formulas = json.loads(row["custom_formulas"])
            formulas[name] = formula_expr
            
            await db.execute(
                "UPDATE characters SET custom_formulas = ? WHERE user_id = ? AND name = ?",
                (json.dumps(formulas, ensure_ascii=False), hashed_id, char_name)
            )
            await db.commit()
        return True

    @staticmethod
    async def delete_custom_formula(user_id: int, name: str) -> bool:
        """Удаляет кастомную формулу броска для активного персонажа."""
        hashed_id = _hash_user_id(user_id)
        async with aiosqlite.connect(DB_PATH) as db:
            # Находим активного персонажа
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT name, custom_formulas FROM characters WHERE user_id = ? AND is_active = 1",
                (hashed_id,)
            )
            row = await cursor.fetchone()
            if not row:
                return False
                
            char_name = row["name"]
            formulas = json.loads(row["custom_formulas"])
            if name in formulas:
                del formulas[name]
                
            await db.execute(
                "UPDATE characters SET custom_formulas = ? WHERE user_id = ? AND name = ?",
                (json.dumps(formulas, ensure_ascii=False), hashed_id, char_name)
            )
            await db.commit()
        return True

    @staticmethod
    async def save_chat_topic(chat_id: int, thread_id: Optional[int], name: str) -> bool:
        """Сохраняет или обновляет название темы (раздела) чата (с хешированием chat_id и thread_id)."""
        hashed_chat = _hash_chat_id(chat_id)
        hashed_thread = _hash_thread_id(thread_id)
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("""
                INSERT OR REPLACE INTO chat_topics (chat_id, thread_id, name)
                VALUES (?, ?, ?)
            """, (hashed_chat, hashed_thread, name))
            await db.commit()
        return True

    @staticmethod
    async def get_chat_topics(chat_id: int) -> List[Dict[str, Any]]:
        """Возвращает список всех зарегистрированных тем для данного чата."""
        hashed_chat = _hash_chat_id(chat_id)
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM chat_topics WHERE chat_id = ? ORDER BY name ASC",
                (hashed_chat,)
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    @staticmethod
    async def bind_character(
        user_id: int,
        chat_id: int,
        thread_id: Optional[int],
        char_name: str,
        tg_username: Optional[str] = None,
        tg_first_name: Optional[str] = None
    ) -> bool:
        """Привязывает персонажа к конкретному чату и теме (с хешированием параметров и шифрованием тегов)."""
        hashed_user = _hash_user_id(user_id)
        hashed_chat = _hash_chat_id(chat_id)
        hashed_thread = _hash_thread_id(thread_id)
        
        # Шифруем персональные данные игрока
        enc_username = encrypt_val(tg_username)
        enc_first_name = encrypt_val(tg_first_name)
        
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("""
                INSERT OR REPLACE INTO char_bindings (user_id, chat_id, thread_id, char_name, tg_username, tg_first_name)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (hashed_user, hashed_chat, hashed_thread, char_name, enc_username, enc_first_name))
            await db.commit()
        return True

    @staticmethod
    async def get_character_bindings(user_id: int, char_name: str) -> List[Dict[str, Any]]:
        """Возвращает список всех привязок конкретного персонажа пользователя."""
        hashed_user = _hash_user_id(user_id)
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT cb.chat_id, cb.thread_id, ct.name AS topic_name 
                FROM char_bindings cb
                LEFT JOIN chat_topics ct ON cb.chat_id = ct.chat_id AND cb.thread_id = ct.thread_id
                WHERE cb.user_id = ? AND cb.char_name = ?
            """, (hashed_user, char_name))
            rows = await cursor.fetchall()
            bindings = []
            none_thread_hash = _hash_thread_id(None)
            for row in rows:
                b = dict(row)
                if b["thread_id"] != none_thread_hash:
                    # Это тема форума. Получим название самого чата (где thread_id = None)
                    chat_cursor = await db.execute(
                        "SELECT name FROM chat_topics WHERE chat_id = ? AND thread_id = ?",
                        (b["chat_id"], none_thread_hash)
                    )
                    chat_row = await chat_cursor.fetchone()
                    chat_title = chat_row["name"] if chat_row else f"Чат {b['chat_id'][:8]}..."
                    topic_name = b["topic_name"] or f"Тема {b['thread_id'][:8]}..."
                    
                    # Если название темы уже содержит название чата (старый формат), не дублируем
                    if chat_title in topic_name:
                        b["topic_name"] = topic_name
                    else:
                        b["topic_name"] = f"{chat_title} (раздел «{topic_name}»)"
                else:
                    # Это общий раздел
                    b["topic_name"] = b["topic_name"] or f"Чат {b['chat_id'][:8]}..."
                bindings.append(b)
            return bindings

    @staticmethod
    async def delete_binding(user_id: int, chat_id_hash: str, thread_id_hash: str, char_name: str) -> bool:
        """Удаляет привязку персонажа."""
        hashed_user = _hash_user_id(user_id)
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("""
                DELETE FROM char_bindings
                WHERE user_id = ? AND chat_id = ? AND thread_id = ? AND char_name = ?
            """, (hashed_user, chat_id_hash, thread_id_hash, char_name))
            await db.commit()
        return True

    @staticmethod
    async def get_bound_characters_in_chat(chat_id: int, thread_id: Optional[int]) -> List[Dict[str, Any]]:
        """Возвращает список всех привязанных к чату/теме персонажей и владельцев."""
        hashed_chat = _hash_chat_id(chat_id)
        hashed_thread = _hash_thread_id(thread_id)
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT char_name, tg_username, tg_first_name, user_id FROM char_bindings
                WHERE chat_id = ? AND thread_id = ?
            """, (hashed_chat, hashed_thread))
            rows = await cursor.fetchall()
            
            result = []
            for row in rows:
                b = dict(row)
                # Расшифровываем персональные данные игрока
                b["tg_username"] = decrypt_val(b.get("tg_username"))
                b["tg_first_name"] = decrypt_val(b.get("tg_first_name"))
                result.append(b)
            return result

    @staticmethod
    async def get_bound_character(user_id: int, chat_id: int, thread_id: Optional[int]) -> Optional[Dict[str, Any]]:
        """Возвращает лист персонажа, привязанного к чату и теме (с хешированием параметров)."""
        hashed_user = _hash_user_id(user_id)
        hashed_chat = _hash_chat_id(chat_id)
        hashed_thread = _hash_thread_id(thread_id)
        
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            
            # Получаем все привязки для этого пользователя в этом чате/теме
            cursor = await db.execute("""
                SELECT char_name FROM char_bindings 
                WHERE user_id = ? AND chat_id = ? AND thread_id = ?
            """, (hashed_user, hashed_chat, hashed_thread))
            rows = await cursor.fetchall()
            if not rows:
                return None
                
            bound_names = {r["char_name"].lower() for r in rows}
            
            # Ищем активного персонажа пользователя
            cursor_active = await db.execute("""
                SELECT name FROM characters 
                WHERE user_id = ? AND is_active = 1
            """, (hashed_user,))
            row_active = await cursor_active.fetchone()
            
            char_name = None
            if row_active and row_active["name"].lower() in bound_names:
                # Если активный персонаж привязан к этому топику, используем его!
                char_name = row_active["name"]
            else:
                # Иначе берем первый попавшийся привязанный
                char_name = rows[0]["char_name"]
                
            # Загружаем персонажа
            cursor_char = await db.execute("""
                SELECT * FROM characters WHERE user_id = ? AND name = ?
            """, (hashed_user, char_name))
            row_char = await cursor_char.fetchone()
            if not row_char:
                return None
                
            character = dict(row_char)
            character["saving_throws"] = json.loads(character["saving_throws"])
            character["skills"] = json.loads(character["skills"])
            character["tools"] = json.loads(character["tools"])
            character["custom_formulas"] = json.loads(character["custom_formulas"])
            return character

    @staticmethod
    async def get_user_bound_character_names(user_id: int, chat_id: int, thread_id: Optional[int]) -> List[str]:
        """Возвращает список имен всех персонажей пользователя, привязанных к данному чату/теме."""
        hashed_user = _hash_user_id(user_id)
        hashed_chat = _hash_chat_id(chat_id)
        hashed_thread = _hash_thread_id(thread_id)
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT char_name FROM char_bindings 
                WHERE user_id = ? AND chat_id = ? AND thread_id = ?
            """, (hashed_user, hashed_chat, hashed_thread))
            rows = await cursor.fetchall()
            return [r["char_name"] for r in rows]

    @staticmethod
    async def get_character_by_name(user_id: int, name: str) -> Optional[Dict[str, Any]]:
        """Возвращает лист персонажа по его имени (с хешированием user_id)."""
        hashed_id = _hash_user_id(user_id)
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT * FROM characters WHERE user_id = ? AND name = ?
            """, (hashed_id, name))
            row = await cursor.fetchone()
            if not row:
                return None
                
            character = dict(row)
            character["saving_throws"] = json.loads(character["saving_throws"])
            character["skills"] = json.loads(character["skills"])
            character["tools"] = json.loads(character["tools"])
            character["custom_formulas"] = json.loads(character["custom_formulas"])
            return character

    @staticmethod
    def resolve_thread_id(hashed_thread: str) -> Optional[int]:
        """Восстанавливает оригинальный thread_id по его хешу с помощью быстрого перебора."""
        if hashed_thread == _hash_thread_id(None):
            return None
        # Обычно thread_id — небольшие последовательные числа,
        # поэтому перебор до 200 000 покроет практически все реальные топики и выполнится за миллисекунды.
        for i in range(1, 200000):
            if _hash_thread_id(i) == hashed_thread:
                return i
        return None

    @staticmethod
    async def set_keyboard_persistence(user_id: int, mode: int) -> bool:
        """Сохраняет настройку режима клавиатуры для пользователя (0 - скрываемая, 1 - постоянная, 2 - отключена)."""
        hashed_id = _hash_user_id(user_id)
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("""
                INSERT OR REPLACE INTO user_settings (user_id, keyboard_persistent)
                VALUES (?, ?)
            """, (hashed_id, mode))
            await db.commit()
        return True

    @staticmethod
    async def get_keyboard_mode(user_id: int) -> int:
        """Возвращает режим клавиатуры для пользователя (по умолчанию 0 - скрываемая)."""
        hashed_id = _hash_user_id(user_id)
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(
                "SELECT keyboard_persistent FROM user_settings WHERE user_id = ?",
                (hashed_id,)
            )
            row = await cursor.fetchone()
            if row:
                return row[0]
            return 0

    @staticmethod
    async def is_keyboard_persistent(user_id: int) -> bool:
        """Возвращает True, если клавиатура должна быть постоянной (для обратной совместимости)."""
        mode = await DatabaseService.get_keyboard_mode(user_id)
        return mode == 1

    @staticmethod
    async def create_check_request(
        chat_id: int,
        thread_id: Optional[int],
        check_type: str,
        dc: Optional[int],
        description: Optional[str],
        target_characters: List[str],
        creator_id: int
    ) -> int:
        """Создает новый запрос на проверку от Мастера."""
        hashed_chat = _hash_chat_id(chat_id)
        hashed_thread = _hash_thread_id(thread_id)
        hashed_creator = _hash_user_id(creator_id)
        
        # Переводим имена целей в нижний регистр для надежного сопоставления
        targets_lower = [t.strip().lower() for t in target_characters]
        targets_json = json.dumps(targets_lower, ensure_ascii=False)
        
        async with aiosqlite.connect(DB_PATH) as db:
            # Сначала деактивируем все предыдущие активные проверки в этом чате и теме
            await db.execute("""
                UPDATE check_requests 
                SET is_active = 0 
                WHERE chat_id = ? AND thread_id = ? AND is_active = 1
            """, (hashed_chat, hashed_thread))
            
            cursor = await db.execute("""
                INSERT INTO check_requests (chat_id, thread_id, check_type, dc, description, target_characters, creator_id, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?, 1)
            """, (hashed_chat, hashed_thread, check_type, dc, description, targets_json, hashed_creator))
            request_id = cursor.lastrowid
            await db.commit()
            return request_id

    @staticmethod
    async def set_check_request_message_id(request_id: int, message_id: int) -> bool:
        """Сохраняет ID сообщения отправленной карточки проверки."""
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "UPDATE check_requests SET message_id = ? WHERE id = ?",
                (message_id, request_id)
            )
            await db.commit()
        return True

    @staticmethod
    async def get_active_check_request(chat_id: int, thread_id: Optional[int]) -> Optional[Dict[str, Any]]:
        """Возвращает активную заявку на проверку для данного чата и темы."""
        hashed_chat = _hash_chat_id(chat_id)
        hashed_thread = _hash_thread_id(thread_id)
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT * FROM check_requests 
                WHERE chat_id = ? AND thread_id = ? AND is_active = 1
                ORDER BY id DESC LIMIT 1
            """, (hashed_chat, hashed_thread))
            row = await cursor.fetchone()
            if not row:
                return None
            
            req = dict(row)
            req["target_characters"] = json.loads(req["target_characters"])
            req["passed_characters"] = json.loads(req["passed_characters"])
            return req

    @staticmethod
    async def get_check_request_by_id(request_id: int) -> Optional[Dict[str, Any]]:
        """Возвращает заявку на проверку по ее ID."""
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM check_requests WHERE id = ?", (request_id,))
            row = await cursor.fetchone()
            if not row:
                return None
            
            req = dict(row)
            req["target_characters"] = json.loads(req["target_characters"])
            req["passed_characters"] = json.loads(req["passed_characters"])
            return req

    @staticmethod
    async def add_passed_character(
        request_id: int,
        char_name: str,
        result: int,
        user_id: int,
        roll_detail: str,
        message_id: Optional[int] = None
    ) -> bool:
        """Добавляет информацию о персонаже, прошедшем проверку, и автоматически завершает ее при необходимости."""
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT target_characters, passed_characters FROM check_requests WHERE id = ?", (request_id,))
            row = await cursor.fetchone()
            if not row:
                return False
                
            target_characters = json.loads(row["target_characters"])
            passed_characters = json.loads(row["passed_characters"])
            
            # Проверяем, нет ли уже броска от этого персонажа
            if any(p["char_name"].lower() == char_name.lower() for p in passed_characters):
                return False
                
            hashed_user = _hash_user_id(user_id)
            passed_characters.append({
                "char_name": char_name,
                "result": result,
                "user_id": hashed_user,
                "roll_detail": roll_detail,
                "message_id": message_id
            })
            
            # Проверяем, все ли участники выполнили бросок
            is_active = 1
            if target_characters != ["all"]:
                # Если все конкретные персонажи сдали
                passed_names_lower = {p["char_name"].lower() for p in passed_characters}
                if all(t in passed_names_lower for t in target_characters):
                    is_active = 0
            
            await db.execute("""
                UPDATE check_requests 
                SET passed_characters = ?, is_active = ? 
                WHERE id = ?
            """, (json.dumps(passed_characters, ensure_ascii=False), is_active, request_id))
            await db.commit()
            return True

    @staticmethod
    async def close_check_request(request_id: int) -> bool:
        """Принудительно закрывает проверку."""
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "UPDATE check_requests SET is_active = 0 WHERE id = ?",
                (request_id,)
            )
            await db.commit()
        return True
