import os
import threading
import time
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

# --- CONFIGURACIÓN DEL BOT Y MÚLTIPLES API KEYS DE GEMINI ---
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")

# Cargamos una lista con las múltiples API keys configuradas en Render
api_keys = [
    os.environ.get("GEMINI_API_KEY_1"),
    os.environ.get("GEMINI_API_KEY_2"),
    os.environ.get("GEMINI_API_KEY_3"),
    os.environ.get("GEMINI_API_KEY_4")
]

# Filtramos para asegurar que solo se usen las que estén configuradas y no estén vacías
api_keys = [key for key in api_keys if key]

if not api_keys:
    raise ValueError("⚠️ No se encontró ninguna API Key configurada en las variables de entorno.")

bot = telebot.TeleBot(TELEGRAM_TOKEN)

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

def generar_respuesta_con_fallback(contents, delay=1):
    """
    Rota automáticamente entre las múltiples API Keys disponibles si una falla o se agota.
    Usa el modelo optimizado gemini-3.5-flash-lite.
    """
    total_keys = len(api_keys)
    
    for key_index, api_key in enumerate(api_keys):
        try:
            # Creamos un cliente temporal con la clave actual en turno
            temp_client = genai.Client(api_key=api_key)
            
            # Intentamos la generación con el modelo flash-lite
            return temp_client.models.generate_content(
                model="gemini-3.5-flash-lite",
                contents=contents
            )
        except Exception as e:
            print(f"⚠️ La API Key #{key_index + 1} falló o se agotó: {e}")
            
            # Si era la última llave de la lista, lanzamos el error definitivo
            if key_index == total_keys - 1:
                raise Exception("❌ Todas las API Keys configuradas se han agotado o han presentado errores.")
            
            # Breve pausa antes de saltar a la siguiente clave de la cuenta de otro miembro
            time.sleep(delay)

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
    image_path = "temp_image.jpg"
    try:
        bot.send_chat_action(message.chat.id, 'typing')
        
        fileID = message.photo[-1].file_id
        file_info = bot.get_file(fileID)
        downloaded_file = bot.download_file(file_info.file_path)
        
        with open(image_path, 'wb') as new_file:
            new_file.write(downloaded_file)
            
        # Nota: Para subir archivos a Gemini usamos el cliente genérico o el primero disponible
        temp_client_upload = genai.Client(api_key=api_keys[0])
        uploaded_file = temp_client_upload.files.upload(file=image_path)
        
        caption = message.caption if message.caption else "Analiza esta imagen para el proyecto Primesis:ORIGINS bajo tu rol de Director de Arte / Diseñador Gráfico."
        prompt_completo = f"{SYSTEM_PROMPT}\n\n[Consulta de Imagen / Diseño]: {caption}"
        
        response = generar_respuesta_con_fallback([uploaded_file, prompt_completo])
        enviar_respuesta_larga(message, response.text)
        
    except Exception as e:
        bot.reply_to(message, f"❌ Ocurrió un error al procesar la imagen: {e}")
    finally:
        if os.path.exists(image_path):
            os.remove(image_path)

# Manejador para Archivos de Texto / Documentos (.txt, .cs, .md, etc.)
@bot.message_handler(content_types=['document'])
def responder_documento(message):
    file_path = f"temp_{message.document.file_name}"
    try:
        bot.send_chat_action(message.chat.id, 'typing')
        
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        file_name = message.document.file_name
        with open(file_path, 'wb') as new_file:
            new_file.write(downloaded_file)
            
        temp_client_upload = genai.Client(api_key=api_keys[0])
        uploaded_file = temp_client_upload.files.upload(file=file_path)
        
        caption = message.caption if message.caption else f"Analiza este archivo ({file_name}) para Primesis:ORIGINS."
        prompt_completo = f"{SYSTEM_PROMPT}\n\n[Archivo adjunto del equipo: {file_name}]\nInstrucción: {caption}"
        
        response = generar_respuesta_con_fallback([uploaded_file, prompt_completo])
        enviar_respuesta_larga(message, response.text)
        
    except Exception as e:
        bot.reply_to(message, f"❌ Ocurrió un error al procesar el archivo: {e}")
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

if __name__ == "__main__":
    threading.Thread(target=run_web_server, daemon=True).start()
    print("🤖 ¡El bot A.R.K. de Primesis está activo con rotación de API Keys!")
    bot.infinity_polling()
