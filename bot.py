import asyncio
import logging
import json
import os
from datetime import datetime
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message
from dotenv import load_dotenv

load_dotenv()
API_TOKEN = os.getenv("API_TOKEN")

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher()


def convert_to_serializable(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")


@dp.message(Command("start"))
async def send_welcome(message: Message):
    raw_data = {
        "update_id": message.message_id,  
        "message": message.model_dump()   
    }

    raw_json = json.dumps(
        raw_data,
        indent=4,
        ensure_ascii=False,
        default=convert_to_serializable
    )

    for i in range(0, len(raw_json), 3900):
        chunk = raw_json[i:i + 3900]
        await message.answer(
            f"```json\n{chunk}\n```",
            parse_mode="Markdown"
        )

    user_id = message.from_user.id
    os.makedirs("users", exist_ok=True)
    with open(f"users/{user_id}.json", "w", encoding="utf-8") as f:
        json.dump(raw_data, f, indent=4, ensure_ascii=False, default=convert_to_serializable)


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())