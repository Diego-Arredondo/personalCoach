import datetime
import logging
from calendar_google import GoogleCalendar

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def delete_next_week_all_events(calendar_name='PersonalCoach'):
    """
    Borra TODOS los eventos de la próxima semana (Lunes a Domingo)
    en el calendario especificado. Pide confirmación interactiva.

    Returns:
        int: El número de eventos borrados, o -1 si hubo un error.
    """
    deleted_count = -1 # Valor por defecto en caso de error
    try:
        today = datetime.date.today()
        days_until_monday = (0 - today.weekday() + 7) % 7
        if days_until_monday == 0: days_until_monday = 7
        next_monday = today + datetime.timedelta(days=days_until_monday)
        next_sunday = next_monday + datetime.timedelta(days=6)
        start_date_str = next_monday.strftime('%Y-%m-%d')
        end_date_str = next_sunday.strftime('%Y-%m-%d')

        logging.info(f"Intentando borrar TODOS los eventos en el calendario '{calendar_name}' "
                     f"para la semana del {start_date_str} al {end_date_str}.")

        gc = GoogleCalendar()

        # Llamar a la función de borrado SIN filtro y SIN saltar confirmación
        deleted_count = gc.delete_events_in_range(
            start_date_str=start_date_str,
            end_date_str=end_date_str,
            calendar_target=calendar_name,
            skip_confirmation=False # Asegura que pida confirmación
        )

    except Exception as e:
        logging.error(f"Error durante el borrado de eventos: {e}", exc_info=True)
        print(f"Error durante el borrado: {e}")
        # deleted_count sigue siendo -1

    return deleted_count # Devolver el contador o -1

if __name__ == "__main__":
    target_calendar = 'PersonalCoach'
    print(f"--- Script para Borrar TODOS los Eventos de la Próxima Semana en '{target_calendar}' ---")

    result_count = delete_next_week_all_events(calendar_name=target_calendar)
    if result_count >= 0:
         print(f"\nResultado final: {result_count} eventos borrados.")
    else:
         print("\nEl proceso de borrado falló o fue cancelado.")
