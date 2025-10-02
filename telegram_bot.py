#!/usr/bin/env python3
"""
Bot de Telegram personalizado que se conecta a RASA via API REST
Este bot evita el problema del event loop cerrado en RASA 3.6.19
"""
import os
import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
import aiohttp

# Configuración desde variables de entorno
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
RASA_URL = os.getenv("RASA_URL")

if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_TOKEN no está configurado en las variables de entorno")
if not RASA_URL:
    raise ValueError("RASA_URL no está configurado en las variables de entorno")

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Inicializar bot y dispatcher
bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()


async def send_message_to_rasa(sender_id: str, message: str):
    """Envía mensaje a RASA y obtiene respuesta"""
    payload = {
        "sender": sender_id,
        "message": message
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(RASA_URL, json=payload) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.error(f"Error de RASA: {response.status}")
                    return []
    except Exception as e:
        logger.error(f"Error conectando con RASA: {e}")
        return []


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    """Maneja el comando /start"""
    sender_id = str(message.from_user.id)
    responses = await send_message_to_rasa(sender_id, "/start")

    if not responses:
        await message.answer("¡Hola! Soy tu asistente de ventas. ¿En qué puedo ayudarte?")
    else:
        for response in responses:
            if "text" in response:
                await message.answer(response["text"])


@dp.message()
async def handle_message(message: types.Message):
    """Maneja todos los mensajes de texto"""
    sender_id = str(message.from_user.id)
    user_message = message.text

    logger.info(f"Usuario {sender_id}: {user_message}")

    # Enviar mensaje a RASA
    responses = await send_message_to_rasa(sender_id, user_message)

    # Enviar respuestas al usuario
    if not responses:
        await message.answer("Lo siento, hubo un problema. Por favor intenta de nuevo.")
    else:
        for response in responses:
            if "text" in response:
                await message.answer(response["text"])
            elif "image" in response:
                await message.answer_photo(response["image"])


async def main():
    """Función principal"""
    logger.info("Iniciando bot de Telegram...")
    logger.info(f"Conectando con RASA en {RASA_URL}")

    # Eliminar webhook si existe
    await bot.delete_webhook(drop_pending_updates=True)

    # Iniciar polling
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
