import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware # Para permitir peticiones desde un front (opcional pero común)
import uvicorn
import datetime # Necesario para calcular fechas
import os # Necesario para trabajar con archivos
from pydantic import BaseModel # Para definir el modelo de respuesta (opcional pero bueno)

# Importar las funciones principales de tus otros scripts
try:
    from main_orchestrator import generate_integrated_schedule
    from calendar_google import GoogleCalendar
    # --- Change: Import function from calendar_processor ---
    from calendar_processor import get_formatted_next_week_schedule
    # --- End Change ---
except ImportError as e:
    logging.error(f"Error al importar módulos necesarios: {e}. Asegúrate de que los archivos .py estén en el directorio correcto.")
    # Podrías decidir salir o manejar esto de otra forma si la API no puede funcionar
    raise

# Configurar logging básico para la API
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - API - %(message)s')

# Crear instancia de FastAPI
app = FastAPI(
    title="Personal Coach Backend API",
    description="API para generar y gestionar la planificación semanal.",
    version="1.0.0"
)

# --- Change: Modify CORS settings ---
# Configurar CORS para permitir CUALQUIER origen (para desarrollo/ngrok)
# ¡¡¡RECUERDA RESTRINGIR ESTO EN PRODUCCIÓN!!!
origins = ["*"] # Permitir todos los orígenes

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins, # Cambiado a ["*"]
    allow_credentials=True,
    allow_methods=["*"], # Permitir todos los métodos (GET, POST, DELETE, OPTIONS, etc.)
    allow_headers=["*"], # Permitir todos los headers
)
# --- End Change ---

# --- Constante para el directorio de asistentes ---
ASSISTANTS_BASE_DIR = "asistentes"

# --- Modelo de respuesta para el prompt (opcional) ---
class AssistantPromptResponse(BaseModel):
    assistant_name: str
    content: str

# --- Change: Add response model for formatted schedule ---
class FormattedScheduleResponse(BaseModel):
    formatted_schedule: str
# --- End Change ---

# --- Endpoints de la API ---

@app.get("/", summary="Health Check", description="Endpoint básico para verificar si la API está funcionando.")
async def read_root():
    """
    Endpoint raíz para verificar el estado de la API.
    """
    logging.info("Health check endpoint '/' llamado.")
    return {"status": "Personal Coach API is running!"}

@app.post("/generate-schedule", summary="Generar Planificación Semanal", description="Ejecuta el orquestador completo para generar la planificación y crear eventos en Google Calendar.")
async def generate_schedule_endpoint():
    """
    Llama a la función `generate_integrated_schedule` del orquestador.
    Devuelve el calendario en texto o un error HTTP.
    """
    logging.info("Endpoint '/generate-schedule' llamado.")
    try:
        # Ejecutar la lógica principal del orquestador
        # Nota: Esta llamada puede ser bloqueante y tardar. Considera ejecutarla en un threadpool si es necesario.
        schedule_result = generate_integrated_schedule()

        # Verificar si el resultado indica un error interno
        if "Error:" in schedule_result:
            logging.error(f"Error interno al generar el calendario: {schedule_result}")
            # Devolver un error HTTP 500 (Internal Server Error)
            raise HTTPException(status_code=500, detail=schedule_result)

        logging.info("Planificación generada exitosamente.")
        # Devolver el resultado exitoso
        return {"schedule": schedule_result}

    except HTTPException as http_exc:
        # Re-lanzar excepciones HTTP ya manejadas
        raise http_exc
    except Exception as e:
        logging.exception("Error inesperado en el endpoint /generate-schedule.") # Log con traceback
        # Capturar cualquier otro error inesperado
        raise HTTPException(status_code=500, detail=f"Error inesperado del servidor: {e}")

@app.delete("/delete-schedule", summary="Borrar Planificación Semanal", description="Borra TODOS los eventos de la próxima semana en el calendario 'PersonalCoach'.")
async def delete_schedule_endpoint():
    """
    Borra TODOS los eventos de la próxima semana en el calendario 'PersonalCoach',
    saltando la confirmación interactiva. Devuelve el número de eventos borrados.
    """
    logging.info("Endpoint '/delete-schedule' llamado.")
    target_calendar = 'PersonalCoach'
    try:
        # Calcular fechas de la próxima semana aquí mismo
        today = datetime.date.today()
        days_until_monday = (0 - today.weekday() + 7) % 7
        if days_until_monday == 0: days_until_monday = 7
        next_monday = today + datetime.timedelta(days=days_until_monday)
        next_sunday = next_monday + datetime.timedelta(days=6)
        start_date_str = next_monday.strftime('%Y-%m-%d')
        end_date_str = next_sunday.strftime('%Y-%m-%d')

        # Inicializar GoogleCalendar y llamar directamente a delete_events_in_range
        gc = GoogleCalendar()
        deleted_count = gc.delete_events_in_range(
            start_date_str=start_date_str,
            end_date_str=end_date_str,
            calendar_target=target_calendar,
            skip_confirmation=True # ¡Importante para la API!
        )

        logging.info(f"Borrado completado a través de API. Eventos borrados: {deleted_count}")
        # Devolver el resultado al frontend
        return {"message": f"Borrado completado para la semana {start_date_str} a {end_date_str}.", "deleted_count": deleted_count}

    except Exception as e:
        logging.exception("Error inesperado en el endpoint /delete-schedule.") # Log con traceback
        # Capturar cualquier error inesperado
        raise HTTPException(status_code=500, detail=f"Error inesperado del servidor durante el borrado: {e}")

# --- Change: Add endpoint to get assistant prompt ---
@app.get("/assistant-prompt/{assistant_name}",
         response_model=AssistantPromptResponse, # Usa el modelo de respuesta
         summary="Obtener Prompt de Asistente",
         description="Devuelve el contenido del archivo Markdown para el asistente especificado.")
async def get_assistant_prompt(assistant_name: str):
    """
    Busca y devuelve el contenido del archivo .md correspondiente al assistant_name.
    """
    logging.info(f"Solicitud recibida para el prompt del asistente: '{assistant_name}'")
    # Construir la ruta esperada del archivo
    # ¡Importante! Asegurarse de que assistant_name no contenga caracteres maliciosos (ej. '../')
    # Para este caso, asumimos nombres simples. Podrías añadir validación/sanitización.
    file_path = os.path.join(ASSISTANTS_BASE_DIR, f"{assistant_name}.md")
    logging.debug(f"Buscando archivo en: {file_path}")

    if not os.path.exists(file_path) or not os.path.isfile(file_path):
        logging.warning(f"Archivo de prompt no encontrado: {file_path}")
        raise HTTPException(status_code=404, detail=f"Prompt para el asistente '{assistant_name}' no encontrado.")

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        logging.info(f"Prompt para '{assistant_name}' leído exitosamente.")
        return AssistantPromptResponse(assistant_name=assistant_name, content=content)
    except Exception as e:
        logging.exception(f"Error al leer el archivo de prompt: {file_path}")
        raise HTTPException(status_code=500, detail=f"Error interno al leer el prompt para '{assistant_name}'.")
# --- End Change ---

# --- Change: Add endpoint for formatted schedule ---
@app.get("/formatted-schedule",
         response_model=FormattedScheduleResponse,
         summary="Obtener Calendario Formateado (GPT)",
         description="Obtiene los eventos de Google Calendar de la próxima semana y los formatea usando el asistente 'calendar_formatter'.")
async def get_formatted_schedule_endpoint():
    """
    Llama a la función `get_formatted_next_week_schedule` y devuelve el resultado.
    """
    logging.info("Endpoint '/formatted-schedule' llamado.")
    try:
        # Llamar a la función que obtiene y formatea el calendario
        # Esta función ya maneja la interacción con Google Calendar y GPT
        formatted_schedule_result = get_formatted_next_week_schedule()

        # Verificar si la función devolvió un error
        if "Error:" in formatted_schedule_result:
            logging.error(f"Error interno al obtener/formatear el calendario: {formatted_schedule_result}")
            raise HTTPException(status_code=500, detail=formatted_schedule_result)

        logging.info("Calendario formateado obtenido exitosamente.")
        # Devolver el resultado en el modelo de respuesta esperado
        return FormattedScheduleResponse(formatted_schedule=formatted_schedule_result)

    except HTTPException as http_exc:
        # Re-lanzar excepciones HTTP ya manejadas
        raise http_exc
    except Exception as e:
        logging.exception("Error inesperado en el endpoint /formatted-schedule.")
        raise HTTPException(status_code=500, detail=f"Error inesperado del servidor al obtener el calendario formateado: {e}")
# --- End Change ---

# --- Ejecución con Uvicorn (si se ejecuta este archivo directamente) ---
if __name__ == "__main__":
    print("Iniciando servidor FastAPI con Uvicorn...")
    print("Accede a la documentación interactiva en http://127.0.0.1:8000/docs")
    # Ejecutar Uvicorn programáticamente
    # host="0.0.0.0" permite conexiones desde otras máquinas en la red local
    # host="127.0.0.1" solo permite conexiones desde la misma máquina
    uvicorn.run("api:app", host="127.0.0.1", port=8000, reload=True)
    # reload=True es útil para desarrollo, recarga el servidor si cambias el código.
    # Quítalo o ponlo a False en producción.
