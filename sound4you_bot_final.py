import os
import json
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ConversationHandler, filters, ContextTypes
from telegram.constants import ParseMode
import logging

# Логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Константы
BOT_TOKEN = os.getenv('BOT_TOKEN', 'YOUR_BOT_TOKEN_HERE')
ADMIN_ID = int(os.getenv('ADMIN_ID', '0'))
COMMISSION_PERCENT = 10

# JSON файлы
USERS_FILE = 'users.json'
PRODUCTS_FILE = 'products.json'
SERVICES_FILE = 'services.json'
TRANSACTIONS_FILE = 'transactions.json'
RIGHTS_FILE = 'rights.json'  # Авторские права

# Состояния
ADDING_PRODUCT = 1
PRODUCT_NAME = 2
PRODUCT_PRICE = 3
PRODUCT_DEMO = 4
PRODUCT_RIGHTS = 5
ADDING_SERVICE = 10
SERVICE_NAME = 11
SERVICE_DESC = 12
SERVICE_PRICE = 13

# Красивые эмодзи для бренда
LOGO = "🎵"
MARKETPLACE_HEADER = "🏪"
PROFILE_HEADER = "👤"
SERVICES_HEADER = "🎚️"

# ============ ФУНКЦИИ РАБОТЫ С ДАННЫМИ ============

def load_json(filename):
    if os.path.exists(filename):
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {} if filename != TRANSACTIONS_FILE else []

def save_json(filename, data):
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_user_data(user_id):
    users = load_json(USERS_FILE)
    user_id_str = str(user_id)
    
    if user_id_str not in users:
        users[user_id_str] = {
            'username': '',
            'balance': 0,
            'total_earned': 0,
            'total_spent': 0,
            'products_count': 0,
            'verified': False,
            'created_at': datetime.now().isoformat()
        }
        save_json(USERS_FILE, users)
    
    return users[user_id_str]

def add_balance(user_id, amount, reason=""):
    users = load_json(USERS_FILE)
    user_id_str = str(user_id)
    
    if user_id_str not in users:
        get_user_data(user_id)
        users = load_json(USERS_FILE)
    
    users[user_id_str]['balance'] += amount
    if amount > 0:
        users[user_id_str]['total_earned'] += amount
    save_json(USERS_FILE, users)
    
    transactions = load_json(TRANSACTIONS_FILE)
    transactions.append({
        'user_id': user_id,
        'amount': amount,
        'reason': reason,
        'timestamp': datetime.now().isoformat(),
        'balance_after': users[user_id_str]['balance']
    })
    save_json(TRANSACTIONS_FILE, transactions)

def verify_copyright(product_id, user_id):
    """Проверить авторские права"""
    rights = load_json(RIGHTS_FILE)
    
    if product_id not in rights:
        return {'verified': False, 'message': 'Права не проверены'}
    
    right = rights[product_id]
    
    if right['owner_id'] != user_id:
        return {'verified': False, 'message': 'Вы не владелец этого произведения'}
    
    if right['status'] == 'verified':
        return {'verified': True, 'message': '✅ Авторские права подтверждены'}
    
    return {'verified': False, 'message': 'Права на модерации'}

def register_copyright(product_id, user_id, product_name):
    """Зарегистрировать авторские права"""
    rights = load_json(RIGHTS_FILE)
    
    rights[product_id] = {
        'product_name': product_name,
        'owner_id': user_id,
        'status': 'pending',  # pending, verified, disputed
        'created_at': datetime.now().isoformat(),
        'hash': f"SOUND4YOU_{product_id}_{user_id}_{datetime.now().timestamp()}"
    }
    
    save_json(RIGHTS_FILE, rights)
    return rights[product_id]['hash']

# ============ КРАСИВЫЕ СООБЩЕНИЯ ============

def get_main_menu_keyboard():
    keyboard = [
        [KeyboardButton(f"🏪 МАРКЕТПЛЕЙС"), KeyboardButton(f"👤 МОЙ ПРОФИЛЬ")],
        [KeyboardButton(f"📤 ПРОДАТЬ"), KeyboardButton(f"🎚️ УСЛУГИ")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

def get_welcome_message():
    return (
        f"╭─────────────────────────╮\n"
        f"│  {LOGO} <b>SOUND4YOU</b> {LOGO}  │\n"
        f"│  Маркетплейс Звука     │\n"
        f"╰─────────────────────────╯\n\n"
        f"🎉 <b>Добро пожаловать!</b>\n\n"
        f"Здесь ты можешь:\n"
        f"✅ Купить и продать биты\n"
        f"✅ Заказать услуги (сведение, мастеринг)\n"
        f"✅ Обложки для релизов\n"
        f"✅ Защита авторских прав\n\n"
        f"💰 <b>Комиссия: 10%</b>\n"
        f"🔒 <b>Проверка авторских прав</b>\n"
        f"⚡ <b>Быстрые платежи</b>\n\n"
        f"Выбери действие 👇"
    )

# ============ КОМАНДЫ ПОЛЬЗОВАТЕЛЯ ============

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start"""
    user_id = update.effective_user.id
    user = get_user_data(user_id)
    
    if not user.get('username'):
        user['username'] = update.effective_user.username or 'Unknown'
        users = load_json(USERS_FILE)
        users[str(user_id)] = user
        save_json(USERS_FILE, users)
    
    await update.message.reply_text(
        get_welcome_message(),
        reply_markup=get_main_menu_keyboard(),
        parse_mode=ParseMode.HTML
    )

async def marketplace_view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Просмотр маркетплейса"""
    products = load_json(PRODUCTS_FILE)
    
    if not products:
        await update.message.reply_text(
            "🏪 <b>МАРКЕТПЛЕЙС</b>\n\n"
            "😔 Товаров пока нет\n\n"
            "Будьте первым! 📤",
            parse_mode=ParseMode.HTML
        )
        return
    
    text = (
        "╭─────────────────────────╮\n"
        "│  🏪 МАРКЕТПЛЕЙС        │\n"
        "╰─────────────────────────╯\n\n"
    )
    
    keyboard_buttons = []
    for idx, (product_id, product) in enumerate(list(products.items())[:15], 1):
        rights_check = verify_copyright(product_id, product['seller_id'])
        verified_badge = "✅" if rights_check['verified'] else "⚠️"
        
        text += (
            f"{idx}. {verified_badge} <b>{product['name']}</b>\n"
            f"   💰 {product['price']}₽ | 👤 @{product['seller_username']}\n"
            f"   📊 Продано: {product.get('sales', 0)} шт\n\n"
        )
        
        keyboard_buttons.append([
            InlineKeyboardButton(
                f"🎵 {product['name'][:15]}...",
                callback_data=f"view_product_{product_id}"
            )
        ])
    
    reply_markup = InlineKeyboardMarkup(keyboard_buttons)
    await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=reply_markup)

async def my_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Личный профиль"""
    user_id = update.effective_user.id
    user = get_user_data(user_id)
    products = load_json(PRODUCTS_FILE)
    user_products = {k: v for k, v in products.items() if v['seller_id'] == user_id}
    
    verified_badge = "✅ Верифицирован" if user.get('verified') else "⚠️ Не верифицирован"
    
    text = (
        "╭─────────────────────────╮\n"
        f"│  {PROFILE_HEADER} МОЙ ПРОФИЛЬ       │\n"
        "╰─────────────────────────╯\n\n"
        f"👤 <b>Профиль:</b>\n"
        f"   ID: <code>{user_id}</code>\n"
        f"   Статус: {verified_badge}\n\n"
        f"💰 <b>Финансы:</b>\n"
        f"   Баланс: <b>{user['balance']:,} ₽</b>\n"
        f"   Заработано: <b>{user['total_earned']:,} ₽</b>\n"
        f"   Потрачено: <b>{user['total_spent']:,} ₽</b>\n\n"
        f"📦 <b>Товары:</b>\n"
        f"   На продажу: <b>{len(user_products)}</b> шт\n"
        f"   Всего продано: <b>{sum(p.get('sales', 0) for p in user_products.values())}</b> шт\n\n"
    )
    
    keyboard = [
        [InlineKeyboardButton("💵 Вывести", callback_data="withdraw"),
         InlineKeyboardButton("📊 История", callback_data="history")],
        [InlineKeyboardButton("📦 Мои товары", callback_data="my_products"),
         InlineKeyboardButton("🔐 Авторские права", callback_data="copyright_info")],
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=reply_markup)

async def sell_product_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начать продажу"""
    keyboard = [
        [KeyboardButton("🎵 Бит")],
        [KeyboardButton("🎚️ Услуга")],
        [KeyboardButton("⬅️ Назад")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    text = (
        "╭─────────────────────────╮\n"
        "│  📤 ВЫСТАВИТЬ НА ПРОДАЖУ│\n"
        "╰─────────────────────────╯\n\n"
        "Выбери что хочешь продать:"
    )
    
    await update.message.reply_text(text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

async def add_beat_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получить имя бита"""
    context.user_data['sell_type'] = 'beat'
    context.user_data['product_name'] = update.message.text
    
    text = (
        "📝 <b>Шаг 1/4</b>\n"
        f"Название: {update.message.text}\n\n"
        "💰 Введи цену в рублях:"
    )
    
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)
    return PRODUCT_PRICE

async def add_beat_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получить цену"""
    try:
        price = int(update.message.text)
        if price < 50 or price > 100000:
            await update.message.reply_text("❌ Цена должна быть от 50 до 100000 ₽")
            return PRODUCT_PRICE
        
        context.user_data['product_price'] = price
        
        text = (
            "📝 <b>Шаг 2/4</b>\n"
            f"Название: {context.user_data['product_name']}\n"
            f"Цена: {price} ₽\n\n"
            "🎵 Отправь демо-файл (аудио):"
        )
        
        await update.message.reply_text(text, parse_mode=ParseMode.HTML)
        return PRODUCT_DEMO
    except ValueError:
        await update.message.reply_text("❌ Введи число!")
        return PRODUCT_PRICE

async def add_beat_demo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получить демо"""
    if update.message.audio:
        context.user_data['demo_file_id'] = update.message.audio.file_id
        
        text = (
            "📝 <b>Шаг 3/4</b>\n"
            f"Название: {context.user_data['product_name']}\n"
            f"Цена: {context.user_data['product_price']} ₽\n"
            f"Демо: ✅ Загружено\n\n"
            "📜 Подтверждаю что я автор этого произведения\n"
            "(Вводим галочку 🎵 если согласен):"
        )
        
        await update.message.reply_text(text, parse_mode=ParseMode.HTML)
        return PRODUCT_RIGHTS
    else:
        await update.message.reply_text("❌ Отправь аудио файл!")
        return PRODUCT_DEMO

async def add_beat_rights(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Проверить авторские права"""
    if update.message.text != '🎵':
        await update.message.reply_text("❌ Введи 🎵 чтобы подтвердить")
        return PRODUCT_RIGHTS
    
    user_id = update.effective_user.id
    user = get_user_data(user_id)
    
    # Сохраняем товар
    products = load_json(PRODUCTS_FILE)
    product_id = str(len(products) + 1)
    
    products[product_id] = {
        'seller_id': user_id,
        'seller_username': update.effective_user.username or 'Unknown',
        'name': context.user_data['product_name'],
        'price': context.user_data['product_price'],
        'type': 'beat',
        'demo_file_id': context.user_data.get('demo_file_id'),
        'created_at': datetime.now().isoformat(),
        'sales': 0
    }
    
    save_json(PRODUCTS_FILE, products)
    
    # Регистрируем авторские права
    rights_hash = register_copyright(product_id, user_id, context.user_data['product_name'])
    
    # Обновляем счётчик
    user['products_count'] = user.get('products_count', 0) + 1
    users = load_json(USERS_FILE)
    users[str(user_id)] = user
    save_json(USERS_FILE, users)
    
    text = (
        "╭─────────────────────────╮\n"
        "│  ✅ УСПЕШНО!            │\n"
        "╰─────────────────────────╯\n\n"
        f"🎵 <b>{context.user_data['product_name']}</b>\n"
        f"💰 Цена: {context.user_data['product_price']} ₽\n"
        f"📜 Статус авторских прав: <b>Зарегистрировано</b> ✅\n"
        f"🔐 Хеш: <code>{rights_hash}</code>\n\n"
        f"Товар готов к продаже! 🎉"
    )
    
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)
    return ConversationHandler.END

async def services_catalog(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Каталог услуг"""
    services = load_json(SERVICES_FILE)
    
    if not services:
        services = {
            "1": {
                "name": "🎚️ Сведение трека",
                "description": "Профессиональное сведение вашего трека",
                "price": 500,
                "seller_id": ADMIN_ID,
                "type": "service"
            },
            "2": {
                "name": "🎧 Мастеринг",
                "description": "Мастеринг трека под все платформы",
                "price": 800,
                "seller_id": ADMIN_ID,
                "type": "service"
            },
            "3": {
                "name": "🎨 Обложка под релиз",
                "description": "Профессиональная обложка 3000x3000px",
                "price": 300,
                "seller_id": ADMIN_ID,
                "type": "service"
            }
        }
        save_json(SERVICES_FILE, services)
    
    text = (
        "╭─────────────────────────╮\n"
        "│  🎚️ УСЛУГИ             │\n"
        "╰─────────────────────────╯\n\n"
    )
    
    keyboard_buttons = []
    for service_id, service in services.items():
        text += (
            f"<b>{service['name']}</b>\n"
            f"{service['description']}\n"
            f"💰 {service['price']} ₽\n\n"
        )
        keyboard_buttons.append([
            InlineKeyboardButton(f"{service['name']} - {service['price']}₽", callback_data=f"buy_service_{service_id}")
        ])
    
    reply_markup = InlineKeyboardMarkup(keyboard_buttons)
    await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=reply_markup)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка текстовых сообщений"""
    text = update.message.text
    
    if text == "🏪 МАРКЕТПЛЕЙС":
        await marketplace_view(update, context)
    elif text == "👤 МОЙ ПРОФИЛЬ":
        await my_profile(update, context)
    elif text == "📤 ПРОДАТЬ":
        await sell_product_start(update, context)
    elif text == "🎚️ УСЛУГИ":
        await services_catalog(update, context)
    elif text == "🎵 Бит":
        await update.message.reply_text(
            "📝 <b>Шаг 1/4</b>\n\n"
            "Введи название бита:",
            parse_mode=ParseMode.HTML
        )
        return PRODUCT_NAME
    elif text == "⬅️ Назад":
        await start(update, context)

# ============ ОБРАБОТКА КНОПОК ============

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка кнопок"""
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()
    
    if query.data.startswith('view_product_'):
        product_id = query.data.replace('view_product_', '')
        products = load_json(PRODUCTS_FILE)
        product = products.get(product_id)
        
        if product:
            rights = verify_copyright(product_id, product['seller_id'])
            rights_badge = "✅ VERIFIED" if rights['verified'] else "⚠️ PENDING"
            
            text = (
                f"🎵 <b>{product['name']}</b>\n\n"
                f"💰 Цена: <b>{product['price']} ₽</b>\n"
                f"👤 Продавец: @{product['seller_username']}\n"
                f"📊 Продано: {product.get('sales', 0)} шт\n"
                f"🔐 Авторские права: {rights_badge}\n\n"
                f"Мой заработок: {int(product['price'] * 0.9)} ₽ (90%)\n"
                f"Комиссия маркетплейса: {int(product['price'] * 0.1)} ₽ (10%)"
            )
            
            keyboard = [[
                InlineKeyboardButton("💳 КУПИТЬ", callback_data=f"buy_product_{product_id}"),
                InlineKeyboardButton("🔊 СЛУШАТЬ", callback_data=f"listen_product_{product_id}")
            ]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=reply_markup)
    
    elif query.data.startswith('buy_product_'):
        product_id = query.data.replace('buy_product_', '')
        products = load_json(PRODUCTS_FILE)
        product = products.get(product_id)
        
        if product:
            seller_id = product['seller_id']
            user = get_user_data(user_id)
            
            seller_amount = int(product['price'] * 0.9)
            commission = product['price'] - seller_amount
            
            add_balance(user_id, -product['price'], f"Покупка: {product['name']}")
            add_balance(seller_id, seller_amount, f"Продажа: {product['name']}")
            add_balance(ADMIN_ID, commission, f"Комиссия: {product['name']}")
            
            product['sales'] = product.get('sales', 0) + 1
            products[product_id] = product
            save_json(PRODUCTS_FILE, products)
            
            await query.edit_message_text(
                f"╭──────────────────────╮\n"
                f"│  ✅ СПАСИБО!        │\n"
                f"╰──────────────────────╯\n\n"
                f"🎵 {product['name']}\n"
                f"💰 {product['price']} ₽\n\n"
                f"✅ Платёж успешен!\n"
                f"📥 Скачивай в профиле",
                parse_mode=ParseMode.HTML
            )
    
    elif query.data == "copyright_info":
        products = load_json(PRODUCTS_FILE)
        rights = load_json(RIGHTS_FILE)
        
        text = (
            "🔐 <b>АВТОРСКИЕ ПРАВА</b>\n\n"
            "Sound4You защищает твои права:\n\n"
            "✅ Регистрация при загрузке\n"
            "✅ Уникальный хеш произведения\n"
            "✅ Защита от плагиата\n"
            "✅ Подтверждение авторства\n\n"
            "Все твои товары автоматически\n"
            "регистрируются в системе прав!"
        )
        
        await query.edit_message_text(text, parse_mode=ParseMode.HTML)

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Админ панель"""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ У вас нет доступа!")
        return
    
    users = load_json(USERS_FILE)
    products = load_json(PRODUCTS_FILE)
    transactions = load_json(TRANSACTIONS_FILE)
    
    admin_user = users.get(str(ADMIN_ID), {})
    
    text = (
        "╭─────────────────────────╮\n"
        "│  ⚙️ АДМИН ПАНЕЛЬ       │\n"
        "╰─────────────────────────╯\n\n"
        f"💰 Баланс комиссий: {admin_user.get('balance', 0):,} ₽\n"
        f"💸 Всего получено: {admin_user.get('total_earned', 0):,} ₽\n"
        f"👥 Пользователей: {len(users)}\n"
        f"📦 Товаров: {len(products)}\n"
        f"📈 Транзакций: {len(transactions)}\n"
    )
    
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Exception: {context.error}")

# ============ ГЛАВНАЯ ФУНКЦИЯ ============

def main():
    """Запуск бота"""
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Обработчик диалога добавления бита
    beat_conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^🎵 Бит$"), add_beat_name)],
        states={
            PRODUCT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_beat_name)],
            PRODUCT_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_beat_price)],
            PRODUCT_DEMO: [MessageHandler(filters.AUDIO | filters.TEXT & ~filters.COMMAND, add_beat_demo)],
            PRODUCT_RIGHTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_beat_rights)],
        },
        fallbacks=[CommandHandler('cancel', lambda u, c: ConversationHandler.END)],
    )
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(beat_conv_handler)
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_error_handler(error_handler)
    
    print("🎵 SOUND4YOU МАРКЕТПЛЕЙС ЗАПУЩЕН! 🎵")
    print("Нажми Ctrl+C для остановки")
    app.run_polling()

if __name__ == '__main__':
    main()
