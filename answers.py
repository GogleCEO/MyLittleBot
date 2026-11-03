import asyncio
import random
import requests
from vkbottle import Keyboard, KeyboardButtonColor, Text, PhotoMessageUploader, Callback
from vkbottle.bot import Bot, Message, MessageEvent
from vkbottle import BaseStateGroup
from vkbottle import GroupEventType
import wikipediaapi
import aiohttp
import ssl
import certifi
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

HEADERS = {
    "User-Agent": "VKHistoryQuizBot/1.0 (https://vk.com/club242874185; qwerty@gmail.com)"
}
def get_page_image(title: str, lang: str = "ru") -> str | None:
    """Возвращает URL основного изображения страницы или None."""
    url = f"https://{lang}.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "titles": title,
        "prop": "pageimages",
        "piprop": "thumbnail",  # запрашиваем миниатюру
        "pithumbsize": 500,  # ширина в пикселях
        "format": "json",
    }
    resp = requests.get(url, params=params, headers=HEADERS, timeout=10)
    resp.raise_for_status()  # лучше явно обработать 403
    data = resp.json()

    pages = data.get("query", {}).get("pages", {})
    for page_id, page_data in pages.items():
        if "thumbnail" in page_data:
            return page_data["thumbnail"]["source"]
    return None

async def upload_image_from_url(uploader, peer_id: int, image_url: str) -> str:
    """Скачивает картинку по URL и загружает её в VK."""
    ssl_context = ssl.create_default_context(cafile=certifi.where())
    connector = aiohttp.TCPConnector(ssl=ssl_context)

    async with aiohttp.ClientSession(connector=connector) as session:
        # 👇 Добавляем headers в запрос
        async with session.get(image_url, headers=HEADERS) as resp:
            resp.raise_for_status()
            image_bytes = await resp.read()

    attachment = await uploader.upload(image_bytes, peer_id=peer_id)
    return attachment

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
            "Хаммурапи",
            "Рамсес II",
            "Леонид I",
            "Фемистокл",
            "Аристотель",
            "Платон",
            "Марк Аврелий",
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
            "Битва при Фермопилах",
            "Битва при Саламине",
            "Завоевания Александра Македонского",
            "Реформы братьев Гракхов",
            "Гражданская война в Риме",
            "Битва при Акциуме",
            "Основание Рима",
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
            "Древняя Македония",
            "Персидская империя",
            "Хеттское царство",
            "Финикия",
            "Карфаген",
            "Микенская цивилизация",
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
            "Юстиниан I",
            "Карл Мартелл",
            "Оттон I",
            "Фридрих Барбаросса",
            "Ричард Львиное Сердце",
            "Саладин",
            "Ян Жижка",
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
            "Битва при Пуатье",
            "Битва при Гастингсе",
            "Первый крестовый поход",
            "Осада Иерусалима",
            "Битва на Чудском озере",
            "Великая схизма",
            "Падение Гранады",
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
            "Киевская Русь",
            "Новгородская республика",
            "Великое княжество Литовское",
            "Империя Карла Великого",
            "Арабский халифат",
            "Османская империя",
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
            "Иван Грозный",
            "Богдан Хмельницкий",
            "Оливер Кромвель",
            "Джордж Вашингтон",
            "Максимилиан Робеспьер",
            "Михаил Кутузов",
            "Александр Суворов",
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
            "Открытие Америки",
            "Кругосветное плавание Магеллана",
            "Варфоломеевская ночь",
            "Битва при Лепанто",
            "Осада Троице-Сергиевой лавры",
            "Полтавская битва",
            "Бородинское сражение",
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
            "Московское царство",
            "Габсбургская монархия",
            "Испанская империя",
            "Королевство Франция",
            "Английское королевство",
            "Речь Посполитая",
        ],
    },
}