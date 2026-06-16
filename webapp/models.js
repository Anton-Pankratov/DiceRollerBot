/**
 * D&D 5e Character Model and Rules Engine (Domain Layer)
 * Handles automatic calculations, stats, rest mechanics, and serialization.
 */

class AbilityScore {
    constructor(name, baseVal = 10, racialBonus = 0) {
        this.name = name;
        this.baseVal = baseVal;
        this.racialBonus = racialBonus;
    }

    get score() {
        return this.baseVal + this.racialBonus;
    }

    get modifier() {
        return Math.floor((this.score - 10) / 2);
    }
}

class Character {
    constructor(data = {}) {
        this.id = data.id || null;
        this.name = data.name || "";
        this.portrait = data.portrait || ""; // URL or base64 or emoji
        this.alignment = data.alignment || "True Neutral";
        this.background = data.background || "Custom";
        this.xp = Number(data.xp) || 0;
        this.race = data.race || "Human";
        this.subrace = data.subrace || "";
        
        // classes is an array of { className: string, level: number, subclass: string }
        this.classes = data.classes && data.classes.length ? data.classes : [{ className: "Fighter", level: 1, subclass: "" }];
        
        // D&D 2014 Extended Identity
        this.playerName = data.playerName || "";
        this.languages = data.languages || "";
        this.otherProficiencies = data.otherProficiencies || "";
        
        // Custom Stat/Combat Overrides
        this.customSpeed = data.customSpeed !== undefined && data.customSpeed !== null ? data.customSpeed : null;
        this.customAC = data.customAC !== undefined && data.customAC !== null ? data.customAC : null;
        this.customInitiative = data.customInitiative !== undefined && data.customInitiative !== null ? data.customInitiative : null;
        this.customSpellDC = data.customSpellDC !== undefined && data.customSpellDC !== null ? data.customSpellDC : null;
        this.customSpellAttack = data.customSpellAttack !== undefined && data.customSpellAttack !== null ? data.customSpellAttack : null;
        
        // Death Saves
        this.deathSaves = data.deathSaves || { successes: 0, failures: 0 };
        
        // Coins (Money)
        this.coins = data.coins || { cp: 0, sp: 0, ep: 0, gp: 0, pp: 0 };
        
        // Custom lists
        this.customAttacks = data.customAttacks || [];
        this.customFeatures = data.customFeatures || [];
        this.customSpells = data.customSpells || [];
        
        // Personality & Backstory
        this.personalityTraits = data.personalityTraits || "";
        this.ideals = data.ideals || "";
        this.bonds = data.bonds || "";
        this.flaws = data.flaws || "";
        this.backstory = data.backstory || "";
        this.allies = data.allies || "";
        this.treasure = data.treasure || "";
        
        // Appearance
        this.age = data.age || "";
        this.height = data.height || "";
        this.weight = data.weight || "";
        this.eyes = data.eyes || "";
        this.skin = data.skin || "";
        this.hair = data.hair || "";
        
        // base stats
        this.stats = data.stats || {
            strength: 10,
            dexterity: 10,
            constitution: 10,
            intelligence: 10,
            wisdom: 10,
            charisma: 10
        };

        // Custom choice data for stats generation (Standard Array, Point Buy, Manual, Roll)
        this.statGenMethod = data.statGenMethod || "standard_array";
        this.statGenData = data.statGenData || {};

        // Proficiencies
        this.savingThrows = data.savingThrows || []; // List of ability names in Russian (Сила, Ловкость, etc.)
        
        // skills: object mapping skill name to level ('none', 'proficient', 'expert', 'half')
        this.skills = data.skills || {}; 
        
        this.tools = data.tools || [];
        
        // hp
        this.hp = data.hp || { current: 10, max: 10, temp: 0 };
        
        // Hit Dice spent per class die size (e.g. { "d10": 0 })
        this.hitDiceSpent = data.hitDiceSpent || {};
        
        // Inventory
        this.equipment = data.equipment || [];
        
        // Spellcasting
        this.spells = data.spells || []; // List of { name, level, prepared }
        this.spellSlotsSpent = data.spellSlotsSpent || { 1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0, 7: 0, 8: 0, 9: 0 };
        
        // Trackers
        this.conditions = data.conditions || [];
        this.resources = data.resources || {}; // Custom trackers e.g. { rageSpent: 0, rageMax: 2, kiSpent: 0 }
        
        this.notes = data.notes || "";
        
        // custom_formulas is stored as key-value pairs
        this.custom_formulas = data.custom_formulas || {};
        
        // Active status
        this.is_active = !!data.is_active;
    }

    // --- Computed Properties ---

    get totalLevel() {
        return this.classes.reduce((sum, cls) => sum + (Number(cls.level) || 0), 0);
    }

    get proficiencyBonus() {
        const lvl = this.totalLevel;
        if (lvl >= 17) return 6;
        if (lvl >= 13) return 5;
        if (lvl >= 9) return 4;
        if (lvl >= 5) return 3;
        return 2;
    }

    // Get the base hit die type for classes
    getHitDiceMax() {
        const totals = {};
        this.classes.forEach(c => {
            const rule = DND_CLASSES[c.className];
            if (rule) {
                const die = `d${rule.hit_die}`;
                totals[die] = (totals[die] || 0) + c.level;
            }
        });
        return totals;
    }

    // Calculate ability score including racial and subrace bonuses
    getAbilityScore(abilityName) {
        const base = this.stats[abilityName.toLowerCase()] || 10;
        let racial = 0;
        
        const raceRule = DND_RACES[this.race];
        if (raceRule) {
            // Base race bonus
            if (raceRule.bonuses && raceRule.bonuses[abilityName.toLowerCase()]) {
                racial += raceRule.bonuses[abilityName.toLowerCase()];
            }
            // Subrace bonus
            if (this.subrace && raceRule.subraces) {
                const sub = raceRule.subraces.find(s => s.name === this.subrace);
                if (sub && sub.bonuses && sub.bonuses[abilityName.toLowerCase()]) {
                    racial += sub.bonuses[abilityName.toLowerCase()];
                }
            }
        }
        return base + racial;
    }

    getAbilityModifier(abilityName) {
        const score = this.getAbilityScore(abilityName);
        return Math.floor((score - 10) / 2);
    }

    // Check if character is a Bard of Level 2+ for Jack of all Trades
    hasJackOfAllTrades() {
        const bard = this.classes.find(c => c.className === "Bard");
        return bard && bard.level >= 2;
    }

    // Skill modifier calculations
    getSkillModifier(skillName) {
        const skillRule = ALL_SKILLS_META[skillName];
        if (!skillRule) return 0;

        const attr = skillRule.attr; // e.g. 'dexterity'
        const baseMod = this.getAbilityModifier(attr);
        const pb = this.proficiencyBonus;

        const prof = this.skills[skillName] || "none";
        
        if (prof === "expert") {
            return baseMod + (2 * pb);
        } else if (prof === "proficient") {
            return baseMod + pb;
        } else if (prof === "half") {
            return baseMod + Math.floor(pb / 2);
        } else if (this.hasJackOfAllTrades()) {
            // Jack of all Trades adds half proficiency bonus (rounded down) to any ability check that doesn't already include PB
            return baseMod + Math.floor(pb / 2);
        }
        return baseMod;
    }

    // Saving throw modifier calculations
    getSaveModifier(abilityNameRu) {
        const abilityEn = RU_TO_EN_ABBR[abilityNameRu];
        const baseMod = this.getAbilityModifier(abilityEn);
        const pb = this.proficiencyBonus;
        
        const isProf = this.savingThrows.includes(abilityNameRu);
        return baseMod + (isProf ? pb : 0);
    }

    // AC Calculations based on armor, shields, and class features
    getArmorClass() {
        if (this.customAC !== null && this.customAC !== undefined && this.customAC !== "") {
            return Number(this.customAC);
        }
        let equippedArmor = null;
        let hasShield = false;
        
        this.equipment.forEach(item => {
            if (item.equipped) {
                if (item.type === "armor") {
                    equippedArmor = item.name;
                } else if (item.type === "shield") {
                    hasShield = true;
                }
            }
        });

        const dexMod = this.getAbilityModifier("dexterity");
        const wisMod = this.getAbilityModifier("wisdom");
        const conMod = this.getAbilityModifier("constitution");
        
        let baseAC = 10 + dexMod;

        if (equippedArmor) {
            // Find AC in item list or match standard D&D rules
            if (equippedArmor.includes("Leather") || equippedArmor.includes("Кожаный")) {
                baseAC = 11 + dexMod;
            } else if (equippedArmor.includes("Scale") || equippedArmor.includes("Чешуйчатый")) {
                baseAC = 14 + Math.min(2, dexMod);
            } else if (equippedArmor.includes("Chain") || equippedArmor.includes("Кольчатый")) {
                baseAC = 16;
            } else if (equippedArmor.includes("Plate") || equippedArmor.includes("Латы")) {
                baseAC = 18;
            } else {
                // Generic fallback for custom armor names
                baseAC = 11 + dexMod;
            }
        } else {
            // Unarmored Defense features
            const hasBarbarian = this.classes.some(c => c.className === "Barbarian");
            const hasMonk = this.classes.some(c => c.className === "Monk");
            
            if (hasMonk && !hasShield) {
                baseAC = 10 + dexMod + wisMod;
            } else if (hasBarbarian) {
                baseAC = 10 + dexMod + conMod; // Barbarians can use shields
            }
        }

        if (hasShield) {
            baseAC += 2;
        }

        return baseAC;
    }

    // Carrying Capacity
    getCarryingCapacity() {
        const strScore = this.getAbilityScore("strength");
        let multiplier = 15;
        
        // Large size doubles, Small/Tiny sizes adjust but 5e Medium/Small both use 15x
        const raceRule = DND_RACES[this.race];
        if (raceRule && raceRule.size === "Tiny") {
            multiplier = 7.5;
        }
        
        return strScore * multiplier;
    }

    getTotalWeight() {
        return this.equipment.reduce((sum, item) => sum + ((Number(item.weight) || 0) * (Number(item.quantity) || 1)), 0);
    }

    // Initiative Modifier (Dexterity check)
    getInitiativeModifier() {
        if (this.customInitiative !== null && this.customInitiative !== undefined && this.customInitiative !== "") {
            return Number(this.customInitiative);
        }
        let mod = this.getAbilityModifier("dexterity");
        if (this.hasJackOfAllTrades()) {
            mod += Math.floor(this.proficiencyBonus / 2);
        }
        return mod;
    }

    // Passive Scores
    getPassivePerception() {
        return 10 + this.getSkillModifier("Внимательность");
    }

    getPassiveInsight() {
        return 10 + this.getSkillModifier("Проницательность");
    }

    getPassiveInvestigation() {
        return 10 + this.getSkillModifier("Анализ");
    }

    // Spellcasting Stats per class
    getSpellcastingStats() {
        const stats = [];
        this.classes.forEach(c => {
            const rule = DND_CLASSES[c.className];
            if (rule && rule.spellcaster) {
                let attr = "charisma";
                if (["Wizard"].includes(c.className)) attr = "intelligence";
                else if (["Cleric", "Druid", "Ranger"].includes(c.className)) attr = "wisdom";
                
                const mod = this.getAbilityModifier(attr);
                let saveDC = 8 + this.proficiencyBonus + mod;
                let attackBonus = this.proficiencyBonus + mod;
                
                if (this.customSpellDC !== null && this.customSpellDC !== undefined && this.customSpellDC !== "") {
                    saveDC = Number(this.customSpellDC);
                }
                if (this.customSpellAttack !== null && this.customSpellAttack !== undefined && this.customSpellAttack !== "") {
                    attackBonus = Number(this.customSpellAttack);
                }
                
                stats.push({
                    className: c.className,
                    ability: EN_TO_RU_ABBR[attr],
                    saveDC,
                    attackBonus
                });
            }
        });
        return stats;
    }

    // Multiclass Spell Slots Calculation
    getMaxSpellSlots() {
        let pactMagicSlots = 0;
        let pactMagicLevel = 0;
        
        // Count spellcasting level contributions
        let casterLevelSum = 0;
        
        this.classes.forEach(c => {
            const level = c.level;
            if (c.className === "Warlock") {
                pactMagicLevel = level;
                // Warlock slots progression
                if (level >= 17) { pactMagicSlots = 4; pactMagicLevel = 5; }
                else if (level >= 11) { pactMagicSlots = 3; pactMagicLevel = 5; }
                else if (level >= 9) { pactMagicSlots = 2; pactMagicLevel = 5; }
                else if (level >= 7) { pactMagicSlots = 2; pactMagicLevel = 4; }
                else if (level >= 5) { pactMagicSlots = 2; pactMagicLevel = 3; }
                else if (level >= 3) { pactMagicSlots = 2; pactMagicLevel = 2; }
                else if (level >= 1) { pactMagicSlots = 1; pactMagicLevel = 1; }
            } else if (["Wizard", "Cleric", "Druid", "Sorcerer", "Bard"].includes(c.className)) {
                casterLevelSum += level;
            } else if (["Paladin", "Ranger"].includes(c.className)) {
                casterLevelSum += Math.floor(level / 2);
            } else if (["Fighter", "Rogue"].includes(c.className) && ["Eldritch Knight", "Arcane Trickster"].includes(c.subclass)) {
                casterLevelSum += Math.floor(level / 3);
            }
        });

        // If not a caster at all
        if (casterLevelSum === 0 && pactMagicSlots === 0) {
            return { slots: {}, pactMagic: null };
        }

        const slots = {};
        if (casterLevelSum > 0) {
            // standard spell slot progression
            const index = Math.min(20, Math.max(1, casterLevelSum)) - 1;
            const row = MULTICLASS_SPELL_SLOTS_TABLE[index];
            row.forEach((count, i) => {
                if (count > 0) {
                    slots[i + 1] = count;
                }
            });
        }

        // Apply custom max slots overrides
        for (let lvl = 1; lvl <= 9; lvl++) {
            if (this.customMaxSlots && this.customMaxSlots[lvl] !== undefined) {
                const cVal = Number(this.customMaxSlots[lvl]);
                if (cVal > 0) {
                    slots[lvl] = cVal;
                } else {
                    delete slots[lvl];
                }
            }
        }

        return {
            slots,
            pactMagic: pactMagicSlots > 0 ? {
                slots: pactMagicSlots,
                level: pactMagicLevel,
                spent: this.spellSlotsSpent["pact"] || 0
            } : null
        };
    }

    // --- Actions & Rest Mechanics ---

    applyDamage(amount) {
        amount = Math.max(0, Number(amount) || 0);
        if (this.hp.temp > 0) {
            if (this.hp.temp >= amount) {
                this.hp.temp -= amount;
                amount = 0;
            } else {
                amount -= this.hp.temp;
                this.hp.temp = 0;
            }
        }
        this.hp.current = Math.max(0, this.hp.current - amount);
    }

    applyHealing(amount) {
        amount = Math.max(0, Number(amount) || 0);
        this.hp.current = Math.min(this.hp.max, this.hp.current + amount);
    }

    shortRest() {
        // Regain Warlock Pact Magic slots
        if (this.spellSlotsSpent["pact"]) {
            this.spellSlotsSpent["pact"] = 0;
        }
        
        // Custom resources recharge check
        Object.keys(this.resources).forEach(key => {
            if (key.endsWith("_recharge") && this.resources[key] === "short") {
                const baseKey = key.replace("_recharge", "");
                if (this.resources[baseKey + "_spent"]) {
                    this.resources[baseKey + "_spent"] = 0;
                }
            }
        });
    }

    longRest() {
        // Recover all HP
        this.hp.current = this.hp.max;
        this.hp.temp = 0;

        // Reset spent spell slots
        Object.keys(this.spellSlotsSpent).forEach(k => {
            this.spellSlotsSpent[k] = 0;
        });

        // Recover Hit Dice (up to half of max dice, minimum 1)
        const maxDice = this.getHitDiceMax();
        Object.keys(maxDice).forEach(die => {
            const max = maxDice[die];
            const spent = this.hitDiceSpent[die] || 0;
            const recover = Math.max(1, Math.floor(max / 2));
            this.hitDiceSpent[die] = Math.max(0, spent - recover);
        });

        // Reset all custom resources
        Object.keys(this.resources).forEach(key => {
            if (key.endsWith("_spent")) {
                this.resources[key] = 0;
            }
        });
    }

    // --- Serialization ---

    // Outputs data structured for db.py save_character()
    toDbFormat() {
        // Build Russian skill lists for direct bot match
        const profSkills = Object.keys(this.skills).filter(s => this.skills[s] === "proficient" || this.skills[s] === "expert");

        // Main class display format, e.g. "Wizard 3 / Fighter 1"
        const classStr = this.classes.map(c => `${c.className} ${c.level}`).join(" / ");

        return {
            id: this.id,
            name: this.name,
            class: classStr,
            proficiency_bonus: this.proficiencyBonus,
            mod_strength: this.getAbilityModifier("strength"),
            mod_dexterity: this.getAbilityModifier("dexterity"),
            mod_constitution: this.getAbilityModifier("constitution"),
            mod_intelligence: this.getAbilityModifier("intelligence"),
            mod_wisdom: this.getAbilityModifier("wisdom"),
            mod_charisma: this.getAbilityModifier("charisma"),
            saving_throws: this.savingThrows,
            skills: profSkills,
            tools: this.tools,
            custom_formulas: this.custom_formulas,
            is_active: this.is_active ? 1 : 0
        };
    }
}

// --- Constants & Meta tables ---

const RU_TO_EN_ABBR = {
    "Сила": "strength",
    "Ловкость": "dexterity",
    "Телосложение": "constitution",
    "Интеллект": "intelligence",
    "Мудрость": "wisdom",
    "Харизма": "charisma"
};

const EN_TO_RU_ABBR = {
    "strength": "Сила",
    "dexterity": "Ловкость",
    "constitution": "Телосложение",
    "intelligence": "Интеллект",
    "wisdom": "Мудрость",
    "charisma": "Харизма"
};

const ALL_SKILLS_META = {
    "Атлетика": { attr: "strength" },
    "Акробатика": { attr: "dexterity" },
    "Ловкость рук": { attr: "dexterity" },
    "Скрытность": { attr: "dexterity" },
    "Анализ": { attr: "intelligence" },
    "История": { attr: "intelligence" },
    "Магия": { attr: "intelligence" },
    "Природа": { attr: "intelligence" },
    "Религия": { attr: "intelligence" },
    "Уход за животными": { attr: "wisdom" },
    "Внимательность": { attr: "wisdom" },
    "Проницательность": { attr: "wisdom" },
    "Медицина": { attr: "wisdom" },
    "Выживание": { attr: "wisdom" },
    "Обман": { attr: "charisma" },
    "Запугивание": { attr: "charisma" },
    "Выступление": { attr: "charisma" },
    "Убеждение": { attr: "charisma" }
};

const MULTICLASS_SPELL_SLOTS_TABLE = [
    // 1st 2nd 3rd 4th 5th 6th 7th 8th 9th
    [2, 0, 0, 0, 0, 0, 0, 0, 0], // Lvl 1
    [3, 0, 0, 0, 0, 0, 0, 0, 0], // Lvl 2
    [4, 2, 0, 0, 0, 0, 0, 0, 0], // Lvl 3
    [4, 3, 0, 0, 0, 0, 0, 0, 0], // Lvl 4
    [4, 3, 2, 0, 0, 0, 0, 0, 0], // Lvl 5
    [4, 3, 3, 0, 0, 0, 0, 0, 0], // Lvl 6
    [4, 3, 3, 1, 0, 0, 0, 0, 0], // Lvl 7
    [4, 3, 3, 2, 0, 0, 0, 0, 0], // Lvl 8
    [4, 3, 3, 3, 1, 0, 0, 0, 0], // Lvl 9
    [4, 3, 3, 3, 2, 0, 0, 0, 0], // Lvl 10
    [4, 3, 3, 3, 2, 1, 0, 0, 0], // Lvl 11
    [4, 3, 3, 3, 2, 1, 0, 0, 0], // Lvl 12
    [4, 3, 3, 3, 2, 1, 1, 0, 0], // Lvl 13
    [4, 3, 3, 3, 2, 1, 1, 0, 0], // Lvl 14
    [4, 3, 3, 3, 2, 1, 1, 1, 0], // Lvl 15
    [4, 3, 3, 3, 2, 1, 1, 1, 0], // Lvl 16
    [4, 3, 3, 3, 2, 1, 1, 1, 1], // Lvl 17
    [4, 3, 3, 3, 3, 1, 1, 1, 1], // Lvl 18
    [4, 3, 3, 3, 3, 2, 1, 1, 1], // Lvl 19
    [4, 3, 3, 3, 3, 2, 2, 1, 1]  // Lvl 20
];
