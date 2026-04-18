import asyncio
import logging
import json
import os
from datetime import datetime
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
    Chat,
    User,
)
from dotenv import load_dotenv

load_dotenv()
API_TOKEN = os.getenv("API_TOKEN")

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher()


# ─────────────────────────────────────────────
# Helper: datetime → JSON serializable
# ─────────────────────────────────────────────
def convert_to_serializable(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")


# ─────────────────────────────────────────────
# Helper: save data to users/ folder
# ─────────────────────────────────────────────
def save_user_data(user_id: int, data: dict):
    os.makedirs("users", exist_ok=True)
    with open(f"users/{user_id}.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False, default=convert_to_serializable)


# ─────────────────────────────────────────────
# Helper: send JSON as chunked code blocks
# ─────────────────────────────────────────────
async def send_json_chunks(message: Message, data: dict):
    raw_json = json.dumps(
        data,
        indent=4,
        ensure_ascii=False,
        default=convert_to_serializable,
    )
    for i in range(0, len(raw_json), 3900):
        chunk = raw_json[i : i + 3900]
        await message.answer(
            f"```json\n{chunk}\n```",
            parse_mode="Markdown",
        )


# ─────────────────────────────────────────────
# Filter keyboard (screenshot'dagi 9 ta tugma)
# ─────────────────────────────────────────────
def get_filter_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(text="👤 User",       callback_data="filter_user"),
            InlineKeyboardButton(text="⭐ Premium",    callback_data="filter_premium"),
            InlineKeyboardButton(text="👾 Bot",        callback_data="filter_bot"),
        ],
        [
            InlineKeyboardButton(text="👥 Group",      callback_data="filter_group"),
            InlineKeyboardButton(text="📢 Channel",    callback_data="filter_channel"),
            InlineKeyboardButton(text="💬 Forum",      callback_data="filter_forum"),
        ],
        [
            InlineKeyboardButton(text="👥 My Group",   callback_data="filter_my_group"),
            InlineKeyboardButton(text="📢 My Channel", callback_data="filter_my_channel"),
            InlineKeyboardButton(text="💬 My Forum",   callback_data="filter_my_forum"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ─────────────────────────────────────────────
# /start — welcome + filter keyboard
# ─────────────────────────────────────────────
@dp.message(Command("start"))
async def send_welcome(message: Message):
    raw_data = {
        "update_id": message.message_id,
        "message": message.model_dump(),
    }

    await send_json_chunks(message, raw_data)
    save_user_data(message.from_user.id, raw_data)

    await message.answer(
        "🔍 <b>Filter turini tanlang:</b>",
        parse_mode="HTML",
        reply_markup=get_filter_keyboard(),
    )


# ─────────────────────────────────────────────
# /filter — keyboard'ni qayta chiqarish
# ─────────────────────────────────────────────
@dp.message(Command("filter"))
async def show_filter_menu(message: Message):
    await message.answer(
        "🔍 <b>Filter turini tanlang:</b>",
        parse_mode="HTML",
        reply_markup=get_filter_keyboard(),
    )


# ─────────────────────────────────────────────
# Callback: filter_user  — oddiy foydalanuvchilar
# ─────────────────────────────────────────────
@dp.callback_query(F.data == "filter_user")
async def filter_user(callback: CallbackQuery):
    await callback.answer("👤 User filtri tanlandi", show_alert=False)
    user: User = callback.from_user
    info = {
        "filter": "user",
        "id": user.id,
        "username": user.username,
        "full_name": user.full_name,
        "is_bot": user.is_bot,
        "is_premium": getattr(user, "is_premium", False),
        "language_code": user.language_code,
    }
    await send_json_chunks(callback.message, info)


# ─────────────────────────────────────────────
# Callback: filter_premium — premium foydalanuvchilar
# ─────────────────────────────────────────────
@dp.callback_query(F.data == "filter_premium")
async def filter_premium(callback: CallbackQuery):
    await callback.answer("⭐ Premium filtri tanlandi", show_alert=False)
    user: User = callback.from_user
    is_premium = getattr(user, "is_premium", False)
    info = {
        "filter": "premium",
        "id": user.id,
        "username": user.username,
        "full_name": user.full_name,
        "is_premium": bool(is_premium),
        "note": "Premium foydalanuvchi" if is_premium else "Premium emas",
    }
    await send_json_chunks(callback.message, info)


# ─────────────────────────────────────────────
# Callback: filter_bot — bot hisoblar
# ─────────────────────────────────────────────
@dp.callback_query(F.data == "filter_bot")
async def filter_bot(callback: CallbackQuery):
    await callback.answer("👾 Bot filtri tanlandi", show_alert=False)
    user: User = callback.from_user
    info = {
        "filter": "bot",
        "id": user.id,
        "username": user.username,
        "full_name": user.full_name,
        "is_bot": user.is_bot,
        "note": "Bot hisobi" if user.is_bot else "Bot emas (oddiy foydalanuvchi)",
    }
    await send_json_chunks(callback.message, info)


# ─────────────────────────────────────────────
# Callback: filter_group — guruhlar haqida ma'lumot
# ─────────────────────────────────────────────
@dp.callback_query(F.data == "filter_group")
async def filter_group(callback: CallbackQuery):
    await callback.answer("👥 Group filtri tanlandi", show_alert=False)
    chat: Chat = callback.message.chat
    info = {
        "filter": "group",
        "chat_id": chat.id,
        "chat_type": chat.type,
        "title": chat.title,
        "username": chat.username,
        "note": "Bu xabar guruhda yozilgan" if chat.type in ("group", "supergroup") else "Bu shaxsiy chat",
    }
    await send_json_chunks(callback.message, info)


# ─────────────────────────────────────────────
# Callback: filter_channel — kanallar haqida ma'lumot
# ─────────────────────────────────────────────
@dp.callback_query(F.data == "filter_channel")
async def filter_channel(callback: CallbackQuery):
    await callback.answer("📢 Channel filtri tanlandi", show_alert=False)
    chat: Chat = callback.message.chat
    info = {
        "filter": "channel",
        "chat_id": chat.id,
        "chat_type": chat.type,
        "title": chat.title,
        "username": chat.username,
        "note": "Kanal" if chat.type == "channel" else "Bu kanal emas",
    }
    await send_json_chunks(callback.message, info)


# ─────────────────────────────────────────────
# Callback: filter_forum — forum (supergroup) haqida
# ─────────────────────────────────────────────
@dp.callback_query(F.data == "filter_forum")
async def filter_forum(callback: CallbackQuery):
    await callback.answer("💬 Forum filtri tanlandi", show_alert=False)
    chat: Chat = callback.message.chat
    is_forum = getattr(chat, "is_forum", False)
    info = {
        "filter": "forum",
        "chat_id": chat.id,
        "chat_type": chat.type,
        "title": chat.title,
        "is_forum": bool(is_forum),
        "note": "Forum (supergroup with topics)" if is_forum else "Forum emas",
    }
    await send_json_chunks(callback.message, info)


# ─────────────────────────────────────────────
# Callback: filter_my_group — bot qo'shilgan guruhlar
# ─────────────────────────────────────────────
@dp.callback_query(F.data == "filter_my_group")
async def filter_my_group(callback: CallbackQuery):
    await callback.answer("👥 My Group filtri tanlandi", show_alert=False)
    chat: Chat = callback.message.chat
    try:
        member = await bot.get_chat_member(chat.id, (await bot.get_me()).id)
        bot_status = member.status
    except Exception:
        bot_status = "unknown"

    info = {
        "filter": "my_group",
        "chat_id": chat.id,
        "chat_type": chat.type,
        "title": chat.title,
        "bot_status_in_chat": bot_status,
        "note": "Botning ushbu guruhdagi holati",
    }
    await send_json_chunks(callback.message, info)


# ─────────────────────────────────────────────
# Callback: filter_my_channel — bot admin bo'lgan kanallar
# ─────────────────────────────────────────────
@dp.callback_query(F.data == "filter_my_channel")
async def filter_my_channel(callback: CallbackQuery):
    await callback.answer("📢 My Channel filtri tanlandi", show_alert=False)
    chat: Chat = callback.message.chat
    try:
        member = await bot.get_chat_member(chat.id, (await bot.get_me()).id)
        bot_status = member.status
    except Exception:
        bot_status = "unknown"

    info = {
        "filter": "my_channel",
        "chat_id": chat.id,
        "chat_type": chat.type,
        "title": chat.title,
        "bot_status_in_chat": bot_status,
        "note": "Botning ushbu kanaldagi holati",
    }
    await send_json_chunks(callback.message, info)


# ─────────────────────────────────────────────
# Callback: filter_my_forum — bot admin bo'lgan forumlar
# ─────────────────────────────────────────────
@dp.callback_query(F.data == "filter_my_forum")
async def filter_my_forum(callback: CallbackQuery):
    await callback.answer("💬 My Forum filtri tanlandi", show_alert=False)
    chat: Chat = callback.message.chat
    is_forum = getattr(chat, "is_forum", False)
    try:
        member = await bot.get_chat_member(chat.id, (await bot.get_me()).id)
        bot_status = member.status
    except Exception:
        bot_status = "unknown"

    info = {
        "filter": "my_forum",
        "chat_id": chat.id,
        "chat_type": chat.type,
        "title": chat.title,
        "is_forum": bool(is_forum),
        "bot_status_in_chat": bot_status,
        "note": "Botning ushbu forumdagi holati",
    }
    await send_json_chunks(callback.message, info)


# ─────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────
async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())