import random
from typing import Dict, Any, Optional

class DiceRollerService:
    """
    Бизнес-логика для бросков кубиков (дайсов).
    Разделение логики броска и интерфейса Telegram позволяет
    в будущем переиспользовать этот класс для веб-версии, мобильного API или тестов.
    """
    
    # Максимальный лимит граней для предотвращения переполнения
    MAX_SIDES = 1_000_000
    
    @staticmethod
    def roll(sides: int) -> Dict[str, Any]:
        """
        Совершает бросок кубика с заданным количеством граней.
        
        :param sides: Количество граней кубика
        :return: Словарь с результатами броска
        """
        if sides < 1:
            return {
                "success": False,
                "error": "Количество граней должно быть не менее 1."
            }
            
        if sides > DiceRollerService.MAX_SIDES:
            return {
                "success": False,
                "error": f"Максимально допустимое количество граней: {DiceRollerService.MAX_SIDES:,}."
            }
            
        # Генерация случайного числа
        result = random.randint(1, sides)
        
        return {
            "success": True,
            "sides": sides,
            "result": result,
            "description": f"Бросок d{sides}"
        }

    @classmethod
    def parse_and_roll(cls, text: str) -> Dict[str, Any]:
        """
        Парсит текстовый ввод (например, '20', 'd20', '🎲 d100') и делает бросок.
        Удаляет эмодзи, буквы и пробелы, чтобы извлечь число граней.
        
        :param text: Строка для парсинга
        :return: Результат броска
        """
        import re
        clean_text = text.strip()
        # Извлекаем все цифры из строки
        digits = re.sub(r'[^\d]', '', clean_text)
        
        try:
            sides = int(digits)
            return cls.roll(sides)
        except ValueError:
            return {
                "success": False,
                "error": "Не удалось распознать количество граней. Отправьте число, например '20' или 'd20'."
            }

