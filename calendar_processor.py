import logging
import datetime
from calendar_google import GoogleCalendar # Asume que calendar_google.py está accesible
from gpt import GPTClient # Asume que gpt.py está accesible

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def format_event_details(event):
    """Formatea los detalles de un evento individual para el prompt de GPT."""
    details = []
    start_info = event.get('start', {})
    end_info = event.get('end', {})
    start_time = start_info.get('dateTime', start_info.get('date'))
    end_time = end_info.get('dateTime', end_info.get('date'))

    # Determinar si es todo el día o tiene hora específica
    if 'T' in start_time: # Tiene hora específica
        start_dt = datetime.datetime.fromisoformat(start_time)
        end_dt = datetime.datetime.fromisoformat(end_time)
        time_str = f"{start_dt.strftime('%H:%M')} - {end_dt.strftime('%H:%M')}"
    else: # Evento de todo el día
        time_str = "Todo el día"

    details.append(f"[{event.get('calendar_summary', 'Desconocido')}] {time_str}: {event.get('summary', 'Sin título')}")
    if event.get('description'):
        # Limpiar descripción para evitar saltos de línea excesivos en el prompt
        description = event['description'].replace('\n', ' ').replace('\r', '')
        details.append(f"  Descripción: {description}")
    if event.get('location'):
        details.append(f"  Ubicación: {event['location']}")
    return "\n".join(details)

def format_calendar_data_for_gpt(events_by_day, start_date, end_date):
    """Convierte el diccionario de eventos en un string formateado para el prompt de GPT."""
    prompt_lines = [f"Eventos de la semana del {start_date.strftime('%Y-%m-%d')} al {end_date.strftime('%Y-%m-%d')}:\n"]
    dias_semana = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]

    current_date = start_date
    while current_date <= end_date:
        date_str = current_date.strftime('%Y-%m-%d')
        day_name = dias_semana[current_date.weekday()]
        prompt_lines.append(f"--- {day_name.upper()} {date_str} ---")
        if date_str in events_by_day and events_by_day[date_str]:
            for event in events_by_day[date_str]:
                prompt_lines.append(format_event_details(event))
        else:
            prompt_lines.append("Sin eventos.")
        prompt_lines.append("") # Línea en blanco para separar días
        current_date += datetime.timedelta(days=1)

    return "\n".join(prompt_lines)

def get_formatted_next_week_schedule():
    """
    Obtiene los eventos de la próxima semana de calendarios específicos del Google Calendar,
    y los formatea usando un asistente GPT. Imprime los datos crudos antes del formateo GPT.

    Returns:
        str: El calendario formateado por GPT, o un mensaje de error.
    """
    try:
        # 1. Calcular fechas de la próxima semana (Lunes a Domingo)
        today = datetime.date.today()
        days_until_monday = (0 - today.weekday() + 7) % 7
        if days_until_monday == 0: # Si hoy es lunes, queremos el *próximo* lunes
             days_until_monday = 7
        next_monday = today + datetime.timedelta(days_until_monday)
        next_sunday = next_monday + datetime.timedelta(days=6)
        start_date_str = next_monday.strftime('%Y-%m-%d')
        end_date_str = next_sunday.strftime('%Y-%m-%d')
        logging.info(f"Calculando calendario para la semana: {start_date_str} a {end_date_str}")

        # --- Change: Define calendars to filter ---
        calendars_to_include = ["diego.arredondom@gmail.com", "diego.arredondo@cenia.cl"]
        # --- End Change ---

        # 2. Obtener eventos del calendario
        logging.info("Inicializando Google Calendar...")
        gc = GoogleCalendar() # Asume que credentials.json y token.json están configurados
        logging.info(f"Buscando eventos en Google Calendar para: {', '.join(calendars_to_include)}...")
        # --- Change: Pass filter list to buscar_eventos_todos ---
        events_data = gc.buscar_eventos_todos(start_date_str, end_date_str, filter_summaries=calendars_to_include)
        # --- End Change ---
        logging.info(f"Se encontraron eventos para {len(events_data)} días en el rango para los calendarios especificados.")

        # 3. Formatear datos para GPT
        calendar_prompt_input = format_calendar_data_for_gpt(events_data, next_monday, next_sunday)

        # --- Change: Print raw data before sending to GPT ---
        print("\n===== DATOS CRUDOS DEL CALENDARIO (PARA GPT) =====")
        print(calendar_prompt_input)
        print("=================================================\n")
        # --- End Change ---

        # 4. Consultar a GPT para formateo final
        logging.info("Inicializando GPTClient...")
        gpt_client = GPTClient()
        formatter_assistant = "calendar_formatter"

        if formatter_assistant not in gpt_client.assistants:
            error_msg = f"Error: Asistente '{formatter_assistant}' no encontrado. Asegúrate de que 'asistentes/calendar_formatter.md' existe."
            logging.error(error_msg)
            # --- Change: Return raw data if formatter is missing ---
            print("ADVERTENCIA: Asistente formateador no encontrado. Devolviendo datos crudos.")
            return calendar_prompt_input
            # --- End Change ---

        logging.info(f"Consultando al asistente '{formatter_assistant}' para formatear el calendario...")
        formatted_schedule = gpt_client.query(formatter_assistant, calendar_prompt_input)
        logging.info("Calendario formateado recibido de GPT.")

        return formatted_schedule

    except Exception as e:
        logging.error(f"Error en el proceso de obtención y formato del calendario: {e}", exc_info=True)
        return f"Error al generar el calendario formateado: {e}"

if __name__ == "__main__":
    print("Obteniendo y formateando el calendario de la próxima semana...")
    schedule = get_formatted_next_week_schedule()
    print("\n===== CALENDARIO FORMATEADO DE LA PRÓXIMA SEMANA =====")
    print(schedule)
    print("=====================================================")
