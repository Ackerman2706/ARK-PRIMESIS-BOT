import os
import threading
from flask import Flask
import telebot
from google import genai

# --- SERVIDOR WEB SECUNDARIO PARA MANTENER VIVO RENDER ---
app = Flask(__name__)

@app.route('/')
def health_check():
    return "A.R.K. Bot online 24/7", 200

def run_web_server():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

# --- CONFIGURACIÓN DEL BOT Y CLIENTE GEMINI ---
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

bot = telebot.TeleBot(TELEGRAM_TOKEN)
client = genai.Client(api_key=GEMINI_API_KEY)

SYSTEM_PROMPT = """
Eres A.R.K., el asistente principal de documentación, diseño, dirección de arte y programación del videojuego independiente 
Primesis:ORIGINS (un juego de supervivencia de bestias en 3D con mecánicas de territorio, inspirado en Kenshi y Darksiders 2 en su estilo visual, 
desarrollado en Unity con C#). No tengas miedo en preguntar los detalles del juego para armar tu base de datos y tener una dirección clara.

Según la carpeta o la solicitud del equipo, adopta el rol profesional correspondiente:

1. PROGRAMADOR SENIOR (C# / UNITY):
   - Si te pasan código o consultas técnicas, actúa como un Ingeniero de Software experto.
   - Revisa arquitectura, optimización (rendimiento/GC), uso de ScriptableObjects y máquinas de estados.
   - Entrega código C# limpio, comentado y listo para producción.

2. DIRECTOR DE ARTE Y DISEÑADOR GRÁFICO (MULTIMODAL):
   - Si te comparten una imagen o diseño, actúa como un Director de Arte profesional.
   - Evalúa proporciones anatómicas de bestias, siluetas, paleta de colores y estilo estilizado/fantasía oscura tipo Joe Madureira / Darksiders 2.

3. LEAD GAME DESIGNER (GDD / LORE):
   - Ayuda a estructurar el GDD, mecánicas de territorio, ecología de criaturas y balance general.

Sé directo, realista, técnico, organizado y usa un tono motivador.
"""

# Manejador para Mensajes de Texto
@bot.message_handler(func=lambda message: True, content_types=['text'])
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

# Manejador para Fotos e Imágenes
@bot.message_handler(content_types=['photo'])
def responder_foto(message):
    try:
        bot.send_chat_action(message.chat.id, 'typing')
        
        # Descargar la foto enviada en mayor resolución
        fileID = message.photo[-1].file_id
        file_info = bot.get_file(fileID)
        downloaded_file = bot.download_file(file_info.file_path)
        
        image_path = "temp_image.jpg"
        with open(image_path, 'wb') as new_file:
            new_file.write(downloaded_file)
            
        uploaded_file = client.files.upload(file=image_path)
        
        caption = message.caption if message.caption else "Analiza esta imagen para el proyecto Primesis:ORIGINS bajo tu rol de Director de Arte / Diseñador Gráfico."
        prompt_completo = f"{SYSTEM_PROMPT}\n\n[Consulta de Imagen / Diseño]: {caption}"
        
        response = client.models.generate_content(
            model="gemini-3.8-flash",
            contents=[uploaded_file, prompt_completo]
        )
        
        bot.reply_to(message, response.text)
        
        if os.path.exists(image_path):
            os.remove(image_path)
            
    except Exception as e:
        bot.reply_to(message, f"❌ Ocurrió un error al procesar la imagen: {e}")

if __name__ == "__main__":
    # Iniciar servidor Flask en hilo secundario
    threading.Thread(target=run_web_server, daemon=True).start()
    
    print("🤖 ¡El bot A.R.K. de Primesis está activo y escuchando!")
    bot.infinity_polling()
