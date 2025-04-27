import os
from dotenv import load_dotenv
from openai import OpenAI
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class GPTClient:
    """
    A client to interact with OpenAI's GPT-4o model using specific assistant prompts.
    """
    def __init__(self, assistants_dir="asistentes"):
        """
        Initializes the GPTClient.

        Loads the OpenAI API key from environment variables, initializes the OpenAI client,
        and loads assistant prompts from the specified directory.

        Args:
            assistants_dir (str): The directory containing assistant prompt files (.txt).
                                  Defaults to "asistentes".
        """
        load_dotenv()
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            logging.error("OPENAI_API_KEY not found in environment variables.")
            raise ValueError("OPENAI_API_KEY must be set in your .env file.")

        self.client = OpenAI(api_key=self.api_key)
        self.assistants_dir = assistants_dir
        self.assistants = self._load_assistants()
        logging.info(f"Loaded {len(self.assistants)} assistants: {list(self.assistants.keys())}")

    def _load_assistants(self):
        """
        Loads assistant prompts from .md files in the assistants directory.
        The filename (without extension) is used as the assistant name.

        Returns:
            dict: A dictionary mapping assistant names to their prompt content.
        """
        assistants = {}
        if not os.path.isdir(self.assistants_dir):
            logging.warning(f"Assistants directory '{self.assistants_dir}' not found. No assistants loaded.")
            return assistants

        try:
            for filename in os.listdir(self.assistants_dir):
                if filename.endswith(".md"):
                    assistant_name = os.path.splitext(filename)[0]
                    filepath = os.path.join(self.assistants_dir, filename)
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            assistants[assistant_name] = f.read().strip()
                        logging.debug(f"Loaded assistant '{assistant_name}' from {filename}")
                    except Exception as e:
                        logging.error(f"Error reading assistant file {filepath}: {e}")
        except Exception as e:
            logging.error(f"Error listing files in assistants directory '{self.assistants_dir}': {e}")

        return assistants

    def query(self, assistant_name: str, user_prompt: str, model: str = "gpt-4o") -> str:
        """
        Sends a query to the specified GPT model using a selected assistant's prompt.

        Args:
            assistant_name (str): The name of the assistant to use (must match a .txt file name).
            user_prompt (str): The specific prompt or question from the user.
            model (str): The OpenAI model to use. Defaults to "gpt-4o".

        Returns:
            str: The content of the model's response.

        Raises:
            ValueError: If the specified assistant_name is not found.
            Exception: If there is an error during the API call.
        """
        if assistant_name not in self.assistants:
            logging.error(f"Assistant '{assistant_name}' not found. Available: {list(self.assistants.keys())}")
            raise ValueError(f"Assistant '{assistant_name}' not found.")

        base_prompt = self.assistants[assistant_name]
        full_prompt = f"{base_prompt}\n\n{user_prompt}"
        logging.info(f"Querying model '{model}' with assistant '{assistant_name}'.")
        # logging.debug(f"Full prompt being sent:\n{full_prompt}") # Uncomment for debugging prompts

        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "user", "content": full_prompt}
                ]
                # You can add other parameters like max_tokens, temperature, etc. here
                # max_tokens=150,
                # temperature=0.7,
            )
            # Check if response and choices are valid
            if response and response.choices and len(response.choices) > 0:
                content = response.choices[0].message.content
                logging.info(f"Received response from model '{model}'.")
                return content.strip() if content else ""
            else:
                logging.error("Invalid response structure received from OpenAI API.")
                return "Error: Invalid response structure from API."

        except Exception as e:
            logging.error(f"Error calling OpenAI API: {e}")
            # Consider re-raising or returning a specific error message
            # raise e # Option: re-raise the exception
            return f"Error interacting with OpenAI: {e}"

# Example Usage (optional, can be run if this file is executed directly)
if __name__ == '__main__':
    # Ensure you have a .env file with OPENAI_API_KEY="your_key_here"
    # Ensure you have 'asistentes/deporte.md' file.

    try:
        gpt_client = GPTClient()

        assistant = "nutri" # Assumes asistentes/deporte.md exists

        print(f"Interactuando con el asistente '{assistant}'. Escribe 'salir' para terminar.")

        while True:
            prompt = input("Tú: ")
            if prompt.lower() in ['salir', 'exit', 'quit']:
                print("Saliendo...")
                break
            if not prompt:
                continue

            if assistant not in gpt_client.assistants:
                 print(f"Error: Asistente '{assistant}' no encontrado en '{gpt_client.assistants_dir}'. Verifica que 'asistentes/deporte.md' existe.")
                 break # Exit if the required assistant is missing

            response_text = gpt_client.query(assistant, prompt)
            print(f"Asistente {assistant}: {response_text}")

    except ValueError as e:
        print(f"Configuration Error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

