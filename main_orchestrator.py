import logging
import re
import datetime
from weekly_planner import get_weekly_plan
from calendar_processor import get_formatted_next_week_schedule
from gpt import GPTClient
from calendar_google import GoogleCalendar
try:
    from tzlocal import get_localzone
    local_tz = get_localzone()
    logging.info(f"Timezone local detectada: {local_tz}")
except ImportError:
    local_tz = None
    logging.warning("tzlocal no instalado. No se podrá asignar timezone local a los eventos creados.")
except Exception as tz_err: # Capturar otros posibles errores de tzlocal
    local_tz = None
    logging.warning(f"Error al inicializar tzlocal: {tz_err}. No se usará timezone local.")


# --- Change: Set logging level to DEBUG for detailed output ---
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
# --- End Change ---

def parse_and_create_events(schedule_string: str, gc: GoogleCalendar, target_calendar: str = 'PersonalCoach'):
    """
    Parses the integrated schedule string and creates Google Calendar events for entries marked with [PLAN].
    Includes detailed logging for debugging.
    """
    logging.info(f"Iniciando parseo del calendario integrado para crear eventos en '{target_calendar}'.")
    # --- Change: Adjust event_pattern to match leading '* ' ---
    # Original: r"\*\*\s*(\d{2}:\d{2})\s*-\s*(\d{2}:\d{2})\s*\*\*:\s*\[PLAN\]\s*(.*)"
    # Nuevo: Añadir `\s*\*\s*` al principio para capturar el asterisco y espacios opcionales
    event_pattern = re.compile(r"\s*\*\s*\*\*\s*(\d{2}:\d{2})\s*-\s*(\d{2}:\d{2})\s*\*\*:\s*\[PLAN\]\s*(.*)")
    # --- End Change ---
    desc_pattern = re.compile(r"\s*\*\s*Descripción:\s*(.*)")
    loc_pattern = re.compile(r"\s*\*\s*Ubicación:\s*(.*)")
    # Regex más robusto para la fecha, buscando el formato YYYY-MM-DD en la línea del día
    date_pattern = re.compile(r"(\d{4}-\d{2}-\d{2})")

    current_date_str = None
    created_count = 0
    lines = schedule_string.splitlines()
    logging.debug(f"Número total de líneas a parsear: {len(lines)}")

    for i, line in enumerate(lines):
        line = line.strip() # Limpiar espacios al inicio/final
        logging.debug(f"Procesando línea {i+1}: '{line}'")

        # Intentar encontrar una fecha en la línea
        date_match = date_pattern.search(line)
        if date_match and "**" in line: # Asegurarse de que sea la línea del día (heurística)
            new_date_str = date_match.group(1)
            if new_date_str != current_date_str:
                current_date_str = new_date_str
                logging.info(f"Nueva fecha detectada: {current_date_str}")
            continue # Pasar a la siguiente línea después de encontrar la fecha

        if not current_date_str:
            logging.debug("Saltando línea (aún no se encontró una fecha válida).")
            continue

        # Intentar encontrar un evento [PLAN]
        # --- Change: Use re.search instead of re.match for flexibility ---
        event_match = event_pattern.search(line) # Usar search() permite que el patrón esté en cualquier parte de la línea (aunque aquí coincide desde el inicio con el ajuste)
        # --- End Change ---
        if event_match:
            start_time_str, end_time_str, summary = event_match.groups()
            summary = summary.strip()
            description = None
            location = None
            logging.info(f"¡Evento [PLAN] detectado!: {current_date_str} {start_time_str}-{end_time_str} '{summary}'")

            # Buscar descripción y ubicación en las líneas siguientes (mejorado)
            lookahead_index = i + 1
            while lookahead_index < len(lines) and lines[lookahead_index].strip().startswith("*"):
                next_line_stripped = lines[lookahead_index].strip()
                desc_match = desc_pattern.match(next_line_stripped)
                if desc_match:
                    description = desc_match.group(1).strip()
                    logging.debug(f"  Descripción encontrada: '{description}'")
                else:
                    loc_match = loc_pattern.match(next_line_stripped)
                    if loc_match:
                        location = loc_match.group(1).strip()
                        logging.debug(f"  Ubicación encontrada: '{location}'")
                lookahead_index += 1


            try:
                logging.debug(f"  Intentando parsear: Fecha='{current_date_str}', Inicio='{start_time_str}', Fin='{end_time_str}'")
                start_dt_naive = datetime.datetime.strptime(f"{current_date_str} {start_time_str}", "%Y-%m-%d %H:%M")
                end_dt_naive = datetime.datetime.strptime(f"{current_date_str} {end_time_str}", "%Y-%m-%d %H:%M")
                logging.debug(f"  Datetimes naive creados: Inicio={start_dt_naive}, Fin={end_dt_naive}")

                start_dt_aware = start_dt_naive
                end_dt_aware = end_dt_naive
                if local_tz:
                    try:
                        start_dt_aware = start_dt_naive.replace(tzinfo=local_tz)
                        end_dt_aware = end_dt_naive.replace(tzinfo=local_tz)
                        logging.debug(f"  Datetimes aware creados: Inicio={start_dt_aware}, Fin={end_dt_aware}")
                    except Exception as tz_apply_err:
                         logging.error(f"  Error al aplicar timezone a {start_dt_naive}/{end_dt_naive}: {tz_apply_err}. Usando naive.")
                         # Se usarán los naive definidos antes del bloque if
                else:
                    logging.warning("  Creando evento sin timezone explícita (tzlocal no disponible/falló).")

                logging.debug(f"  Llamando a gc.create_event con: summary='{summary}', start='{start_dt_aware}', end='{end_dt_aware}', desc='{description}', loc='{location}', target='{target_calendar}'")
                created = gc.create_event(
                    summary=summary,
                    start_datetime=start_dt_aware,
                    end_datetime=end_dt_aware,
                    description=description,
                    location=location,
                    calendar_target=target_calendar
                )
                if created:
                    created_count += 1
                    logging.info(f"  -> Evento '{summary}' CREADO exitosamente en Google Calendar.")
                else:
                    logging.warning(f"  -> Llamada a create_event para '{summary}' NO retornó un evento (posible fallo, revisar logs de GoogleCalendar).")

            except ValueError as ve:
                logging.error(f"  Error de formato de fecha/hora para evento '{summary}' en {current_date_str}: {ve}")
            except Exception as e:
                logging.error(f"  Error inesperado al procesar/crear evento '{summary}': {e}", exc_info=True) # Log con traceback
        # --- Change: Log if line didn't match date or event pattern ---
        elif not line.startswith("*   **Ubicaciones Principales:") and not line.startswith("*   **Eventos:") and line and not line.startswith("**"):
             logging.debug(f"Línea no reconocida como fecha, evento [PLAN] o cabecera: '{line}'")
        # --- End Change ---


    logging.info(f"Parseo completado. Intentos de creación de eventos [PLAN]: {created_count}") # Ajustado para reflejar intentos


def generate_integrated_schedule():
    # ... (Código inicial sin cambios: obtener plan, obtener calendario, preparar prompt, consultar integrador) ...
    try:
        logging.info("Iniciando la obtención de la planificación semanal recomendada...")
        recommended_plan = get_weekly_plan()
        if "Error:" in recommended_plan:
            logging.error(f"Fallo al obtener la planificación recomendada: {recommended_plan}")
            return f"Error al obtener la planificación recomendada: {recommended_plan}"
        logging.info("Planificación semanal recomendada obtenida.")

        logging.info("Iniciando la obtención del calendario formateado de la próxima semana...")
        existing_schedule_raw = get_formatted_next_week_schedule()
        if "Error:" in existing_schedule_raw:
             logging.error(f"Fallo al obtener el calendario existente: {existing_schedule_raw}")
             return f"Error al obtener el calendario existente: {existing_schedule_raw}"
        logging.info("Calendario existente formateado obtenido.")

        integrator_assistant_name = "schedule_integrator"
        integration_prompt = f"""
**1. PLANIFICACIÓN SEMANAL RECOMENDADA:**

{recommended_plan}

---

**2. CALENDARIO EXISTENTE DE LA PRÓXIMA SEMANA (FORMATEADO):**

{existing_schedule_raw}

---

**INSTRUCCIÓN FINAL:** Por favor, integra la planificación recomendada en el calendario existente siguiendo las reglas especificadas en tu prompt base. Genera el calendario final detallado y aumentado.
"""
        logging.debug("Prompt preparado para el asistente integrador.")

        logging.info("Inicializando GPTClient para la integración final...")
        gpt_client = GPTClient()
        if integrator_assistant_name not in gpt_client.assistants:
            error_msg = f"Error: Asistente integrador '{integrator_assistant_name}' no encontrado."
            logging.error(error_msg)
            return error_msg
        logging.info(f"Consultando al asistente '{integrator_assistant_name}' para generar el calendario integrado...")
        final_integrated_schedule = gpt_client.query(integrator_assistant_name, integration_prompt)
        logging.info("Calendario integrado final recibido.")
        # --- Change: Log the received schedule for inspection ---
        logging.debug("===== CALENDARIO INTEGRADO FINAL (RECIBIDO DE GPT) =====")
        logging.debug(final_integrated_schedule)
        logging.debug("======================================================")
        # --- End Change ---

        try:
            logging.info("Inicializando Google Calendar para la creación de eventos...")
            gc = GoogleCalendar()

            # ... (Borrado previo opcional - sin cambios, sigue comentado) ...
            today = datetime.date.today()
            days_until_monday = (0 - today.weekday() + 7) % 7
            if days_until_monday == 0: days_until_monday = 7
            next_monday = today + datetime.timedelta(days=days_until_monday)
            next_sunday = next_monday + datetime.timedelta(days=6)
            start_date_str = next_monday.strftime('%Y-%m-%d')
            end_date_str = next_sunday.strftime('%Y-%m-%d')
            # --- Change: Remove summary_prefix_filter to delete ALL events in range ---
            logging.info(f"BORRADO ACTIVO: Borrando TODOS los eventos existentes en 'PersonalCoach' para la semana {start_date_str} a {end_date_str}...")
            deleted_count = gc.delete_events_in_range(
                start_date_str=start_date_str,
                end_date_str=end_date_str,
                calendar_target='PersonalCoach'
                # summary_prefix_filter="[PLAN]" # REMOVED
            )
            logging.info(f"Se borraron {deleted_count} eventos existentes en el rango.")
            # --- End Change ---


            # Parsear el resultado y crear eventos
            parse_and_create_events(final_integrated_schedule, gc, target_calendar='PersonalCoach')

        except Exception as cal_error:
            logging.error(f"Error durante la interacción con Google Calendar (borrado/creación): {cal_error}", exc_info=True)

        return final_integrated_schedule

    except Exception as e:
        logging.error(f"Error inesperado en el orquestador principal: {e}", exc_info=True)
        return f"Error inesperado durante la orquestación: {e}"

if __name__ == "__main__":
    # ... (Llamada a generate_integrated_schedule y print final sin cambios) ...
    print("Iniciando el proceso de generación de calendario semanal integrado y creación de eventos...")
    final_schedule = generate_integrated_schedule()
    print("\n===== CALENDARIO SEMANAL INTEGRADO FINAL (TEXTO) =====")
    print(final_schedule)
    print("======================================================")
    print("\nNOTA: Los eventos marcados con [PLAN] deberían haber sido creados en el calendario 'PersonalCoach' de Google Calendar (si no hubo errores). Revisa los logs para detalles.")

