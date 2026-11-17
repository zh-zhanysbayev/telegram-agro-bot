import asyncio
import logging
import os
import random
import subprocess

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from dotenv import load_dotenv

AGENTS_DIR = r"D:\!Working\living-soil-case"
CLAUDE_TIMEOUT = 180
ALLOWED_TOOLS = "Task,Read,Write"
MAX_MESSAGE_LEN = 4000

FACTS = [
    "🌱 В одной чайной ложке здорового почвенного слоя живёт больше микроорганизмов, чем людей на Земле.",
    "🍄 Микоризные грибы соединяют корни растений в «лесной интернет» и передают питательные вещества и сигналы.",
    "🍺 Хмель — многолетняя лиана: за сезон она может вырасти на 6–8 метров, до 10 см в сутки.",
    "🪱 Дождевые черви могут переработать до 30 тонн почвы на гектар в год, улучшая её структуру и аэрацию.",
    "🍄 Мицелий гриба — одна из крупнейших живых структур: опёнок в Орегоне занимает около 9 км².",
    "🤝 Микориза есть примерно у 80–90% наземных растений: гриб даёт воду и фосфор, растение — сахара.",
    "🫘 Бобовые вместе с клубеньковыми бактериями (ризобиями) фиксируют азот из воздуха и обогащают им почву.",
    "⚡ Часть азота в почву попадает даже от молний: они превращают атмосферный азот в доступные растениям нитраты.",
    "☀️ При фотосинтезе растения отдают корням до 30–40% произведённых сахаров, подкармливая почвенную микрофлору.",
    "🌿 Гломалин — белок микоризных грибов: он «склеивает» частицы почвы в устойчивые комочки и хранит углерод.",
    "🍺 Шишки хмеля содержат лупулин — желтоватые железки с горькими кислотами и эфирными маслами для пива.",
    "🌱 Хмель вьётся строго по часовой стрелке, а на плантациях его направляют по шпалерам высотой до 7 м.",
    "🧫 Почвенные актиномицеты придают земле характерный запах после дождя — его создаёт вещество геосмин.",
    "🍂 Для образования 1 см плодородной почвы в природе нужны сотни лет, а смыть её можно за один сезон.",
    "🍄 Грибы — не растения: они ближе к животным и питаются, разлагая органику и выделяя ферменты.",
]

QUESTIONS = {
    "culture": "1/5. 🌿 Какая культура? (например: хмель, томаты, вешенка)",
    "conditions": "2/5. 🏡 Условия выращивания? (открытый грунт, теплица, субстрат, тип почвы…)",
    "climate": "3/5. 🌡 Температура и влажность?",
    "symptoms": "4/5. 🔍 Какие симптомы или проблемы вы наблюдаете?",
    "actions": "5/5. 🛠 Что вы делали за последние 2 недели? (полив, подкормки, обработки…)",
}

router = Router()


class Survey(StatesGroup):
    culture = State()
    conditions = State()
    climate = State()
    symptoms = State()
    actions = State()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="Задать вопрос", callback_data="ask")]]
    )
    await message.answer(
        "Привет! 👋 Я бот-консилиум по живой почве, грибам и хмелю.\n"
        "Отвечу на несколько вопросов — и передам их команде советников.\n\n"
        "/fact — случайный факт",
        reply_markup=keyboard,
    )


@router.message(Command("fact"))
async def cmd_fact(message: Message) -> None:
    await message.answer(random.choice(FACTS))


@router.callback_query(F.data == "ask")
async def start_survey(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.set_state(Survey.culture)
    await callback.message.answer(QUESTIONS["culture"])


@router.message(Survey.culture, F.text)
async def step_culture(message: Message, state: FSMContext) -> None:
    await state.update_data(culture=message.text)
    await state.set_state(Survey.conditions)
    await message.answer(QUESTIONS["conditions"])


@router.message(Survey.conditions, F.text)
async def step_conditions(message: Message, state: FSMContext) -> None:
    await state.update_data(conditions=message.text)
    await state.set_state(Survey.climate)
    await message.answer(QUESTIONS["climate"])


@router.message(Survey.climate, F.text)
async def step_climate(message: Message, state: FSMContext) -> None:
    await state.update_data(climate=message.text)
    await state.set_state(Survey.symptoms)
    await message.answer(QUESTIONS["symptoms"])


@router.message(Survey.symptoms, F.text)
async def step_symptoms(message: Message, state: FSMContext) -> None:
    await state.update_data(symptoms=message.text)
    await state.set_state(Survey.actions)
    await message.answer(QUESTIONS["actions"])


@router.message(Survey.actions, F.text)
async def step_actions(message: Message, state: FSMContext) -> None:
    await state.update_data(actions=message.text)
    data = await state.get_data()
    await state.clear()

    await message.answer("⏳ Собираю консилиум советников...")
    query = build_query(data)

    try:
        result = await asyncio.to_thread(run_claude, query)
    except subprocess.TimeoutExpired:
        await message.answer(f"❌ Консилиум не уложился в {CLAUDE_TIMEOUT} секунд. Попробуйте ещё раз.")
        return
    except FileNotFoundError:
        await message.answer("❌ Команда `claude` не найдена. Проверьте установку Claude Code.")
        return

    if result.returncode != 0:
        error = result.stderr.strip() or "неизвестная ошибка"
        await message.answer(f"❌ Ошибка (код {result.returncode}):\n{error[:MAX_MESSAGE_LEN]}")
        return

    output = result.stdout.strip() or "Пустой ответ от системы."
    for chunk in split_text(output):
        await message.answer(chunk)


def build_query(data: dict) -> str:
    return (
        "Проведи консилиум советников по ситуации пользователя.\n"
        f"Культура: {data['culture']}\n"
        f"Условия выращивания: {data['conditions']}\n"
        f"Температура/влажность: {data['climate']}\n"
        f"Симптомы: {data['symptoms']}\n"
        f"Действия за последние 2 недели: {data['actions']}"
    )


def run_claude(query: str) -> subprocess.CompletedProcess:
    # cwd — папка с агентами и CLAUDE.md, чтобы Claude Code увидел их
    return subprocess.run(
        ["claude", "-p", query, "--allowedTools", ALLOWED_TOOLS],
        cwd=AGENTS_DIR,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=CLAUDE_TIMEOUT,
    )


def split_text(text: str, size: int = MAX_MESSAGE_LEN) -> list[str]:
    return [text[i : i + size] for i in range(0, len(text), size)]


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    load_dotenv()
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise SystemExit("TELEGRAM_BOT_TOKEN не задан в .env")

    bot = Bot(token=token)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
