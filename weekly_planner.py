import logging
from gpt import GPTClient # Asegúrate de que gpt.py esté en el mismo directorio o en el PYTHONPATH
# --- Change: Import ThreadPoolExecutor ---
import concurrent.futures
# --- End Change ---

# Configure logging (opcional, pero útil para depuración)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_weekly_plan():
    """
    Orquesta la consulta a los asistentes expertos y genera una planificación semanal integrada.
    Utiliza ejecución paralela para consultar a los expertos.

    Returns:
        str: La planificación semanal integrada generada por el asistente 'planner'.
             Retorna un mensaje de error si ocurre algún problema.
    """
    try:
        # 1. Inicializar el cliente GPT
        gpt_client = GPTClient(assistants_dir="asistentes")
        logging.info("GPTClient inicializado.")

        # 2. Definir los asistentes expertos y la consulta
        expert_assistants = ["deporte", "estres", "medico", "nutri"]
        query = "me dirías la planificación para esta semana?"
        planner_assistant = "planner" # El asistente que integrará todo

        # Verificar que todos los asistentes necesarios existen
        available_assistants = gpt_client.assistants.keys()
        required_assistants = expert_assistants + [planner_assistant]
        missing_assistants = [name for name in required_assistants if name not in available_assistants]
        if missing_assistants:
            error_msg = f"Error: Faltan los siguientes asistentes en '{gpt_client.assistants_dir}': {', '.join(missing_assistants)}"
            logging.error(error_msg)
            return error_msg

        # --- Change: Consultar a cada experto en paralelo ---
        expert_responses = {}
        logging.info(f"Consultando a los asistentes expertos en paralelo: {', '.join(expert_assistants)}")

        # Usar ThreadPoolExecutor para llamadas concurrentes a la API
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(expert_assistants)) as executor:
            # Crear un diccionario de futuros {future: assistant_name}
            future_to_assistant = {
                executor.submit(gpt_client.query, assistant_name, query): assistant_name
                for assistant_name in expert_assistants
            }

            # Procesar los resultados a medida que se completan
            for future in concurrent.futures.as_completed(future_to_assistant):
                assistant_name = future_to_assistant[future]
                try:
                    response = future.result() # Obtener el resultado o la excepción
                    expert_responses[assistant_name] = response
                    logging.info(f"Respuesta recibida de '{assistant_name}'.")
                except Exception as e:
                    # Capturar cualquier excepción ocurrida durante la ejecución del futuro
                    error_msg = f"Error al consultar al asistente '{assistant_name}' en paralelo: {e}"
                    logging.error(error_msg)
                    # Decidir si detenerse o continuar. Detenerse es más seguro.
                    # Se podría intentar continuar con las respuestas obtenidas,
                    # pero el planificador podría no tener toda la información.
                    # Cancelar futuros restantes si es necesario:
                    # for f in future_to_assistant: f.cancel()
                    return error_msg # Detener el proceso si una consulta falla

        # Verificar si se obtuvieron todas las respuestas (importante si se decide no detener en error)
        if len(expert_responses) != len(expert_assistants):
             error_msg = "No se pudieron obtener respuestas de todos los asistentes expertos."
             logging.error(error_msg)
             return error_msg
        # --- End Change ---

        # 4. Formatear las respuestas para el asistente 'planner'
        planner_input_parts = ["Aquí están las recomendaciones de los expertos para la semana:"]
        # Ordenar por nombre de asistente para consistencia (opcional)
        for assistant_name in sorted(expert_responses.keys()):
            response = expert_responses[assistant_name]
            formatted_response = f"\n--- Recomendación de '{assistant_name.capitalize()}' ---\n{response}\n--- Fin Recomendación '{assistant_name.capitalize()}' ---"
            planner_input_parts.append(formatted_response)

        planner_prompt = "\n".join(planner_input_parts)
        logging.debug(f"Prompt completo para el asistente 'planner':\n{planner_prompt}")

        # 5. Consultar al asistente 'planner'
        logging.info(f"Consultando al asistente '{planner_assistant}' para integrar las recomendaciones...")
        try:
            final_plan = gpt_client.query(planner_assistant, planner_prompt)
            logging.info("Planificación semanal integrada recibida.")
            return final_plan
        except ValueError as e:
             error_msg = f"Error al consultar al asistente '{planner_assistant}': {e}"
             logging.error(error_msg)
             return error_msg
        except Exception as e:
            error_msg = f"Error inesperado al consultar al asistente '{planner_assistant}': {e}"
            logging.error(error_msg)
            return error_msg

    except ValueError as e:
        # Error de configuración inicial (ej. API Key)
        logging.error(f"Error de configuración en GPTClient: {e}")
        return f"Error de configuración: {e}"
    except Exception as e:
        logging.error(f"Error inesperado en el flujo principal: {e}")
        return f"Error inesperado: {e}"

if __name__ == "__main__":
    print("Generando la planificación semanal integral (consultas en paralelo)...")
    integrated_plan = get_weekly_plan()
    print("\n===== PLANIFICACIÓN SEMANAL INTEGRADA =====")
    print(integrated_plan)
    print("==========================================")

