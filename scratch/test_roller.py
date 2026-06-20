import json
import random
from handlers.roller import roll_custom_formula, perform_dnd_check_roll

def test_roll_custom_formula():
    print("Testing roll_custom_formula...")
    # Test d20 roll with minimum 10
    # Since rolling is random, we run it multiple times to cover both cases
    for _ in range(100):
        total, rolls, mod, formula_str = roll_custom_formula("1d20+5", min_d20_val=10)
        assert len(rolls) == 1
        assert rolls[0] >= 10
        if "➔" in formula_str:
            # Replaced case
            # E.g. "4 ➔ 10 + 5"
            assert "➔ 10" in formula_str
            # Check sum
            assert total == 15
        else:
            # Normal case
            assert total >= 15
            
    print("roll_custom_formula tests passed!")

def test_perform_dnd_check_roll():
    print("Testing perform_dnd_check_roll...")
    character = {
        "id": 1,
        "name": "Тестовый Rogue",
        "class": "Плут 11",
        "proficiency_bonus": 4,
        "mod_strength": 0,
        "mod_dexterity": 4,
        "mod_constitution": 1,
        "mod_intelligence": 0,
        "mod_wisdom": 2,
        "mod_charisma": -1,
        "saving_throws": ["Ловкость", "Интеллект"],
        "skills": ["Скрытность", "Акробатика"],
        "tools": [],
        "full_data": {
            "skills": {
                "Скрытность": "expert",
                "Акробатика": "proficient"
            },
            "min_rolls": {
                "Скрытность": 10
            }
        }
    }
    
    # We do a normal check on Stealth (Скрытность)
    # Expected modifier: mod_dexterity (4) + added_pb (4) + added_exp (4) = 12
    # Since min_rolls is 10, d20_roll must be >= 10.
    for _ in range(100):
        res = perform_dnd_check_roll(character, "Скрытность")
        total = res["total"]
        detail = res["detail_str"]
        result_d20 = res["result"]
        
        assert result_d20 >= 10
        if "➔" in detail:
            # E.g. "<b>4 ➔ 10</b> + 4 (Ловкость) + 4 (владение) + 4 (экспертность)"
            assert "➔ 10" in detail
            assert total == 22
        else:
            assert total >= 22
            
    print("perform_dnd_check_roll tests passed!")

if __name__ == "__main__":
    test_roll_custom_formula()
    test_perform_dnd_check_roll()
    print("All Python roller tests passed successfully!")
