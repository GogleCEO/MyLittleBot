import asyncio
import random
from vkbottle import Keyboard, KeyboardButtonColor, Text, PhotoMessageUploader, Callback
from vkbottle.bot import Bot, Message, MessageEvent
from vkbottle import BaseStateGroup
from vkbottle import GroupEventType
import wikipediaapi
from dataclasses import dataclass, field
from typing import Optional

def extract_description(text: str, title: str, limit: int = 250) -> str:
    # 1. Удаляем ВСЕ вхождения названия темы из текста
    if title:
        text = text.replace(title, "")

    # 2. Убираем лишние пробелы и обрезаем заголовок до первого тире
    text = " ".join(text.split())  # схлопываем повторные пробелы
    for dash in ("—", "–", "-"):
        if dash in text:
            text = text.split(dash, 1)[1]
            break
    text = text.strip()

    # 3. Если текст короче лимита — возвращаем как есть
    if len(text) <= limit:
        return text

    # 4. Берём первые limit символов
    short = text[:limit]

    # 5. Ищем следующую точку после limit-го символа
    dot_pos = text.find(".", limit)
    if dot_pos != -1:
        return text[:dot_pos + 1].strip()

    # 6. Если точки после limit нет — возвращаем хотя бы limit символов
    return short.strip()
async def getWiki(title: str) -> str:
    """Получить краткое описание через Wikipedia-API (упрощённо, нужен pip install Wikipedia-API)"""
    wiki = wikipediaapi.Wikipedia(user_agent="VKHistoryBot/1.0 (contact@example.com)", language="ru")
    page = wiki.page(title)
    if page.exists():
        return extract_description(page.summary, title)  # обрезаем, чтобы не было слишком длинно
    return "Описание недоступно."
async def ancientAnswer(event: MessageEvent):
    chosen = event.payload.get("era")
    await event.send_message(await getWiki(pick_question(chosen)["correct"]))
async def medievalAnswer(event: MessageEvent):
    chosen = event.payload.get("era")
    await event.send_message(await getWiki(pick_question(chosen)["correct"]))

async def modernAnswer(event: MessageEvent):
    chosen = event.payload.get("era")
    await event.send_message(await getWiki(pick_question(chosen)["correct"]))

async def allAnswer(event: MessageEvent):
    chosen = event.payload.get("era")
    await event.send_message(chosen)

def pick_question(era: str) -> dict:
    # 1. Определяем, из каких эр брать вопрос
    if era == "all":
        available_eras = ["ancient", "medieval", "modern"]
        chosen_era = random.choice(available_eras)
    elif era in ERAS:
        chosen_era = era
    else:
        raise ValueError(f"Неизвестная эра: {era}. Допустимо: ancient, medieval, modern, all")

    # 2. Случайно выбираем категорию
    categories = list(ERAS[chosen_era].keys())  # ["persons", "events", "states"]
    chosen_category = random.choice(categories)

    pool = ERAS[chosen_era][chosen_category]

    # 3. Выбираем правильный ответ
    correct = random.choice(pool)

    # 4. Выбираем 3 неправильных варианта из того же пула
    wrong_candidates = [item for item in pool if item != correct]
    wrong_options = random.sample(wrong_candidates, min(3, len(wrong_candidates)))

    # 5. Собираем все 4 варианта и перемешиваем
    options = [correct] + wrong_options
    random.shuffle(options)

    return {
        "correct": correct,
        "options": options,
        "era": chosen_era,
        "category": chosen_category,
    }

ERAS = {
    "ancient": {
        "persons": [
            "Тутанхамон",
            "Александр Македонский",
            "Юлий Цезарь",
            "Ганнибал",
            "Спартак",
            "Солон",
            "Перикл",
            "Дарий I",
            "Клеопатра VII",
            "Октавиан Август",
        ],
        "events": [
            "Битва при Марафоне",
            "Греко-персидские войны",
            "Пунические войны",
            "Падение Западной Римской империи",
            "Пелопоннесская война",
            "Битва при Каррах",
            "Кризис Римской империи III века",
            "Реформы Солона",
            "Завоевание Галлии Цезарем",
            "Восстание Спартака",
        ],
        "states": [
            "Древний Египет",
            "Древний Вавилон",
            "Древняя Греция",
            "Спарта",
            "Древний Рим",
            "Римская республика",
            "Римская империя",
            "Держава Ахеменидов",
            "Династия Птолемеев",
            "Ассирийская империя",
        ],
    },
    "medieval": {
        "persons": [
            "Карл Великий",
            "Салах ад-Дин",
            "Жанна д'Арк",
            "Чингисхан",
            "Иван III",
            "Александр Невский",
            "Дмитрий Донской",
            "Вильгельм Завоеватель",
            "Ян Гус",
            "Тамерлан",
        ],
        "events": [
            "Крестовые походы",
            "Чёрная смерть",
            "Битва на Косовом поле",
            "Монгольское нашествие на Русь",
            "Ледовое побоище",
            "Куликовская битва",
            "Падение Константинополя",
            "Реконкиста",
            "Альбигойский крестовый поход",
            "Гуситские войны",
            "Война Алой и Белой розы",
            "Борьба за инвеституру",
            "Столетняя война",
            "Великая хартия вольностей",
        ],
        "states": [
            "Франкское государство",
            "Византийская империя",
            "Арабский халифат",
            "Империя Каролингов",
            "Латинская империя",
            "Никейская империя",
            "Золотая Орда",
            "Священная Римская империя",
            "Тамплиеры",
            "Ганза",
        ],
    },
    "modern": {
        "persons": [
            "Колумб",
            "Магеллан",
            "Мартин Лютер",
            "Леонардо да Винчи",
            "Людовик XIV",
            "Оливер Кромвель",
            "Пётр I",
            "Екатерина II",
            "Наполеон Бонапарт",
            "Отто фон Бисмарк",
            "Джордж Вашингтон",
            "Карл Маркс",
        ],
        "events": [
            "Великие географические открытия",
            "Реформация",
            "Английская революция",
            "Славная революция",
            "Война за независимость США",
            "Французская революция",
            "Венский конгресс",
            "Промышленный переворот",
            "Тридцатилетняя война",
            "Война за испанское наследство",
            "Семилетняя война",
            "Разделы Речи Посполитой",
            "Континентальная блокада",
            "Гражданская война в США",
            "Объединение Германии",
        ],
        "states": [
            "Речь Посполитая",
            "Абсолютизм",
            "Возрождение",
            "Священный союз",
            "Вестфальская система",
            "Нидерландская революция",
            "Российская империя",
            "Британская империя",
            "Османская империя",
            "Пруссия",
        ],
    },
}