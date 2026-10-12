import os
import telebot
from google import genai

# Lee las claves de forma segura desde el servidor en la nube
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

bot = telebot.TeleBot(TELEGRAM_TOKEN)
client = genai.Client(api_key=GEMINI_API_KEY)

# Instrucciones para el comportamiento del bot
SYSTEM_PROMPT = """
Eres A.R.K., el asistente principal de documentación, diseño y programación del videojuego independiente 
Primesis:ORIGINS (un juego de supervivencia de bestias en 3D con mecánicas de territorio, inspirado en Kenshi y Darksiders 2 en su estilo visual, 
desarrollado en Unity con C#). No tengas miedo en preguntar los detalles del juego para armar tu base de datos y tener una dirección clara. 
Ayuda al equipo a estructurar el GDD, definir criaturas, lore, sistemas y código.
Sé directo, realista, técnico, organizado y usa un tono motivador.
"""

@bot.message_handler(func=lambda message: True)
def responder_equipo(message):
    try:
        bot.send_chat_action(message.chat.id, 'typing')
        prompt_completo = f"{SYSTEM_PROMPT}\n\nMensaje del equipo: {message.text}"
        response = client.models.generate_content(
            model="gemini-3.8-flash",
            contents=prompt_completo
        )
        bot.reply_to(message, response.text)
    except Exception as e:
        bot.reply_to(message, f"❌ Ocurrió un error: {e}")

print("🤖 ¡El bot A.R.K. de Primesis está activo y escuchando!")
bot.infinity_polling()
