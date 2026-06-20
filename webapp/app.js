// DiceRoller Mini App - App Manager and Event Handlers
const tg = window.Telegram.WebApp;
tg.expand();

const ALL_SAVING_THROWS = [
    "Сила", "Ловкость", "Телосложение", 
    "Интеллект", "Мудрость", "Харизма"
];

const ALL_SKILLS = [
    "Атлетика", "Акробатика", "Ловкость рук", "Скрытность",
    "Анализ", "История", "Магия", "Природа", "Религия",
    "Уход за животными", "Внимательность", "Проницательность", "Медицина", "Выживание",
    "Обман", "Запугивание", "Выступление", "Убеждение"
];

const ALL_TOOLS = [
    "Воровские инструменты", "Инструменты навигатора", "Инструменты отравителя",
    "Набор травника", "Набор для грима", "Набор для фальсификации",
    "Сухопутный транспорт", "Водный транспорт",
    "Игровой набор: Драконьи шахматы", "Игровой набор: Карты", 
    "Игровой набор: Кости", "Игровой набор: Ставка трёх драконов",
    "Музыкальный инструмент: Барабан", "Музыкальный инструмент: Виола", 
    "Музыкальный инструмент: Волынка", "Музыкальный инструмент: Лира", 
    "Музыкальный инструмент: Лютня", "Музыкальный инструмент: Рожок", 
    "Музыкальный инструмент: Свирель", "Музыкальный инструмент: Флейта", 
    "Музыкальный инструмент: Цимбалы", "Музыкальный инструмент: Шалмей",
    "Инструменты алхимика", "Инструменты пивовара", "Инструменты каллиграфа",
    "Инструменты плотника", "Инструменты картографа", "Инструменты сапожника",
    "Инструменты повара", "Инструменты стеклодува", "Инструменты ювелира",
    "Инструменты кожевника", "Инструменты каменщика", "Инструменты художника",
    "Инструменты гончара", "Инструменты резчика по дереву", "Инструменты кузнеца",
    "Инструменты ткача", "Инструменты ремонтника"
];

// App State
let state = {
    characters: [],
    currentCharacter: null, // Character class instance
    wizardStep: 1,
    rolledStats: [],
    activeView: 'list' // list, wizard, sheet
};

// --- DOM References ---
const viewList = document.getElementById('list-view');
const viewWizard = document.getElementById('wizard-view');
const viewSheet = document.getElementById('sheet-view');

// --- API Helpers ---
const initData = tg.initData || '';

async function apiCall(endpoint, method = 'GET', body = null) {
    const headers = {
        'Content-Type': 'application/json',
        'X-Telegram-Init-Data': initData
    };
    const config = { method, headers };
    if (body) {
        config.body = JSON.stringify(body);
    }
    
    try {
        const response = await fetch(endpoint, config);
        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.error || 'Ошибка сервера');
        }
        return await response.json();
    } catch (err) {
        showToast(err.message, 'error');
        throw err;
    }
}

// Toast System
function showToast(message, type = 'success') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `<span>${type === 'success' ? '✅' : '⚠️'}</span> ${message}`;
    container.appendChild(toast);
    
    setTimeout(() => {
        toast.classList.add('toast-out');
        toast.addEventListener('animationend', () => toast.remove());
    }, 3500);
}

// Escape Html helper
function escapeHtml(unsafe) {
    if (!unsafe) return "";
    return String(unsafe)
         .replace(/&/g, "&amp;")
         .replace(/</g, "&lt;")
         .replace(/>/g, "&gt;")
         .replace(/"/g, "&quot;")
         .replace(/'/g, "&#039;");
}

// --- Dynamic Database loading ---
async function loadCharacters() {
    const listContainer = document.getElementById('characters-list');
    listContainer.innerHTML = `
        <div class="loading-placeholder">
            <div class="spinner"></div>
            <p>Загрузка списка героев...</p>
        </div>
    `;
    
    try {
        state.characters = await apiCall('/api/characters');
        document.getElementById('characters-count').textContent = `${state.characters.length} героев`;
        renderCharactersList();
    } catch (err) {
        listContainer.innerHTML = `
            <div class="empty-state">
                <p>Не удалось загрузить список персонажей.</p>
                <button class="btn btn-primary" onclick="loadCharacters()">Повторить</button>
            </div>
        `;
    }
}

function renderCharactersList() {
    const listContainer = document.getElementById('characters-list');
    
    if (state.characters.length === 0) {
        listContainer.innerHTML = `
            <div class="empty-state">
                <span style="font-size: 44px;">🧙‍♂️</span>
                <h3>Создайте своего героя</h3>
                <p>У вас пока нет персонажей. Нажмите кнопку ниже, чтобы начать приключение!</p>
            </div>
        `;
        return;
    }
    
    listContainer.innerHTML = '';
    state.characters.forEach(charData => {
        // Hydrate to Character model
        const char = new Character(charData.full_data && Object.keys(charData.full_data).length ? charData.full_data : charData);
        const card = document.createElement('div');
        card.className = `char-card ${charData.is_active ? 'active-char' : ''}`;
        
        const formatMod = (v) => v >= 0 ? `+${v}` : v;
        const portraitHtml = char.portrait.length > 2 
            ? `<img src="${escapeHtml(char.portrait)}" class="sheet-portrait-image" alt="P">` 
            : char.portrait || "🧙‍♂️";
        
        card.innerHTML = `
            <div class="char-card-header">
                <div class="sheet-hero-identity">
                    <div class="sheet-portrait-circle" style="width:36px; height:36px; font-size:18px;">${portraitHtml}</div>
                    <div class="char-card-title">
                        <h3>${escapeHtml(char.name)}</h3>
                        <p>${escapeHtml(char.classes.map(c => `${c.className} ${c.level}`).join(" / "))}</p>
                    </div>
                </div>
                <div class="char-actions-top">
                    ${charData.is_active ? '<span class="char-badge active-badge">Активен</span>' : ''}
                    <button class="btn btn-icon-only edit-btn" style="margin-left: 8px; font-size: 11px; padding: 4px; width:28px; height:28px;">✏️</button>
                </div>
            </div>
            <div class="char-card-body">
                <div class="char-mini-stat"><span class="stat-name">СИЛ</span><span class="stat-value">${formatMod(char.getAbilityModifier("strength"))}</span></div>
                <div class="char-mini-stat"><span class="stat-name">ЛОВ</span><span class="stat-value">${formatMod(char.getAbilityModifier("dexterity"))}</span></div>
                <div class="char-mini-stat"><span class="stat-name">ТЕЛ</span><span class="stat-value">${formatMod(char.getAbilityModifier("constitution"))}</span></div>
                <div class="char-mini-stat"><span class="stat-name">ИНТ</span><span class="stat-value">${formatMod(char.getAbilityModifier("intelligence"))}</span></div>
                <div class="char-mini-stat"><span class="stat-name">МДР</span><span class="stat-value">${formatMod(char.getAbilityModifier("wisdom"))}</span></div>
                <div class="char-mini-stat"><span class="stat-name">ХАР</span><span class="stat-value">${formatMod(char.getAbilityModifier("charisma"))}</span></div>
            </div>
        `;
        
        // Card click -> Dashboard Sheet
        card.addEventListener('click', (e) => {
            if (e.target.closest('.edit-btn')) {
                openWizard(char);
                return;
            }
            openSheet(char);
        });
        
        listContainer.appendChild(card);
    });
}

// --- Navigation / View Routing ---
function switchView(viewName) {
    state.activeView = viewName;
    viewList.classList.remove('active');
    viewWizard.classList.remove('active');
    viewSheet.classList.remove('active');
    
    if (viewName === 'list') {
        viewList.classList.add('active');
    } else if (viewName === 'wizard') {
        viewWizard.classList.add('active');
    } else if (viewName === 'sheet') {
        viewSheet.classList.add('active');
    }
}

// --- 1. DIRECT INLINE EDITING LOGIC ---
function toggleEditMode(forceState = null) {
    const isEdit = forceState !== null ? forceState : !viewSheet.classList.contains('edit-mode');
    const editBtn = document.getElementById('btn-sheet-edit');
    
    if (isEdit) {
        viewSheet.classList.add('edit-mode');
        editBtn.textContent = '💾';
        editBtn.title = 'Сохранить';
        
        // Populate inputs from current character model
        populateEditInputs();
    } else {
        viewSheet.classList.remove('edit-mode');
        editBtn.textContent = '✏️';
        editBtn.title = 'Редактировать';
        
        // Save current inputs to character model, recalculate, and sync with db
        saveEditInputs();
    }
}

function populateEditInputs() {
    const char = state.currentCharacter;
    if (!char) return;
    
    document.getElementById('sheet-portrait-input').value = char.portrait || '🧙‍♂️';
    document.getElementById('sheet-char-name-input').value = char.name;
    document.getElementById('sheet-char-background-input').value = char.background || 'Custom';
    document.getElementById('sheet-char-alignment-select').value = char.alignment || 'True Neutral';
    document.getElementById('sheet-char-xp-input').value = char.xp || 0;
    document.getElementById('sheet-hp-max-input').value = char.hp.max || 10;
    
    // Player Name
    document.getElementById('sheet-player-name-input').value = char.playerName || '';
    
    // Overrides
    document.getElementById('sheet-speed-input').value = char.customSpeed !== null ? char.customSpeed : '';
    document.getElementById('sheet-ac-override-input').value = char.customAC !== null ? char.customAC : '';
    document.getElementById('sheet-init-override-input').value = char.customInitiative !== null ? char.customInitiative : '';
    document.getElementById('sheet-spell-dc-override-input').value = char.customSpellDC !== null ? char.customSpellDC : '';
    document.getElementById('sheet-spell-attack-override-input').value = char.customSpellAttack !== null ? char.customSpellAttack : '';
    
    // Populate Races dropdown
    const raceSel = document.getElementById('sheet-char-race-select');
    raceSel.innerHTML = '';
    Object.keys(DND_RACES).forEach(rName => {
        const opt = document.createElement('option');
        opt.value = rName;
        opt.textContent = rName;
        if (rName === char.race) opt.selected = true;
        raceSel.appendChild(opt);
    });
    
    // Subraces dropdown
    updateSubraceSelector(char.race, char.subrace);
    
    // Bind Race select change listener
    raceSel.onchange = () => {
        char.race = raceSel.value;
        char.subrace = '';
        updateSubraceSelector(char.race, '');
        recalculateAndSave();
    };
    
    // Render classes editor
    renderClassesEditor();
    
    // Populate coin inputs
    document.getElementById('sheet-coin-cp-input').value = char.coins?.cp || 0;
    document.getElementById('sheet-coin-sp-input').value = char.coins?.sp || 0;
    document.getElementById('sheet-coin-ep-input').value = char.coins?.ep || 0;
    document.getElementById('sheet-coin-gp-input').value = char.coins?.gp || 0;
    document.getElementById('sheet-coin-pp-input').value = char.coins?.pp || 0;

    // Languages and Other Proficiencies
    document.getElementById('sheet-languages-input').value = char.languages || '';
    document.getElementById('sheet-other-proficiencies-input').value = char.otherProficiencies || '';

    // Personality Traits, Ideals, Bonds, Flaws
    document.getElementById('sheet-personality-input').value = char.personalityTraits || '';
    document.getElementById('sheet-ideals-input').value = char.ideals || '';
    document.getElementById('sheet-bonds-input').value = char.bonds || '';
    document.getElementById('sheet-flaws-input').value = char.flaws || '';

    // Appearance & Backstory
    document.getElementById('sheet-age-input').value = char.age || '';
    document.getElementById('sheet-height-input').value = char.height || '';
    document.getElementById('sheet-weight-input').value = char.weight || '';
    document.getElementById('sheet-eyes-input').value = char.eyes || '';
    document.getElementById('sheet-skin-input').value = char.skin || '';
    document.getElementById('sheet-hair-input').value = char.hair || '';
    document.getElementById('sheet-backstory-input').value = char.backstory || '';
}

function updateSubraceSelector(raceName, selectedSubrace) {
    const subSel = document.getElementById('sheet-char-subrace-select');
    subSel.innerHTML = '';
    const raceRule = DND_RACES[raceName];
    
    if (raceRule && raceRule.subraces && raceRule.subraces.length > 0) {
        subSel.style.display = 'inline-block';
        const emptyOpt = document.createElement('option');
        emptyOpt.value = '';
        emptyOpt.textContent = '— Без субрасы —';
        subSel.appendChild(emptyOpt);
        
        raceRule.subraces.forEach(sub => {
            const opt = document.createElement('option');
            opt.value = sub.name;
            opt.textContent = sub.name;
            if (sub.name === selectedSubrace) opt.selected = true;
            subSel.appendChild(opt);
        });
        
        subSel.onchange = () => {
            state.currentCharacter.subrace = subSel.value;
            recalculateAndSave();
        };
    } else {
        subSel.style.display = 'none';
        state.currentCharacter.subrace = '';
    }
}

function renderClassesEditor() {
    const char = state.currentCharacter;
    const container = document.getElementById('sheet-classes-list-edit');
    container.innerHTML = '';
    
    char.classes.forEach((c, index) => {
        const row = document.createElement('div');
        row.className = 'class-edit-row';
        
        let selectHtml = `<select class="sheet-class-sel" data-index="${index}">`;
        Object.keys(DND_CLASSES).forEach(clsName => {
            selectHtml += `<option value="${clsName}" ${c.className === clsName ? 'selected' : ''}>${clsName}</option>`;
        });
        selectHtml += `</select>`;
        
        row.innerHTML = `
            ${selectHtml}
            <div class="number-input" style="display:flex; gap:4px; align-items:center;">
                <button type="button" class="btn btn-secondary btn-sm minus-cls-sheet" data-index="${index}" style="padding:4px 8px;">—</button>
                <input type="number" class="sheet-class-lvl-input" data-index="${index}" value="${c.level}" readonly style="width:40px; text-align:center; padding:4px; border:1px solid var(--border-color); background:rgba(0,0,0,0.2); color:#fff; border-radius:6px; font-weight:700;">
                <button type="button" class="btn btn-secondary btn-sm plus-cls-sheet" data-index="${index}" style="padding:4px 8px;">+</button>
            </div>
            ${index > 0 ? `<button type="button" class="btn btn-danger btn-sm del-class-sheet" data-index="${index}" style="padding:4px 8px;">🗑️</button>` : ''}
        `;
        
        // Listeners
        row.querySelector('.sheet-class-sel').onchange = (e) => {
            char.classes[index].className = e.target.value;
            char.classes[index].subclass = '';
            recalculateAndSave();
        };
        
        row.querySelector('.plus-cls-sheet').onclick = () => {
            const currentTotal = char.totalLevel;
            if (currentTotal >= 20) {
                showToast('Максимальный уровень персонажа — 20!', 'error');
                return;
            }
            char.classes[index].level = Math.min(20, char.classes[index].level + 1);
            recalculateAndSave();
            renderClassesEditor();
        };
        
        row.querySelector('.minus-cls-sheet').onclick = () => {
            char.classes[index].level = Math.max(1, char.classes[index].level - 1);
            recalculateAndSave();
            renderClassesEditor();
        };
        
        if (index > 0) {
            row.querySelector('.del-class-sheet').onclick = () => {
                char.classes.splice(index, 1);
                recalculateAndSave();
                renderClassesEditor();
            };
        }
        
        container.appendChild(row);
    });
}

function saveEditInputs() {
    const char = state.currentCharacter;
    if (!char) return;
    
    const nameVal = document.getElementById('sheet-char-name-input').value.trim();
    if (!nameVal) {
        showToast('Имя персонажа не может быть пустым!', 'error');
        document.getElementById('sheet-char-name-input').value = char.name; // revert
        return;
    }
    
    char.name = nameVal;
    char.portrait = document.getElementById('sheet-portrait-input').value.trim() || '🧙‍♂️';
    char.background = document.getElementById('sheet-char-background-input').value.trim() || 'Custom';
    char.alignment = document.getElementById('sheet-char-alignment-select').value;
    char.xp = parseInt(document.getElementById('sheet-char-xp-input').value) || 0;
    
    const maxHp = parseInt(document.getElementById('sheet-hp-max-input').value) || 10;
    char.hp.max = maxHp;
    if (char.hp.current > maxHp) char.hp.current = maxHp;
    
    // Player Name
    char.playerName = document.getElementById('sheet-player-name-input').value.trim();
    
    // Overrides
    const speedVal = document.getElementById('sheet-speed-input').value.trim();
    char.customSpeed = speedVal !== '' ? parseInt(speedVal) : null;
    
    const acVal = document.getElementById('sheet-ac-override-input').value.trim();
    char.customAC = acVal !== '' ? parseInt(acVal) : null;
    
    const initVal = document.getElementById('sheet-init-override-input').value.trim();
    char.customInitiative = initVal !== '' ? parseInt(initVal) : null;
    
    const dcVal = document.getElementById('sheet-spell-dc-override-input').value.trim();
    char.customSpellDC = dcVal !== '' ? parseInt(dcVal) : null;
    
    const spellAtkVal = document.getElementById('sheet-spell-attack-override-input').value.trim();
    char.customSpellAttack = spellAtkVal !== '' ? parseInt(spellAtkVal) : null;
    
    // Coins
    char.coins = {
        cp: parseInt(document.getElementById('sheet-coin-cp-input').value) || 0,
        sp: parseInt(document.getElementById('sheet-coin-sp-input').value) || 0,
        ep: parseInt(document.getElementById('sheet-coin-ep-input').value) || 0,
        gp: parseInt(document.getElementById('sheet-coin-gp-input').value) || 0,
        pp: parseInt(document.getElementById('sheet-coin-pp-input').value) || 0
    };

    // Languages and Other Proficiencies
    char.languages = document.getElementById('sheet-languages-input').value.trim();
    char.otherProficiencies = document.getElementById('sheet-other-proficiencies-input').value.trim();

    // Personality Traits, Ideals, Bonds, Flaws
    char.personalityTraits = document.getElementById('sheet-personality-input').value.trim();
    char.ideals = document.getElementById('sheet-ideals-input').value.trim();
    char.bonds = document.getElementById('sheet-bonds-input').value.trim();
    char.flaws = document.getElementById('sheet-flaws-input').value.trim();

    // Appearance & Backstory
    char.age = document.getElementById('sheet-age-input').value.trim();
    char.height = document.getElementById('sheet-height-input').value.trim();
    char.weight = document.getElementById('sheet-weight-input').value.trim();
    char.eyes = document.getElementById('sheet-eyes-input').value.trim();
    char.skin = document.getElementById('sheet-skin-input').value.trim();
    char.hair = document.getElementById('sheet-hair-input').value.trim();
    char.backstory = document.getElementById('sheet-backstory-input').value.trim();
    
    recalculateAndSave();
}

async function recalculateAndSave() {
    const char = state.currentCharacter;
    if (!char) return;
    
    // Update headers and meta on sheet
    const portraitHtml = char.portrait.length > 2 
        ? `<img src="${escapeHtml(char.portrait)}" class="sheet-portrait-image" alt="P">` 
        : char.portrait || "🧙‍♂️";
    document.getElementById('sheet-portrait-placeholder').innerHTML = portraitHtml;
    document.getElementById('sheet-char-name').textContent = char.name;
    const classesStr = char.classes.map(c => `${c.className} ${c.level}`).join(" / ");
    document.getElementById('sheet-char-meta').textContent = `${char.race} • ${classesStr} • Ур. ${char.totalLevel}`;
    
    // Re-draw tabs in view mode
    updateDashboardCombatTab();
    updateDashboardStatsTab();
    updateDashboardInventoryTab();
    updateDashboardSpellsTab();
    updateDashboardFeaturesTab();
    updateDashboardNotesTab();
    
    // Sync with database
    await syncCharacterData();
}

function openWizard(character = null) {
    if (character) {
        state.currentCharacter = character;
    } else {
        state.currentCharacter = new Character({
            name: "Новый герой",
            stats: { strength: 10, dexterity: 10, constitution: 10, intelligence: 10, wisdom: 10, charisma: 10 },
            hp: { current: 10, max: 10, temp: 0 }
        });
    }
    
    state.wizardStep = 1;
    switchView('wizard');
    initWizardStep();
}

function initWizardStep() {
    const panels = document.querySelectorAll('.wizard-step-panel');
    panels.forEach(p => {
        const stepNum = parseInt(p.getAttribute('data-step'));
        if (stepNum === state.wizardStep) {
            p.classList.add('active');
        } else {
            p.classList.remove('active');
        }
    });

    const dots = document.querySelectorAll('.step-dot');
    dots.forEach(d => {
        const stepNum = parseInt(d.getAttribute('data-step'));
        if (stepNum === state.wizardStep) {
            d.classList.add('active');
        } else {
            d.classList.remove('active');
        }
    });

    const btnPrev = document.getElementById('btn-wizard-prev');
    const btnNext = document.getElementById('btn-wizard-next');
    const btnFinish = document.getElementById('btn-wizard-finish');

    btnPrev.disabled = (state.wizardStep === 1);
    
    if (state.wizardStep === 9) {
        btnNext.style.display = 'none';
        btnFinish.style.display = 'inline-block';
    } else {
        btnNext.style.display = 'inline-block';
        btnFinish.style.display = 'none';
    }

    renderStepContent();
}

function saveWizardStepData() {
    const char = state.currentCharacter;
    if (!char) return;
    
    if (state.wizardStep === 1) {
        char.name = document.getElementById('wiz-name').value.trim() || 'Без имени';
        char.playerName = document.getElementById('wiz-player-name').value.trim();
        char.xp = parseInt(document.getElementById('wiz-xp').value) || 0;
        char.portrait = document.getElementById('wiz-portrait').value.trim() || '🧙‍♂️';
        char.alignment = document.getElementById('wiz-alignment').value;
        char.background = document.getElementById('wiz-background').value.trim() || 'Custom';
    } else if (state.wizardStep === 2) {
        char.age = document.getElementById('wiz-age').value.trim();
        char.height = document.getElementById('wiz-height').value.trim();
        char.weight = document.getElementById('wiz-weight').value.trim();
        char.eyes = document.getElementById('wiz-eyes').value.trim();
        char.skin = document.getElementById('wiz-skin').value.trim();
        char.hair = document.getElementById('wiz-hair').value.trim();
        char.backstory = document.getElementById('wiz-backstory').value.trim();
    } else if (state.wizardStep === 3) {
        char.languages = document.getElementById('wiz-languages').value.trim();
        char.otherProficiencies = document.getElementById('wiz-other-proficiencies').value.trim();
    } else if (state.wizardStep === 4) {
        char.hp.max = parseInt(document.getElementById('wiz-max-hp').value) || 10;
        if (char.hp.current > char.hp.max) char.hp.current = char.hp.max;
        
        const speedVal = document.getElementById('wiz-speed-override').value.trim();
        char.customSpeed = speedVal !== '' ? parseInt(speedVal) : null;
        
        const acVal = document.getElementById('wiz-ac-override').value.trim();
        char.customAC = acVal !== '' ? parseInt(acVal) : null;
        
        const initVal = document.getElementById('wiz-init-override').value.trim();
        char.customInitiative = initVal !== '' ? parseInt(initVal) : null;
        
        const dcVal = document.getElementById('wiz-dc-override').value.trim();
        char.customSpellDC = dcVal !== '' ? parseInt(dcVal) : null;
        
        const attVal = document.getElementById('wiz-spell-attack-override').value.trim();
        char.customSpellAttack = attVal !== '' ? parseInt(attVal) : null;
    }
}

function renderStepContent() {
    const char = state.currentCharacter;
    if (state.wizardStep === 1) {
        document.getElementById('wiz-name').value = char.name || '';
        document.getElementById('wiz-player-name').value = char.playerName || '';
        document.getElementById('wiz-xp').value = char.xp || 0;
        document.getElementById('wiz-portrait').value = char.portrait || '';
        document.getElementById('wiz-alignment').value = char.alignment || 'True Neutral';
        document.getElementById('wiz-background').value = char.background || 'Custom';
        
        const presets = document.querySelectorAll('.preset-emoji');
        presets.forEach(p => {
            p.onclick = () => {
                document.getElementById('wiz-portrait').value = p.textContent;
                char.portrait = p.textContent;
            };
        });
    } else if (state.wizardStep === 2) {
        document.getElementById('wiz-age').value = char.age || '';
        document.getElementById('wiz-height').value = char.height || '';
        document.getElementById('wiz-weight').value = char.weight || '';
        document.getElementById('wiz-eyes').value = char.eyes || '';
        document.getElementById('wiz-skin').value = char.skin || '';
        document.getElementById('wiz-hair').value = char.hair || '';
        document.getElementById('wiz-backstory').value = char.backstory || '';
    } else if (state.wizardStep === 3) {
        renderRaceStep();
    } else if (state.wizardStep === 4) {
        renderClassStep();
    } else if (state.wizardStep === 5) {
        renderStatsStep();
    } else if (state.wizardStep === 6) {
        renderProficienciesStep();
    } else if (state.wizardStep === 7) {
        renderFeaturesStep();
    } else if (state.wizardStep === 8) {
        renderEquipmentStep();
    } else if (state.wizardStep === 9) {
        renderSpellsStep();
    }
}

function renderRaceStep() {
    const container = document.getElementById('race-grid-container');
    if (!container) return;
    container.innerHTML = '';

    const char = state.currentCharacter;
    
    Object.keys(DND_RACES).forEach(rKey => {
        const race = DND_RACES[rKey];
        const card = document.createElement('div');
        card.className = `grid-select-card ${char.race === rKey ? 'selected' : ''}`;
        card.innerHTML = `
            <h4>${escapeHtml(race.name)}</h4>
            <p style="font-size:11px; color:var(--text-muted);">${escapeHtml(race.description.substring(0, 50))}...</p>
        `;
        card.onclick = () => {
            container.querySelectorAll('.grid-select-card').forEach(c => c.classList.remove('selected'));
            card.classList.add('selected');
            
            char.race = rKey;
            char.subrace = '';
            
            if (!char.languages) {
                char.languages = race.languages.join(', ');
                document.getElementById('wiz-languages').value = char.languages;
            }
            
            updateWizardSubrace(rKey);
            showRaceDescription(rKey);
        };
        container.appendChild(card);
    });

    updateWizardSubrace(char.race, char.subrace);
    showRaceDescription(char.race);
    
    document.getElementById('wiz-languages').value = char.languages || '';
    document.getElementById('wiz-other-proficiencies').value = char.otherProficiencies || '';
}

function updateWizardSubrace(raceKey, selectedSubrace = '') {
    const subContainer = document.getElementById('subrace-container');
    const select = document.getElementById('wiz-subrace');
    const race = DND_RACES[raceKey];
    
    if (race && race.subraces && race.subraces.length > 0) {
        subContainer.style.display = 'block';
        select.innerHTML = '<option value="">— Выберите субрасу —</option>';
        race.subraces.forEach(sub => {
            const opt = document.createElement('option');
            opt.value = sub.name;
            opt.textContent = sub.name;
            if (sub.name === (selectedSubrace || state.currentCharacter.subrace)) opt.selected = true;
            select.appendChild(opt);
        });
        select.onchange = () => {
            state.currentCharacter.subrace = select.value;
        };
    } else {
        subContainer.style.display = 'none';
        state.currentCharacter.subrace = '';
    }
}

function showRaceDescription(raceKey) {
    const panel = document.getElementById('race-description-panel');
    const race = DND_RACES[raceKey];
    if (race) {
        panel.style.display = 'block';
        let featHtml = race.features.map(f => `<li>${escapeHtml(f)}</li>`).join('');
        panel.innerHTML = `
            <strong>Особенности расы:</strong>
            <p style="font-size:12px; margin: 4px 0 8px 0;">${escapeHtml(race.description)}</p>
            <ul style="font-size:11px; padding-left:15px; margin:0;">${featHtml}</ul>
        `;
    } else {
        panel.style.display = 'none';
    }
}

function renderClassStep() {
    const container = document.getElementById('classes-list-wrapper');
    if (!container) return;
    container.innerHTML = '';
    
    const char = state.currentCharacter;
    
    char.classes.forEach((c, index) => {
        const row = document.createElement('div');
        row.className = 'class-edit-row';
        row.style.display = 'flex';
        row.style.gap = '8px';
        row.style.alignItems = 'center';
        row.style.marginBottom = '8px';
        
        let selectHtml = `<select class="wiz-class-sel" data-index="${index}" style="flex:1; padding:6px; border-radius:6px; background:var(--bg-card); color:#fff; border:1px solid var(--border-color);">`;
        Object.keys(DND_CLASSES).forEach(clsName => {
            selectHtml += `<option value="${clsName}" ${c.className === clsName ? 'selected' : ''}>${clsName}</option>`;
        });
        selectHtml += `</select>`;
        
        row.innerHTML = `
            ${selectHtml}
            <div style="display:flex; gap:4px; align-items:center;">
                <button type="button" class="btn btn-secondary btn-sm wiz-minus-class" data-index="${index}">—</button>
                <input type="number" class="wiz-class-lvl-input" data-index="${index}" value="${c.level}" readonly style="width:40px; text-align:center; padding:4px; border:1px solid var(--border-color); background:rgba(0,0,0,0.2); color:#fff; border-radius:6px; font-weight:700;">
                <button type="button" class="btn btn-secondary btn-sm wiz-plus-class" data-index="${index}">+</button>
            </div>
            ${index > 0 ? `<button type="button" class="btn btn-danger btn-sm wiz-del-class" data-index="${index}">🗑️</button>` : ''}
        `;
        
        row.querySelector('.wiz-class-sel').onchange = (e) => {
            char.classes[index].className = e.target.value;
            char.classes[index].subclass = '';
        };
        
        row.querySelector('.wiz-plus-class').onclick = () => {
            const currentTotal = char.classes.reduce((sum, cl) => sum + cl.level, 0);
            if (currentTotal >= 20) {
                showToast('Максимальный уровень персонажа — 20!', 'error');
                return;
            }
            char.classes[index].level = Math.min(20, char.classes[index].level + 1);
            row.querySelector('.wiz-class-lvl-input').value = char.classes[index].level;
        };
        
        row.querySelector('.wiz-minus-class').onclick = () => {
            char.classes[index].level = Math.max(1, char.classes[index].level - 1);
            row.querySelector('.wiz-class-lvl-input').value = char.classes[index].level;
        };
        
        if (index > 0) {
            row.querySelector('.wiz-del-class').onclick = () => {
                char.classes.splice(index, 1);
                renderClassStep();
            };
        }
        
        container.appendChild(row);
    });
    
    document.getElementById('btn-wizard-add-class').onclick = () => {
        const currentTotal = char.classes.reduce((sum, cl) => sum + cl.level, 0);
        if (currentTotal >= 20) {
            showToast('Максимальный уровень персонажа — 20!', 'error');
            return;
        }
        char.classes.push({ className: 'Fighter', level: 1, subclass: '' });
        renderClassStep();
    };
    
    document.getElementById('wiz-max-hp').value = char.hp.max || 10;
    
    document.getElementById('wiz-speed-override').value = char.customSpeed !== null ? char.customSpeed : '';
    document.getElementById('wiz-ac-override').value = char.customAC !== null ? char.customAC : '';
    document.getElementById('wiz-init-override').value = char.customInitiative !== null ? char.customInitiative : '';
    document.getElementById('wiz-dc-override').value = char.customSpellDC !== null ? char.customSpellDC : '';
    document.getElementById('wiz-spell-attack-override').value = char.customSpellAttack !== null ? char.customSpellAttack : '';
}

function renderStatsStep() {
    const methodSelect = document.getElementById('stat-gen-method-select');
    if (!methodSelect) return;
    
    const char = state.currentCharacter;
    methodSelect.value = char.statGenMethod || 'standard_array';
    
    methodSelect.onchange = () => {
        char.statGenMethod = methodSelect.value;
        char.statGenData = {};
        ['strength', 'dexterity', 'constitution', 'intelligence', 'wisdom', 'charisma'].forEach(s => {
            char.stats[s] = 10;
        });
        renderStatsStep();
    };

    const contentDiv = document.getElementById('stat-gen-content');
    contentDiv.innerHTML = '';

    const statsList = ['strength', 'dexterity', 'constitution', 'intelligence', 'wisdom', 'charisma'];
    const statsRu = {
        strength: 'Сила',
        dexterity: 'Ловкость',
        constitution: 'Телосложение',
        intelligence: 'Интеллект',
        wisdom: 'Мудрость',
        charisma: 'Харизма'
    };

    if (char.statGenMethod === 'standard_array') {
        const arrayVals = [15, 14, 13, 12, 10, 8];
        const form = document.createElement('div');
        form.style.display = 'flex';
        form.style.flexDirection = 'column';
        form.style.gap = '8px';
        
        statsList.forEach(sName => {
            const row = document.createElement('div');
            row.style.display = 'flex';
            row.style.justifyContent = 'space-between';
            row.style.alignItems = 'center';
            const currentVal = char.stats[sName] || 10;
            
            let optionsHtml = `<option value="10">Выберите значение</option>`;
            arrayVals.forEach(v => {
                optionsHtml += `<option value="${v}" ${currentVal === v ? 'selected' : ''}>${v}</option>`;
            });
            
            row.innerHTML = `
                <span style="font-weight:600;">${statsRu[sName]}</span>
                <select class="wiz-stat-array-sel" data-stat="${sName}" style="padding:6px; border-radius:6px; background:var(--bg-card); color:#fff; border:1px solid var(--border-color); width:120px;">
                    ${optionsHtml}
                </select>
            `;
            
            row.querySelector('select').onchange = (e) => {
                char.stats[sName] = parseInt(e.target.value) || 10;
                updateStatsSummaryGrid();
            };
            form.appendChild(row);
        });
        contentDiv.appendChild(form);
        
    } else if (char.statGenMethod === 'point_buy') {
        const costTable = { 8: 0, 9: 1, 10: 2, 11: 3, 12: 4, 13: 5, 14: 7, 15: 9 };
        statsList.forEach(sName => {
            if (!char.stats[sName] || char.stats[sName] < 8 || char.stats[sName] > 15) {
                char.stats[sName] = 8;
            }
        });
        
        const calculatePointsSpent = () => {
            let total = 0;
            statsList.forEach(sName => {
                const val = char.stats[sName];
                total += costTable[val] || 0;
            });
            return total;
        };

        const updatePointBuyView = () => {
            const spent = calculatePointsSpent();
            const remaining = 27 - spent;
            
            contentDiv.innerHTML = `
                <div style="margin-bottom: 12px; font-weight:700; text-align:center; color:${remaining >= 0 ? 'var(--primary)' : 'var(--danger)'};">
                    Осталось очков: ${remaining} / 27
                </div>
            `;
            
            const form = document.createElement('div');
            form.style.display = 'flex';
            form.style.flexDirection = 'column';
            form.style.gap = '8px';
            
            statsList.forEach(sName => {
                const row = document.createElement('div');
                row.style.display = 'flex';
                row.style.justifyContent = 'space-between';
                row.style.alignItems = 'center';
                const val = char.stats[sName];
                
                row.innerHTML = `
                    <span style="font-weight:600;">${statsRu[sName]}</span>
                    <div style="display:flex; align-items:center; gap:8px;">
                        <button type="button" class="btn btn-secondary btn-sm dec-pb" style="padding:2px 8px;">—</button>
                        <span style="font-size:16px; font-weight:700; width:24px; text-align:center;">${val}</span>
                        <button type="button" class="btn btn-secondary btn-sm inc-pb" style="padding:2px 8px;">+</button>
                        <span style="font-size:10px; color:var(--text-muted); width:40px; text-align:right;">(${costTable[val]} о.)</span>
                    </div>
                `;
                
                row.querySelector('.dec-pb').onclick = () => {
                    if (val > 8) {
                        char.stats[sName] = val - 1;
                        updatePointBuyView();
                        updateStatsSummaryGrid();
                    }
                };
                
                row.querySelector('.inc-pb').onclick = () => {
                    if (val < 15) {
                        const currentCost = costTable[val];
                        const nextCost = costTable[val + 1];
                        const diff = nextCost - currentCost;
                        if (remaining >= diff) {
                            char.stats[sName] = val + 1;
                            updatePointBuyView();
                            updateStatsSummaryGrid();
                        } else {
                            showToast('Недостаточно очков!', 'error');
                        }
                    }
                };
                form.appendChild(row);
            });
            contentDiv.appendChild(form);
        };
        updatePointBuyView();
        
    } else if (char.statGenMethod === 'dice_roll') {
        if (!char.statGenData.rolls) {
            char.statGenData.rolls = [];
        }
        
        const updateRollsView = () => {
            let rollsHtml = '';
            if (char.statGenData.rolls.length > 0) {
                rollsHtml = `
                    <div style="margin: 10px 0; text-align:center;">
                        <strong>Броски:</strong>
                        <div style="display:flex; gap:6px; justify-content:center; margin-top:6px;">
                            ${char.statGenData.rolls.map((r, i) => `<span class="roll-badge" style="background:var(--primary); color:#fff; padding:4px 8px; border-radius:6px; font-weight:700;">${r}</span>`).join('')}
                        </div>
                    </div>
                `;
            }
            
            contentDiv.innerHTML = `
                <div style="text-align:center; margin-bottom:12px;">
                    <button type="button" id="btn-wiz-roll-dice" class="btn btn-primary" style="width:100%;">Бросить 4d6 (6 раз)</button>
                </div>
                ${rollsHtml}
            `;
            
            const form = document.createElement('div');
            form.style.display = 'flex';
            form.style.flexDirection = 'column';
            form.style.gap = '8px';
            
            statsList.forEach(sName => {
                const row = document.createElement('div');
                row.style.display = 'flex';
                row.style.justifyContent = 'space-between';
                row.style.alignItems = 'center';
                const currentVal = char.stats[sName] || 10;
                
                let selectHtml = `<select class="wiz-stat-roll-sel" data-stat="${sName}" style="padding:6px; border-radius:6px; background:var(--bg-card); color:#fff; border:1px solid var(--border-color); width:120px;">`;
                selectHtml += `<option value="10">10 (По умолч.)</option>`;
                char.statGenData.rolls.forEach((r, idx) => {
                    selectHtml += `<option value="${r}" ${currentVal === r ? 'selected' : ''}>Бросок #${idx + 1} (${r})</option>`;
                });
                selectHtml += `</select>`;
                
                row.innerHTML = `
                    <span style="font-weight:600;">${statsRu[sName]}</span>
                    ${selectHtml}
                `;
                
                row.querySelector('select').onchange = (e) => {
                    char.stats[sName] = parseInt(e.target.value) || 10;
                    updateStatsSummaryGrid();
                };
                form.appendChild(row);
            });
            contentDiv.appendChild(form);
            
            document.getElementById('btn-wiz-roll-dice').onclick = () => {
                const rolls = [];
                for (let i = 0; i < 6; i++) {
                    const die = [
                        Math.floor(Math.random() * 6) + 1,
                        Math.floor(Math.random() * 6) + 1,
                        Math.floor(Math.random() * 6) + 1,
                        Math.floor(Math.random() * 6) + 1
                    ];
                    die.sort();
                    const sum = die[1] + die[2] + die[3];
                    rolls.push(sum);
                }
                char.statGenData.rolls = rolls;
                updateRollsView();
                updateStatsSummaryGrid();
            };
        };
        updateRollsView();
        
    } else {
        const form = document.createElement('div');
        form.style.display = 'flex';
        form.style.flexDirection = 'column';
        form.style.gap = '8px';
        
        statsList.forEach(sName => {
            const row = document.createElement('div');
            row.style.display = 'flex';
            row.style.justifyContent = 'space-between';
            row.style.alignItems = 'center';
            const currentVal = char.stats[sName] || 10;
            
            row.innerHTML = `
                <span style="font-weight:600;">${statsRu[sName]}</span>
                <input type="number" class="wiz-stat-manual-input" data-stat="${sName}" value="${currentVal}" min="3" max="20" style="padding:6px; border-radius:6px; background:var(--bg-card); color:#fff; border:1px solid var(--border-color); width:80px; text-align:center;">
            `;
            
            row.querySelector('input').onchange = (e) => {
                char.stats[sName] = parseInt(e.target.value) || 10;
                updateStatsSummaryGrid();
            };
            form.appendChild(row);
        });
        contentDiv.appendChild(form);
    }
    updateStatsSummaryGrid();
}

function updateStatsSummaryGrid() {
    const grid = document.getElementById('stats-wizard-summary-grid');
    if (!grid) return;
    grid.innerHTML = '';
    
    const char = state.currentCharacter;
    const statsList = ['strength', 'dexterity', 'constitution', 'intelligence', 'wisdom', 'charisma'];
    const statsAbbr = {
        strength: 'СИЛ',
        dexterity: 'ЛОВ',
        constitution: 'ТЕЛ',
        intelligence: 'ИНТ',
        wisdom: 'МДР',
        charisma: 'ХАР'
    };
    
    statsList.forEach(sName => {
        const score = char.getAbilityScore(sName);
        const mod = char.getAbilityModifier(sName);
        const formatMod = (v) => v >= 0 ? `+${v}` : v;
        
        const card = document.createElement('div');
        card.className = 'stat-wiz-summary-card';
        card.style.textAlign = 'center';
        card.style.padding = '8px';
        card.style.background = 'rgba(255,255,255,0.05)';
        card.style.borderRadius = '8px';
        card.style.border = '1px solid var(--border-color)';
        
        card.innerHTML = `
            <div style="font-size:10px; color:var(--text-muted); font-weight:700;">${statsAbbr[sName]}</div>
            <div style="font-size:20px; font-weight:800; color:var(--primary); margin:4px 0;">${formatMod(mod)}</div>
            <div style="font-size:12px; font-weight:600;">${score}</div>
        `;
        grid.appendChild(card);
    });
}

function renderProficienciesStep() {
    const savesGrid = document.getElementById('wiz-saves-grid');
    const skillsList = document.getElementById('wiz-skills-list');
    const toolsGrid = document.getElementById('wiz-tools-grid');
    
    const char = state.currentCharacter;
    
    savesGrid.innerHTML = '';
    ALL_SAVING_THROWS.forEach(save => {
        const label = document.createElement('label');
        label.style.display = 'flex';
        label.style.alignItems = 'center';
        label.style.gap = '6px';
        label.style.fontSize = '12px';
        
        const chk = document.createElement('input');
        chk.type = 'checkbox';
        chk.checked = char.savingThrows.includes(save);
        chk.onchange = () => {
            if (chk.checked) {
                if (!char.savingThrows.includes(save)) char.savingThrows.push(save);
            } else {
                char.savingThrows = char.savingThrows.filter(s => s !== save);
            }
        };
        
        label.appendChild(chk);
        label.appendChild(document.createTextNode(save));
        savesGrid.appendChild(label);
    });
    
    skillsList.innerHTML = '';
    ALL_SKILLS.forEach(skillName => {
        const row = document.createElement('div');
        row.style.display = 'flex';
        row.style.justifyContent = 'space-between';
        row.style.alignItems = 'center';
        row.style.padding = '6px 0';
        row.style.borderBottom = '1px solid rgba(255,255,255,0.05)';
        const currentProf = char.skills[skillName] || 'none';
        
        row.innerHTML = `
            <span style="font-size:12px;">${escapeHtml(skillName)}</span>
            <select class="wiz-skill-sel" style="padding:4px; font-size:11px; border-radius:4px; background:var(--bg-card); color:#fff; border:1px solid var(--border-color);">
                <option value="none" ${currentProf === 'none' ? 'selected' : ''}>Нет</option>
                <option value="proficient" ${currentProf === 'proficient' ? 'selected' : ''}>Владение [В]</option>
                <option value="expert" ${currentProf === 'expert' ? 'selected' : ''}>Экспертиза [Э]</option>
                <option value="half" ${currentProf === 'half' ? 'selected' : ''}>Полу-владение [П]</option>
            </select>
        `;
        
        row.querySelector('select').onchange = (e) => {
            char.skills[skillName] = e.target.value;
        };
        skillsList.appendChild(row);
    });
    
    toolsGrid.innerHTML = '';
    ALL_TOOLS.forEach(tool => {
        const label = document.createElement('label');
        label.style.display = 'flex';
        label.style.alignItems = 'center';
        label.style.gap = '6px';
        label.style.fontSize = '12px';
        
        const chk = document.createElement('input');
        chk.type = 'checkbox';
        chk.checked = char.tools.includes(tool);
        chk.onchange = () => {
            if (chk.checked) {
                if (!char.tools.includes(tool)) char.tools.push(tool);
            } else {
                char.tools = char.tools.filter(t => t !== tool);
            }
        };
        
        label.appendChild(chk);
        label.appendChild(document.createTextNode(tool));
        toolsGrid.appendChild(label);
    });
}

function renderFeaturesStep() {
    const char = state.currentCharacter;
    
    document.getElementById('wiz-personality').value = char.personalityTraits || '';
    document.getElementById('wiz-ideals').value = char.ideals || '';
    document.getElementById('wiz-bonds').value = char.bonds || '';
    document.getElementById('wiz-flaws').value = char.flaws || '';
    
    const list = document.getElementById('wiz-feats-list');
    list.innerHTML = '';
    
    char.customFeatures.forEach((feat, idx) => {
        const li = document.createElement('li');
        li.style.display = 'flex';
        li.style.justifyContent = 'space-between';
        li.style.alignItems = 'flex-start';
        li.style.padding = '8px';
        li.style.background = 'rgba(255,255,255,0.02)';
        li.style.border = '1px solid var(--border-color)';
        li.style.borderRadius = '6px';
        li.style.marginBottom = '6px';
        
        li.innerHTML = `
            <div style="flex:1;">
                <strong style="font-size:12px; color:var(--primary);">${escapeHtml(feat.name)}</strong>
                <p style="font-size:11px; margin: 4px 0 0 0; color:var(--text-muted);">${escapeHtml(feat.description)}</p>
            </div>
            <button type="button" class="btn btn-danger btn-sm wiz-del-feat" style="padding:4px 8px; margin-left:8px;">🗑️</button>
        `;
        
        li.querySelector('.wiz-del-feat').onclick = () => {
            char.customFeatures.splice(idx, 1);
            renderFeaturesStep();
        };
        list.appendChild(li);
    });
    
    document.getElementById('btn-wiz-add-feat').onclick = () => {
        const nameInput = document.getElementById('wiz-feat-name');
        const descInput = document.getElementById('wiz-feat-desc');
        const name = nameInput.value.trim();
        const desc = descInput.value.trim();
        
        if (!name) {
            showToast('Укажите название умения!', 'error');
            return;
        }
        
        char.customFeatures.push({ name, description: desc });
        nameInput.value = '';
        descInput.value = '';
        renderFeaturesStep();
    };
}

function renderEquipmentStep() {
    const char = state.currentCharacter;
    
    document.getElementById('wiz-coin-cp').value = char.coins.cp || 0;
    document.getElementById('wiz-coin-sp').value = char.coins.sp || 0;
    document.getElementById('wiz-coin-ep').value = char.coins.ep || 0;
    document.getElementById('wiz-coin-gp').value = char.coins.gp || 0;
    document.getElementById('wiz-coin-pp').value = char.coins.pp || 0;
    
    ['cp', 'sp', 'ep', 'gp', 'pp'].forEach(coin => {
        document.getElementById(`wiz-coin-${coin}`).onchange = (e) => {
            char.coins[coin] = parseInt(e.target.value) || 0;
        };
    });
    
    const presetsDiv = document.getElementById('wiz-eq-presets');
    presetsDiv.innerHTML = '';
    char.classes.forEach(c => {
        const classRule = DND_CLASSES[c.className];
        if (classRule && classRule.starting_equipment) {
            const block = document.createElement('div');
            block.style.marginBottom = '10px';
            block.innerHTML = `
                <strong style="font-size:12px; color:var(--text-muted);">${c.className}:</strong>
                <ul style="font-size:11px; padding-left:15px; margin: 4px 0 0 0;">
                    ${classRule.starting_equipment.map(eq => `<li>${escapeHtml(eq)}</li>`).join('')}
                </ul>
            `;
            presetsDiv.appendChild(block);
        }
    });
    
    const list = document.getElementById('wiz-items-list');
    list.innerHTML = '';
    
    char.equipment.forEach((item, idx) => {
        const li = document.createElement('li');
        li.style.display = 'flex';
        li.style.justifyContent = 'space-between';
        li.style.alignItems = 'center';
        li.style.padding = '6px 8px';
        li.style.background = 'rgba(255,255,255,0.02)';
        li.style.border = '1px solid var(--border-color)';
        li.style.borderRadius = '6px';
        li.style.marginBottom = '4px';
        
        const weightText = item.weight ? `, ${item.weight} ф.` : '';
        const qtyText = item.qty > 1 ? ` x${item.qty}` : '';
        
        li.innerHTML = `
            <span style="font-size:12px;">${escapeHtml(item.name)}${qtyText} (${item.type === 'weapon' ? 'Оружие' : item.type === 'armor' ? 'Доспех' : 'Прочее'}${weightText})</span>
            <button type="button" class="btn btn-danger btn-sm wiz-del-item" style="padding:2px 6px;">🗑️</button>
        `;
        
        li.querySelector('.wiz-del-item').onclick = () => {
            char.equipment.splice(idx, 1);
            renderEquipmentStep();
        };
        list.appendChild(li);
    });
    
    document.getElementById('btn-wiz-add-item').onclick = () => {
        const nameInput = document.getElementById('wiz-item-name');
        const weightInput = document.getElementById('wiz-item-weight');
        const qtyInput = document.getElementById('wiz-item-qty');
        const typeInput = document.getElementById('wiz-item-type');
        
        const name = nameInput.value.trim();
        const weight = parseFloat(weightInput.value) || 0;
        const qty = parseInt(qtyInput.value) || 1;
        const type = typeInput.value;
        
        if (!name) {
            showToast('Укажите название предмета!', 'error');
            return;
        }
        
        char.equipment.push({ name, weight, qty, type });
        nameInput.value = '';
        weightInput.value = '';
        qtyInput.value = '1';
        renderEquipmentStep();
    };
}

function renderSpellsStep() {
    const char = state.currentCharacter;
    const container = document.getElementById('spells-wizard-container');
    container.innerHTML = '';
    
    DND_SPELLS.forEach(spell => {
        const isSelected = char.spells.some(s => s.name === spell.name);
        const card = document.createElement('div');
        card.className = `spell-wiz-card ${isSelected ? 'selected' : ''}`;
        
        card.innerHTML = `
            <div class="spell-wiz-header">
                <span class="spell-wiz-name">${escapeHtml(spell.name)}</span>
                <span class="spell-wiz-level">${spell.level === 0 ? 'Заговор' : `${spell.level} Ур.`}</span>
            </div>
            <p class="spell-wiz-desc">${escapeHtml(spell.description)}</p>
        `;

        card.onclick = () => {
            card.classList.toggle('selected');
            const idx = char.spells.findIndex(s => s.name === spell.name);
            if (card.classList.contains('selected')) {
                if (idx === -1) {
                    char.spells.push({ name: spell.name, level: spell.level, prepared: true });
                }
            } else {
                if (idx > -1) {
                    char.spells.splice(idx, 1);
                }
            }
        };
        container.appendChild(card);
    });
    
    const customList = document.getElementById('wiz-spells-list');
    customList.innerHTML = '';
    
    const customSpellsOnly = char.customSpells || [];
    customSpellsOnly.forEach((spell, idx) => {
        const li = document.createElement('li');
        li.style.display = 'flex';
        li.style.justifyContent = 'space-between';
        li.style.alignItems = 'flex-start';
        li.style.padding = '8px';
        li.style.background = 'rgba(255,255,255,0.02)';
        li.style.border = '1px solid var(--border-color)';
        li.style.borderRadius = '6px';
        li.style.marginBottom = '6px';
        
        li.innerHTML = `
            <div style="flex:1;">
                <strong style="font-size:12px; color:var(--primary);">${escapeHtml(spell.name)}</strong>
                <span style="font-size:10px; color:var(--text-muted); margin-left:6px;">(${spell.level === 0 ? 'Заговор' : `${spell.level} Ур.`})</span>
                <p style="font-size:11px; margin: 4px 0 0 0; color:var(--text-muted);">${escapeHtml(spell.description)}</p>
            </div>
            <button type="button" class="btn btn-danger btn-sm wiz-del-spell" style="padding:4px 8px; margin-left:8px;">🗑️</button>
        `;
        
        li.querySelector('.wiz-del-spell').onclick = () => {
            char.customSpells.splice(idx, 1);
            renderSpellsStep();
        };
        customList.appendChild(li);
    });
    
    document.getElementById('btn-wiz-add-spell').onclick = () => {
        const nameInput = document.getElementById('wiz-spell-name');
        const lvlSelect = document.getElementById('wiz-spell-lvl');
        const schoolInput = document.getElementById('wiz-spell-school');
        const timeInput = document.getElementById('wiz-spell-time');
        const rangeInput = document.getElementById('wiz-spell-range');
        const descInput = document.getElementById('wiz-spell-desc');
        
        const name = nameInput.value.trim();
        const level = parseInt(lvlSelect.value) || 0;
        const school = schoolInput.value.trim();
        const time = timeInput.value.trim();
        const range = rangeInput.value.trim();
        const description = descInput.value.trim();
        
        if (!name) {
            showToast('Укажите название заклинания!', 'error');
            return;
        }
        
        if (!char.customSpells) char.customSpells = [];
        char.customSpells.push({ name, level, school, time, range, description });
        char.spells.push({ name, level, prepared: true, isCustom: true });
        
        nameInput.value = '';
        schoolInput.value = '';
        timeInput.value = '';
        rangeInput.value = '';
        descInput.value = '';
        renderSpellsStep();
    };
}

// Bind wizard Next / Prev button event listeners
document.getElementById('btn-wizard-next').onclick = () => {
    if (state.wizardStep === 1) {
        const name = document.getElementById('wiz-name').value.trim();
        if (!name) {
            showToast('Укажите имя персонажа!', 'error');
            return;
        }
    }
    saveWizardStepData();
    state.wizardStep = Math.min(9, state.wizardStep + 1);
    initWizardStep();
};

document.getElementById('btn-wizard-prev').onclick = () => {
    saveWizardStepData();
    state.wizardStep = Math.max(1, state.wizardStep - 1);
    initWizardStep();
};

// Finish Wizard -> Save Character to DB
document.getElementById('btn-wizard-finish').onclick = async () => {
    const char = state.currentCharacter;
    saveWizardStepData();
    try {
        const serialized = char.toDbFormat();
        serialized.full_data = char;
        await apiCall('/api/characters', 'POST', serialized);
        showToast('Персонаж сохранен!');
        switchView('list');
        loadCharacters();
    } catch (err) {}
};

// Back out of wizard without saving
document.getElementById('btn-wizard-back').onclick = () => {
    if (confirm('Вы уверены, что хотите выйти? Несохраненные изменения будут потеряны.')) {
        switchView('list');
    }
};

// High-Fidelity D&D 2014 PDF Layout Generator
function generatePrintHtml() {
    const char = state.currentCharacter;
    if (!char) return;

    const printContainer = document.getElementById('print-sheet');
    if (!printContainer) return;

    const formatMod = (v) => v >= 0 ? `+${v}` : v;
    const classStr = char.classes.map(c => `${c.className} ${c.level}`).join(" / ");
    
    // Ability Modifiers
    const strScore = char.getAbilityScore("strength");
    const strMod = char.getAbilityModifier("strength");
    const dexScore = char.getAbilityScore("dexterity");
    const dexMod = char.getAbilityModifier("dexterity");
    const conScore = char.getAbilityScore("constitution");
    const conMod = char.getAbilityModifier("constitution");
    const intScore = char.getAbilityScore("intelligence");
    const intMod = char.getAbilityModifier("intelligence");
    const wisScore = char.getAbilityScore("wisdom");
    const wisMod = char.getAbilityModifier("wisdom");
    const chaScore = char.getAbilityScore("charisma");
    const chaMod = char.getAbilityModifier("charisma");

    const pb = char.proficiencyBonus;

    // Saving throws list
    const savesListHtml = ["Сила", "Ловкость", "Телосложение", "Интеллект", "Мудрость", "Харизма"].map(save => {
        const isProf = char.savingThrows.includes(save);
        const mod = char.getSaveModifier(save);
        return `
            <div class="print-row">
                <span class="print-chk ${isProf ? 'checked' : ''}"></span>
                <span class="print-val">${formatMod(mod)}</span>
                <span class="print-label">${save}</span>
            </div>
        `;
    }).join('');

    // Skills list
    const skillsListHtml = ALL_SKILLS.map(skill => {
        const level = char.skills[skill] || 'none';
        const mod = char.getSkillModifier(skill);
        const attr = ALL_SKILLS_META[skill].attr.substring(0, 3).toUpperCase();
        return `
            <div class="print-row">
                <span class="print-chk ${level === 'proficient' ? 'checked' : level === 'expert' ? 'expert' : level === 'half' ? 'half' : ''}"></span>
                <span class="print-val">${formatMod(mod)}</span>
                <span class="print-label">${skill} <small>(${attr})</small></span>
            </div>
        `;
    }).join('');

    // Senses
    const passivePerception = 10 + char.getSkillModifier("Внимательность");
    
    // Weapons and attacks list
    let attacksHtml = '';
    const weapons = char.equipment.filter(i => i.type === 'weapon');
    weapons.forEach(w => {
        let attr = "strength";
        if (w.description && (w.description.includes("фехтовальное") || w.description.includes("дистанция"))) {
            const dex = char.getAbilityModifier("dexterity");
            const str = char.getAbilityModifier("strength");
            if (dex > str || w.description.includes("дистанция")) {
                attr = "dexterity";
            }
        }
        const attBonus = char.getAbilityModifier(attr) + char.proficiencyBonus;
        let dmg = "1d6";
        if (w.name.toLowerCase().includes("кинжал")) dmg = "1d4";
        else if (w.name.toLowerCase().includes("короткий меч")) dmg = "1d6";
        else if (w.name.toLowerCase().includes("длинный меч")) dmg = "1d8";
        else if (w.name.toLowerCase().includes("двуручный меч")) dmg = "2d6";
        else if (w.name.toLowerCase().includes("лук")) dmg = "1d6";
        else if (w.name.toLowerCase().includes("арбалет")) dmg = "1d8";
        
        attacksHtml += `
            <tr>
                <td><strong>${escapeHtml(w.name)}</strong></td>
                <td>+${attBonus}</td>
                <td>${dmg} + ${char.getAbilityModifier(attr)}</td>
            </tr>
        `;
    });
    if (char.customAttacks) {
        char.customAttacks.forEach(att => {
            attacksHtml += `
                <tr>
                    <td><strong>${escapeHtml(att.name)}</strong></td>
                    <td>+${att.attackBonus}</td>
                    <td>${escapeHtml(att.damageFormula)} ${escapeHtml(att.damageType || '')}</td>
                </tr>
            `;
        });
    }

    const equipmentHtml = char.equipment.map(item => {
        const qtyText = item.quantity > 1 ? ` x${item.quantity}` : '';
        return `<li>${escapeHtml(item.name)}${qtyText}</li>`;
    }).join('');

    const raceRule = DND_RACES[char.race];
    const customFeaturesHtml = char.customFeatures.map(feat => {
        return `
            <div style="margin-bottom:8px;">
                <strong>${escapeHtml(feat.name)}:</strong>
                <span style="font-size:8pt; color:#333;">${escapeHtml(feat.description)}</span>
            </div>
        `;
    }).join('');

    let page1Html = `
        <div class="print-page page-core">
            <div class="print-header">
                <div class="char-name-block">
                    <h1>${escapeHtml(char.name)}</h1>
                    <small>Имя персонажа</small>
                </div>
                <div class="char-meta-block">
                    <div class="meta-row">
                        <div><strong>${escapeHtml(classStr)}</strong><br><small>Класс и Уровень</small></div>
                        <div><strong>${escapeHtml(char.background || 'Custom')}</strong><br><small>Предыстория</small></div>
                        <div><strong>${escapeHtml(char.playerName || '—')}</strong><br><small>Имя игрока</small></div>
                    </div>
                    <div class="meta-row" style="margin-top:6px; border-top:1px solid #ccc; padding-top:4px;">
                        <div><strong>${escapeHtml(char.race)}</strong><br><small>Раса</small></div>
                        <div><strong>${escapeHtml(char.alignment)}</strong><br><small>Мировоззрение</small></div>
                        <div><strong>${char.xp}</strong><br><small>Опыт (XP)</small></div>
                    </div>
                </div>
            </div>

            <div class="print-columns">
                <div class="print-col col-left">
                    <div class="print-abilities">
                        <div class="ability-box">
                            <span class="abbr">СИЛ</span>
                            <span class="mod">${formatMod(strMod)}</span>
                            <span class="score">${strScore}</span>
                        </div>
                        <div class="ability-box">
                            <span class="abbr">ЛОВ</span>
                            <span class="mod">${formatMod(dexMod)}</span>
                            <span class="score">${dexScore}</span>
                        </div>
                        <div class="ability-box">
                            <span class="abbr">ТЕЛ</span>
                            <span class="mod">${formatMod(conMod)}</span>
                            <span class="score">${conScore}</span>
                        </div>
                        <div class="ability-box">
                            <span class="abbr">ИНТ</span>
                            <span class="mod">${formatMod(intMod)}</span>
                            <span class="score">${intScore}</span>
                        </div>
                        <div class="ability-box">
                            <span class="abbr">МДР</span>
                            <span class="mod">${formatMod(wisMod)}</span>
                            <span class="score">${wisScore}</span>
                        </div>
                        <div class="ability-box">
                            <span class="abbr">ХАР</span>
                            <span class="mod">${formatMod(chaMod)}</span>
                            <span class="score">${chaScore}</span>
                        </div>
                    </div>

                    <div class="print-box inspiration-box" style="margin-top:10px;">
                        <span class="insp-circle"></span>
                        <span style="font-weight:700; font-size:8pt; margin-left:6px;">Вдохновение</span>
                    </div>

                    <div class="print-box prof-bonus-box" style="margin-top:8px;">
                        <span class="prof-val">+${pb}</span>
                        <span style="font-weight:700; font-size:8pt; margin-left:8px;">Бонус мастерства</span>
                    </div>

                    <div class="print-box saves-box" style="margin-top:8px;">
                        <h3>Спасброски</h3>
                        ${savesListHtml}
                    </div>

                    <div class="print-box skills-box" style="margin-top:8px;">
                        <h3>Навыки</h3>
                        ${skillsListHtml}
                    </div>

                    <div class="print-box passive-perception-box" style="margin-top:8px;">
                        <span class="pass-val">${passivePerception}</span>
                        <span>Пассивная Внимательность (perception)</span>
                    </div>

                    <div class="print-box other-prof-box" style="margin-top:8px; flex:1;">
                        <h3>Прочие владения и языки</h3>
                        <p style="font-size:8pt; line-height:1.3; white-space:pre-wrap;"><strong>Языки:</strong> ${escapeHtml(char.languages || 'Общий')}\n\n<strong>Владения:</strong> ${escapeHtml(char.otherProficiencies || '—')}</p>
                    </div>
                </div>

                <div class="print-col col-middle">
                    <div class="combat-header-grid">
                        <div class="combat-stat-box">
                            <span class="val">${char.getArmorClass()}</span>
                            <span class="lbl">Класс Доспеха</span>
                        </div>
                        <div class="combat-stat-box">
                            <span class="val">${formatMod(char.getInitiativeModifier())}</span>
                            <span class="lbl">Инициатива</span>
                        </div>
                        <div class="combat-stat-box">
                            <span class="val">${char.customSpeed !== null ? char.customSpeed : (raceRule ? raceRule.speed : 30)} фт.</span>
                            <span class="lbl">Скорость</span>
                        </div>
                    </div>

                    <div class="print-box hp-box" style="margin-top:10px;">
                        <div class="hp-info-header">
                            <span>Макс. хиты: <strong>${char.hp.max}</strong></span>
                            ${char.hp.temp ? `<span>Врем. хиты: <strong>${char.hp.temp}</strong></span>` : ''}
                        </div>
                        <div class="hp-curr-box">
                            <span class="curr-val">${char.hp.current}</span>
                            <span class="lbl">Текущие хиты</span>
                        </div>
                    </div>

                    <div class="hd-death-saves-row" style="margin-top:8px; display:grid; grid-template-columns:1fr 1fr; gap:8px;">
                        <div class="print-box hd-box">
                            <h3>Кости здоровья</h3>
                            <div style="font-size:12pt; font-weight:700; text-align:center; padding:5px 0;">
                                ${Object.keys(char.getHitDiceMax()).map(die => `${char.getHitDiceMax()[die]}${die}`).join(', ') || '—'}
                            </div>
                        </div>
                        <div class="print-box death-saves-box">
                            <h3>Спасброски от смерти</h3>
                            <div style="font-size:7pt; display:flex; flex-direction:column; gap:4px; margin-top:2px;">
                                <div>Успехи: ${[1, 2, 3].map(i => `<span class="death-dot ${i <= (char.deathSaves?.successes || 0) ? 'filled' : ''}"></span>`).join('')}</div>
                                <div>Провалы: ${[1, 2, 3].map(i => `<span class="death-dot fail ${i <= (char.deathSaves?.failures || 0) ? 'filled' : ''}"></span>`).join('')}</div>
                            </div>
                        </div>
                    </div>

                    <div class="print-box attacks-box" style="margin-top:8px;">
                        <h3>Боевые атаки</h3>
                        <table class="print-attacks-table" style="width:100%; border-collapse:collapse; font-size:8pt;">
                            <thead>
                                <tr>
                                    <th style="text-align:left;">Название</th>
                                    <th>Бонус</th>
                                    <th>Урон / Тип</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${attacksHtml || '<tr><td colspan="3" style="text-align:center; color:#666;">Нет атак</td></tr>'}
                            </tbody>
                        </table>
                    </div>

                    <div class="print-box wallet-box" style="margin-top:8px;">
                        <h3>Кошелек</h3>
                        <div class="coins-print-row">
                            <div><strong>ММ:</strong> ${char.coins?.cp || 0}</div>
                            <div><strong>СМ:</strong> ${char.coins?.sp || 0}</div>
                            <div><strong>ЭМ:</strong> ${char.coins?.ep || 0}</div>
                            <div><strong>ЗМ:</strong> ${char.coins?.gp || 0}</div>
                            <div><strong>ПМ:</strong> ${char.coins?.pp || 0}</div>
                        </div>
                    </div>

                    <div class="print-box items-box" style="margin-top:8px; flex:1;">
                        <h3>Снаряжение</h3>
                        <ul class="print-items-list" style="padding-left:12px; margin:0; font-size:8pt; line-height:1.2;">
                            ${equipmentHtml || '<li>Нет снаряжения</li>'}
                        </ul>
                    </div>
                </div>

                <div class="print-col col-right">
                    <div class="print-box traits-box">
                        <h3>Черты характера</h3>
                        <p style="font-size:8pt; line-height:1.3; min-height:40px; margin:0; white-space:pre-wrap;">${escapeHtml(char.personalityTraits || '—')}</p>
                    </div>
                    <div class="print-box ideals-box" style="margin-top:8px;">
                        <h3>Идеалы</h3>
                        <p style="font-size:8pt; line-height:1.3; min-height:40px; margin:0; white-space:pre-wrap;">${escapeHtml(char.ideals || '—')}</p>
                    </div>
                    <div class="print-box bonds-box" style="margin-top:8px;">
                        <h3>Привязанности</h3>
                        <p style="font-size:8pt; line-height:1.3; min-height:40px; margin:0; white-space:pre-wrap;">${escapeHtml(char.bonds || '—')}</p>
                    </div>
                    <div class="print-box flaws-box" style="margin-top:8px;">
                        <h3>Слабости</h3>
                        <p style="font-size:8pt; line-height:1.3; min-height:40px; margin:0; white-space:pre-wrap;">${escapeHtml(char.flaws || '—')}</p>
                    </div>

                    <div class="print-box features-box" style="margin-top:8px; flex:1;">
                        <h3>Особенности и черты</h3>
                        <div class="print-features-body" style="font-size:8pt; line-height:1.3;">
                            ${customFeaturesHtml}
                            ${raceRule && raceRule.features ? raceRule.features.map(f => {
                                const parts = f.split(':');
                                return `<div style="margin-bottom:6px;"><strong>${escapeHtml(parts[0])}:</strong><span style="font-size:8pt; color:#333;">${escapeHtml(parts[1] || '')}</span></div>`;
                            }).join('') : ''}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;

    let page2Html = `
        <div class="print-page page-bio" style="page-break-before: always;">
            <div class="print-header">
                <div class="char-name-block">
                    <h1>${escapeHtml(char.name)}</h1>
                    <small>Биография героя</small>
                </div>
                <div class="appearance-bio-grid" style="display:grid; grid-template-columns:repeat(6, 1fr); gap:6px; font-size:7pt; align-items:center;">
                    <div><strong>Возраст:</strong><br>${escapeHtml(char.age || '—')}</div>
                    <div><strong>Рост:</strong><br>${escapeHtml(char.height || '—')}</div>
                    <div><strong>Вес:</strong><br>${escapeHtml(char.weight || '—')}</div>
                    <div><strong>Глаза:</strong><br>${escapeHtml(char.eyes || '—')}</div>
                    <div><strong>Кожа:</strong><br>${escapeHtml(char.skin || '—')}</div>
                    <div><strong>Волосы:</strong><br>${escapeHtml(char.hair || '—')}</div>
                </div>
            </div>

            <div style="display:grid; grid-template-columns: 2fr 1fr; gap:12px; margin-top:15px; flex:1;">
                <div style="display:flex; flex-direction:column; gap:10px;">
                    <div class="print-box" style="flex:1;">
                        <h3>Предыстория и история персонажа</h3>
                        <p style="font-size:9pt; line-height:1.4; white-space:pre-wrap; margin:0;">${escapeHtml(char.backstory || 'История героя пока не записана...')}</p>
                    </div>
                </div>
                <div style="display:flex; flex-direction:column; gap:10px;">
                    <div class="print-box" style="height:150px; display:flex; align-items:center; justify-content:center; text-align:center; border:2px dashed #999; overflow:hidden;">
                        ${char.portrait && char.portrait.length > 2 
                            ? `<img src="${escapeHtml(char.portrait)}" style="max-width:100%; max-height:100%; object-fit:contain;">`
                            : `<span style="font-size:36pt;">${char.portrait || '🧙‍♂️'}</span>`}
                    </div>
                    <div class="print-box" style="flex:1;">
                        <h3>Союзники и организации</h3>
                        <p style="font-size:8pt; line-height:1.3; white-space:pre-wrap; margin:0;">${escapeHtml(char.allies || '—')}</p>
                    </div>
                    <div class="print-box" style="height:100px;">
                        <h3>Сокровища</h3>
                        <p style="font-size:8pt; line-height:1.3; white-space:pre-wrap; margin:0;">${escapeHtml(char.treasure || '—')}</p>
                    </div>
                </div>
            </div>
        </div>
    `;

    let page3Html = '';
    const allPrintSpells = [];
    if (char.spells) {
        char.spells.forEach(s => allPrintSpells.push(s));
    }
    if (char.customSpells) {
        char.customSpells.forEach(cs => {
            allPrintSpells.push({
                name: cs.name,
                level: cs.level,
                prepared: cs.prepared !== undefined ? cs.prepared : true
            });
        });
    }
    const hasSpells = allPrintSpells.length > 0;
    
    if (hasSpells) {
        const spellStats = char.getSpellcastingStats();
        let spellAttackBonus = '';
        let spellSaveDC = '';
        let spellcastingClass = '';
        let spellcastingAbility = '';
        
        if (spellStats.length > 0) {
            spellAttackBonus = `+${spellStats[0].attackBonus}`;
            spellSaveDC = spellStats[0].saveDC;
            spellcastingClass = spellStats[0].className;
            spellcastingAbility = spellStats[0].ability;
        }

        const spellLevels = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9];
        let spellsGridHtml = '';
        
        spellLevels.forEach(lvl => {
            const lvlSpells = allPrintSpells.filter(s => s.level === lvl);
            if (lvlSpells.length === 0) return;

            let maxSlotsText = '';
            const maxSlotsData = char.getMaxSpellSlots();
            if (lvl > 0) {
                const max = maxSlotsData.slots[lvl] || 0;
                if (max > 0) {
                    maxSlotsText = ` (ячеек: ${max})`;
                }
            }

            spellsGridHtml += `
                <div class="print-box spell-level-box" style="break-inside:avoid; margin-bottom:8px;">
                    <h3 style="background:#eee; padding:3px 6px; margin:0 0 6px 0; font-size:9pt; font-weight:700;">
                        ${lvl === 0 ? 'Заговоры (Cantrips)' : `${lvl}-й Круг заклинаний${maxSlotsText}`}
                    </h3>
                    <div style="display:flex; flex-direction:column; gap:4px; padding:0 6px 6px 6px;">
                        ${lvlSpells.map(s => {
                            const customRule = char.customSpells && char.customSpells.find(cs => cs.name === s.name);
                            const rule = DND_SPELLS.find(ds => ds.name === s.name) || customRule || { school: "Магия", time: "1 действие", description: "" };
                            return `
                                <div style="font-size:8pt; border-bottom:1px solid #eee; padding-bottom:4px; margin-bottom:2px;">
                                    <div style="display:flex; justify-content:space-between; align-items:center;">
                                        <strong>${escapeHtml(s.name)}</strong>
                                        <span style="font-size:7pt; color:#666;">${escapeHtml(rule.school || '')} • ${escapeHtml(rule.time || '')}</span>
                                    </div>
                                    <p style="font-size:7pt; color:#444; margin: 2px 0 0 0; line-height:1.2;">${escapeHtml(rule.description || '')}</p>
                                </div>
                            `;
                        }).join('')}
                    </div>
                </div>
            `;
        });

        page3Html = `
            <div class="print-page page-spells" style="page-break-before: always;">
                <div class="print-header">
                    <div class="char-name-block">
                        <h1>${escapeHtml(char.name)}</h1>
                        <small>Книга заклинаний</small>
                    </div>
                    <div class="spell-casting-meta" style="display:grid; grid-template-columns: repeat(4, 1fr); gap:6px; font-size:7pt; text-align:center; align-items:center;">
                        <div><strong>Класс заклинателя:</strong><br>${escapeHtml(spellcastingClass || '—')}</div>
                        <div><strong>Характеристика:</strong><br>${escapeHtml(spellcastingAbility || '—')}</div>
                        <div><strong>Сл. Спасброска (DC):</strong><br>${spellSaveDC || '—'}</div>
                        <div><strong>Бонус атаки:</strong><br>${spellAttackBonus || '—'}</div>
                    </div>
                </div>
                
                <div class="print-spells-container" style="margin-top:15px; column-count: 2; column-gap: 15px;">
                    ${spellsGridHtml}
                </div>
            </div>
        `;
    }

    printContainer.innerHTML = page1Html + page2Html + page3Html;
}


// --- 2. INTERACTIVE CHARACTER SHEET DASHBOARD LOGIC ---
function openSheet(character) {
    state.currentCharacter = character;
    
    // Draw header UI
    const portraitHtml = character.portrait.length > 2 
        ? `<img src="${escapeHtml(character.portrait)}" class="sheet-portrait-image" alt="P">` 
        : character.portrait || "🧙‍♂️";
    document.getElementById('sheet-portrait-placeholder').innerHTML = portraitHtml;
    
    document.getElementById('sheet-char-name').textContent = character.name;
    
    const classesStr = character.classes.map(c => `${c.className} ${c.level}`).join(" / ");
    document.getElementById('sheet-char-meta').textContent = `${character.race} • ${classesStr} • Ур. ${character.totalLevel}`;
    
    // Player Name
    document.getElementById('sheet-char-player').textContent = character.playerName ? `Игрок: ${character.playerName}` : '';

    // Switch tabs to combat as default
    switchSheetTab('sheet-tab-combat');
    
    // Update contents
    updateDashboardCombatTab();
    updateDashboardStatsTab();
    updateDashboardInventoryTab();
    updateDashboardSpellsTab();
    updateDashboardFeaturesTab();
    updateDashboardNotesTab();
    
    // Notes
    document.getElementById('sheet-notes-area').value = character.notes;
    
    switchView('sheet');
}

// Dashboard Tabs Switcher
function switchSheetTab(tabId) {
    document.querySelectorAll('.sheet-tab-bar .tab-btn').forEach(btn => {
        btn.classList.remove('active');
        if (btn.dataset.tab === tabId) {
            btn.classList.add('active');
        }
    });
    
    document.querySelectorAll('#sheet-view .tab-panel').forEach(p => p.classList.remove('active'));
    document.getElementById(tabId).classList.add('active');
}

document.querySelectorAll('.sheet-tab-bar .tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        switchSheetTab(btn.dataset.tab);
    });
});

// Save notes button
document.getElementById('btn-save-notes').onclick = async () => {
    state.currentCharacter.notes = document.getElementById('sheet-notes-area').value;
    try {
        const serialized = state.currentCharacter.toDbFormat();
        serialized.full_data = state.currentCharacter;
        await apiCall('/api/characters', 'POST', serialized);
        showToast('Заметки успешно сохранены!');
    } catch (err) {}
};

// -- SHEET TAB 1: COMBAT & CORE --
function updateDashboardCombatTab() {
    const char = state.currentCharacter;
    
    // HP Fill
    const totalMax = char.hp.max;
    const currentHp = char.hp.current;
    document.getElementById('sheet-hp-fraction').textContent = `${currentHp} / ${totalMax} HP`;
    
    const percent = Math.min(100, Math.max(0, (currentHp / totalMax) * 100));
    const fill = document.getElementById('sheet-hp-fill');
    fill.style.width = `${percent}%`;
    
    // Color code health bar
    if (percent < 25) fill.style.background = '#ef4444';
    else if (percent < 50) fill.style.background = '#f59e0b';
    else fill.style.background = 'linear-gradient(90deg, #34d399 0%, #10b981 100%)';

    document.getElementById('temp-hp-input').value = char.hp.temp || 0;

    // AC, Speed, Initiative
    document.getElementById('sheet-ac-val').textContent = char.getArmorClass();
    
    const init = char.getInitiativeModifier();
    document.getElementById('sheet-init-val').textContent = init >= 0 ? `+${init}` : init;
    
    let speed = char.customSpeed;
    if (speed === null || speed === undefined || speed === "") {
        const raceRule = DND_RACES[char.race];
        speed = raceRule ? raceRule.speed : 30;
    }
    document.getElementById('sheet-speed-val').textContent = `${speed} фт`;

    // Hit dice counts
    const maxHd = char.getHitDiceMax();
    const hdStrings = [];
    Object.keys(maxHd).forEach(die => {
        const max = maxHd[die];
        const spent = char.hitDiceSpent[die] || 0;
        hdStrings.push(`${max - spent}${die}`);
    });
    document.getElementById('sheet-hd-val').textContent = hdStrings.join(', ') || 'Нет';

    // Interactive death saves bubbles
    const successes = char.deathSaves?.successes || 0;
    const failures = char.deathSaves?.failures || 0;
    
    const successBubbles = document.querySelectorAll('#death-success-bubbles .death-bubble');
    successBubbles.forEach((bubble, idx) => {
        if (idx < successes) {
            bubble.style.backgroundColor = '#10b981';
        } else {
            bubble.style.backgroundColor = 'transparent';
        }
        bubble.onclick = async (e) => {
            e.stopPropagation();
            if (char.deathSaves.successes === idx + 1) {
                char.deathSaves.successes = idx;
            } else {
                char.deathSaves.successes = idx + 1;
            }
            updateDashboardCombatTab();
            try {
                const serialized = char.toDbFormat();
                serialized.full_data = char;
                await apiCall('/api/characters', 'POST', serialized);
            } catch (err) {}
        };
    });

    const failBubbles = document.querySelectorAll('#death-fail-bubbles .death-bubble');
    failBubbles.forEach((bubble, idx) => {
        if (idx < failures) {
            bubble.style.backgroundColor = '#ef4444';
        } else {
            bubble.style.backgroundColor = 'transparent';
        }
        bubble.onclick = async (e) => {
            e.stopPropagation();
            if (char.deathSaves.failures === idx + 1) {
                char.deathSaves.failures = idx;
            } else {
                char.deathSaves.failures = idx + 1;
            }
            updateDashboardCombatTab();
            try {
                const serialized = char.toDbFormat();
                serialized.full_data = char;
                await apiCall('/api/characters', 'POST', serialized);
            } catch (err) {}
        };
    });

    // Attacks List serve (Weapons + Custom Attacks)
    const attacksList = document.getElementById('sheet-attacks-list');
    attacksList.innerHTML = '';
    
    // Find equipped weapons
    const weapons = char.equipment.filter(i => i.type === 'weapon');
    
    if (weapons.length === 0 && (!char.customAttacks || char.customAttacks.length === 0)) {
        attacksList.innerHTML = `<p class="input-helper">Нет доступного оружия или атак. Добавьте оружие во вкладке Инвентарь или создайте свою атаку ниже.</p>`;
    } else {
        // Render weapons
        weapons.forEach(w => {
            const row = document.createElement('div');
            row.className = 'weapon-attack-row';
            
            // basic attack modifier calculation: strength or finesse
            let attr = "strength";
            if (w.description && (w.description.includes("фехтовальное") || w.description.includes("дистанция"))) {
                // Finesse or Ranged uses Dexterity if Dexterity is higher or default
                const dex = char.getAbilityModifier("dexterity");
                const str = char.getAbilityModifier("strength");
                if (dex > str || w.description.includes("дистанция")) {
                    attr = "dexterity";
                }
            }
            const attBonus = char.getAbilityModifier(attr) + char.proficiencyBonus;

            row.innerHTML = `
                <div class="weapon-attack-info">
                    <h4>${escapeHtml(w.name)}</h4>
                    <p>Бонус: +${attBonus} • Свойства: ${escapeHtml(w.description || 'Обычное')}</p>
                </div>
                <button type="button" class="btn btn-primary btn-sm btn-roll-attack" data-name="${escapeHtml(w.name)}" data-bonus="${attBonus}">🎲 Атака</button>
            `;
            
            row.querySelector('.btn-roll-attack').onclick = async () => {
                const bonus = attBonus;
                const formula = `1d20+${bonus}`;
                try {
                    await apiCall('/api/roll', 'POST', {
                        name: char.name,
                        formula_name: `Атака: ${w.name}`,
                        formula_expr: formula
                    });
                    showToast(`Бросок атаки ${w.name} отправлен боту!`);
                    tg.close();
                } catch (err) {}
            };

            attacksList.appendChild(row);
        });

        // Render Custom Attacks
        if (char.customAttacks) {
            char.customAttacks.forEach((att, index) => {
                const row = document.createElement('div');
                row.className = 'weapon-attack-row custom-attack-row';
                
                const bonusStr = att.attackBonus >= 0 ? `+${att.attackBonus}` : att.attackBonus;
                
                row.innerHTML = `
                    <div class="weapon-attack-info">
                        <div style="display:flex; align-items:center; gap:8px;">
                            <h4>${escapeHtml(att.name)}</h4>
                            <span class="badge" style="font-size:9px; background:rgba(255,255,255,0.1); padding:2px 4px; border-radius:4px;">Своё</span>
                        </div>
                        <p>Бонус: ${bonusStr} • Урон: ${escapeHtml(att.damageFormula)} (${escapeHtml(att.damageType || 'физический')})</p>
                    </div>
                    <div style="display:flex; gap:4px; align-items:center;">
                        <button type="button" class="btn btn-primary btn-sm btn-roll-atk" title="Атака">🎲 Атака</button>
                        <button type="button" class="btn btn-secondary btn-sm btn-roll-dmg" title="Урон">💥 Урон</button>
                        <button type="button" class="btn btn-danger btn-sm btn-delete-atk edit-only" style="padding: 4px 6px;">🗑️</button>
                    </div>
                `;
                
                // Roll Attack
                row.querySelector('.btn-roll-atk').onclick = async () => {
                    const formula = `1d20+${att.attackBonus}`;
                    try {
                        await apiCall('/api/roll', 'POST', {
                            name: char.name,
                            formula_name: `Атака: ${att.name}`,
                            formula_expr: formula
                        });
                        showToast(`Бросок атаки ${att.name} отправлен боту!`);
                        tg.close();
                    } catch (err) {}
                };
                
                // Roll Damage
                row.querySelector('.btn-roll-dmg').onclick = async () => {
                    try {
                        await apiCall('/api/roll', 'POST', {
                            name: char.name,
                            formula_name: `Урон: ${att.name}`,
                            formula_expr: att.damageFormula
                        });
                        showToast(`Бросок урона ${att.name} отправлен боту!`);
                        tg.close();
                    } catch (err) {}
                };
                
                // Delete
                row.querySelector('.btn-delete-atk').onclick = async () => {
                    if (confirm(`Удалить атаку "${att.name}"?`)) {
                        char.customAttacks.splice(index, 1);
                        updateDashboardCombatTab();
                        try {
                            const serialized = char.toDbFormat();
                            serialized.full_data = char;
                            await apiCall('/api/characters', 'POST', serialized);
                        } catch (err) {}
                    }
                };
                
                attacksList.appendChild(row);
            });
        }
    }

    // Conditions grid
    const condContainer = document.getElementById('sheet-conditions-grid');
    condContainer.innerHTML = '';
    
    const all5eConditions = ["Ослеплен", "Очарован", "Глух", "Испуган", "Схвачен", "Недееспособен", "Невидимый", "Парализован", "Окаменел", "Отравлен", "Сбит с ног", "Опутан", "Бессознания"];
    all5eConditions.forEach(cond => {
        const isChecked = char.conditions.includes(cond);
        const label = document.createElement('div');
        label.className = `check-label ${isChecked ? 'checked' : ''}`;
        label.innerHTML = `
            <div class="check-box">${isChecked ? '✓' : ''}</div>
            <span>${cond}</span>
        `;
        
        label.onclick = async () => {
            const idx = char.conditions.indexOf(cond);
            if (idx > -1) {
                char.conditions.splice(idx, 1);
            } else {
                char.conditions.push(cond);
            }
            updateDashboardCombatTab();
            // Sync to db quietly
            try {
                const serialized = char.toDbFormat();
                serialized.full_data = char;
                await apiCall('/api/characters', 'POST', serialized);
            } catch (err) {}
        };
        condContainer.appendChild(label);
    });
}

// Apply damage/heal events
document.getElementById('btn-apply-damage').onclick = async () => {
    const amt = parseInt(document.getElementById('hp-change-amount').value) || 0;
    if (amt <= 0) return;
    
    state.currentCharacter.applyDamage(amt);
    document.getElementById('hp-change-amount').value = '';
    updateDashboardCombatTab();
    
    // Save to db
    try {
        const serialized = state.currentCharacter.toDbFormat();
        serialized.full_data = state.currentCharacter;
        await apiCall('/api/characters', 'POST', serialized);
    } catch (err) {}
};

document.getElementById('btn-apply-heal').onclick = async () => {
    const amt = parseInt(document.getElementById('hp-change-amount').value) || 0;
    if (amt <= 0) return;

    state.currentCharacter.applyHealing(amt);
    document.getElementById('hp-change-amount').value = '';
    updateDashboardCombatTab();

    // Save to db
    try {
        const serialized = state.currentCharacter.toDbFormat();
        serialized.full_data = state.currentCharacter;
        await apiCall('/api/characters', 'POST', serialized);
    } catch (err) {}
};

document.getElementById('temp-hp-input').onchange = async (e) => {
    const val = parseInt(e.target.value) || 0;
    state.currentCharacter.hp.temp = val;
    // Save to db
    try {
        const serialized = state.currentCharacter.toDbFormat();
        serialized.full_data = state.currentCharacter;
        await apiCall('/api/characters', 'POST', serialized);
    } catch (err) {}
};

// Resting events
document.getElementById('btn-short-rest').onclick = async () => {
    if (confirm('Провести короткий отдых? Это восстановит ячейки Договора Колдуна и особые умения.')) {
        state.currentCharacter.shortRest();
        updateDashboardCombatTab();
        updateDashboardSpellsTab();
        updateDashboardFeaturesTab();
        
        try {
            const serialized = state.currentCharacter.toDbFormat();
            serialized.full_data = state.currentCharacter;
            await apiCall('/api/characters', 'POST', serialized);
            showToast('Короткий отдых завершен!');
        } catch (e) {}
    }
};

document.getElementById('btn-long-rest').onclick = async () => {
    if (confirm('Провести длинный отдых? Это полностью восстановит хиты, ячейки магии и сбросит траты умений.')) {
        state.currentCharacter.longRest();
        updateDashboardCombatTab();
        updateDashboardSpellsTab();
        updateDashboardFeaturesTab();

        try {
            const serialized = state.currentCharacter.toDbFormat();
            serialized.full_data = state.currentCharacter;
            await apiCall('/api/characters', 'POST', serialized);
            showToast('Длинный отдых завершен! Все показатели восстановлены.');
        } catch (e) {}
    }
};

// Roll Initiative clickable box
document.getElementById('btn-roll-initiative').onclick = async () => {
    const init = state.currentCharacter.getInitiativeModifier();
    const formula = `1d20+${init}`;
    try {
        await apiCall('/api/roll', 'POST', {
            name: state.currentCharacter.name,
            formula_name: 'Инициатива',
            formula_expr: formula
        });
        showToast('Бросок инициативы отправлен боту!');
        tg.close();
    } catch (err) {}
};

// -- SHEET TAB 2: ABILITIES & SKILLS --
function updateDashboardStatsTab() {
    const char = state.currentCharacter;
    
    // Ability cards grid
    const abGrid = document.getElementById('sheet-abilities-grid');
    abGrid.innerHTML = '';
    
    const formatMod = (v) => v >= 0 ? `+${v}` : v;
    
    const abilities = [
        { en: 'strength', ru: 'СИЛ', label: 'Сила' },
        { en: 'dexterity', ru: 'ЛОВ', label: 'Ловкость' },
        { en: 'constitution', ru: 'ТЕЛ', label: 'Телосложение' },
        { en: 'intelligence', ru: 'ИНТ', label: 'Интеллект' },
        { en: 'wisdom', ru: 'МДР', label: 'Мудрость' },
        { en: 'charisma', ru: 'ХАР', label: 'Харизма' }
    ];

    abilities.forEach(a => {
        const score = char.getAbilityScore(a.en);
        const mod = char.getAbilityModifier(a.en);
        
        const card = document.createElement('div');
        card.className = 'sheet-stat-card';
        card.innerHTML = `
            <span class="sheet-stat-name">${a.ru}</span>
            <span class="sheet-stat-mod">${formatMod(mod)}</span>
            <span class="sheet-stat-score">${score}</span>
            <span class="sheet-stat-roll-badge">🎲</span>
        `;
        
        // Ability check roll on click
        card.onclick = async () => {
            const formula = `1d20+${mod}`;
            try {
                await apiCall('/api/roll', 'POST', {
                    name: char.name,
                    formula_name: `Проверка: ${a.label}`,
                    formula_expr: formula
                });
                showToast(`Проверка ${a.label} отправлена боту!`);
                tg.close();
            } catch (err) {}
        };

        abGrid.appendChild(card);
    });

    // Saves list
    const savesList = document.getElementById('sheet-saves-list');
    savesList.innerHTML = '';
    
    const savesRu = ["Сила", "Ловкость", "Телосложение", "Интеллект", "Мудрость", "Харизма"];
    savesRu.forEach(save => {
        const isProf = char.savingThrows.includes(save);
        const mod = char.getSaveModifier(save);
        
        const row = document.createElement('div');
        row.className = 'saves-sheet-row';
        row.innerHTML = `
            <div class="row-left">
                <div class="prof-indicator ${isProf ? 'proficient' : ''}"></div>
                <span class="row-name">Спасбросок: ${save}</span>
            </div>
            <span class="row-mod">${formatMod(mod)} 🎲</span>
        `;

        row.onclick = async () => {
            const formula = `1d20+${mod}`;
            try {
                await apiCall('/api/roll', 'POST', {
                    name: char.name,
                    formula_name: `Спасбросок: ${save}`,
                    formula_expr: formula
                });
                showToast(`Спасбросок ${save} отправлен боту!`);
                tg.close();
            } catch (err) {}
        };

        savesList.appendChild(row);
    });

    // Skills list
    const skillsList = document.getElementById('sheet-skills-list');
    skillsList.innerHTML = '';
    
    ALL_SKILLS.forEach(skill => {
        const level = char.skills[skill] || 'none';
        const mod = char.getSkillModifier(skill);
        const attr = ALL_SKILLS_META[skill].attr;
        
        const minVal = char.minRolls ? (char.minRolls[skill] || 0) : 0;
        const minBadge = minVal > 0 ? ` <span class="skill-min-badge" style="font-size:10px; opacity:0.85; color: #ffbc00; background: rgba(255, 188, 0, 0.15); padding: 1px 4px; border-radius: 4px; margin-left: 4px;">🎲≥${minVal}</span>` : '';
        
        const row = document.createElement('div');
        row.className = 'skills-sheet-row';
        row.innerHTML = `
            <div class="row-left">
                <div class="prof-indicator ${level !== 'none' ? level : ''}"></div>
                <span class="row-name">${skill}${minBadge} <small class="row-attr">${attr.substring(0,3).toUpperCase()}</small></span>
            </div>
            <span class="row-mod">${formatMod(mod)} 🎲</span>
        `;

        row.onclick = async () => {
            const formula = `1d20+${mod}`;
            try {
                await apiCall('/api/roll', 'POST', {
                    name: char.name,
                    formula_name: `Проверка навыка: ${skill}`,
                    formula_expr: formula
                });
                showToast(`Проверка навыка ${skill} отправлена боту!`);
                tg.close();
            } catch (err) {}
        };

        skillsList.appendChild(row);
    });

    // Tools list
    const toolsList = document.getElementById('sheet-tools-list');
    toolsList.innerHTML = '';
    if (char.tools.length === 0) {
        toolsList.innerHTML = `<p class="input-helper">Нет владений инструментами.</p>`;
    } else {
        char.tools.forEach(t => {
            const row = document.createElement('div');
            row.className = 'tools-sheet-row';
            row.innerHTML = `
                <div class="row-left">
                    <div class="prof-indicator proficient"></div>
                    <span class="row-name">${t}</span>
                </div>
            `;
            toolsList.appendChild(row);
        });
    }

    // Passive Senses
    document.getElementById('sheet-passive-perception').textContent = char.getPassivePerception();
    document.getElementById('sheet-passive-insight').textContent = char.getPassiveInsight();
    document.getElementById('sheet-passive-investigation').textContent = char.getPassiveInvestigation();

    // Languages and Other Proficiencies
    document.getElementById('sheet-languages-val').textContent = char.languages || '—';
    document.getElementById('sheet-other-proficiencies-val').textContent = char.otherProficiencies || '—';
}

// -- SHEET TAB 3: INVENTORY --
function updateDashboardInventoryTab() {
    const char = state.currentCharacter;
    
    const currentWeight = char.getTotalWeight();
    const maxCapacity = char.getCarryingCapacity();
    
    document.getElementById('sheet-weight-fraction').textContent = `${currentWeight.toFixed(1)} / ${maxCapacity.toFixed(1)} фт.`;
    
    const pct = Math.min(100, (currentWeight / maxCapacity) * 100);
    const fill = document.getElementById('sheet-weight-fill');
    fill.style.width = `${pct}%`;
    if (pct > 90) fill.style.background = 'var(--danger)';
    else if (pct > 75) fill.style.background = 'var(--warning)';
    else fill.style.background = 'var(--primary)';

    const list = document.getElementById('sheet-items-list');
    list.innerHTML = '';

    if (char.equipment.length === 0) {
        list.innerHTML = `<p class="input-helper" style="padding:15px; text-align:center;">Рюкзак пуст</p>`;
        return;
    }

    char.equipment.forEach((item, idx) => {
        const row = document.createElement('div');
        row.className = 'item-row-data';
        
        const isEquippable = ['weapon', 'armor', 'shield'].includes(item.type);
        const equipCheckbox = isEquippable 
            ? `<input type="checkbox" class="item-equip-chk" ${item.equipped ? 'checked' : ''} data-idx="${idx}">` 
            : `—`;

        row.innerHTML = `
            <div style="text-align:center;">${equipCheckbox}</div>
            <div style="font-weight:600;">${escapeHtml(item.name)}</div>
            <div>${item.weight || 0} ф.</div>
            <div><input type="number" class="item-qty-input" value="${item.quantity || 1}" min="1" data-idx="${idx}"></div>
            <div style="text-align:center;"><button class="btn-item-del" data-idx="${idx}">🗑️</button></div>
        `;

        // Listeners for equip/quantity/delete
        if (isEquippable) {
            row.querySelector('.item-equip-chk').onchange = async (e) => {
                char.equipment[idx].equipped = e.target.checked;
                updateDashboardCombatTab(); // recalculate AC/damage
                updateDashboardInventoryTab();
                await syncCharacterData();
            };
        }

        row.querySelector('.item-qty-input').onchange = async (e) => {
            char.equipment[idx].quantity = Math.max(1, parseInt(e.target.value) || 1);
            updateDashboardInventoryTab();
            await syncCharacterData();
        };

        row.querySelector('.btn-item-del').onclick = async () => {
            char.equipment.splice(idx, 1);
            updateDashboardCombatTab();
            updateDashboardInventoryTab();
            await syncCharacterData();
        };

        list.appendChild(row);
    });

    // Display coin counts in view-only mode
    document.getElementById('sheet-coin-cp').textContent = char.coins?.cp || 0;
    document.getElementById('sheet-coin-sp').textContent = char.coins?.sp || 0;
    document.getElementById('sheet-coin-ep').textContent = char.coins?.ep || 0;
    document.getElementById('sheet-coin-gp').textContent = char.coins?.gp || 0;
    document.getElementById('sheet-coin-pp').textContent = char.coins?.pp || 0;
}

// Add custom item on sheet
document.getElementById('btn-sheet-add-item').onclick = async () => {
    const input = document.getElementById('sheet-add-item-name');
    const name = input.value.trim();
    if (!name) return;

    state.currentCharacter.equipment.push({
        id: 'item_' + Math.random().toString(36).substring(2, 9),
        name,
        type: 'other',
        weight: 1.0,
        quantity: 1,
        equipped: false,
        description: ""
    });

    input.value = '';
    updateDashboardInventoryTab();
    await syncCharacterData();
};

async function syncCharacterData() {
    try {
        const serialized = state.currentCharacter.toDbFormat();
        serialized.full_data = state.currentCharacter;
        await apiCall('/api/characters', 'POST', serialized);
    } catch (e) {}
}

// -- SHEET TAB 4: SPELLS --
function updateDashboardSpellsTab() {
    const char = state.currentCharacter;
    
    // Spell meta
    const metaContainer = document.getElementById('sheet-spells-meta');
    metaContainer.innerHTML = '';
    
    const spellStats = char.getSpellcastingStats();
    if (spellStats.length === 0) {
        metaContainer.innerHTML = `<div><h5>Нет заклинательной способности</h5></div>`;
    } else {
        spellStats.forEach(s => {
            metaContainer.innerHTML += `
                <div>
                    <h5>+${s.attackBonus}</h5>
                    <small>Атака магии (${s.className})</small>
                </div>
                <div>
                    <h5>Спас DC ${s.saveDC}</h5>
                    <small>Сл. Спасброска (${s.ability})</small>
                </div>
            `;
        });
    }

    // Spell slots spent tracker
    const slotsContainer = document.getElementById('sheet-spell-slots-tracker');
    slotsContainer.innerHTML = '';
    
    const maxSlotsData = char.getMaxSpellSlots();
    
    if (Object.keys(maxSlotsData.slots).length === 0 && !maxSlotsData.pactMagic) {
        slotsContainer.innerHTML = `<p class="input-helper">Вам не доступны ячейки заклинаний на текущих уровнях.</p>`;
    } else {
        // Standard slots
        Object.keys(maxSlotsData.slots).forEach(lvl => {
            const max = maxSlotsData.slots[lvl];
            const spent = char.spellSlotsSpent[lvl] || 0;
            
            const row = document.createElement('div');
            row.className = 'spell-slots-row';
            
            let bubblesHtml = '';
            for (let i = 0; i < max; i++) {
                const isSpent = (i < spent);
                bubblesHtml += `<span class="slot-bubble ${isSpent ? '' : 'filled'}" data-level="${lvl}" data-idx="${i}"></span>`;
            }

            row.innerHTML = `
                <span class="spell-level-label">${lvl}-й круг (${max} яч.)</span>
                <div class="slots-bubbles">${bubblesHtml}</div>
            `;
            
            // click to spend/recover
            row.querySelectorAll('.slot-bubble').forEach(b => {
                b.onclick = async () => {
                    const l = b.dataset.level;
                    let currentSpent = char.spellSlotsSpent[l] || 0;
                    if (b.classList.contains('filled')) {
                        // spend slot
                        char.spellSlotsSpent[l] = Math.min(max, currentSpent + 1);
                    } else {
                        // restore slot
                        char.spellSlotsSpent[l] = Math.max(0, currentSpent - 1);
                    }
                    updateDashboardSpellsTab();
                    await syncCharacterData();
                };
            });

            slotsContainer.appendChild(row);
        });

        // Pact magic slots (Warlock)
        if (maxSlotsData.pactMagic) {
            const pact = maxSlotsData.pactMagic;
            const row = document.createElement('div');
            row.className = 'spell-slots-row';
            
            let bubblesHtml = '';
            for (let i = 0; i < pact.slots; i++) {
                const isSpent = (i < pact.spent);
                bubblesHtml += `<span class="slot-bubble Pact ${isSpent ? '' : 'filled'}" data-idx="${i}"></span>`;
            }

            row.innerHTML = `
                <span class="spell-level-label">Договор (${pact.level} круг)</span>
                <div class="slots-bubbles">${bubblesHtml}</div>
            `;
            
            row.querySelectorAll('.slot-bubble').forEach(b => {
                b.onclick = async () => {
                    let spent = char.spellSlotsSpent["pact"] || 0;
                    if (b.classList.contains('filled')) {
                        char.spellSlotsSpent["pact"] = Math.min(pact.slots, spent + 1);
                    } else {
                        char.spellSlotsSpent["pact"] = Math.max(0, spent - 1);
                    }
                    updateDashboardSpellsTab();
                    await syncCharacterData();
                };
            });
            slotsContainer.appendChild(row);
        }
    }

    // Spellbook List
    const spellbookList = document.getElementById('sheet-spellbook-list');
    spellbookList.innerHTML = '';
    
    const allSpells = [];
    char.spells.forEach((s, idx) => {
        const dndMatch = DND_SPELLS.find(ds => ds.name === s.name);
        allSpells.push({
            name: s.name,
            level: s.level,
            prepared: s.prepared,
            school: dndMatch ? dndMatch.school : "Магия",
            time: dndMatch ? dndMatch.time : "1 действие",
            range: dndMatch ? dndMatch.range : "—",
            description: dndMatch ? dndMatch.description : "",
            isCustom: false,
            originalIndex: idx
        });
    });

    if (char.customSpells) {
        char.customSpells.forEach((cs, idx) => {
            allSpells.push({
                name: cs.name,
                level: cs.level,
                prepared: cs.prepared !== undefined ? cs.prepared : true,
                school: cs.school || "Магия",
                time: cs.time || "1 действие",
                range: cs.range || "—",
                description: cs.description || "",
                isCustom: true,
                originalIndex: idx
            });
        });
    }

    if (allSpells.length === 0) {
        spellbookList.innerHTML = `<p class="input-helper">Книга заклинаний пуста.</p>`;
        return;
    }

    // Group spells by level
    const spellLevels = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9];
    spellLevels.forEach(lvl => {
        const lvlSpells = allSpells.filter(s => s.level === lvl);
        if (lvlSpells.length === 0) return;

        const heading = document.createElement('h4');
        heading.textContent = lvl === 0 ? 'Заговоры' : `${lvl}-й Круг`;
        spellbookList.appendChild(heading);

        lvlSpells.forEach(spell => {
            const row = document.createElement('div');
            row.className = 'spell-row-card';
            
            const badgeHtml = spell.isCustom 
                ? `<span class="badge" style="font-size:9px; background:rgba(255,255,255,0.1); padding:2px 4px; border-radius:4px; margin-left:6px;">Своё</span>` 
                : '';
                
            row.innerHTML = `
                <div class="spell-row-left">
                    <div class="spell-prep-dot ${spell.prepared ? 'prepared' : ''}" title="Подготовлено"></div>
                    <div class="spell-info-body">
                        <div style="display:flex; align-items:center;">
                            <h5>${escapeHtml(spell.name)}</h5>
                            ${badgeHtml}
                        </div>
                        <p>${escapeHtml(spell.school)} • ${escapeHtml(spell.time)} • ${escapeHtml(spell.range)}</p>
                    </div>
                </div>
                <div style="display:flex; gap:4px; align-items:center;">
                    <button type="button" class="btn btn-secondary btn-sm roll-spell-btn" title="Колдовать">🎲</button>
                    ${spell.isCustom ? `<button type="button" class="btn btn-danger btn-sm btn-delete-custom-spell edit-only" style="padding: 4px 6px;">🗑️</button>` : ''}
                </div>
            `;

            // Prep toggle
            row.querySelector('.spell-prep-dot').onclick = async () => {
                if (spell.isCustom) {
                    char.customSpells[spell.originalIndex].prepared = !char.customSpells[spell.originalIndex].prepared;
                } else {
                    char.spells[spell.originalIndex].prepared = !char.spells[spell.originalIndex].prepared;
                }
                updateDashboardSpellsTab();
                await syncCharacterData();
            };

            // Cast Spell roll
            row.querySelector('.roll-spell-btn').onclick = async () => {
                try {
                    await apiCall('/api/roll', 'POST', {
                        name: char.name,
                        formula_name: `Заклинание: ${spell.name}`,
                        formula_expr: "1d20"
                    });
                    showToast(`Заклинание ${spell.name} наложено и отправлено в чат!`);
                    tg.close();
                } catch (e) {}
            };

            // Delete custom spell
            if (spell.isCustom) {
                row.querySelector('.btn-delete-custom-spell').onclick = async () => {
                    if (confirm(`Удалить заклинание "${spell.name}"?`)) {
                        char.customSpells.splice(spell.originalIndex, 1);
                        updateDashboardSpellsTab();
                        await syncCharacterData();
                    }
                };
            }

            spellbookList.appendChild(row);
        });
    });
}

// -- SHEET TAB 6: NOTES & APPEARANCE --
function updateDashboardNotesTab() {
    const char = state.currentCharacter;
    if (!char) return;
    
    document.getElementById('sheet-age-val').textContent = char.age || '—';
    document.getElementById('sheet-height-val').textContent = char.height || '—';
    document.getElementById('sheet-weight-val').textContent = char.weight || '—';
    document.getElementById('sheet-eyes-val').textContent = char.eyes || '—';
    document.getElementById('sheet-skin-val').textContent = char.skin || '—';
    document.getElementById('sheet-hair-val').textContent = char.hair || '—';
    document.getElementById('sheet-backstory-val').textContent = char.backstory || '—';
}

// -- SHEET TAB 5: FEATURES & TRAITS --
function updateDashboardFeaturesTab() {
    const char = state.currentCharacter;
    
    // Class resources (Rage, Ki tracker)
    const resBox = document.getElementById('sheet-class-resources');
    resBox.innerHTML = '';

    // Check if Barbarian
    const barb = char.classes.find(c => c.className === 'Barbarian');
    if (barb) {
        let rageMax = 2;
        if (barb.level >= 17) rageMax = 6;
        else if (barb.level >= 12) rageMax = 5;
        else if (barb.level >= 9) rageMax = 4;
        else if (barb.level >= 3) rageMax = 3;
        
        const spent = char.resources["rage_spent"] || 0;
        
        renderResourceBubbleBox(resBox, "Ярость (Rage)", rageMax, spent, "rage_spent", "short");
    }

    // Monk Ki
    const monk = char.classes.find(c => c.className === 'Monk');
    if (monk && monk.level >= 2) {
        const kiMax = monk.level;
        const spent = char.resources["ki_spent"] || 0;
        renderResourceBubbleBox(resBox, "Очки Ки (Ki)", kiMax, spent, "ki_spent", "short");
    }

    // Bardic Inspiration
    const bard = char.classes.find(c => c.className === 'Bard');
    if (bard) {
        const chaMod = char.getAbilityModifier("charisma");
        const max = Math.max(1, chaMod);
        const spent = char.resources["bard_spent"] || 0;
        renderResourceBubbleBox(resBox, "Вдохновение барда", max, spent, "bard_spent", "long");
    }

    // Racial features list
    const racialList = document.getElementById('sheet-racial-features');
    racialList.innerHTML = '';
    const raceRule = DND_RACES[char.race];
    
    if (raceRule && raceRule.features) {
        raceRule.features.forEach(feat => {
            const parts = feat.split(':');
            const title = parts[0] || 'Черта';
            const body = parts[1] || '';
            racialList.innerHTML += `<li><strong>${escapeHtml(title)}</strong>${escapeHtml(body)}</li>`;
        });
    }

    // Class features list
    const classList = document.getElementById('sheet-class-features');
    classList.innerHTML = '';
    
    char.classes.forEach(c => {
        const rule = DND_CLASSES[c.className];
        if (rule) {
            // basic class rules
            classList.innerHTML += `
                <li>
                    <strong>Кость здоровья класса ${c.className}: d${rule.hit_die}</strong>
                    Владение оружием: ${rule.weapon_proficiencies.join(', ')}. Владение броней: ${rule.armor_proficiencies.join(', ') || 'нет'}.
                </li>
            `;
        }
    });

    // Personality Traits, Ideals, Bonds, Flaws
    document.getElementById('sheet-personality-val').textContent = char.personalityTraits || '—';
    document.getElementById('sheet-ideals-val').textContent = char.ideals || '—';
    document.getElementById('sheet-bonds-val').textContent = char.bonds || '—';
    document.getElementById('sheet-flaws-val').textContent = char.flaws || '—';

    // Custom Features List
    const customFeatsList = document.getElementById('sheet-custom-features-list');
    customFeatsList.innerHTML = '';
    
    if (char.customFeatures && char.customFeatures.length > 0) {
        char.customFeatures.forEach((feat, idx) => {
            const featDiv = document.createElement('div');
            featDiv.className = 'info-block';
            featDiv.style.position = 'relative';
            featDiv.innerHTML = `
                <div style="font-weight:700; margin-bottom:4px; display:flex; justify-content:space-between; align-items:center;">
                    <span>${escapeHtml(feat.name)}</span>
                    <button class="btn btn-danger btn-sm btn-delete-feat edit-only" data-idx="${idx}" style="padding:2px 6px; font-size:10px;">🗑️</button>
                </div>
                <div style="white-space:pre-wrap; font-size:11px;">${escapeHtml(feat.description)}</div>
            `;
            
            featDiv.querySelector('.btn-delete-feat').onclick = async (e) => {
                e.stopPropagation();
                if (confirm(`Удалить умение "${feat.name}"?`)) {
                    char.customFeatures.splice(idx, 1);
                    updateDashboardFeaturesTab();
                    await syncCharacterData();
                }
            };
            customFeatsList.appendChild(featDiv);
        });
    } else {
        customFeatsList.innerHTML = `<p class="input-helper">Нет добавленных умений.</p>`;
    }
}

function renderResourceBubbleBox(parent, title, max, spent, resourceKey, restRecharge) {
    const card = document.createElement('div');
    card.className = 'resource-tracker-box';
    
    let bubblesHtml = '';
    for (let i = 0; i < max; i++) {
        const isSpent = (i < spent);
        bubblesHtml += `<span class="slot-bubble ${isSpent ? '' : 'filled'}" data-key="${resourceKey}" data-idx="${i}"></span>`;
    }

    card.innerHTML = `
        <div class="resource-tracker-header">
            <span>${title} (${max - spent} / ${max})</span>
            <small style="color:var(--text-dim);">Восст. при: ${restRecharge === 'short' ? 'Коротком' : 'Длинном'} отдыхе</small>
        </div>
        <div class="slots-bubbles">${bubblesHtml}</div>
    `;

    card.querySelectorAll('.slot-bubble').forEach(b => {
        b.onclick = async () => {
            const char = state.currentCharacter;
            let current = char.resources[resourceKey] || 0;
            if (b.classList.contains('filled')) {
                char.resources[resourceKey] = Math.min(max, current + 1);
            } else {
                char.resources[resourceKey] = Math.max(0, current - 1);
            }
            char.resources[resourceKey + "_recharge"] = restRecharge; // metadata
            updateDashboardFeaturesTab();
            await syncCharacterData();
        };
    });

    parent.appendChild(card);
}

// Sheet controls events
document.getElementById('btn-sheet-back').onclick = () => {
    switchView('list');
    loadCharacters();
};

document.getElementById('btn-sheet-edit').onclick = () => {
    toggleEditMode();
};

document.getElementById('btn-sheet-add-attack').onclick = async () => {
    const char = state.currentCharacter;
    if (!char) return;
    
    const nameInput = document.getElementById('sheet-attack-name');
    const bonusInput = document.getElementById('sheet-attack-bonus');
    const dmgInput = document.getElementById('sheet-attack-damage');
    const typeInput = document.getElementById('sheet-attack-type');
    
    const name = nameInput.value.trim();
    const bonus = parseInt(bonusInput.value) || 0;
    const damage = dmgInput.value.trim();
    const type = typeInput.value.trim() || 'физический';
    
    if (!name || !damage) {
        showToast('Введите название и урон атаки!', 'error');
        return;
    }
    
    if (!char.customAttacks) {
        char.customAttacks = [];
    }
    
    char.customAttacks.push({
        id: 'atk_' + Math.random().toString(36).substring(2, 9),
        name,
        attackBonus: bonus,
        damageFormula: damage,
        damageType: type
    });
    
    nameInput.value = '';
    bonusInput.value = '';
    dmgInput.value = '';
    typeInput.value = '';
    
    updateDashboardCombatTab();
    await syncCharacterData();
    showToast('Атака успешно добавлена!');
};

document.getElementById('btn-sheet-add-feat').onclick = async () => {
    const char = state.currentCharacter;
    if (!char) return;
    
    const nameInput = document.getElementById('sheet-add-feat-name');
    const descInput = document.getElementById('sheet-add-feat-desc');
    const name = nameInput.value.trim();
    const desc = descInput.value.trim();
    
    if (!name) {
        showToast('Введите название умения!', 'error');
        return;
    }
    
    char.customFeatures.push({ name, description: desc });
    nameInput.value = '';
    descInput.value = '';
    
    updateDashboardFeaturesTab();
    await syncCharacterData();
    showToast('Умение успешно добавлено!');
};

document.getElementById('btn-sheet-add-spell').onclick = async () => {
    const char = state.currentCharacter;
    if (!char) return;

    const nameInput = document.getElementById('sheet-spell-name');
    const lvlSelect = document.getElementById('sheet-spell-lvl');
    const schoolInput = document.getElementById('sheet-spell-school');
    const timeInput = document.getElementById('sheet-spell-time');
    const rangeInput = document.getElementById('sheet-spell-range');
    const descInput = document.getElementById('sheet-spell-desc');

    const name = nameInput.value.trim();
    const level = parseInt(lvlSelect.value) || 0;
    const school = schoolInput.value.trim() || 'Магия';
    const time = timeInput.value.trim() || '1 действие';
    const range = rangeInput.value.trim() || '—';
    const description = descInput.value.trim();

    if (!name) {
        showToast('Укажите название заклинания!', 'error');
        return;
    }

    if (!char.customSpells) {
        char.customSpells = [];
    }

    char.customSpells.push({ name, level, school, time, range, description, prepared: true });

    nameInput.value = '';
    schoolInput.value = '';
    timeInput.value = '';
    rangeInput.value = '';
    descInput.value = '';

    updateDashboardSpellsTab();
    await syncCharacterData();
    showToast('Заклинание добавлено в книгу!');
};

document.getElementById('btn-sheet-print').onclick = () => {
    generatePrintHtml();
    window.print();
};

document.getElementById('btn-sheet-export').onclick = () => {
    const char = state.currentCharacter;
    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(char, null, 2));
    const dlAnchor = document.createElement('a');
    dlAnchor.setAttribute("href", dataStr);
    dlAnchor.setAttribute("download", `${char.name || 'character'}_sheet.json`);
    document.body.appendChild(dlAnchor);
    dlAnchor.click();
    dlAnchor.remove();
    showToast('JSON экспортирован!');
};

// Character creation trigger
document.getElementById('btn-create-char').onclick = () => {
    openWizard();
};

// Character deletion trigger
document.getElementById('btn-sheet-delete').onclick = async () => {
    const char = state.currentCharacter;
    if (!char) return;
    
    if (!confirm(`Вы действительно хотите удалить персонажа ${char.name}?`)) {
        return;
    }
    
    try {
        await apiCall(`/api/characters?name=${encodeURIComponent(char.name)}`, 'DELETE');
        showToast('Персонаж удален');
        switchView('list');
        loadCharacters();
    } catch (err) {}
};

// --- 3. THEME TOGGLE & FILE IMPORT LOGIC ---
const themeBtn = document.getElementById('btn-theme-toggle');
themeBtn.onclick = () => {
    document.body.classList.toggle('light-theme');
    const isLight = document.body.classList.contains('light-theme');
    localStorage.setItem('roller_theme', isLight ? 'light' : 'dark');
};

// Apply loaded theme preference
if (localStorage.getItem('roller_theme') === 'light') {
    document.body.classList.add('light-theme');
}

// Import JSON triggers
const importTrigger = document.getElementById('btn-import-trigger');
const fileInput = document.getElementById('import-file-input');

importTrigger.onclick = () => {
    fileInput.click();
};

fileInput.onchange = (e) => {
    const file = e.target.files[0];
    if (!file) return;
    
    const reader = new FileReader();
    reader.onload = async (evt) => {
        try {
            const data = JSON.parse(evt.target.result);
            if (!data.name) {
                throw new Error("Неверный формат JSON! Отсутствует поле 'name'.");
            }
            
            // Validate & Save
            const char = new Character(data);
            const serialized = char.toDbFormat();
            serialized.full_data = char;
            
            await apiCall('/api/characters', 'POST', serialized);
            showToast(`Персонаж ${char.name} импортирован успешно!`);
            loadCharacters();
        } catch (err) {
            showToast(err.message, 'error');
        }
        fileInput.value = '';
    };
    reader.readAsText(file);
};


// --- INITIAL STARTUP INVOCATION ---
loadCharacters();
