import asyncio
import logging
import json
import os
from datetime import datetime

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
    KeyboardButtonRequestChat,
    KeyboardButtonRequestUsers,
    ChatShared,
    UsersShared,
    SwitchInlineQueryChosenChat,
    BotCommand,
)
from dotenv import load_dotenv

load_dotenv()
API_TOKEN = os.getenv("API_TOKEN")

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# ── Stats ─────────────────────────────────────────────────────────────────────
STATS_FILE = "stats.json"


def load_stats() -> dict:
    if os.path.exists(STATS_FILE):
        with open(STATS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"all_user_ids": [], "monthly_users": {}}


def save_stats(stats: dict):
    with open(STATS_FILE, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=4, ensure_ascii=False)


def get_monthly_count() -> int:
    stats = load_stats()
    month_key = datetime.now().strftime("%Y-%m")
    return len(stats["monthly_users"].get(month_key, []))


def get_total_count() -> int:
    stats = load_stats()
    return len(stats.get("all_user_ids", []))


async def update_short_description():
    """Short description ni hamma joydan chaqiriladigan yagona funksiya."""
    monthly = get_monthly_count()
    try:
        await bot.set_my_short_description(
            short_description=f"{monthly:,} monthly users · Message data in JSON format (@geodev_at) 📩"
        )
    except Exception as e:
        logging.warning(f"set_my_short_description error: {e}")


async def register_user(user_id: int):
    """
    Foydalanuvchini statistikaga qo'shadi.
    - Yangi total user bo'lsa -> all_user_ids ga qo'shiladi
    - Yangi oylik user bo'lsa -> monthly_users ga qo'shiladi + short_description yangilanadi
    """
    stats = load_stats()
    month_key = datetime.now().strftime("%Y-%m")

    total_changed   = False
    monthly_changed = False

    # Total hisob
    if user_id not in stats["all_user_ids"]:
        stats["all_user_ids"].append(user_id)
        total_changed = True

    # Oylik hisob
    if month_key not in stats["monthly_users"]:
        stats["monthly_users"][month_key] = []

    if user_id not in stats["monthly_users"][month_key]:
        stats["monthly_users"][month_key].append(user_id)
        monthly_changed = True

    # Faqat o'zgarish bo'lsa saqlash
    if total_changed or monthly_changed:
        save_stats(stats)

    # Oylik o'zgarsa short_description yangilanadi
    if monthly_changed:
        await update_short_description()


# ── Request IDs ───────────────────────────────────────────────────────────────
REQ = {
    "user":       7,
    "premium":    8,
    "bot":        9,
    "group":      1,
    "channel":    2,
    "forum":      3,
    "my_group":   4,
    "my_channel": 5,
    "my_forum":   6,
}

# ── Helpers ───────────────────────────────────────────────────────────────────
def _serial(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")


def save_user(user_id: int, data: dict):
    os.makedirs("users", exist_ok=True)
    with open(f"users/{user_id}.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False, default=_serial)


def to_json_str(data: dict) -> str:
    return json.dumps(data, indent=4, ensure_ascii=False, default=_serial)


async def send_json(message: Message, data: dict):
    raw = to_json_str(data)
    raw_escaped = (
        raw
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
    for i in range(0, len(raw_escaped), 3900):
        chunk = raw_escaped[i:i + 3900]
        await message.answer(
            f"<pre><code class='language-json'>{chunk}</code></pre>",
            parse_mode="HTML",
        )


def result_keyboard(entity_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text=f"Copy {entity_id}",
                callback_data=f"copy_{entity_id}",
            )
        ],
        [
            InlineKeyboardButton(
                text="🚀 Share ID",
                switch_inline_query_chosen_chat=SwitchInlineQueryChosenChat(
                    query=str(entity_id),
                    allow_user_chats=True,
                    allow_bot_chats=True,
                    allow_group_chats=True,
                    allow_channel_chats=True,
                ),
            )
        ],
    ])


def get_filter_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(
                    text="👤 User",
                    request_users=KeyboardButtonRequestUsers(
                        request_id=REQ["user"],
                        user_is_bot=False,
                        request_name=True,
                        request_username=True,
                        request_photo=False,
                    ),
                ),
                KeyboardButton(
                    text="⭐ Premium",
                    request_users=KeyboardButtonRequestUsers(
                        request_id=REQ["premium"],
                        user_is_bot=False,
                        user_is_premium=True,
                        request_name=True,
                        request_username=True,
                        request_photo=False,
                    ),
                ),
                KeyboardButton(
                    text="👾 Bot",
                    request_users=KeyboardButtonRequestUsers(
                        request_id=REQ["bot"],
                        user_is_bot=True,
                        request_name=True,
                        request_username=True,
                        request_photo=False,
                    ),
                ),
            ],
            [
                KeyboardButton(
                    text="👥 Group",
                    request_chat=KeyboardButtonRequestChat(
                        request_id=REQ["group"],
                        chat_is_channel=False,
                        chat_is_forum=False,
                        request_title=True,
                        request_username=True,
                    ),
                ),
                KeyboardButton(
                    text="📢 Channel",
                    request_chat=KeyboardButtonRequestChat(
                        request_id=REQ["channel"],
                        chat_is_channel=True,
                        request_title=True,
                        request_username=True,
                    ),
                ),
                KeyboardButton(
                    text="💬 Forum",
                    request_chat=KeyboardButtonRequestChat(
                        request_id=REQ["forum"],
                        chat_is_channel=False,
                        chat_is_forum=True,
                        request_title=True,
                        request_username=True,
                    ),
                ),
            ],
            [
                KeyboardButton(
                    text="👥 My Group",
                    request_chat=KeyboardButtonRequestChat(
                        request_id=REQ["my_group"],
                        chat_is_channel=False,
                        chat_is_forum=False,
                        chat_is_created=True,
                        request_title=True,
                        request_username=True,
                    ),
                ),
                KeyboardButton(
                    text="📢 My Channel",
                    request_chat=KeyboardButtonRequestChat(
                        request_id=REQ["my_channel"],
                        chat_is_channel=True,
                        chat_is_created=True,
                        request_title=True,
                        request_username=True,
                    ),
                ),
                KeyboardButton(
                    text="💬 My Forum",
                    request_chat=KeyboardButtonRequestChat(
                        request_id=REQ["my_forum"],
                        chat_is_channel=False,
                        chat_is_forum=True,
                        chat_is_created=True,
                        request_title=True,
                        request_username=True,
                    ),
                ),
            ],
        ],
        resize_keyboard=True,
        one_time_keyboard=False,
    )


# ── /start ────────────────────────────────────────────────────────────────────
@dp.message(Command("start"))
async def cmd_start(message: Message):
    user = message.from_user
    await register_user(user.id)

    raw_data = {
        "update_id": message.message_id,
        "message": message.model_dump(),
    }
    save_user(user.id, raw_data)

    await message.answer(
        "Hi Welcome To @gettelegram_rawdata_bot 🖐\n\n"
        "📚 Help : /help\n\n"
        "🔔 Bot News : @geodevcode",
        parse_mode="HTML",
    )

    await message.answer(
        f"Your ID : <code>{user.id}</code>",
        parse_mode="HTML",
        reply_markup=result_keyboard(user.id),
    )

    await message.answer(
        "🔍 <b>Filter turini tanlang:</b>",
        parse_mode="HTML",
        reply_markup=get_filter_keyboard(),
    )


# ── /help ─────────────────────────────────────────────────────────────────────
@dp.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "Hi Welcome To @gettelegram_rawdata_bot 🖐\n"
        "The bot is free to use\n\n"
        "This robot can help you get Telegram ID from the following :\n\n"
        "▪️ <b>👤 User</b> — istalgan foydalanuvchini tanlang\n"
        "▪️ <b>⭐ Premium</b> — faqat Premium foydalanuvchilarni tanlang\n"
        "▪️ <b>👾 Bot</b> — botlarni tanlang\n"
        "▪️ Guruh / Kanal / Forum tugmalaridan chat tanlang\n"
        "▪️ Xabarni forward qiling — ID olish uchun\n\n"
        "🔔 News : @geodevcode",
        parse_mode="HTML",
        reply_markup=get_filter_keyboard(),
    )


# ── /filter ───────────────────────────────────────────────────────────────────
@dp.message(Command("filter"))
async def show_filter_menu(message: Message):
    await message.answer(
        "🔍 <b>Filter turini tanlang:</b>",
        parse_mode="HTML",
        reply_markup=get_filter_keyboard(),
    )


# ── /stats ────────────────────────────────────────────────────────────────────
OWNER_ID = int(os.getenv("OWNER_ID", 0))
@dp.message(Command("stats"))
async def cmd_stats(message: Message):
    if message.from_user.id != OWNER_ID:
        return  
    
    monthly = get_monthly_count()
    total   = get_total_count()
    await message.answer(
        f"📊 <b>Statistika</b>\n\n"
        f"👥 Oylik foydalanuvchilar : <b>{monthly:,}</b>\n"
        f"📈 Jami foydalanuvchilar  : <b>{total:,}</b>",
        parse_mode="HTML",
    )


# ── Copy callback ─────────────────────────────────────────────────────────────
@dp.callback_query(F.data.startswith("copy_"))
async def copy_callback(callback: CallbackQuery):
    val = callback.data.split("_", 1)[1]
    await callback.answer(f"Copied: {val}", show_alert=True)


# ── UsersShared handler — User / Premium / Bot tugmalari ─────────────────────
@dp.message(F.users_shared)
async def on_users_shared(message: Message):
    shared: UsersShared = message.users_shared
    rid = shared.request_id

    label_map = {
        REQ["user"]:    "👤 User",
        REQ["premium"]: "⭐ Premium",
        REQ["bot"]:     "👾 Bot",
    }
    label = label_map.get(rid, "👤 User")

    for user in shared.users:
        user_id  = user.user_id
        first    = getattr(user, "first_name", None) or "—"
        last     = getattr(user, "last_name",  None) or ""
        username = getattr(user, "username",   None)
        full     = f"{first} {last}".strip()

        data = {
            "filter":     label,
            "user_id":    user_id,
            "first_name": first,
            "last_name":  last,
            "full_name":  full,
            "username":   username,
            "raw":        user.model_dump(),
        }

        save_user(user_id, data)
        await send_json(message, data)

        extra = f"\n🔗 @{username}" if username else ""
        await message.answer(
            f"{label}\n"
            f"👤 <b>{full}</b>{extra}\n"
            f"◆ User ID : <code>{user_id}</code>",
            parse_mode="HTML",
            reply_markup=result_keyboard(user_id),
        )


# ── Forward handler ───────────────────────────────────────────────────────────
@dp.message(F.forward_origin)
async def on_forward(message: Message):
    origin = message.forward_origin
    origin_type = type(origin).__name__

    data = {"forward_type": origin_type, "raw": origin.model_dump()}

    if hasattr(origin, "sender_user") and origin.sender_user:
        u = origin.sender_user
        data["user_id"]   = u.id
        data["username"]  = u.username
        data["full_name"] = u.full_name
        entity_id = u.id
        label = f"👤 Forwarded User\n👤 <b>{u.full_name}</b>"
    elif hasattr(origin, "chat") and origin.chat:
        c = origin.chat
        data["chat_id"]  = c.id
        data["title"]    = c.title
        data["username"] = c.username
        entity_id = c.id
        label = f"📢 Forwarded Chat\n📌 <b>{c.title or '—'}</b>"
    elif hasattr(origin, "sender_chat") and origin.sender_chat:
        c = origin.sender_chat
        data["chat_id"]  = c.id
        data["title"]    = c.title
        data["username"] = c.username
        entity_id = c.id
        label = f"📢 Forwarded Chat\n📌 <b>{c.title or '—'}</b>"
    else:
        sender_name = getattr(origin, "sender_user_name", "Hidden user")
        data["sender_name"] = sender_name
        entity_id = None
        label = f"👤 Hidden User : <b>{sender_name}</b>"

    await send_json(message, data)

    if entity_id:
        await message.answer(
            f"{label}\n◆ ID : <code>{entity_id}</code>",
            parse_mode="HTML",
            reply_markup=result_keyboard(entity_id),
        )
    else:
        await message.answer(label, parse_mode="HTML")


# ── ChatShared handler ────────────────────────────────────────────────────────
@dp.message(F.chat_shared)
async def on_chat_shared(message: Message):
    shared: ChatShared = message.chat_shared
    rid      = shared.request_id
    chat_id  = shared.chat_id
    title    = getattr(shared, "title",    None) or "—"
    username = getattr(shared, "username", None)

    labels = {
        REQ["group"]:      "👥 Group",
        REQ["channel"]:    "📢 Channel",
        REQ["forum"]:      "💬 Forum",
        REQ["my_group"]:   "👥 My Group",
        REQ["my_channel"]: "📢 My Channel",
        REQ["my_forum"]:   "💬 My Forum",
    }
    label = labels.get(rid, "Chat")

    data = {
        "filter":   label,
        "chat_id":  chat_id,
        "title":    title,
        "username": username,
        "raw":      shared.model_dump(),
    }

    await send_json(message, data)

    extra = f"\n🔗 @{username}" if username else ""
    await message.answer(
        f"{label}\n"
        f"📌 <b>{title}</b>{extra}\n"
        f"◆ Chat ID : <code>{chat_id}</code>",
        parse_mode="HTML",
        reply_markup=result_keyboard(chat_id),
    )


# ── Bot commands & descriptions ───────────────────────────────────────────────
async def set_commands():
    # Barcha userlar uchun
    await bot.set_my_commands([
        BotCommand(command="start",  description="Restart"),
        BotCommand(command="help",   description="How to use the bot"),
        BotCommand(command="filter", description="Show filter keyboard"),
    ])

    # Faqat egaga ko'rinadigan komandalar
    if OWNER_ID:
        from aiogram.types import BotCommandScopeChat
        await bot.set_my_commands(
            [
                BotCommand(command="start",  description="Restart"),
                BotCommand(command="help",   description="How to use the bot"),
                BotCommand(command="filter", description="Show filter keyboard"),
                BotCommand(command="stats",  description="📊 Statistika"),
            ],
            scope=BotCommandScopeChat(chat_id=OWNER_ID),
        )

    monthly = get_monthly_count()
    total   = get_total_count()

    try:
        await bot.set_my_short_description(
            short_description=f"{monthly:,} monthly users · Message data in JSON format (@geodev_at) 📩"
        )
    except Exception as e:
        logging.warning(f"set_my_short_description error: {e}")

    try:
        await bot.set_my_description(
            description=(
                f"Hi! Welcome To @gettelegram_rawdata_bot 🖐\n"
                f"The bot is free to use\n\n"
                f"Get any Telegram ID instantly 🚀\n\n"
                f"👥 Monthly users : {monthly:,}\n"
                f"📊 Total users   : {total:,}\n\n"
                f"🔔 News : @geodevcode"
            )
        )
    except Exception as e:
        logging.warning(f"set_my_description error: {e}")


# ── Entry point ───────────────────────────────────────────────────────────────
async def main():
    await set_commands()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())