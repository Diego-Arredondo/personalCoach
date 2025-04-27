from __future__ import print_function
import datetime
import os.path
from google.oauth2.credentials import Credentials
# --- Change: Correct typo oauthlib ---
from google_auth_oauthlib.flow import InstalledAppFlow
# --- End Change ---
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from google.auth.exceptions import RefreshError
import json # Importar json para pretty printing
import time # Import time for potential delays if needed

class GoogleCalendar:
    def __init__(self, credentials_file='credentials.json', token_file='token.json'):
        """
        Inicializa la clase, realizando la autenticación con la API de Google Calendar.
        Parámetros:
           credentials_file: Ruta al archivo de credenciales OAuth 2.0.
           token_file: Archivo en el que se almacenan los tokens de acceso.
        """
        self.credentials_file = credentials_file
        self.token_file = token_file
        self.scopes = ['https://www.googleapis.com/auth/calendar']
        self.creds = None
        # --- Change: Store calendars list on init for reuse ---
        self._calendars_cache = None
        # --- End Change ---
        self.authenticate()
        # Construir el servicio para interactuar con la API
        self.service = build('calendar', 'v3', credentials=self.creds)

    def authenticate(self):
        """Realiza OAuth2.0; si el refresh falla, fuerza un nuevo login."""
        # Intentamos cargar credenciales guardadas
        if os.path.exists(self.token_file):
            self.creds = Credentials.from_authorized_user_file(self.token_file, self.scopes)
        # Si son inválidas o expiraron, tratamos de refrescar o relanzamos el flujo
        if not self.creds or not self.creds.valid:
            try:
                if self.creds and self.creds.expired and self.creds.refresh_token:
                    self.creds.refresh(Request())
                else:
                    raise RefreshError("No hay refresh_token válido")
            except RefreshError:
                # Borramos el token viejo y forzamos un nuevo login
                if os.path.exists(self.token_file):
                    os.remove(self.token_file)
                flow = InstalledAppFlow.from_client_secrets_file(self.credentials_file, self.scopes)
                self.creds = flow.run_local_server(port=0)

            # Guardamos las credenciales nuevas
            with open(self.token_file, 'w') as token:
                token.write(self.creds.to_json())

    def list_available_calendars(self, force_refresh=False):
        """
        Obtiene y retorna la lista de todos los calendarios accesibles por la cuenta autenticada.

        Retorna:
           Una lista de diccionarios, donde cada diccionario representa un calendario.
           Retorna una lista vacía si ocurre un error.
        """
        # --- Change: Use cache ---
        if self._calendars_cache is not None and not force_refresh:
            return self._calendars_cache
        # --- End Change ---
        try:
            print("Obteniendo lista de calendarios desde la API...")
            calendar_list_result = self.service.calendarList().list().execute()
            calendars = calendar_list_result.get('items', [])
            # --- Change: Update cache ---
            self._calendars_cache = calendars
            # --- End Change ---
            return calendars
        except Exception as e:
            print(f"Error al obtener la lista de calendarios: {e}")
            # --- Change: Clear cache on error ---
            self._calendars_cache = None
            # --- End Change ---
            return []

    # --- Change: Add helper to get ID by name ---
    def get_calendar_id_by_summary(self, summary_name):
        """Busca el ID de un calendario por su nombre (summary)."""
        calendars = self.list_available_calendars()
        for calendar in calendars:
            if calendar.get('summary') == summary_name:
                return calendar.get('id')
        print(f"Advertencia: No se encontró un calendario con el nombre '{summary_name}'.")
        return None
    # --- End Change ---

    def buscar_eventos(self, fecha_inicio, fecha_fin):
        """
        Busca eventos en el calendario primario (original) para el rango de fechas especificado y 
        retorna un diccionario agrupado por días, donde cada día contiene una lista de eventos ordenados cronológicamente.
        
        Parámetros:
           fecha_inicio: String en formato 'YYYY-MM-DD' indicando el inicio del rango.
           fecha_fin: String en formato 'YYYY-MM-DD' indicando el fin del rango.
           
        Retorna:
           Un diccionario con la estructura:
             {
               'YYYY-MM-DD': [ {evento1}, {evento2}, ... ],
               ...
             }
        """
        # Convertir cadenas de fecha a objetos datetime
        start_date = datetime.datetime.strptime(fecha_inicio, '%Y-%m-%d')
        end_date = datetime.datetime.strptime(fecha_fin, '%Y-%m-%d')
        
        time_min = datetime.datetime(start_date.year, start_date.month, start_date.day, 0, 0, 0).isoformat() + 'Z'
        time_max = datetime.datetime(end_date.year, end_date.month, end_date.day, 23, 59, 59).isoformat() + 'Z'
        
        events_result = self.service.events().list(
            calendarId='primary',
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        events = events_result.get('items', [])
        
        eventos_por_dia = {}
        for event in events:
            start_str = event['start'].get('dateTime', event['start'].get('date'))
            event_date = start_str.split('T')[0] if 'T' in start_str else start_str
            
            evento_info = {
                'id': event.get('id'),
                'summary': event.get('summary'),
                'description': event.get('description'),
                'start': event.get('start'),
                'end': event.get('end'),
                'location': event.get('location'),
                'attendees': event.get('attendees'),
                'htmlLink': event.get('htmlLink')
            }
            if event_date in eventos_por_dia:
                eventos_por_dia[event_date].append(evento_info)
            else:
                eventos_por_dia[event_date] = [evento_info]
        
        for dia, lista_eventos in eventos_por_dia.items():
            lista_eventos.sort(key=lambda ev: ev['start'].get('dateTime', ev['start'].get('date')))
        
        return eventos_por_dia

    def buscar_eventos_todos(self, fecha_inicio, fecha_fin, filter_summaries=None):
        """
        Busca eventos en los calendarios especificados, filtrando por estado 'accepted'
        si es una invitación, y retorna un diccionario agrupado por días.
        """
        # Convertir las cadenas de fecha a objetos datetime
        start_date = datetime.datetime.strptime(fecha_inicio, '%Y-%m-%d')
        end_date = datetime.datetime.strptime(fecha_fin, '%Y-%m-%d')
        
        time_min = datetime.datetime(start_date.year, start_date.month, start_date.day, 0, 0, 0).isoformat() + 'Z'
        time_max = datetime.datetime(end_date.year, end_date.month, end_date.day, 23, 59, 59).isoformat() + 'Z'
        
        # Obtener la lista de calendarios disponibles usando el nuevo método
        all_calendars = self.list_available_calendars() # Usa el método interno

        # --- Change: Filter calendars if filter_summaries is provided ---
        if filter_summaries:
            calendars_to_search = [
                cal for cal in all_calendars if cal.get('summary') in filter_summaries
            ]
            print(f"Filtrando calendarios. Se buscará en: {[cal.get('summary') for cal in calendars_to_search]}")
        else:
            calendars_to_search = all_calendars
            print("No se especificó filtro, buscando en todos los calendarios.")
        # --- End Change ---

        eventos_por_dia = {}
        
        # Iterar sobre cada calendario filtrado
        # --- Change: Iterate over calendars_to_search ---
        for calendar in calendars_to_search:
        # --- End Change ---
            calendar_id = calendar.get('id')
            calendar_summary = calendar.get('summary')
            try:
                events_result = self.service.events().list(
                    calendarId=calendar_id,
                    timeMin=time_min,
                    timeMax=time_max,
                    singleEvents=True,
                    orderBy='startTime'
                ).execute()
            except Exception as e:
                # En ocasiones puede haber errores con algún calendario; se pueden omitir o manejar según convenga
                print(f"Error al obtener eventos del calendario {calendar_id}: {e}")
                continue

            events = events_result.get('items', [])
            for event in events:
                # --- Change: Filter by attendee status ---
                include_event = True # Default to include
                attendees = event.get('attendees', [])
                user_status = None
                is_invitation_for_user = False

                for attendee in attendees:
                    if attendee.get('self'): # Check if this attendee is the user
                        is_invitation_for_user = True
                        user_status = attendee.get('responseStatus')
                        break # Found the user's status

                # If it's an invitation for the user, only include if accepted
                if is_invitation_for_user and user_status != 'accepted':
                    include_event = False
                    # Optional logging for skipped events:
                    # print(f"Skipping event '{event.get('summary')}' (status: {user_status})")

                if not include_event:
                    continue # Skip this event and go to the next one
                # --- End Change ---

                # --- Process event only if include_event is True ---
                start_str = event['start'].get('dateTime', event['start'].get('date'))
                event_date = start_str.split('T')[0] if 'T' in start_str else start_str

                evento_info = {
                    'calendar_id': calendar_id,
                    'calendar_summary': calendar_summary,
                    'id': event.get('id'),
                    'summary': event.get('summary'),
                    'description': event.get('description'),
                    'start': event.get('start'),
                    'end': event.get('end'),
                    'location': event.get('location'),
                    # Attendees might still be useful for the formatter, keep it for now
                    'attendees': event.get('attendees'),
                    'htmlLink': event.get('htmlLink')
                }

                if event_date in eventos_por_dia:
                    eventos_por_dia[event_date].append(evento_info)
                else:
                    eventos_por_dia[event_date] = [evento_info]
                # --- End event processing ---
        
        # Ordenar la lista de eventos de cada día por la hora de inicio
        for dia, lista_eventos in eventos_por_dia.items():
            lista_eventos.sort(key=lambda ev: ev['start'].get('dateTime', ev['start'].get('date')))
        
        return eventos_por_dia

    # --- Change: Modify create_event default and logic ---
    def create_event(self, summary, start_datetime, end_datetime, description=None, location=None, calendar_target='PersonalCoach'):
        """
        Crea un nuevo evento en el calendario especificado (por nombre o ID).
        Default: 'PersonalCoach'.

        Parámetros:
           summary (str): Título del evento.
           start_datetime (datetime.datetime): Objeto datetime para el inicio del evento (con timezone).
           end_datetime (datetime.datetime): Objeto datetime para el fin del evento (con timezone).
           description (str, opcional): Descripción del evento.
           location (str, opcional): Ubicación del evento.
           calendar_target (str): Nombre (summary) o ID del calendario. Default 'PersonalCoach'.
        """
        target_id = calendar_target
        # Si el target parece un nombre y no un ID (heurística simple: contiene '@' o '.'), buscar ID
        if '@' not in calendar_target and '.' not in calendar_target:
             found_id = self.get_calendar_id_by_summary(calendar_target)
             if found_id:
                 target_id = found_id
             else:
                 print(f"No se pudo encontrar el ID para el calendario '{calendar_target}'. Usando 'primary' como fallback.")
                 target_id = 'primary' # Fallback a primario si no se encuentra

        # Por simplicidad, aquí asumiremos que los datetimes ya vienen con timezone
        # o la API usará la timezone por defecto del calendario.
        # Es MUY recomendable manejar timezones explícitamente en producción.

        event_body = {
            'summary': summary,
            'location': location,
            'description': description,
            'start': {
                'dateTime': start_datetime.isoformat(),
                # 'timeZone': 'America/Santiago', # Opcional: especificar timezone
            },
            'end': {
                'dateTime': end_datetime.isoformat(),
                # 'timeZone': 'America/Santiago', # Opcional: especificar timezone
            },
            # Puedes añadir más campos como 'attendees', 'reminders', etc.
            # 'attendees': [
            #     {'email': 'alguien@example.com'},
            # ],
            # 'reminders': {
            #     'useDefault': False,
            #     'overrides': [
            #         {'method': 'email', 'minutes': 24 * 60},
            #         {'method': 'popup', 'minutes': 10},
            #     ],
            # },
        }

        try:
            print(f"Intentando crear evento: '{summary}' en calendario ID: '{target_id}' (Target: '{calendar_target}')")
            created_event = self.service.events().insert(calendarId=target_id, body=event_body).execute()
            print(f"Evento creado exitosamente! ID: {created_event.get('id')}")
            print(f"Link: {created_event.get('htmlLink')}")
            return created_event
        except Exception as e:
            print(f"Error al crear el evento: {e}")
            return None
    # --- End Change ---

    # --- Change: Add method to delete events ---
    def delete_events_in_range(self, start_date_str, end_date_str, calendar_target='PersonalCoach', summary_prefix_filter=None, skip_confirmation=False):
        """
        Borra eventos dentro de un rango de fechas en un calendario específico,
        opcionalmente filtrando por un prefijo en el título.

        Parámetros:
           start_date_str (str): Fecha de inicio 'YYYY-MM-DD'.
           end_date_str (str): Fecha de fin 'YYYY-MM-DD'.
           calendar_target (str): Nombre (summary) o ID del calendario. Default 'PersonalCoach'.
           summary_prefix_filter (str, opcional): Si se proporciona, solo borra eventos
                                                  cuyo título comience con este string.
           Si summary_prefix_filter es None, borra TODOS los eventos en el rango.
           skip_confirmation (bool, opcional): Si es True, no pedirá confirmación interactiva al borrar sin filtro.

        Returns:
            int: El número de eventos borrados.
        """
        target_id = calendar_target
        if '@' not in calendar_target and '.' not in calendar_target:
             found_id = self.get_calendar_id_by_summary(calendar_target)
             if found_id:
                 target_id = found_id
             else:
                 print(f"No se pudo encontrar el ID para el calendario '{calendar_target}' para borrar eventos. Abortando borrado.")
                 return 0 # No se borró nada

        print(f"Buscando eventos para borrar en '{calendar_target}' (ID: {target_id}) entre {start_date_str} y {end_date_str}")
        if summary_prefix_filter:
            print(f"Filtrando por títulos que comiencen con: '{summary_prefix_filter}'")
        # --- Change: Remove safety check and adjust logic ---
        else:
            print("ADVERTENCIA: No se especificó filtro de prefijo. Se procederá a borrar TODOS los eventos en el rango.")
        # --- End Change ---

        try:
            start_dt = datetime.datetime.strptime(start_date_str, '%Y-%m-%d')
            end_dt = datetime.datetime.strptime(end_date_str, '%Y-%m-%d')
            time_min = datetime.datetime(start_dt.year, start_dt.month, start_dt.day, 0, 0, 0).isoformat() + 'Z'
            time_max = datetime.datetime(end_dt.year, end_dt.month, end_dt.day, 23, 59, 59).isoformat() + 'Z'

            events_to_delete = []
            page_token = None
            while True:
                events_result = self.service.events().list(
                    calendarId=target_id,
                    timeMin=time_min,
                    timeMax=time_max,
                    singleEvents=True,
                    pageToken=page_token
                ).execute()
                events = events_result.get('items', [])

                for event in events:
                    # --- Change: Append all events if no filter ---
                    if summary_prefix_filter:
                        summary = event.get('summary', '')
                        if summary.startswith(summary_prefix_filter):
                            events_to_delete.append(event)
                    else:
                        # Si no hay filtro, añadir todos para borrar
                        events_to_delete.append(event)
                    # --- End Change ---

                page_token = events_result.get('nextPageToken')
                if not page_token:
                    break

            deleted_count = 0
            if not events_to_delete:
                print("No se encontraron eventos que coincidan para borrar.")
                return 0

            print(f"Se encontraron {len(events_to_delete)} eventos para borrar:")
            for event in events_to_delete:
                 print(f"  - ID: {event.get('id')}, Título: {event.get('summary')}")

            # --- Change: Add confirmation prompt if deleting without filter ---
            if not summary_prefix_filter and not skip_confirmation:
                 try:
                     confirm = input("¡CONFIRMACIÓN ADICIONAL! ¿Realmente quieres borrar TODOS estos eventos? (s/N): ")
                     if confirm.lower() != 's':
                         print("Borrado cancelado por el usuario.")
                         return 0
                 except EOFError:
                      # Si no hay terminal interactiva (ej. corriendo bajo Uvicorn sin tty)
                      print("No se puede pedir confirmación interactiva. Abortando borrado por seguridad.")
                      return 0
            # --- End Change ---

            print("Borrando eventos...")
            for event in events_to_delete:
                try:
                    self.service.events().delete(calendarId=target_id, eventId=event['id']).execute()
                    print(f"  Evento '{event.get('summary')}' (ID: {event['id']}) borrado.")
                    deleted_count += 1
                    # time.sleep(0.1) # Pequeña pausa para evitar rate limits si son muchos eventos
                except Exception as e:
                    print(f"  Error al borrar evento ID {event.get('id')}: {e}")

            print(f"Total de eventos borrados: {deleted_count}")
            return deleted_count

        except Exception as e:
            print(f"Error durante el proceso de borrado de eventos: {e}")
            return 0
    # --- End Change ---

# Ejemplo de uso:
if __name__ == '__main__':
    gc = GoogleCalendar()

    # --- Change: List available calendars ---
    print("\n===== CALENDARIOS DISPONIBLES =====")
    available_calendars = gc.list_available_calendars()
    if available_calendars:
        # Imprimir de forma más legible (summary e id)
        for cal in available_calendars:
             print(f"- Summary: {cal.get('summary', 'N/A')}, ID: {cal.get('id', 'N/A')}")
        # O imprimir toda la información en formato JSON pretty
        # print(json.dumps(available_calendars, indent=2))
    else:
        print("No se pudieron obtener los calendarios o no hay calendarios disponibles.")
    print("==================================\n")
    # --- End Change ---

    # Buscar eventos en todos los calendarios para la semana: del 10 al 16 de abril de 2025
    eventos_semana = gc.buscar_eventos_todos('2025-04-10', '2025-04-16')
    
    # Mostrar los eventos agrupados por día junto con el calendario de origen
    for dia, eventos in eventos_semana.items():
        print(f'Eventos el {dia}:')
        for ev in eventos:
            # Se obtiene la hora de inicio (dateTime o date)
            start_time = ev['start'].get('dateTime', ev['start'].get('date'))
            print(f"  - {start_time}: {ev.get('summary', 'Sin título')} (Calendario: {ev.get('calendar_summary')})")

    # --- Change: Example of creating an event ---
    print("\n===== CREANDO EVENTO DE PRUEBA EN 'PersonalCoach' =====")
    test_event_summary = "Evento de Prueba API - Borrar" # Añadir sufijo para facilitar borrado
    try:
        now_naive = datetime.datetime.now() # Obtener datetime naive
        now_aware = None
        try:
            # Intentar obtener timezone local con tzlocal (puede usar zoneinfo)
            from tzlocal import get_localzone
            local_tz = get_localzone()
            # --- Change: Use replace(tzinfo=...) instead of localize() ---
            now_aware = now_naive.replace(tzinfo=local_tz)
            # --- End Change ---
            print(f"Usando timezone local detectada: {local_tz}") # Muestra la zona detectada
        except ImportError:
            print("Advertencia: tzlocal no instalado. Usando datetime sin timezone explícita.")
            now_aware = now_naive # Se usará sin timezone, la API usará la default del calendario
        except Exception as tz_err:
             print(f"Error al obtener/aplicar timezone local: {tz_err}. Usando datetime sin timezone explícita.")
             now_aware = now_naive

        # Asegurarse de que now_aware no sea None antes de usarlo
        if now_aware is None:
             now_aware = now_naive # Fallback a naive si todo falló

        start_time_test = now_aware + datetime.timedelta(days=2)
        end_time_test = start_time_test + datetime.timedelta(hours=1)

        created = gc.create_event(
            summary=test_event_summary,
            start_datetime=start_time_test,
            end_datetime=end_time_test,
            description='Este es un evento creado automáticamente para probar la API y el borrado.',
            location='Virtual / Python Script',
            calendar_target='PersonalCoach' # Especificar el calendario por nombre
        )
        if created:
            print("Detalles del evento creado:")
            # print(json.dumps(created, indent=2)) # Opcional: imprimir detalles completos
        else:
            print("No se pudo crear el evento de prueba.")
    except Exception as e:
        print(f"Error durante la creación del evento de prueba: {e}")
    print("======================================================\n")

    # Agregar un stop para poder ver el resultado en mi calendar
    input("Presiona Enter para continuar y borrar el evento de prueba...")

    print("\n===== BORRANDO EVENTOS DE PRUEBA DE LA PRÓXIMA SEMANA EN 'PersonalCoach' =====")
    try:
        # Calcular fechas de la próxima semana
        today = datetime.date.today()
        days_until_monday = (0 - today.weekday() + 7) % 7
        if days_until_monday == 0: days_until_monday = 7
        next_monday = today + datetime.timedelta(days=days_until_monday)
        next_sunday = next_monday + datetime.timedelta(days=6)
        start_date_str = next_monday.strftime('%Y-%m-%d')
        end_date_str = next_sunday.strftime('%Y-%m-%d')

        # Borrar eventos en la próxima semana que comiencen con el prefijo del evento de prueba
        deleted_count = gc.delete_events_in_range(
            start_date_str=start_date_str,
            end_date_str=end_date_str,
            calendar_target='PersonalCoach',
            summary_prefix_filter=test_event_summary, # Filtro para borrar solo los de prueba
            skip_confirmation=False # No saltar confirmación al ejecutar directamente
            # summary_prefix_filter="[PLAN]" # Ejemplo para borrar eventos planificados
        )
        print(f"Proceso de borrado completado. Eventos borrados: {deleted_count}")

    except Exception as e:
        print(f"Error durante el borrado de eventos de prueba: {e}")
    print("=========================================================================\n")
    # --- End Change ---
