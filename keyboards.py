from vkbottle import Keyboard, KeyboardButtonColor, Callback

def menu_keyboard() -> Keyboard:
    kb = Keyboard(one_time=True, inline=False)
    kb.add(Callback("Тренировка", payload={"action": "train"}), color=KeyboardButtonColor.PRIMARY)
    kb.add(Callback("⚔️ Соревнование", payload={"action": "duel_start"}), color=KeyboardButtonColor.NEGATIVE)
    kb.row()
    kb.add(Callback("Мой рейтинг", payload={"action": "mmr"}), color=KeyboardButtonColor.POSITIVE)
    kb.add(Callback("Топ игроков", payload={"action": "leaderboard"}), color=KeyboardButtonColor.POSITIVE)
    return kb

def train_keyboard() -> Keyboard:
    kb = Keyboard(one_time=True, inline=False)
    kb.add(Callback("Древний мир", payload={"action": "start", "era": "ancient"}), color=KeyboardButtonColor.PRIMARY)
    kb.add(Callback("Средневековье", payload={"action": "start", "era": "medieval"}), color=KeyboardButtonColor.PRIMARY)
    kb.row()
    kb.add(Callback("Новое время", payload={"action": "start", "era": "modern"}), color=KeyboardButtonColor.PRIMARY)
    kb.add(Callback("Всё подряд", payload={"action": "start", "era": "all"}), color=KeyboardButtonColor.PRIMARY)
    kb.add(Callback("Назад", payload={"action": "menu"}), color=KeyboardButtonColor.NEGATIVE)
    return kb

def answers_keyboard(options: list[str], correct: str, era: str) -> Keyboard:
    kb = Keyboard(one_time=True, inline=False)
    for i, opt in enumerate(options):
        kb.add(
            Callback(opt, payload={"action": "answer", "answer": opt, "correct": correct, "era": era}),
            color=KeyboardButtonColor.SECONDARY,
        )
        if i == 1:  # раскладка 2x2
            kb.row()
    return kb

def after_answer_keyboard(era: str) -> Keyboard:
    kb = Keyboard(one_time=True, inline=False)
    kb.add(Callback("➡️ Следующий вопрос", payload={"action": "next", "era": era}), color=KeyboardButtonColor.POSITIVE)
    kb.add(Callback("🏠 В меню", payload={"action": "menu"}), color=KeyboardButtonColor.SECONDARY)
    return kb
