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
    ChatShared,
    SwitchInlineQueryChosenChat,
)
from dotenv import load_dotenv

load_dotenv()
API_TOKEN = os.getenv("API_TOKEN")

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

REQ = {
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
    """
    JSON ni HTML <pre><code> ichida yuboradi.
    parse_mode=Markdown ishlatilmaydi — maxsus belgilar xato beradi.
    """
    raw = to_json_str(data)
    # HTML uchun < > & belgilarini escape qilamiz
    raw_escaped = raw.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    chunk_size = 3900
    for i in range(0, len(raw_escaped), chunk_size):
        chunk = raw_escaped[i:i + chunk_size]
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


# ── Copy callback ─────────────────────────────────────────────────────────────
@dp.callback_query(F.data.startswith("copy_"))
async def copy_callback(callback: CallbackQuery):
    val = callback.data.split("_", 1)[1]
    await callback.answer(f"Copied: {val}", show_alert=True)


# ── /start ────────────────────────────────────────────────────────────────────
@dp.message(Command("start"))
async def cmd_start(message: Message):
    raw_data = {
        "update_id": message.message_id,
        "message": message.model_dump(),
    }
    await send_json(message, raw_data)
    save_user(message.from_user.id, raw_data)
    await show_filter_menu(message)


# ── /filter ───────────────────────────────────────────────────────────────────
@dp.message(Command("filter"))
async def show_filter_menu(message: Message):
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="👤 User"),
                KeyboardButton(text="⭐ Premium"),
                KeyboardButton(text="👾 Bot"),
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
    await message.answer(
        "🔍 <b>Filter turini tanlang:</b>",
        parse_mode="HTML",
        reply_markup=kb,
    )


# ── 👤 User / ⭐ Premium / 👾 Bot ─────────────────────────────────────────────
@dp.message(F.text.in_({"👤 User", "⭐ Premium", "👾 Bot"}))
async def show_self_info(message: Message):
    u = message.from_user
    label = message.text

    data = {
        "filter": label,
        "user_id": u.id,
        "first_name": u.first_name,
        "last_name": u.last_name,
        "username": u.username,
        "full_name": u.full_name,
        "is_bot": u.is_bot,
        "is_premium": bool(getattr(u, "is_premium", False)),
        "language_code": u.language_code,
        "raw": u.model_dump(),
    }
    save_user(u.id, data)

    await send_json(message, data)
    await message.answer(
        f"{label}\n"
        f"👤 <b>{u.full_name}</b>\n"
        f"◆ User ID : <code>{u.id}</code>",
        parse_mode="HTML",
        reply_markup=result_keyboard(u.id),
    )


# ── ChatShared handler ────────────────────────────────────────────────────────
@dp.message(F.chat_shared)
async def on_chat_shared(message: Message):
    shared: ChatShared = message.chat_shared
    rid = shared.request_id
    chat_id = shared.chat_id
    title = getattr(shared, "title", None) or "—"
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
        "filter": label,
        "chat_id": chat_id,
        "title": title,
        "username": username,
        "raw": shared.model_dump(),
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


# ── Entry point ───────────────────────────────────────────────────────────────
async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())