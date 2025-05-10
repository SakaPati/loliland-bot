import logging
import asyncio
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler, ConversationHandler, MessageHandler, filters

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Конфигурация
TELEGRAM_TOKEN = "7311382986:AAESbiY4oydyxpsn_xTX7eYkE2blhFbj36w"
ALLOWED_USER_IDS = [1892554531]

# Словарь серверов
SERVERS = {
    'TechnoMagicRPG': 'TechnoMagic RPG',
    'HiTech': 'HiTech',
    'UltraTech': 'UltraTech',
    'MagicRPG': 'Magic RPG',
    'DarkMagic': 'DarkMagic',
    'MysteryMagic': 'MysteryMagic',
    'TechnoWizardry': 'TechnoWizardry',
    'TechnoMagicSKY': 'TechnoMagic SKY',
    'SpaceX': 'SpaceX',
    'FantasyTechRPG': 'FantasyTech RPG',
    'PixelMon': 'PixelMon'
}

# Состояния для ConversationHandler
SELECT_MODE, ENTER_NICKNAME = range(2)

# Очередь задач (пока просто логируем команды)
task_queue = asyncio.Queue()

async def check_user_access(update: Update) -> bool:
    user_id = update.effective_user.id
    if user_id not in ALLOWED_USER_IDS:
        await update.message.reply_text("🚫 Доступ запрещен")
        logger.warning(f"Попытка доступа от {user_id}")
        return False
    return True

async def process_queue():
    while True:
        if task_queue.empty():
            await asyncio.sleep(1)
            continue
        
        user_id, server, nickname, context = await task_queue.get()
        task_id = f"User_{user_id}_Server_{server}"
        logger.info(f"Обрабатываю задачу из очереди для {task_id}: отправка /tpa {nickname} на сервер {server}")
        
        # Здесь можно добавить вызов локального скрипта для автоматизации
        await context.bot.send_message(chat_id=user_id, text=f"✅ Команда /tpa {nickname} будет отправлена на сервер {server}.")
        
        task_queue.task_done()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_user_access(update):
        return
    await update.message.reply_text(
        "🤖 Бот управления LoliLand\n"
        "Доступные команды:\n"
        "/login - Подключиться к серверу\n"
    )

async def login_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_user_access(update):
        return ConversationHandler.END
    
    # Отправляем сообщение с кнопками для выбора режима
    keyboard = [
        [
            InlineKeyboardButton("TechnoMagic RPG", callback_data="/TechnoMagicRPG"),
            InlineKeyboardButton("HiTech", callback_data="/HiTech"),
            InlineKeyboardButton("UltraTech", callback_data="/UltraTech"),
        ],
        [
            InlineKeyboardButton("Magic RPG", callback_data="/MagicRPG"),
            InlineKeyboardButton("DarkMagic", callback_data="/DarkMagic"),
            InlineKeyboardButton("MysteryMagic", callback_data="/MysteryMagic"),
        ],
        [
            InlineKeyboardButton("TechnoWizardry", callback_data="/TechnoWizardry"),
            InlineKeyboardButton("TechnoMagic SKY", callback_data="/TechnoMagicSKY"),
            InlineKeyboardButton("SpaceX", callback_data="/SpaceX"),
        ],
        [
            InlineKeyboardButton("FantasyTech RPG", callback_data="/FantasyTechRPG"),
            InlineKeyboardButton("PixelMon", callback_data="/PixelMon"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    logger.info(f"Отправляю сообщение с кнопками для пользователя {update.effective_user.id}")
    await update.message.reply_text("Выберите режим:", reply_markup=reply_markup)
    return SELECT_MODE

async def select_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_user_access(update):
        return ConversationHandler.END
    
    query = update.callback_query
    await query.answer()
    command = query.data
    server = command[1:]  # Удаляем слэш из callback_data
    context.user_data['server'] = server  # Сохраняем выбранный режим
    await query.edit_message_text(text=f"Вы выбрали {SERVERS[server]}. Теперь введите ник игрока (например, PaXoLoM_):")
    
    return ENTER_NICKNAME

async def enter_nickname(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_user_access(update):
        return ConversationHandler.END
    
    nickname = update.message.text.strip()
    server = context.user_data.get('server')
    
    await update.message.reply_text(f"🔄 Вы добавлены в очередь для подключения к {SERVERS[server]} и отправки /tpa {nickname}...")
    
    # Добавляем задачу в очередь
    task_queue.put_nowait((update.effective_user.id, server, nickname, context))
    
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Процесс подключения отменен.")
    return ConversationHandler.END

async def main():
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Настройка ConversationHandler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("login", login_command)],
        states={
            SELECT_MODE: [CallbackQueryHandler(select_mode)],
            ENTER_NICKNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_nickname)]
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(conv_handler)
    
    # Запускаем фоновую задачу для обработки очереди
    asyncio.create_task(process_queue())
    
    # Настройка Webhook
    PORT = int(os.environ.get("PORT", 8443))
    WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "https://loliland-bot.onrender.com")
    if not WEBHOOK_URL:
        raise ValueError("WEBHOOK_URL environment variable not set")
    
    webhook_url = f"{WEBHOOK_URL}/{TELEGRAM_TOKEN}"
    await application.bot.set_webhook(url=webhook_url)
    logger.info(f"Webhook установлен: {webhook_url}")
    
    await application.initialize()
    await application.start()
    await application.updater.start_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=TELEGRAM_TOKEN,
        webhook_url=webhook_url
    )
    
    logger.info("Бот запущен")
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Остановка бота")
    except Exception as e:
        logger.error(f"Фатальная ошибка: {str(e)}")