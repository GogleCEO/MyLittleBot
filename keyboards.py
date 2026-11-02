from vkbottle import Keyboard, KeyboardButtonColor, Callback

def era_keyboard() -> Keyboard:
    kb = Keyboard(one_time=True, inline=False)
    kb.add(Callback("Древний мир", payload={"action": "start", "era": "ancient"}), color=KeyboardButtonColor.PRIMARY)
    kb.add(Callback("Средневековье", payload={"action": "start", "era": "medieval"}), color=KeyboardButtonColor.PRIMARY)
    kb.row()
    kb.add(Callback("Новое время", payload={"action": "start", "era": "modern"}), color=KeyboardButtonColor.PRIMARY)
    kb.add(Callback("Всё подряд", payload={"action": "start", "era": "all"}), color=KeyboardButtonColor.PRIMARY)
    kb.add(Callback("⚔️ Соревнование", payload={"action": "duel_start"}), color=KeyboardButtonColor.POSITIVE)
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