import asyncio
import os
import json
import re
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.filters import CommandStart, StateFilter
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from aiogram.types import ReplyKeyboardMarkup
from dotenv import load_dotenv
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime

load_dotenv()
print("🚀 АвтоСтоянка • LIVE КАТАЛОГ + EXPORT • ФИНАЛЬНАЯ ВЕРСИЯ")

# Состояния
class SellForm(StatesGroup):
    title = State()
    price = State()

class AdminComment(StatesGroup):
    waiting_comment = State()

class UserEdit(StatesGroup):
    waiting_edit = State()

# 🔥 ГЛАВНАЯ БД
ADS_DB = "ads_db.json"
current_comment_ad_id = None
current_edit_ad_id = None
ADMIN_ID = int(os.getenv("ADMIN_ID") or 0)

def load_ads_db():
    """🔥 Загрузка БД"""
    if os.path.exists(ADS_DB):
        try:
            with open(ADS_DB, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('pending', {}), data.get('approved', [])
        except:
            pass
    return {}, []

def save_ads_db(pending, approved):
    """🔥 LIVE UPDATE - ГАРАНТИЯ для Mini App"""
    try:
        os.makedirs("webapp", exist_ok=True)
        
        # 🔥 1. ОСНОВНАЯ БД
        db_data = {
            'pending': pending,
            'approved': approved,
            'updated': datetime.now().isoformat(),
            'stats': {
                'pending_count': len(pending),
                'approved_count': len(approved)
            }
        }
        with open(ADS_DB, 'w', encoding='utf-8') as f:
            json.dump(db_data, f, ensure_ascii=False, indent=2)
        
        # 🔥 2. MINI APP ФАЙЛ (локально)
        catalog_data = {
            'ads': approved,
            'updated': datetime.now().isoformat(),
            'live': True,
            'total': len(approved)
        }
        with open('ads.json', 'w', encoding='utf-8') as f:
            json.dump(catalog_data, f, ensure_ascii=False, indent=2)
        
        print(f"🎉 LIVE UPDATE: {len(approved)} объявлений в ads.json!")
        
    except Exception as e:
        print(f"❌ ОШИБКА сохранения: {e}")

# 🔥 EXPORT для Netlify (НОВОЕ!)
async def export_catalog():
    """📤 Автообновление export_ads.json каждые 30 сек"""
    while True:
        try:
            pending, approved = load_ads_db()
            catalog_data = {
                'ads': approved,
                'live': True,
                'updated': datetime.now().isoformat(),
                'total': len(approved)
            }
            with open('export_ads.json', 'w', encoding='utf-8') as f:
                json.dump(catalog_data, f, ensure_ascii=False, indent=2)
            print(f"📤 EXPORT: {len(approved)} в export_ads.json")
        except Exception as e:
            print(f"❌ Export error: {e}")
        await asyncio.sleep(30)

def main_menu():
    builder = ReplyKeyboardBuilder()
    builder.button(text="🛒 Купить")
    builder.button(text="💰 Продать")
    builder.button(text="📱 Открыть приложение")
    builder.button(text="ℹ️ Профиль")
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

def admin_menu(ad_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Одобрить", callback_data=f"approve_{ad_id}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_{ad_id}")
        ],
        [InlineKeyboardButton(text="📝 Комментарий", callback_data=f"comment_{ad_id}")]
    ])

def user_action_menu(ad_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✏️ Дополнить", callback_data=f"edit_{ad_id}"),
            InlineKeyboardButton(text="❌ Отменить", callback_data=f"cancel_{ad_id}")
        ]
    ])

# ИНИЦИАЛИЗАЦИЯ
bot = Bot(token=os.getenv("BOT_TOKEN"))
dp = Dispatcher()

@dp.message(CommandStart())
async def start(message: Message):
    print(f"👤 {message.from_user.first_name} (ID: {message.from_user.id}) подключился")
    await message.answer("🚗 АвтоСтоянка СПб!", reply_markup=main_menu())

@dp.message(F.text == "🛒 Купить")
async def buy(message: Message):
    await message.answer("📱 Каталог в приложении!")

@dp.message(F.text == "📱 Открыть приложение")
async def open_app(message: Message):
    await message.answer(
        "📱 АвтоСтоянка Mini App",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="🚗 Открыть", 
                web_app=WebAppInfo(url="https://autostoyanka.netlify.app/")
            )]
        ]),
        parse_mode="HTML"
    )

@dp.message(F.text == "ℹ️ Профиль")
async def profile(message: Message):
    pending, approved = load_ads_db()
    my_pending = sum(1 for ad_id, ad in pending.items() if ad['user_id'] == message.from_user.id)
    my_approved = sum(1 for ad in approved if ad['user_id'] == message.from_user.id)
    
    await message.answer(
        f"👤 Ваш профиль\n\n"
        f"ID: <code>{message.from_user.id}</code>\n"
        f"⏳ На модерации: {my_pending}\n"
        f"✅ В каталоге: {my_approved}",
        parse_mode="HTML"
    )

@dp.message(F.text == "💰 Продать")
async def sell_start(message: Message, state: FSMContext):
    await message.answer("🚗 Модель авто:\nПример: BMW X5 2020")
    await state.set_state(SellForm.title)

@dp.message(StateFilter(SellForm.title))
async def get_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text.strip())
    await message.answer("💰 Цена в рублях:\nПример: 2500000")
    await state.set_state(SellForm.price)

@dp.message(StateFilter(SellForm.price))
async def get_price(message: Message, state: FSMContext):
    clean_price = re.sub(r'[^\d]', '', message.text)
    try:
        price = int(clean_price)
        data = await state.get_data()
        title = data['title']
        
        pending, approved = load_ads_db()
        ad_id = str(max([int(k) for k in pending.keys()], default=0) + 1)
        
        pending[ad_id] = {
            'title': title,
            'price': price,
            'user_id': message.from_user.id,
            'user_name': message.from_user.first_name,
            'created_at': datetime.now().isoformat()
        }
        
        save_ads_db(pending, approved)
        print(f"🆕 Создано #{ad_id}: {title}")
        
        await message.answer(
            f"✅ <b>#{ad_id}</b> создано!\n\n"
            f"🚗 <b>{title}</b>\n"
            f"💰 <b>{price:,} ₽</b>\n\n"
            f"⏳ На модерации...\n"
            f"📱 Уже видно в профиле!",
            parse_mode="HTML"
        )
        
        if ADMIN_ID:
            await bot.send_message(
                ADMIN_ID,
                f"🆕 <b>#{ad_id}</b>\n\n"
                f"🚗 <b>{title}</b>\n"
                f"💰 <b>{price:,} ₽</b>\n"
                f"👤 {message.from_user.first_name} (ID: {message.from_user.id})",
                parse_mode="HTML",
                reply_markup=admin_menu(int(ad_id))
            )
        await state.clear()
    except:
        await message.answer("❌ Только цифры для цены!")

@dp.callback_query(F.data.startswith(("approve_", "reject_")))
async def moderate_ad(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return await callback.answer("❌ Только админ!")
    
    ad_id = callback.data.split("_")[1]
    pending, approved = load_ads_db()
    
    if ad_id not in pending:
        return await callback.answer("❌ Объявление завершено!")
    
    ad = pending[ad_id]
    is_approve = callback.data.startswith("approve")
    
    if is_approve:
        approved_ad = {
            'id': int(ad_id),
            'title': ad['title'],
            'price': ad['price'],
            'seller': ad['user_name'],
            'user_id': ad['user_id'],
            'status': 'approved',
            'created_at': ad.get('created_at')
        }
        approved.append(approved_ad)
        del pending[ad_id]
        save_ads_db(pending, approved)
        print(f"🎉 #{ad_id} ДОБАВЛЕН В КАТАЛОГ! export_ads.json обновится через 30с!")
    
    status_emoji = "✅ ОДОБРЕНО" if is_approve else "❌ ОТКЛОНЕНО"
    
    await bot.send_message(
        ad['user_id'],
        f"{status_emoji}\n\n"
        f"🚗 <b>{ad['title']}</b>\n"
        f"💰 <b>{ad['price']:,} ₽</b>\n\n"
        f"📱 Уже в каталоге и профиле!",
        parse_mode="HTML"
    )
    
    await callback.message.edit_text(f"{status_emoji} <b>#{ad_id}</b>", parse_mode="HTML")
    await callback.answer("✓")

@dp.callback_query(F.data.startswith("comment_"))
async def start_comment(callback: CallbackQuery, state: FSMContext):
    global current_comment_ad_id
    ad_id = callback.data.split("_")[1]
    
    pending, _ = load_ads_db()
    if ad_id not in pending:
        return await callback.answer("❌ Объявление завершено!")
    
    current_comment_ad_id = ad_id
    await state.set_state(AdminComment.waiting_comment)
    await callback.message.edit_text(f"📝 Комментарий к <b>#{ad_id}</b>\n\nПишите сообщение:", parse_mode="HTML")
    await callback.answer("💬")

@dp.message(StateFilter(AdminComment.waiting_comment))
async def process_comment(message: Message, state: FSMContext):
    global current_comment_ad_id
    if message.from_user.id != ADMIN_ID or not current_comment_ad_id:
        return
    
    pending, _ = load_ads_db()
    ad_id = current_comment_ad_id
    ad = pending[ad_id]
    
    await bot.send_message(
        ad['user_id'],
        f"📝 <b>Модератор:</b> {message.text}\n\n"
        f"🚗 <b>{ad['title']}</b>\n💰 <b>{ad['price']:,} ₽</b>\n\n"
        f"<b>#{ad_id}</b> — действия?",
        parse_mode="HTML",
        reply_markup=user_action_menu(int(ad_id))
    )
    
    await message.answer("✅ Отправлено!", reply_markup=main_menu())
    await state.clear()
    current_comment_ad_id = None

@dp.callback_query(F.data.startswith("cancel_"))
async def cancel_ad(callback: CallbackQuery):
    ad_id = callback.data.split("_")[1]
    pending, approved = load_ads_db()
    
    if ad_id in pending:
        del pending[ad_id]
        save_ads_db(pending, approved)
        print(f"🗑️ #{ad_id} отменено")
    
    await callback.message.edit_text(f"❌ <b>#{ad_id}</b> отменено!", parse_mode="HTML")
    await callback.answer("✗")

@dp.callback_query()
async def ignore(callback: CallbackQuery):
    await callback.answer()

# 🔥 ОДНА И ЕДИНСТВЕННАЯ main() функция!
async def main():
    print("🚀 Бот запущен!")
    print(f"👤 Админ: {ADMIN_ID}")
    print(f"📁 Корень: {os.getcwd()}")
    
    # Создаем начальный пустой каталог
    save_ads_db({}, [])
    
    # 🔥 ЗАПУСКАЕМ EXPORT каждые 30 секунд
    asyncio.create_task(export_catalog())
    
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
