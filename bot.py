import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from database import init_db, get_player, create_player, update_player
from game_logic import ARTIFACT_NAMES, get_artifact_levels, set_artifact_levels, get_artifact_info, get_upgrade_cost
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Главное меню
MAIN_MENU = [
    ["Артефакты 🪬", "Персонаж 👤", "Хранилище 📥"],
    ["Данж 🌋", "Арена 🏟️", "Клан 🛡️"],
    ["Магазин 🏪", "Обсерватория 🔬"],
    ["Рыбалка 🎣", "Охота 🏹", "Путешествие 🏃‍♂️"],
    ["Топ 👑", "Обновить 🔄", "Настройки ⚙️"]
]

def build_menu(buttons, n_cols=3, back_button=None):
    menu = [buttons[i:i + n_cols] for i in range(0, len(buttons), n_cols)]
    if back_button:
        menu.append([back_button])
    return menu

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not get_player(user.id):
        await update.message.reply_text(
            "Приветствую тебя, странник! Добро пожаловать в игру Hero Saga! Назовись:"
        )
        context.user_data['awaiting_name'] = True
    else:
        await show_main_menu(update, context)

async def handle_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('awaiting_name'):
        username = update.message.text.strip()
        if len(username) < 2:
            await update.message.reply_text("Имя должно быть от 2 символов. Назовись:")
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
            "Нажми на любую кнопку ниже, чтобы начать!"
        )
        await show_main_menu(update, context)

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = build_menu(
        [InlineKeyboardButton(text, callback_data=f"menu_{text.split()[0]}") for row in MAIN_MENU for text in row]
    )
    reply_markup = InlineKeyboardMarkup(keyboard)
    if update.callback_query:
        await update.callback_query.edit_message_text("Главное меню:", reply_markup=reply_markup)
    else:
        await update.message.reply_text("Главное меню:", reply_markup=reply_markup)

# Артефакты
async def show_artifacts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    player = get_player(user_id)
    if not player:
        await update.callback_query.answer("Сначала зарегистрируйся!")
        return

    levels = get_artifact_levels(player[11])
    buttons = [
        InlineKeyboardButton(ARTIFACT_NAMES[i], callback_data=f"artifact_{i}")
        for i in range(len(ARTIFACT_NAMES))
    ]
    keyboard = build_menu(buttons, n_cols=2, back_button=InlineKeyboardButton("Вернуться на главную ⬅️", callback_data="main_menu"))
    reply_markup = InlineKeyboardMarkup(keyboard)

    text = "Ваши артефакты:\n" + "\n".join([f"{ARTIFACT_NAMES[i]} — Уровень {levels[i]}" for i in range(8)])
    await update.callback_query.edit_message_text(text, reply_markup=reply_markup)

# Информация об артефакте
async def show_artifact_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    artifact_id = int(query.data.split('_')[1])
    user_id = update.effective_user.id
    player = get_player(user_id)
    levels = get_artifact_levels(player[11])
    level = levels[artifact_id]

    info = get_artifact_info(artifact_id, level)
    cost = get_upgrade_cost(level)

    keyboard = [
        [InlineKeyboardButton("Улучшить", callback_data=f"upgrade_{artifact_id}")],
        [InlineKeyboardButton("Обновить", callback_data=f"artifact_{artifact_id}"),
         InlineKeyboardButton("Назад", callback_data="artifacts")]
    ]
    if artifact_id == 3:  # Кинжал — добавить распределение
        keyboard[0].append(InlineKeyboardButton("Распределить хар-ки", callback_data="distribute"))

    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(info + f"\n\nСтоимость улучшения:\n🪙 {cost['coins']}\n⚱️ {cost['artifact_parts']}\n✨ {cost['magic_dust']}", reply_markup=reply_markup)

# Улучшение артефакта
async def upgrade_artifact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    artifact_id = int(query.data.split('_')[1])
    user_id = update.effective_user.id
    player = get_player(user_id)
    levels = get_artifact_levels(player[11])
    level = levels[artifact_id]
    cost = get_upgrade_cost(level)

    if player[2] < cost['coins'] or player[3] < cost['artifact_parts'] or player[4] < cost['magic_dust']:
        await query.answer("Недостаточно ресурсов!", show_alert=True)
        return

    # Списываем ресурсы
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

    await query.answer("Артефакт улучшен!", show_alert=True)
    await show_artifact_detail(update, context)

# Персонаж
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
    keyboard = [
        [InlineKeyboardButton("Обновить", callback_data="character"),
         InlineKeyboardButton("Назад", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.edit_message_text(text, reply_markup=reply_markup)

# Обработчик кнопок
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data

    if data == "main_menu":
        await show_main_menu(update, context)
    elif data == "artifacts":
        await show_artifacts(update, context)
    elif data.startswith("artifact_"):
        await show_artifact_detail(update, context)
    elif data.startswith("upgrade_"):
        await upgrade_artifact(update, context)
    elif data == "character":
        await show_character(update, context)
    else:
        await query.edit_message_text(f"Раздел '{data}' пока в разработке ⚙️")

# Инициализация
def main():
    init_db()
    app = Application.builder().token("ВАШ_ТОКЕН_БОТА").build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_name))
    app.add_handler(CallbackQueryHandler(button_handler))

    logger.info("Бот запущен!")
    app.run_polling()

if __name__ == '__main__':
    main()
