import logging
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from database import init_db, get_player, create_player, update_player, update_resources
from game_logic import ARTIFACT_NAMES, get_artifact_levels, set_artifact_levels, get_artifact_info, get_upgrade_cost, calculate_passive_income
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Основная клавиатура внизу
MAIN_KEYBOARD = [
    ["Артефакты 🪬", "Персонаж 👤", "Хранилище 📥"],
    ["Данж 🌋", "Арена 🏟️", "Клан 🛡️"],
    ["Магазин 🏪", "Обсерватория 🔬"],
    ["Рыбалка 🎣", "Охота 🏹", "Путешествие 🏃‍♂️"],
    ["Топ 👑", "Обновить 🔄", "Настройки ⚙️"]
]

REPLY_MARKUP = ReplyKeyboardMarkup(MAIN_KEYBOARD, resize_keyboard=True, one_time_keyboard=False)

# Хранилище времени последнего обновления для каждого игрока
last_income_update = {}

async def passive_income_job(context: ContextTypes.DEFAULT_TYPE):
    """Фоновая задача для пассивного дохода через JobQueue"""
    global last_income_update
    try:
        conn = sqlite3.connect('game.db')
        c = conn.cursor()
        c.execute("SELECT user_id, artifact_levels FROM players")
        players = c.fetchall()
        conn.close()

        now = datetime.utcnow().timestamp()
        for (user_id, levels_str) in players:
            levels = get_artifact_levels(levels_str)
            income = calculate_passive_income(levels)

            last_time = last_income_update.get(user_id, now)
            elapsed = now - last_time
            if elapsed < 1:
                continue

            add_coins = income['coins'] * elapsed
            add_dust = income['magic_dust'] * elapsed
            add_guns = income['guns'] * elapsed
            add_parts = income['artifact_parts'] * elapsed

            update_resources(user_id, add_coins, add_parts, add_dust, add_guns)
            last_income_update[user_id] = now

    except Exception as e:
        logger.error(f"Ошибка в passive_income_job: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not get_player(user.id):
        await update.message.reply_text(
            "Приветствую тебя, странник! Добро пожаловать в игру Hero Saga! Назовись:",
            reply_markup=ReplyKeyboardMarkup([["Отмена"]], resize_keyboard=True)
        )
        context.user_data['awaiting_name'] = True
    else:
        await update.message.reply_text("Главное меню:", reply_markup=REPLY_MARKUP)

async def handle_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('awaiting_name'):
        if update.message.text == "Отмена":
            del context.user_data['awaiting_name']
            await update.message.reply_text("Регистрация отменена.", reply_markup=REPLY_MARKUP)
            return

        username = update.message.text.strip()
        if len(username) < 2 or len(username) > 20:
            await update.message.reply_text("Имя должно быть от 2 до 20 символов. Назовись:")
            return

        create_player(update.effective_user.id, username)
        del context.user_data['awaiting_name']
        await update.message.reply_text(
            f"Добро пожаловать, {username}! 🌟\n\n"
            "🎮 Это Idle-игра. Ты будешь получать ресурсы даже когда не в сети!\n"
            "🎣 Рыбалка, 🏹 Охота и 🏃‍♂️ Путешествие дают ресурсы и артефакты.\n"
            "🪬 Улучшай артефакты, чтобы увеличить доход!\n"
            "💥 Сражайся в Данже и на Арене!\n"
            "🛡️ Объединяйся в кланы для бонусов!\n\n"
            "Выбери действие в меню ниже 👇",
            reply_markup=REPLY_MARKUP
        )

async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id

    if not get_player(user_id):
        await update.message.reply_text("Сначала зарегистрируйся через /start")
        return

    if text == "Артефакты 🪬":
        await show_artifacts_list(update, context)
    elif text == "Персонаж 👤":
        await show_character(update, context)
    elif text == "Хранилище 📥":
        await update.message.reply_text("Хранилище пока пусто. Собирай предметы!", reply_markup=REPLY_MARKUP)
    elif text in ["Данж 🌋", "Арена 🏟️", "Клан 🛡️", "Магазин 🏪", "Обсерватория 🔬",
                  "Рыбалка 🎣", "Охота 🏹", "Путешествие 🏃‍♂️", "Топ 👑", "Настройки ⚙️"]:
        await update.message.reply_text(f"Раздел «{text}» находится в разработке ⚙️", reply_markup=REPLY_MARKUP)
    elif text == "Обновить 🔄":
        await update.message.reply_text("Данные обновлены!", reply_markup=REPLY_MARKUP)
    else:
        await update.message.reply_text("Неизвестная команда.", reply_markup=REPLY_MARKUP)

async def show_artifacts_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    player = get_player(user_id)
    levels = get_artifact_levels(player[11])

    text = "Ваши артефакты:\n" + "\n".join([f"{ARTIFACT_NAMES[i]} — Уровень {levels[i]}" for i in range(8)])

    buttons = [
        InlineKeyboardButton(ARTIFACT_NAMES[i], callback_data=f"artifact_{i}")
        for i in range(len(ARTIFACT_NAMES))
    ]
    keyboard = [buttons[i:i+2] for i in range(0, len(buttons), 2)]
    keyboard.append([InlineKeyboardButton("⬅️ Назад в меню", callback_data="back_to_main")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(text, reply_markup=reply_markup)

async def show_character(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    player = get_player(user_id)
    text = (
        f"👤 {player[1]}\n\n"
        f"🪙 Золото: {player[2]:,}\n"
        f"⚱️ Части артефактов: {player[3]:,}\n"
        f"✨ Магическая пыль: {player[4]:,}\n"
        f"🔫 Самопалы: {player[5]:,}\n"
        f"💷 Эфирная валюта: {player[6]:,}\n\n"
        f"👊 Сила: {player[7]}\n"
        f"🔫 Хитрость: {player[8]}\n"
        f"🧠 Ум: {player[9]}"
    )
    await update.message.reply_text(text, reply_markup=REPLY_MARKUP)

async def inline_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "back_to_main":
        await query.message.delete()
        await query.message.reply_text("Главное меню:", reply_markup=REPLY_MARKUP)
        return

    if data.startswith("artifact_"):
        artifact_id = int(data.split("_")[1])
        await show_artifact_detail(update, context, artifact_id)
    elif data.startswith("upgrade_"):
        await upgrade_artifact(update, context)
    elif data.startswith("back_artifact_"):
        artifact_id = int(data.split("_")[2])
        await show_artifact_detail(update, context, artifact_id)

async def show_artifact_detail(update: Update, context: ContextTypes.DEFAULT_TYPE, artifact_id: int):
    user_id = update.effective_user.id
    player = get_player(user_id)
    levels = get_artifact_levels(player[11])
    level = levels[artifact_id]
    info = get_artifact_info(artifact_id, level)
    cost = get_upgrade_cost(level)

    keyboard = [
        [InlineKeyboardButton("Улучшить", callback_data=f"upgrade_{artifact_id}")],
        [InlineKeyboardButton("Обновить", callback_data=f"back_artifact_{artifact_id}"),
         InlineKeyboardButton("⬅️ Назад", callback_data="back_to_main")]
    ]
    if artifact_id == 3:  # Кинжал
        keyboard[0].append(InlineKeyboardButton("Распределить хар-ки", callback_data="distribute"))

    reply_markup = InlineKeyboardMarkup(keyboard)
    cost_text = f"\n\nСтоимость улучшения:\n🪙 {cost['coins']:,}\n⚱️ {cost['artifact_parts']:,}\n✨ {cost['magic_dust']:,}"
    full_text = info + cost_text

    if update.callback_query:
        await update.callback_query.edit_message_text(full_text, reply_markup=reply_markup)
    else:
        await update.message.reply_text(full_text, reply_markup=reply_markup)

async def upgrade_artifact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    artifact_id = int(query.data.split("_")[1])
    user_id = update.effective_user.id
    player = get_player(user_id)
    levels = get_artifact_levels(player[11])
    level = levels[artifact_id]
    cost = get_upgrade_cost(level)

    if player[2] < cost['coins'] or player[3] < cost['artifact_parts'] or player[4] < cost['magic_dust']:
        await query.answer("❌ Недостаточно ресурсов!", show_alert=True)
        return

    new_coins = player[2] - cost['coins']
    new_parts = player[3] - cost['artifact_parts']
    new_dust = player[4] - cost['magic_dust']
    levels[artifact_id] += 1
    new_levels = set_artifact_levels(levels)

    update_player(user_id,
                  coins=new_coins,
                  artifact_parts=new_parts,
                  magic_dust=new_dust,
                  artifact_levels=new_levels)

    await query.answer("✅ Артефакт улучшен!", show_alert=True)
    await show_artifact_detail(update, context, artifact_id)

def main():
    init_db()
    app = Application.builder().token("ВАШ_ТОКЕН_СЮДА").build()

    # Регистрируем фоновую задачу каждые 10 секунд
    app.job_queue.run_repeating(passive_income_job, interval=10, first=10)

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_name))
    app.add_handler(MessageHandler(filters.Regex("^(" + "|".join(
        [btn for row in MAIN_KEYBOARD for btn in row]
    ) + ")$"), menu_handler))
    app.add_handler(CallbackQueryHandler(inline_button_handler))

    logger.info("Бот запущен! (Termux OK) | Пассивный доход каждые 10 сек")
    app.run_polling()

if __name__ == '__main__':
    main()