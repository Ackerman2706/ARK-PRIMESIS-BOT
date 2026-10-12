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
Eres A.R.K., la Inteligencia Artificial central de soporte para desarrollo, arquitectura, arte y documentación del videojuego independiente Primesis:ORIGINS. 

[CONTEXTO DEL PROYECTO]
- Título: Primesis:ORIGINS.
- Género: Supervivencia 3D de bestias / criaturas jugables, simulación de ecosistemas y guerras de territorio por bandas/facciones.
- Inspiraciones Clave:
  • Mecánicas y Libertad: Kenshi (ecosistema hostil, progresión orgánicamente dura).
  • Control Territorial: Grand Theft Auto: San Andreas (mecánicas de pandillas y control de zonas).
  • Narrativa Ambiental: Hollow Knight (lore descubierto por el entorno y detalles biomecanicos).
  • Estilo Visual: Fantasía oscura estilizada, proporciones exageradas y siluetas marcadas (Joe Madureira / Darksiders II).
- Stack Técnico: Unity (versión 2021 LTS), lenguaje C# modular y Blender (2.9+). 
- Criterio Técnico: Optimización estricta. Cero basura innecesaria para el Garbage Collector (GC), uso masivo de ScriptableObjects, Eventos/Delegados C# decoupled, y Máquinas de Estados Finitas (FSM).

[ROLES PROFESIONALES OBLIGATORIOS]
Según el contexto de la solicitud, asume con máxima rigurosidad uno o varios de estos roles:

1. LEAD SOFTWARE ENGINEER (C# / UNITY):
   - Genera código C# limpio, optimizado, modular, comentado y directo para producción.
   - Aplica buenas prácticas: evitar `Update()` innecesarios, usar asignación de memoria eficiente y caching de componentes (`GetComponent`).
   - Sigue patrones de arquitectura limpios adecuados para un juego de bestias y simulación de territorios.

2. DIRECTOR DE ARTE Y DISEÑO MULTIMODAL:
   - Al analizar imágenes, conceptos o modelos 3D, evalúa: silueta, legibilidad de la criatura, proporciones anatómicas estilizadas y paletas de color con estética fantasía oscura.
   - Proporciona críticas técnicas sobre la topología para animación en Blender y el paso a Unity.

3. LEAD GAME DESIGNER Y GUIONISTA DE LORE:
   - Estructura documentaciones (GDD) en formato claro, jerárquico y usable.
   - Diseña mecánicas de simulación de territorio, comportamiento animal y balance del ecosistema sin rodeos ni relleno.

[REGLAS DE ACTUACIÓN]
- Si una instrucción técnica no está clara o faltan variables del proyecto, HAZ las preguntas técnicas necesarias antes de asumir datos.
- Mantén un tono profesional, técnico, directo y enfocado en producción real de videojuegos.
"""
import time

def generar_respuesta_con_fallback(contents, retries=3, delay=2):
    """Reintenta automáticamente hasta 3 veces con gemini-3.5-flash-lite si hay picos de demanda."""
    for intento in range(retries):
        try:
            return client.models.generate_content(
                model="gemini-3.5-flash-lite",
                contents=contents
            )
        except Exception as e:
            # Si es el tercer y último intento, lanza el error
            if intento == retries - 1:
                raise e
            # Espera antes de volver a intentar en el mismo modelo
            time.sleep(delay * (intento + 1))

def enviar_respuesta_larga(message, texto):
    """Divide los mensajes que superen el límite de Telegram (4096 caracteres) en fragmentos seguros."""
    limite = 4000
    if len(texto) <= limite:
        bot.reply_to(message, texto)
    else:
        trozos = [texto[i:i+limite] for i in range(0, len(texto), limite)]
        for trozo in trozos:
            bot.send_message(message.chat.id, trozo)

# Manejador para Mensajes de Texto
@bot.message_handler(func=lambda message: True, content_types=['text'])
def responder_equipo(message):
    try:
        bot.send_chat_action(message.chat.id, 'typing')
        prompt_completo = f"{SYSTEM_PROMPT}\n\nMensaje del equipo: {message.text}"
        response = generar_respuesta_con_fallback(prompt_completo)
        enviar_respuesta_larga(message, response.text)
    except Exception as e:
        bot.reply_to(message, f"❌ Ocurrió un error: {e}")

# Manejador para Fotos e Imágenes
@bot.message_handler(content_types=['photo'])
def responder_foto(message):
    try:
        bot.send_chat_action(message.chat.id, 'typing')
        
        fileID = message.photo[-1].file_id
        file_info = bot.get_file(fileID)
        downloaded_file = bot.download_file(file_info.file_path)
        
        image_path = "temp_image.jpg"
        with open(image_path, 'wb') as new_file:
            new_file.write(downloaded_file)
            
        uploaded_file = client.files.upload(file=image_path)
        
        caption = message.caption if message.caption else "Analiza esta imagen para el proyecto Primesis:ORIGINS bajo tu rol de Director de Arte / Diseñador Gráfico."
        prompt_completo = f"{SYSTEM_PROMPT}\n\n[Consulta de Imagen / Diseño]: {caption}"
        
        response = generar_respuesta_con_fallback([uploaded_file, prompt_completo])
        enviar_respuesta_larga(message, response.text)
        
        if os.path.exists(image_path):
            os.remove(image_path)
            
    except Exception as e:
        bot.reply_to(message, f"❌ Ocurrió un error al procesar la imagen: {e}")

# Manejador para Archivos de Texto / Documentos (.txt, .cs, .md, etc.)
@bot.message_handler(content_types=['document'])
def responder_documento(message):
    try:
        bot.send_chat_action(message.chat.id, 'typing')
        
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        file_name = message.document.file_name
        file_path = f"temp_{file_name}"
        
        with open(file_path, 'wb') as new_file:
            new_file.write(downloaded_file)
            
        # Subir el archivo directamente a la API de Gemini (soporta código, textos, etc.)
        uploaded_file = client.files.upload(file=file_path)
        
        caption = message.caption if message.caption else f"Analiza este archivo ({file_name}) para Primesis:ORIGINS."
        prompt_completo = f"{SYSTEM_PROMPT}\n\n[Archivo adjunto del equipo: {file_name}]\nInstrucción: {caption}"
        
        response = generar_respuesta_con_fallback([uploaded_file, prompt_completo])
        enviar_respuesta_larga(message, response.text)
        
        if os.path.exists(file_path):
            os.remove(file_path)
            
    except Exception as e:
        bot.reply_to(message, f"❌ Ocurrió un error al procesar el archivo: {e}")

if __name__ == "__main__":
    threading.Thread(target=run_web_server, daemon=True).start()
    print("🤖 ¡El bot A.R.K. de Primesis está activo y escuchando!")
    bot.infinity_polling()
