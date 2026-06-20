from aiogram import Router, html, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, ReplyKeyboardRemove, InlineKeyboardButton, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from keyboards import get_dice_keyboard, get_dice_keyboard_for_user
from services.db import DatabaseService

router = Router(name="common")

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    """
    Обработчик команды /start.
    Проверяет наличие персонажа в базе данных.
    Если персонажа нет, предлагает создать. Если есть — приветствует.
    """
    user_id = message.from_user.id
    
    # Check for deep link starting config/wizard
    args = message.text.split(maxsplit=1)
    if len(args) > 1:
        param = args[1]
        if param == "keyboard":
            await cmd_keyboard(message)
            return
        elif param == "characters":
            from handlers.setup import list_characters_menu
            await list_characters_menu(message, state)
            return
        elif param == "create_character":
            from handlers.setup import start_character_setup
            await start_character_setup(message, state)
            return

    character = await DatabaseService.get_character(user_id)
    user_name = html.quote(message.from_user.full_name)
    
    if not character:
        welcome_text = (
            f"🎲 <b>Приветствую тебя, путник, в DiceRollerBot!</b> 🧙‍♂️\n\n"
            f"Я — твой верный цифровой мастер бросков и хранитель листов персонажей для настольной ролевой игры <b>D&D 5e</b>! "
            f"С моей помощью твои приключения станут быстрее, удобнее и эпичнее.\n\n"
            f"🛡️ <b>Что я умею делать:</b>\n\n"
            f"1️⃣ <b>Бросать любые кости:</b>\n"
            f"• Быстрые кнопки стандартных дайсов (<code>d4</code> – <code>d100</code>) на одной строке клавиатуры.\n"
            f"• Быстрые переключатели <b>Преимущества</b> 🟢 и <b>Помехи</b> 🔴 — включи режим, и твой следующий бросок d20 автоматически пересчитается по правилам D&D, после чего вернется в норму!\n\n"
            f"2️⃣ <b>Хранить листы персонажей (мульти-персонажность):</b>\n"
            f"• Создавай сколько угодно героев! Поддерживается выбор из <b>12 классических классов D&D 2014</b> или создание своего уникального класса.\n"
            f"• Управляй своей гильдией персонажей с помощью удобной кнопки 👥 <b>Персонажи</b> (или команды /characters).\n\n"
            f"3️⃣ <b>Автоматизировать D&D-проверки в реальном времени:</b>\n"
            f"• Добавьте обязательный восклицательный знак <code>!</code> перед названием проверки, и я сам прибавлю нужные модификаторы и бонус мастерства!\n"
            f"• <i>Примеры ввода:</i>\n"
            f"  👉 <code>!Атлетика</code> — проверка Силы Атлетики.\n"
            f"  👉 <code>!Спасбросок Мудрости</code> — расчет спасброска.\n"
            f"  👉 <code>!Скрытность +2</code> — бросок с временным модификатором.\n"
            f"  👉 <code>!Магия Мудрость</code> — бросок навыка через альтернативную характеристику.\n"
            f"  👉 <code>!Пассивная Внимательность</code> — мгновенный расчет пассивного значения.\n"
            f"  👉 <code>!Инструменты вора</code> — проверка владения инструментами.\n\n"
            f"4️⃣ <b>🧪 Кастомные формулы бросков:</b>\n"
            f"• Добавляй свои заклинания или любимое оружие (например, <code>Двуручный меч: 2d6+4</code>) прямо в лист своего активного героя и бросай по одной кнопке!\n\n"
            f"5️⃣ <b>⚙️ Настройка клавиатуры:</b>\n"
            f"• Вы можете закрепить клавиатуру, чтобы она всегда была на экране, или сделать её сворачиваемой с помощью команды 👉 /keyboard!\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"✨ <b>Твоё приключение начинается прямо сейчас!</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"Нажмите 👉 /create_character чтобы запустить мастер создания вашего первого персонажа!"
        )
        await message.answer(welcome_text)
    else:
        welcome_text = (
            f"🏰 <b>Добро пожаловать в игру, {user_name}!</b> 🧙‍♂️\n\n"
            f"Ты играешь за персонажа <b>{character['name']}</b> (Класс: <b>{character['class']}</b>, Бонус мастерства: <code>+{character['proficiency_bonus']}</code>).\n\n"
            f"🎲 Твои кубики готовы к броску! Используй панель быстрого доступа ниже для бросков d4–d100, переключателей преимуществ или открытия меню персонажей.\n\n"
            f"⚙️ <b>Настройка интерфейса:</b>\n"
            f"• Если выдвижная Reply-клавиатура скрывается или вам нужно её всегда держать открытой, настройте отображение через команду 👉 /keyboard.\n\n"
            f"💬 <i>Просто вводи проверки характеристик с обязательным восклицательным знаком (например: <code>!Сила</code>, <code>!Спасбросок Ловкости</code>, <code>!Скрытность</code>) прямо в чат — я автоматически прибавлю все модификаторы твоего героя!</i>"
        )
        markup = await get_dice_keyboard_for_user(user_id)
        await message.reply(welcome_text, reply_markup=markup)


@router.message(Command("stop"))
async def cmd_stop(message: Message):
    """
    Обработчик команды /stop.
    Убирает за собой Reply-клавиатуру и прощается с игроком.
    """
    await message.reply(
        "👋 <b>Приключение временно приостановлено!</b>\n\n"
        "Листы ваших персонажей находятся в полной безопасности в таверне. "
        "Выдвижная Reply-клавиатура скрыта. Чтобы вернуть клавиатуру и продолжить игру, введите команду 👉 /start.",
        reply_markup=ReplyKeyboardRemove(selective=True)
    )


@router.message(Command("help"))
async def cmd_help(message: Message):
    """
    Обработчик команды /help.
    Показывает справочную информацию.
    """
    help_text = (
        f"📋 <b>ПОЛНОЕ РУКОВОДСТВО ПО БРОСКАМ И ПРОВЕРКАМ</b>\n\n"
        
        f"👤 <b>1. Управление персонажами и формулами:</b>\n"
        f"• <b>/create_character</b> — создать нового персонажа.\n"
        f"• <b>/keyboard</b> — настроить постоянную или сворачиваемую Reply-клавиатуру.\n"
        f"• <b>/characters</b> (или кнопка 👥 <b>Персонажи</b>) — открыть меню управления. Здесь вы можете:\n"
        f"  - Переключаться между вашими персонажами.\n"
        f"  - Редактировать характеристики, спасброски, класс и навыки активного героя.\n"
        f"  - Управлять <b>кастомными формулами бросков</b> (добавлять оружие/заклинания, например <code>2d6+4</code>) и бросать их в один клик или отправляя команду <code>!НазваниеФормулы</code>!\n\n"
        
        f"🎲 <b>2. Броски костей (стандартные формулы):</b>\n"
        f"Отправьте в чат формулу броска кубиков (префикс <code>!</code> не требуется):\n"
        f"• <code>d20</code> или <code>20</code> — бросок одного d20.\n"
        f"• <code>2d6</code> — бросок двух d6 (результаты сложатся).\n"
        f"• <code>1d20+5</code> — бросок d20 с прибавлением модификатора +5.\n"
        f"• <code>8d6-1</code> — бросок восьми d6 с вычитанием 1.\n\n"
        
        f"🟢 <b>3. Режимы броска (Преимущество / Помеха):</b>\n"
        f"• Вы можете нажать 🟢 <b>Преимущество</b> или 🔴 <b>Помеха</b> на выдвижной клавиатуре.\n"
        f"• Ваш <u>следующий один бросок</u> d20 или проверка автоматически пройдут с этим модификатором (бросок двух d20 ➡️ выбор наибольшего или наименьшего значения), после чего режим автоматически вернется на <b>Обычный</b>.\n\n"
        
        f"⚔️ <b>4. Формулы вызова стандартных D&D проверок (обязательный префикс <code>!</code>):</b>\n"
        f"Чтобы совершить проверку характеристик, навыков, спасбросков или инструментов, напишите название проверки, обязательно поставив <b>восклицательный знак <code>!</code> в самом начале</b>. Бот сам прибавит модификаторы активного персонажа и Бонус мастерства при наличии владения!\n\n"
        
        f"💪 <b>Проверки характеристик:</b>\n"
        f"• <code>!Сила</code>, <code>!Ловкость</code>, <code>!Телосложение</code>, <code>!Интеллект</code>, <code>!Мудрость</code>, <code>!Харизма</code>\n\n"
        
        f"🛡️ <b>Спасброски:</b>\n"
        f"Пропишите <code>!Спасбросок [Характеристика]</code> или <code>!Спас [Характеристика]</code>:\n"
        f"• <i>Примеры:</i> <code>!Спасбросок Ловкости</code>, <code>!Спас Силы</code>, <code>!Спасбросок Телосложения</code>\n\n"
        
        f"📜 <b>Проверки навыков (все 18 навыков D&D):</b>\n"
        f"Просто напишите название навыка в чат с префиксом <code>!</code>:\n"
        f"• <i>!Атлетика, !Акробатика, !Ловкость рук, !Скрытность</i>\n"
        f"• <i>!Анализ, !История, !Магия, !Природа, !Религия</i>\n"
        f"• <i>!Уход за животными, !Внимательность, !Проницательность, !Медицина, !Выживание</i>\n"
        f"• <i>!Обман, !Запугивание, !Выступление, !Убеждение</i>\n"
        f"• <i>Пример:</i> <code>!Скрытность</code> или <code>!Магия</code>\n\n"
        
        f"🛠️ <b>Владение инструментами и транспортом:</b>\n"
        f"Напишите название инструмента с префиксом <code>!</code>:\n"
        f"• <i>Примеры:</i> <code>!Воровские инструменты</code>, <code>!Карты</code>, <code>!Лютня</code>, <code>!Сухопутный транспорт</code>\n\n"
        
        f"🔥 <b>5. Продвинутые формулы проверок:</b>\n"
        f"Вы можете комбинировать параметры в одном сообщении с префиксом <code>!</code>:\n\n"
        f"1️⃣ <b>Временный модификатор:</b> добавьте <code>+X</code> или <code>-X</code> к проверке.\n"
        f"   👉 <code>!Атлетика +2</code> (бросок Атлетики + модификатор Силы + Бонус мастерства + 2)\n"
        f"2️⃣ <b>Взаимозаменяемая характеристика:</b> укажите навык и неосновную характеристику через пробел.\n"
        f"   👉 <code>!Запугивание Сила</code> (проверка Запугивания на основе Силы вместо Харизмы)\n"
        f"3️⃣ <b>Преимущество/Помеха текстом:</b> допишите ключевые слова.\n"
        f"   👉 <code>!Спасбросок Мудрости преимущество</code> или <code>!История пом</code>\n"
        f"4️⃣ <b>Пассивная проверка:</b> добавьте слово <code>пассивная</code> в начале. Вместо броска d20 возьмется базовое значение 10.\n"
        f"   👉 <code>!Пассивная Внимательность +5</code> (значение пассивной Внимательности +5)\n\n"
        f"<i>Приятной игры! Пусть кубики всегда будут благосклонны к вам! 🎲🌟</i>"
    )
    await message.answer(help_text)


@router.message(F.text.startswith("ℹ️ Справка"))
async def reply_keyboard_help(message: Message):
    """
    Обработчик кнопки Справка на выдвижной клавиатуре.
    Выводит описание правил использования и формул для вызова проверок.
    """
    await cmd_help(message)


@router.message(Command("keyboard"))
async def cmd_keyboard(message: Message):
    """
    Обработчик команды /keyboard.
    Позволяет пользователю настроить режим отображения Reply-клавиатуры:
    постоянная (закрепленная), сворачиваемая или полностью скрытая.
    """
    user_id = message.from_user.id
    
    if message.chat.type != "private":
        # Если команда вызвана в группе/теме, перенаправляем в ЛС с ботом
        bot_user = await message.bot.get_me()
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(
                text="⚙️ Настроить в ЛС",
                url=f"https://t.me/{bot_user.username}?start=keyboard"
            )
        )
        await message.reply(
            "⚙️ <b>Индивидуальная настройка Reply-клавиатуры:</b>\n\n"
            "Настройка клавиатуры выполняется персонально в личной переписке с ботом, "
            "чтобы не мешать другим участникам чата.\n\n"
            "Нажмите кнопку ниже, перейдите в ЛС и нажмите «Запустить» для настройки:",
            reply_markup=builder.as_markup()
        )
        return

    mode_val = await DatabaseService.get_keyboard_mode(user_id)
    
    if mode_val == 1:
        status_text = "📌 <b>Режим клавиатуры:</b> 🟢 <b>ВКЛЮЧЕНА ВСЕГДА</b> (постоянно закреплена на экране)"
    elif mode_val == 2:
        status_text = "📌 <b>Режим клавиатуры:</b> 🚫 <b>ПОЛНОСТЬЮ ОТКЛЮЧЕНА</b> (кнопки и иконка скрыты)"
    else:
        status_text = "📌 <b>Режим клавиатуры:</b> 🔴 <b>СВОРАЧИВАЕМАЯ</b> (скрывается под иконку в поле ввода)"
    
    # Inline клавиатура для переключения настроек
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📌 Всегда показывать", callback_data="set_kbd_mode:1"),
        InlineKeyboardButton(text="📱 Сворачивать в иконку", callback_data="set_kbd_mode:0")
    )
    builder.row(
        InlineKeyboardButton(text="🚫 Полностью отключить", callback_data="set_kbd_mode:2")
    )
    
    await message.reply(
        f"⚙️ <b>Настройка отображения Reply-клавиатуры:</b>\n\n"
        f"{status_text}\n\n"
        f"Вы можете выбрать один из 3 режимов:\n"
        f"1️⃣ <b>Всегда показывать</b> — панель кубиков закреплена и не исчезает с экрана.\n"
        f"2️⃣ <b>Сворачивать в иконку</b> — клавиатура прячется, но её можно открыть кнопкой 🎛 в правой части поля ввода.\n"
        f"3️⃣ <b>Полностью отключить</b> — кнопки и иконка скрываются. Идеально для тех, кто вводит броски только текстом (через <code>!</code>).",
        reply_markup=builder.as_markup()
    )


@router.callback_query(F.data.startswith("set_kbd_mode:"))
async def handle_set_kbd_mode(callback: CallbackQuery):
    user_id = callback.from_user.id
    mode = int(callback.data.split(":", 1)[1])
    
    await DatabaseService.set_keyboard_persistence(user_id, mode)
    
    if mode == 1:
        status_text = "🟢 <b>ВКЛЮЧЕНА ВСЕГДА</b> (постоянно закреплена на экране)"
        alert_msg = "Режим: Всегда показывать!"
    elif mode == 2:
        status_text = "🚫 <b>ПОЛНОСТЬЮ ОТКЛЮЧЕНА</b> (кнопки и иконка скрыты)"
        alert_msg = "Режим: Полностью отключена!"
    else:
        status_text = "🔴 <b>СВОРАЧИВАЕМАЯ</b> (скрывается под иконку)"
        alert_msg = "Режим: Сворачивать в иконку!"
        
    await callback.answer(alert_msg, show_alert=True)
    
    # Сгенерируем новую Reply-клавиатуру/удаление для пользователя
    markup = await get_dice_keyboard_for_user(user_id)
    
    await callback.message.edit_text(
        f"⚙️ <b>Настройка отображения Reply-клавиатуры сохранена!</b>\n\n"
        f"📌 <b>Новый статус:</b> {status_text}\n\n"
        f"Настройки успешно обновлены. Чтобы применить изменения на выдвижной клавиатуре, совершите любой бросок или отправьте сообщение с префиксом `!`.",
        reply_markup=None
    )
    
    text = ""
    if mode == 2:
        text = (
            f"🚫 Режим без клавиатуры успешно активирован! Кнопки и иконка клавиатуры полностью скрыты.\n"
            f"Если вы захотите вернуть её назад, просто отправьте команду 👉 /keyboard."
        )
    else:
        text = f"🔄 Настройки успешно применены! Игровая клавиатура обновлена под ваш выбор."
        
    # В группах присылаем клавиатуру только если отвечаем на сообщение пользователя (selective=True сработает корректно)
    # Иначе не присылаем её в общий чат, чтобы не перезаписать клавиатуру другим пользователям.
    target_markup = markup
    if callback.message.chat.type != "private" and not callback.message.reply_to_message:
        target_markup = None

    if callback.message.reply_to_message:
        await callback.message.reply_to_message.reply(text, reply_markup=target_markup)
    else:
        mention = callback.from_user.mention_html()
        await callback.message.answer(f"{mention}, {text}", reply_markup=target_markup)


@router.callback_query(F.data.startswith("set_kbd_persistent:"))
async def handle_set_kbd_persistent(callback: CallbackQuery):
    user_id = callback.from_user.id
    action = callback.data.split(":", 1)[1]
    mode = 1 if action == "yes" else 0
    # Перенаправляем на новый универсальный обработчик
    callback.data = f"set_kbd_mode:{mode}"
    await handle_set_kbd_mode(callback)


@router.message(Command("webapp"))
async def cmd_webapp(message: Message):
    """
    Обработчик команды /webapp.
    Отправляет инлайн-кнопку для запуска WebApp.
    """
    import config
    from aiogram.types import WebAppInfo
    
    if config.WEBAPP_URL.startswith("https://"):
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(
                text="🎲 Открыть лист персонажа",
                web_app=WebAppInfo(url=config.WEBAPP_URL)
            )
        )
        await message.reply(
            "🧙‍♂️ <b>Интерактивный лист персонажа (Mini App)</b>\n\n"
            "Нажмите кнопку ниже, чтобы открыть графический интерфейс управления вашими героями, "
            "где вы можете легко создавать листы персонажей, редактировать характеристики и настраивать кастомные формулы!",
            reply_markup=builder.as_markup()
        )
    else:
        await message.reply(
            "🧙‍♂️ <b>Интерактивный лист персонажа (Mini App)</b>\n\n"
            "⚠️ <b>Внимание:</b> Для запуска Mini App внутри Telegram требуется безопасное подключение (<b>HTTPS</b>).\n\n"
            f"1️⃣ Вы можете открыть и протестировать интерфейс в вашем обычном браузере на компьютере: {config.WEBAPP_URL}\n"
            "2️⃣ Чтобы запустить приложение внутри Telegram, пробросьте локальный порт наружу (например: <code>ngrok http 8000</code>), "
            "скопируйте ссылку <code>https://...</code> и вставьте её в переменную <code>WEBAPP_URL</code> в файле <code>.env</code>, после чего перезапустите бота."
        )
