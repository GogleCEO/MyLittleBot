import asyncio
import random
from vkbottle import Keyboard, KeyboardButtonColor, Text, PhotoMessageUploader, Callback
from vkbottle.bot import Bot, Message, MessageEvent
from vkbottle import BaseStateGroup
from vkbottle import GroupEventType
from dataclasses import dataclass, field
from typing import Optional

from answers import *
from keyboards import *

bot = Bot()
# Очередь ожидающих: {user_id: peer_id} (в личке они совпадают, но peer_id надёжнее)
waiting_players: dict[int, int] = {}

# Активные матчи: match_id (например, кортеж из двух user_id) -> данные матча
@dataclass
class Match:
    players: list[int]              # [user_id1, user_id2]
    questions: list[dict]           # 5 вопросов (каждый — результат pick_question)
    answers: dict[int, list] = field(default_factory=dict)  # user_id -> список ответов (bool)
    current_index: dict[int, int] = field(default_factory=dict)  # user_id -> текущий вопрос

active_matches: dict[tuple, Match] = {}

async def send_duel_question(user_id: int, match: Match):
    """Отправляет игроку текущий вопрос соревнования."""
    q_idx = match.current_index[user_id]
    question = match.questions[q_idx]
    description = await getWiki(question["correct"])

    kb = Keyboard(one_time=True, inline=False)
    for i, opt in enumerate(question["options"]):
        kb.add(
            Callback(opt, payload={"action": "duel_answer", "answer": opt}),
            color=KeyboardButtonColor.SECONDARY,
        )
        if i == 1:
            kb.row()

    text = f"⚔️ Вопрос {q_idx + 1}/5\n\n{description}\n\nЧто это?"
    await bot.api.messages.send(peer_id=user_id, message=text, keyboard=kb.get_json(), random_id=0)


async def announce_duel_result(match: Match):
    """Считает результаты и отправляет обоим игрокам."""
    p1, p2 = match.players
    score1 = sum(match.answers[p1])
    score2 = sum(match.answers[p2])

    if score1 > score2:
        winner = p1
        result_text = f"🏆 Победитель: Игрок {p1} ({score1}:{score2})"
    elif score2 > score1:
        winner = p2
        result_text = f"🏆 Победитель: Игрок {p2} ({score2}:{score1})"
    else:
        result_text = f"🤝 Ничья! ({score1}:{score2})"

    for uid in match.players:
        await bot.api.messages.send(
            peer_id=uid,
            message=f"Соревнование окончено!\n{result_text}\n\nТвой счёт: {match.answers[uid].count(True)}/5",
            keyboard=era_keyboard().get_json(),
            random_id=0,
        )

@bot.on.message(text="/start")
async def start(message: Message):
    await message.answer("Выбери время", keyboard=era_keyboard().get_json())


@bot.on.raw_event(GroupEventType.MESSAGE_EVENT, dataclass=MessageEvent)
async def handle_callback(event: MessageEvent):
    payload = event.payload
    action = payload.get("action")
    user_id = event.user_id
    peer_id = event.peer_id

    # 1. Старт: выбор эпохи → первый вопрос
    if action == "start":
        era = payload.get("era")
        question = pick_question(era)
        description = await getWiki(question["correct"])
        text = f"{description}\n\nЧто это за событие/личность/государство?"
        kb = answers_keyboard(question["options"], question["correct"], era)
        await event.send_message(text, keyboard=kb.get_json())
        await event.show_snackbar("Вопрос загружен")
        return

    # 2. Ответ на вопрос
    if action == "answer":
        chosen = payload.get("answer")
        correct = payload.get("correct")
        era = payload.get("era")

        if chosen == correct:
            result = "✅ Верно!"
        else:
            result = f"❌ Неверно. Правильный ответ: {correct}"

        kb = after_answer_keyboard(era)
        await event.send_message(result, keyboard=kb.get_json())
        await event.show_snackbar("Ответ принят")
        return

    # 3. Следующий вопрос из той же эпохи
    if action == "next":
        era = payload.get("era")
        question = pick_question(era)
        description = await getWiki(question["correct"])
        text = f"{description}\n\nЧто это за событие/личность/государство?"
        kb = answers_keyboard(question["options"], question["correct"], era)
        await event.send_message(text, keyboard=kb.get_json())
        await event.show_snackbar("Новый вопрос")
        return

    # 4. Возврат в меню
    if action == "menu":
        await event.send_message("Выбери эпоху:", keyboard=era_keyboard().get_json())
        await event.show_snackbar("В меню")
        return

    # === СОРЕВНОВАНИЕ: поиск соперника ===
    if action == "duel_start":
        # Если игрок уже в активном матче — предупредить
        for match_key, match in active_matches.items():
            if user_id in match.players:
                await event.show_snackbar("Ты уже в матче!")
                return

        # Если игрок уже в очереди — напомнить
        if user_id in waiting_players:
            await event.show_snackbar("Ты уже в очереди, жди соперника")
            return

        # Ищем соперника в очереди
        opponent_id = None
        for uid in list(waiting_players.keys()):
            if uid != user_id:
                opponent_id = uid
                break

        if opponent_id is None:
            # Соперника нет — встаём в очередь
            waiting_players[user_id] = peer_id
            await event.send_message("⏳ Ожидание соперника... Нажми /cancel_duel чтобы отменить.")
            await event.show_snackbar("Ты в очереди")
        else:
            # Нашли соперника — создаём матч
            del waiting_players[opponent_id]
            opponent_peer = waiting_players.get(opponent_id, opponent_id)  # на всякий случай
            # На самом деле peer уже удалён, сохраним заранее
            # (лучше хранить peer_id в очереди как dict[user_id] = peer_id и брать до удаления)

            match_key = tuple(sorted([user_id, opponent_id]))

            # Генерируем 5 общих вопросов (из той же эпохи, что выбрал первый?
            # Для простоты — "all", или можно спросить эпоху перед стартом)
            questions = [pick_question("all") for _ in range(5)]

            match = Match(
                players=[user_id, opponent_id],
                questions=questions,
                answers={user_id: [], opponent_id: []},
                current_index={user_id: 0, opponent_id: 0},
            )
            active_matches[match_key] = match

            # Отправляем первый вопрос обоим
            await send_duel_question(user_id, match)
            await send_duel_question(opponent_id, match)

            await event.show_snackbar("Соперник найден! Игра началась")
        return

    # === ОТВЕТ В СОРЕВНОВАНИИ ===
    if action == "duel_answer":
        # Находим матч, в котором участвует игрок
        match = None
        match_key = None
        for mk, m in active_matches.items():
            if user_id in m.players:
                match = m
                match_key = mk
                break

        if match is None:
            await event.show_snackbar("Матч не найден")
            return

        chosen = payload.get("answer")
        q_idx = match.current_index[user_id]
        question = match.questions[q_idx]
        is_correct = (chosen == question["correct"])
        match.answers[user_id].append(is_correct)

        # Отправляем фидбек игроку
        if is_correct:
            await event.send_message("✅ Верно!")
        else:
            await event.send_message(f"❌ Неверно. Правильный ответ: {question['correct']}")

        # Переходим к следующему вопросу
        next_idx = q_idx + 1
        match.current_index[user_id] = next_idx

        if next_idx >= 5:
            # Игрок закончил все 5 вопросов
            # Проверяем, закончил ли второй
            other_id = match.players[0] if match.players[1] == user_id else match.players[1]
            if match.current_index[other_id] >= 5:
                # Оба закончили — объявляем результат
                await announce_duel_result(match)
                del active_matches[match_key]
            else:
                await event.send_message("🏁 Ты ответил на все вопросы! Ждём соперника...")
        else:
            await send_duel_question(user_id, match)

        await event.show_snackbar("Ответ принят")
        return

if __name__ == "__main__":
    asyncio.run(bot.run_polling())  # ✅ Запуск через asyncio.run