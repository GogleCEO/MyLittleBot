import os

from dotenv import load_dotenv
from answers import *
from keyboards import *
from data import *

load_dotenv()

bot = Bot(os.getenv("VK_API_TOKEN"))
waiting_players: dict[int, int] = {}
uploader = PhotoMessageUploader(bot.api)

@dataclass
class Match:
    players: list[int]
    questions: list[dict]
    answers: dict[int, list] = field(default_factory=dict)
    current_index: dict[int, int] = field(default_factory=dict)

active_matches: dict[tuple, Match] = {}

async def get_top_players_text(limit: int = 10) -> str:
    rows = get_top_ratings(limit)

    if not rows:
        return "🏆 Рейтинг пока пуст — сыграйте первый матч!"

    user_ids = [uid for uid, _ in rows]
    users = await bot.api.users.get(
        user_ids=user_ids,
        fields=["first_name", "last_name"]
    )

    names = {u.id: f"{u.first_name} {u.last_name}".strip() for u in users}

    lines = ["🏆 Топ-10 игроков:\n"]
    for i, (uid, rating) in enumerate(rows, start=1):
        name = names.get(uid, f"Игрок {uid}")
        lines.append(f"{i}. {name} — {rating}")

    return "\n".join(lines)

async def send_op_found(user_id: int, opponent_id: int):
    users = await bot.api.users.get(
        user_ids=opponent_id,
        fields=["photo_200", "first_name", "last_name"]
    )
    opponent = users[0]
    rating = get_rating(opponent_id)

    text = (
        f"⚔️ Соперник найден!\n\n"
        f"👤 {opponent.first_name} {opponent.last_name}\n"
        f"🏆 Рейтинг: {rating}"
    )

    await bot.api.messages.send(
        peer_id=user_id,
        message=text,
        random_id=0
    )
async def get_image(title):
    image_url = None
    # 50% шанс попытаться прикрепить картинку
    if random.random() < 0.5:
        image_url = get_page_image(title)
    return image_url
async def send_duel_question(user_id: int, match: Match):
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

    image_url = await get_image(question["correct"])
    if image_url:
        attachment = await upload_image_from_url(uploader, user_id, image_url)
        text = f"⚔️ Вопрос {q_idx + 1}/5\n\nЧто изображено на фото?"
        await bot.api.messages.send(peer_id=user_id, message=text, attachment=attachment, keyboard=kb.get_json(), random_id=0)
    else:
        text = f"⚔️ Вопрос {q_idx + 1}/5\n\n{description}"
        await bot.api.messages.send(peer_id=user_id, message=text, keyboard=kb.get_json(), random_id=0)
async def announce_duel_result(match: Match):
    p1, p2 = match.players
    score1 = sum(match.answers[p1])
    score2 = sum(match.answers[p2])


    if score1 > score2:
        winner, loser = p1, p2
        users = await bot.api.users.get(
            user_ids=p1,
            fields=["photo_200", "first_name", "last_name"]
        )
        winnerName = users[0]
        result_text = f"🏆 Победитель: {winnerName.first_name} {winnerName.last_name} ({score1}:{score2})"

    elif score2 > score1:
        winner, loser = p2, p1
        users = await bot.api.users.get(
            user_ids=p2,
            fields=["photo_200", "first_name", "last_name"]
        )
        winnerName = users[0]
        result_text = f"🏆 Победитель: {winnerName.first_name} {winnerName.last_name} ({score1}:{score2})"
    else:
        winner = loser = None
        result_text = f"🤝 Ничья! ({score1}:{score2})"

    # Обновляем рейтинг
    if winner is not None:
        update_rating(winner, +20)
        loser_rating = get_rating(loser)
        if loser_rating < 20:
            update_rating(loser, -loser_rating)

    for uid in match.players:
        current_rating = get_rating(uid)
        await bot.api.messages.send(
            peer_id=uid,
            message=(
                f"Соревнование окончено!\n{result_text}\n\n"
                f"Твой счёт: {match.answers[uid].count(True)}/5\n"
                f"Твой рейтинг: {current_rating}"
            ),
            keyboard=menu_keyboard().get_json(),
            random_id=0,
        )

@bot.on.message(text="Начало")
async def start(message: Message):
    await message.answer("Выбери режим", keyboard=menu_keyboard().get_json())


@bot.on.raw_event(GroupEventType.MESSAGE_EVENT, dataclass=MessageEvent)
async def handle_callback(event: MessageEvent):
    payload = event.payload
    action = payload.get("action")
    user_id = event.user_id
    peer_id = event.peer_id

    if action == "train":
        await event.send_message("Режим тренировки. Выбери эпоху", keyboard=train_keyboard().get_json())
        await event.show_snackbar("Выбери эпоху")
        return

    if action == "mmr":
        rating = get_rating(user_id)
        await event.send_message(f"Твой рейтинг: {rating}")
        await event.show_snackbar(f"Твой рейтинг: {rating}")
        return
    if action == "leaderboard":
        text = await get_top_players_text()
        await event.send_message(text)
        return

    # 1. Старт: выбор эпохи → первый вопрос
    if action == "start":
        era = payload.get("era")
        question = pick_question(era)
        text = await getWiki(question["correct"])
        kb = answers_keyboard(question["options"], question["correct"], era)
        image_url = await get_image(question["correct"])
        if image_url:
            attachment = await upload_image_from_url(uploader, event.peer_id, image_url)
            text = "Что изображено на фото?"
            await event.send_message(text, keyboard=kb.get_json(), attachment=attachment)
            print("Изображение отправлено")
        else:
            await event.send_message(text, keyboard=kb.get_json())
        await event.show_snackbar("Вопрос загружен")
        return

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

    if action == "next":
        era = payload.get("era")
        question = pick_question(era)
        text = await getWiki(question["correct"])
        kb = answers_keyboard(question["options"], question["correct"], era)
        image_url = await get_image(question["correct"])
        if image_url:
            attachment = await upload_image_from_url(uploader, event.peer_id, image_url)
            text = "Что изображено на фото?"
            await event.send_message(text, keyboard=kb.get_json(), attachment=attachment)
        else:
            await event.send_message(text, keyboard=kb.get_json())
        await event.show_snackbar("Новый вопрос")
        return

    # 4. Возврат в меню
    if action == "menu":
        await event.send_message("Меню:", keyboard=menu_keyboard().get_json())
        await event.show_snackbar("Возвращаю в меню")
        return

    if action == "duel_cancel":
        del waiting_players[user_id]
        await event.send_message("Меню:", keyboard=menu_keyboard().get_json())
        await event.show_snackbar("Вы вышли из очереди")
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
            kb = Keyboard(one_time=True, inline=False)
            kb.add(Callback("Выйти из очереди", payload={"action": "duel_cancel"}), color=KeyboardButtonColor.POSITIVE)
            await event.send_message("⏳ Ожидание соперника... Нажми выйти из очереди чтобы отменить.", keyboard=kb.get_json())
            await event.show_snackbar("Ты в очереди")
        else:
            # Нашли соперника — создаём матч
            del waiting_players[opponent_id]
            waiting_players.get(opponent_id, opponent_id)
            await send_op_found(user_id, opponent_id)
            await send_op_found(opponent_id, user_id)

            match_key = tuple(sorted([user_id, opponent_id]))
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

    if action == "duel_answer":
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
            other_id = match.players[0] if match.players[1] == user_id else match.players[1]
            if match.current_index[other_id] >= 5:
                await announce_duel_result(match)
                del active_matches[match_key]
            else:
                await event.send_message("🏁 Ты ответил на все вопросы! Ждём соперника...")
        else:
            await send_duel_question(user_id, match)

        await event.show_snackbar("Ответ принят")
        return

if __name__ == "__main__":
    init_db()
    asyncio.run(bot.run_polling())  # ✅ Запуск через asyncio.run
