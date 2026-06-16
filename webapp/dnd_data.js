const DND_RACES = {
    "Human": {
        "name": "Human",
        "description": "Люди самые адаптируемые и честолюбивые среди рас.",
        "bonuses": { "strength": 1, "dexterity": 1, "constitution": 1, "intelligence": 1, "wisdom": 1, "charisma": 1 },
        "speed": 30,
        "size": "Medium",
        "languages": ["Common", "Any one other"],
        "features": ["Versatility: Дополнительный язык на выбор."],
        "subraces": []
    },
    "Elf": {
        "name": "Elf",
        "description": "Эльфы — волшебный народ изящного вида, живущий в лесах.",
        "bonuses": { "dexterity": 2 },
        "speed": 30,
        "size": "Medium",
        "languages": ["Common", "Elvish"],
        "features": ["Darkvision: Зрение в темноте на 60 футов.", "Fey Ancestry: Спасброски от очарования совершаются с преимуществом.", "Trance: Спят 4 часа вместо 8."],
        "subraces": [
            {
                "name": "High Elf",
                "description": "Высшие эльфы обладают острым умом и знают основы магии.",
                "bonuses": { "intelligence": 1 },
                "features": ["Elf Weapon Training: Владение длинным и коротком мечом, длинным и коротким луком.", "Cantrip: Знают один заговор из списка волшебника."]
            },
            {
                "name": "Wood Elf",
                "description": "Лесные эльфы обладают быстрыми ногами и хорошо маскируются.",
                "bonuses": { "wisdom": 1 },
                "features": ["Fleet of Foot: Скорость увеличивается до 35 футов.", "Mask of the Wild: Могут маскироваться в листве."]
            }
        ]
    },
    "Dwarf": {
        "name": "Dwarf",
        "description": "Дварфы — смелые и выносливые мастера по камню и металлу.",
        "bonuses": { "constitution": 2 },
        "speed": 25,
        "size": "Medium",
        "languages": ["Common", "Dwarvish"],
        "features": ["Darkvision: Зрение в темноте 60 футов.", "Dwarven Resilience: Спасброски от яда с преимуществом, сопротивление урону ядом."],
        "subraces": [
            {
                "name": "Hill Dwarf",
                "description": "Холмовые дварфы обладают повышенной интуицией и стойкостью.",
                "bonuses": { "wisdom": 1 },
                "features": ["Dwarven Toughness: Максимум хитов увеличивается на 1 за каждый уровень."]
            },
            {
                "name": "Mountain Dwarf",
                "description": "Горные дварфы сильны и привычны к ношению тяжелой брони.",
                "bonuses": { "strength": 2 },
                "features": ["Dwarven Armor Training: Владение легким и средним доспехом."]
            }
        ]
    },
    "Halfling": {
        "name": "Halfling",
        "description": "Полурослики — дружелюбные, удачливые и проворные существа.",
        "bonuses": { "dexterity": 2 },
        "speed": 25,
        "size": "Small",
        "languages": ["Common", "Halfling"],
        "features": ["Lucky: При выпадении 1 на d20 можно перебросить кубик.", "Brave: Преимущество на спасброски от испуга."],
        "subraces": [
            {
                "name": "Lightfoot",
                "description": "Легконогие полурослики скрытны и умеют прятаться за союзниками.",
                "bonuses": { "charisma": 1 },
                "features": ["Naturally Stealthy: Могут скрываться за существами большего размера."]
            },
            {
                "name": "Stout",
                "description": "Кренастые полурослики выносливее обычных и устойчивы к ядам.",
                "bonuses": { "constitution": 1 },
                "features": ["Stout Resilience: Преимущество на спасброски от яда."]
            }
        ]
    },
    "Dragonborn": {
        "name": "Dragonborn",
        "description": "Драконорожденные горды своей связью с великими драконами.",
        "bonuses": { "strength": 2, "charisma": 1 },
        "speed": 30,
        "size": "Medium",
        "languages": ["Common", "Draconic"],
        "features": ["Draconic Ancestry: Выбор типа дракона (определяет урон дыхания).", "Breath Weapon: Дыхание стихией один раз за короткий отдых."],
        "subraces": []
    },
    "Gnome": {
        "name": "Gnome",
        "description": "Гномы — энергичные исследователи, ученые и изобретатели.",
        "bonuses": { "intelligence": 2 },
        "speed": 25,
        "size": "Small",
        "languages": ["Common", "Gnomish"],
        "features": ["Gnome Cunning: Преимущество на спасброски от магии на основе Интеллекта, Мудрости, Харизмы."],
        "subraces": [
            {
                "name": "Forest Gnome",
                "description": "Лесные гномы владеют иллюзией и дружат с мелкими зверями.",
                "bonuses": { "dexterity": 1 },
                "features": ["Natural Illusionist: Знают заговор Малая Иллюзия.", "Speak with Small Beasts: Общение с мелкими животными."]
            },
            {
                "name": "Rock Gnome",
                "description": "Скальные гномы — великие мастера механизмов и создатели штуковин.",
                "bonuses": { "constitution": 1 },
                "features": ["Artificer's Lore: Двойной бонус мастерства на проверки истории механизмов.", "Tinker: Умение собирать мини-устройства."]
            }
        ]
    },
    "Half-Elf": {
        "name": "Half-Elf",
        "description": "Полуэльфы сочетают в себе лучшие качества людей и эльфов.",
        "bonuses": { "charisma": 2, "strength": 1, "dexterity": 1 }, // Дополнительные +1 распределяются
        "speed": 30,
        "size": "Medium",
        "languages": ["Common", "Elvish", "Any one other"],
        "features": ["Darkvision: Зрение в темноте на 60 футов.", "Fey Ancestry: Спасброски от очарования совершаются с преимуществом.", "Skill Versatility: Владение любыми двумя навыками на выбор."],
        "subraces": []
    },
    "Half-Orc": {
        "name": "Half-Orc",
        "description": "Полуорки сильны физически, яростны в бою и выносливы.",
        "bonuses": { "strength": 2, "constitution": 1 },
        "speed": 30,
        "size": "Medium",
        "languages": ["Common", "Orc"],
        "features": ["Darkvision: Зрение в темноте на 60 футов.", "Menacing: Владение навыком Запугивание.", "Relentless Endurance: При падении в 0 хитов остаются в 1 хите.", "Savage Attacks: Дополнительный кубик урона при критическом попадании."],
        "subraces": []
    },
    "Tiefling": {
        "name": "Tiefling",
        "description": "Тифлинги несут в себе наследие адских сил и вызывают недоверие.",
        "bonuses": { "charisma": 2, "intelligence": 1 },
        "speed": 30,
        "size": "Medium",
        "languages": ["Common", "Infernal"],
        "features": ["Darkvision: Зрение в темноте на 60 футов.", "Hellish Resistance: Сопротивление огненному урону.", "Infernal Legacy: Знают заговор Чудотворство и другие заклинания с уровнем."],
        "subraces": []
    }
};

const DND_CLASSES = {
    "Barbarian": {
        "name": "Barbarian",
        "description": "Свирепый воин дикого происхождения, способный впадать в боевую ярость.",
        "hit_die": 12,
        "saving_throws": ["Сила", "Телосложение"],
        "skills_count": 2,
        "skills_options": ["Атлетика", "Запугивание", "Природа", "Выживание", "Уход за животными", "Внимательность"],
        "weapon_proficiencies": ["Simple weapons", "Martial weapons"],
        "armor_proficiencies": ["Light armor", "Medium armor", "Shields"],
        "starting_equipment": [
            "Секира (Greataxe) или Воинское оружие на выбор",
            "Два ручных топора (Handaxe) или Простое оружие",
            "Набор путешественника (Explorer's Pack) и четыре метательных копья"
        ],
        "subclasses": ["Path of the Berserker", "Path of the Totem Warrior"]
    },
    "Bard": {
        "name": "Bard",
        "description": "Вдохновляющий маг, музыка которого способна ткать заклинания.",
        "hit_die": 8,
        "saving_throws": ["Ловкость", "Харизма"],
        "skills_count": 3,
        "skills_options": ["Акробатика", "Атлетика", "Внимательность", "Выступление", "Выживание", "Запугивание", "История", "Ловкость рук", "Магия", "Медицина", "Обман", "Природа", "Проницательность", "Религия", "Скрытность", "Убеждение", "Уход за животными"],
        "weapon_proficiencies": ["Simple weapons", "Hand crossbows", "Longswords", "Rapiers", "Shortswords"],
        "armor_proficiencies": ["Light armor"],
        "starting_equipment": [
            "Рапира (Rapier) или Длинный меч",
            "Лютня или Другой музыкальный инструмент",
            "Кожаный доспех (Leather Armor), Кинжал",
            "Набор дипломата (Diplomat's Pack)"
        ],
        "spellcaster": true,
        "subclasses": ["College of Lore", "College of Valor"]
    },
    "Cleric": {
        "name": "Cleric",
        "description": "Жрец, служащий божеству и управляющий силой божественной магии.",
        "hit_die": 8,
        "saving_throws": ["Мудрость", "Харизма"],
        "skills_count": 2,
        "skills_options": ["История", "Медицина", "Проницательность", "Религия", "Убеждение"],
        "weapon_proficiencies": ["Simple weapons"],
        "armor_proficiencies": ["Light armor", "Medium armor", "Shields"],
        "starting_equipment": [
            "Булава (Mace) или Боевой молот (при владении)",
            "Чешуйчатый доспех (Scale Mail) или Кожаный доспех",
            "Легкий арбалет и 20 болтов или Простое оружие",
            "Набор священника (Priest's Pack), Щит, Священный символ"
        ],
        "spellcaster": true,
        "subclasses": ["Life Domain", "Light Domain", "War Domain"]
    },
    "Druid": {
        "name": "Druid",
        "description": "Жрец старой веры, использующий силы природы и принимающий формы животных.",
        "hit_die": 8,
        "saving_throws": ["Интеллект", "Мудрость"],
        "skills_count": 2,
        "skills_options": ["Магия", "Уход за животными", "Медицина", "Природа", "Проницательность", "Внимательность", "Выживание"],
        "weapon_proficiencies": ["Clubs", "Daggers", "Darts", "Javelins", "Maces", "Quarterstaffs", "Scimitars", "Sickles", "Slings", "Spears"],
        "armor_proficiencies": ["Light armor (non-metal)", "Medium armor (non-metal)", "Shields (non-metal)"],
        "starting_equipment": [
            "Деревянный щит (Wooden Shield) или Простое оружие",
            "Скимитар (Scimitar) или Простое оружие ближнего боя",
            "Кожаный доспех, Набор путешественника, Друидический фокус"
        ],
        "spellcaster": true,
        "subclasses": ["Circle of the Land", "Circle of the Moon"]
    },
    "Fighter": {
        "name": "Fighter",
        "description": "Мастер боевого искусства, владеющий всеми видами оружия и брони.",
        "hit_die": 10,
        "saving_throws": ["Сила", "Телосложение"],
        "skills_count": 2,
        "skills_options": ["Атлетика", "Акробатика", "Запугивание", "История", "Проницательность", "Выживание", "Уход за животными", "Внимательность"],
        "weapon_proficiencies": ["Simple weapons", "Martial weapons"],
        "armor_proficiencies": ["All armor", "Shields"],
        "starting_equipment": [
            "Кольчатый доспех (Chain Mail) или Кожаный доспех + Длинный лук",
            "Воинское оружие + Щит или Два воинских оружия",
            "Легкий арбалет + 20 болтов или Два ручных топора",
            "Набор путешественника (Explorer's Pack) или Набор подземелья"
        ],
        "subclasses": ["Champion", "Battle Master", "Eldritch Knight"]
    },
    "Monk": {
        "name": "Monk",
        "description": "Мастер рукопашного боя, использующий внутреннюю энергию Ки.",
        "hit_die": 8,
        "saving_throws": ["Сила", "Ловкость"],
        "skills_count": 2,
        "skills_options": ["Акробатика", "Атлетика", "Скрытность", "История", "Проницательность", "Религия"],
        "weapon_proficiencies": ["Simple weapons", "Shortswords"],
        "armor_proficiencies": [],
        "starting_equipment": [
            "Короткий меч (Shortsword) или Простое оружие",
            "Набор путешественника или Набор исследователя",
            "10 метательных дротиков (Darts)"
        ],
        "subclasses": ["Way of the Open Hand", "Way of Shadow", "Way of the Four Elements"]
    },
    "Paladin": {
        "name": "Paladin",
        "description": "Святой воитель, связанный нерушимой клятвой борьбы со злом.",
        "hit_die": 10,
        "saving_throws": ["Мудрость", "Харизма"],
        "skills_count": 2,
        "skills_options": ["Атлетика", "Запугивание", "Проницательность", "Медицина", "Религия", "Убеждение"],
        "weapon_proficiencies": ["Simple weapons", "Martial weapons"],
        "armor_proficiencies": ["All armor", "Shields"],
        "starting_equipment": [
            "Воинское оружие + Щит или Два воинских оружия",
            "Пять метательных копий или Простое оружие ближнего боя",
            "Набор священника или Набор путешественника",
            "Стальной нагрудник (Chain Mail), Священный символ"
        ],
        "spellcaster": true,
        "subclasses": ["Oath of Devotion", "Oath of the Ancients", "Oath of Vengeance"]
    },
    "Ranger": {
        "name": "Ranger",
        "description": "Следопыт и охотник, охраняющий границы цивилизации.",
        "hit_die": 10,
        "saving_throws": ["Сила", "Ловкость"],
        "skills_count": 3,
        "skills_options": ["Акробатика", "Атлетика", "Скрытность", "Выживание", "Природа", "Проницательность", "Внимательность", "Уход за животными"],
        "weapon_proficiencies": ["Simple weapons", "Martial weapons"],
        "armor_proficiencies": ["Light armor", "Medium armor", "Shields"],
        "starting_equipment": [
            "Кожаный доспех или Чешуйчатый доспех",
            "Два коротких меча или Два простых оружия ближнего боя",
            "Набор путешественника или Набор исследователя",
            "Длинный лук и колчан с 20 стрелами"
        ],
        "spellcaster": true,
        "subclasses": ["Hunter", "Beast Master"]
    },
    "Rogue": {
        "name": "Rogue",
        "description": "Ловкий скрытный вор и специалист по решению проблем обходными путями.",
        "hit_die": 8,
        "saving_throws": ["Ловкость", "Интеллект"],
        "skills_count": 4,
        "skills_options": ["Акробатика", "Атлетика", "Выступление", "Запугивание", "Ловкость рук", "Обман", "Внимательность", "Проницательность", "Скрытность", "Убеждение"],
        "weapon_proficiencies": ["Simple weapons", "Hand crossbows", "Rapiers", "Shortswords"],
        "armor_proficiencies": ["Light armor"],
        "starting_equipment": [
            "Рапира (Rapier) или Короткий меч",
            "Короткий лук и колчан с 20 стрелами или Короткий меч",
            "Набор взломщика (Burglar's Pack) или Набор налетчика",
            "Кожаный доспех, Два кинжала, Воровские инструменты"
        ],
        "subclasses": ["Thief", "Assassin", "Arcane Trickster"]
    },
    "Sorcerer": {
        "name": "Sorcerer",
        "description": "Маг, чья сила является врожденным даром крови или звезд.",
        "hit_die": 6,
        "saving_throws": ["Телосложение", "Харизма"],
        "skills_count": 2,
        "skills_options": ["Магия", "Запугивание", "Обман", "Проницательность", "Религия", "Убеждение"],
        "weapon_proficiencies": ["Daggers", "Darts", "Slings", "Quarterstaffs", "Light crossbows"],
        "armor_proficiencies": [],
        "starting_equipment": [
            "Легкий арбалет и 20 болтов или Простое оружие",
            "Компонентная сумка (Component Pouch) или Заклинательный фокус",
            "Набор подземелья или Набор путешественника",
            "Два кинжала"
        ],
        "spellcaster": true,
        "subclasses": ["Draconic Bloodline", "Wild Magic"]
    },
    "Warlock": {
        "name": "Warlock",
        "description": "Заклинатель, получивший силы по договору с могущественным покровителем.",
        "hit_die": 8,
        "saving_throws": ["Мудрость", "Харизма"],
        "skills_count": 2,
        "skills_options": ["Магия", "История", "Запугивание", "Обман", "Природа", "Религия", "Расследование"],
        "weapon_proficiencies": ["Simple weapons"],
        "armor_proficiencies": ["Light armor"],
        "starting_equipment": [
            "Легкий арбалет и 20 болтов или Простое оружие",
            "Компонентная сумка или Заклинательный фокус",
            "Набор ученого (Scholar's Pack) или Набор подземелья",
            "Кожаный доспех, Два кинжала, Простое оружие"
        ],
        "spellcaster": true,
        "subclasses": ["The Fiend", "The Archfey", "The Great Old One"]
    },
    "Wizard": {
        "name": "Wizard",
        "description": "Ученый маг, кропотливо изучающий формулы заклинаний в своей книге.",
        "hit_die": 6,
        "saving_throws": ["Интеллект", "Мудрость"],
        "skills_count": 2,
        "skills_options": ["Магия", "История", "Медицина", "Проницательность", "Религия", "Расследование"],
        "weapon_proficiencies": ["Daggers", "Darts", "Slings", "Quarterstaffs", "Light crossbows"],
        "armor_proficiencies": [],
        "starting_equipment": [
            "Посох (Quarterstaff) или Кинжал",
            "Компонентная сумка или Заклинательный фокус",
            "Набор ученого (Scholar's Pack) или Набор исследователя",
            "Книга заклинаний (Spellbook)"
        ],
        "spellcaster": true,
        "subclasses": ["School of Evocation", "School of Abjuration", "School of Divination"]
    }
};

const DND_ITEMS = [
    // Оружие ближнего боя
    { "name": "Кинжал (Dagger)", "type": "weapon", "weight": 1, "cost": "2 gp", "description": "1d4 колющего урона, легкое, метательное, фехтовальное" },
    { "name": "Длинный меч (Longsword)", "type": "weapon", "weight": 3, "cost": "15 gp", "description": "1d8 рубящего урона (универсальное 1d10)" },
    { "name": "Двуручный меч (Greatsword)", "type": "weapon", "weight": 6, "cost": "50 gp", "description": "2d6 рубящего урона, тяжелое, двуручное" },
    { "name": "Рапира (Rapier)", "type": "weapon", "weight": 2, "cost": "25 gp", "description": "1d8 колющего урона, фехтовальное" },
    { "name": "Секира (Greataxe)", "type": "weapon", "weight": 7, "cost": "30 gp", "description": "1d12 рубящего урона, тяжелое, двуручное" },
    
    // Оружие дальнего боя
    { "name": "Короткий лук (Shortbow)", "type": "weapon", "weight": 2, "cost": "25 gp", "description": "1d6 колющего урона (дистанция 80/320), двуручное" },
    { "name": "Длинный лук (Longbow)", "type": "weapon", "weight": 2, "cost": "50 gp", "description": "1d8 колющего урона (дистанция 150/600), тяжелое, двуручное" },
    { "name": "Легкий арбалет (Light Crossbow)", "type": "weapon", "weight": 5, "cost": "25 gp", "description": "1d8 колющего урона (дистанция 80/320), двуручное, перезарядка" },
    
    // Броня
    { "name": "Кожаный доспех (Leather)", "type": "armor", "weight": 10, "cost": "10 gp", "description": "Легкий доспех. Класс Доспеха (AC) = 11 + Модификатор Ловкости" },
    { "name": "Чешуйчатый доспех (Scale Mail)", "type": "armor", "weight": 45, "cost": "50 gp", "description": "Средний доспех. AC = 14 + Мод Ловкости (макс +2). Помеха на Скрытность" },
    { "name": "Кольчатый доспех (Chain Mail)", "type": "armor", "weight": 55, "cost": "75 gp", "description": "Тяжелый доспех. AC = 16. Требует Силу 13. Помеха на Скрытность" },
    { "name": "Латы (Plate)", "type": "armor", "weight": 65, "cost": "1500 gp", "description": "Тяжелый доспех. AC = 18. Требует Силу 15. Помеха на Скрытность" },
    
    // Щиты
    { "name": "Щит (Shield)", "type": "shield", "weight": 6, "cost": "10 gp", "description": "+2 к Классу Доспеха (AC) при использовании" },
    
    // Инструменты
    { "name": "Воровские инструменты (Thieves' Tools)", "type": "tool", "weight": 1, "cost": "25 gp", "description": "Используются для взлома замков и обезвреживания ловушек" }
];

const DND_SPELLS = [
    { "name": "Мистический Заряд (Eldritch Blast)", "level": 0, "school": "Evocation", "time": "1 action", "range": "120 feet", "components": "V, S", "duration": "Instantaneous", "description": "Луч темной энергии наносит 1d10 силового урона. На более высоких уровнях выпускает дополнительные лучи." },
    { "name": "Чудотворство (Thaumaturgy)", "level": 0, "school": "Transmutation", "time": "1 action", "range": "30 feet", "components": "V", "duration": "Up to 1 minute", "description": "Вы совершаете мелкое чудо: меняете громкость голоса, мерцание факелов или гул земли." },
    { "name": "Малая Иллюзия (Minor Illusion)", "level": 0, "school": "Illusion", "time": "1 action", "range": "30 feet", "components": "S, M", "duration": "1 minute", "description": "Создает звук или визуальный образ предмета в пределах дистанции." },
    
    { "name": "Стрела Хаоса (Chaos Bolt)", "level": 1, "school": "Evocation", "time": "1 action", "range": "120 feet", "components": "V, S", "duration": "Instantaneous", "description": "Наносит 2d8 + 1d6 стихийного урона. При совпадении чисел на d8 заряд прыгает на соседнюю цель." },
    { "name": "Волшебная Стрела (Magic Missile)", "level": 1, "school": "Evocation", "time": "1 action", "range": "120 feet", "components": "V, S", "duration": "Instantaneous", "description": "Три самонаводящиеся стрелы наносят по 1d4 + 1 силового урона каждая без промаха." },
    { "name": "Лечащее Слово (Healing Word)", "level": 1, "school": "Evocation", "time": "1 bonus action", "range": "60 feet", "components": "V", "duration": "Instantaneous", "description": "Существо восстанавливает хиты в размере 1d4 + ваш модификатор заклинательной характеристики." },
    
    { "name": "Огненный Шар (Fireball)", "level": 3, "school": "Evocation", "time": "1 action", "range": "150 feet", "components": "V, S, M", "duration": "Instantaneous", "description": "Взрыв пламени наносит 8d6 огненного урона в сфере радиусом 20 футов. Спасбросок Ловкости половинит урон." }
];
