# Personal Coach - Automated Weekly Planner

## Purpose

This project automates the creation of a personalized weekly schedule by integrating advice from specialized AI assistants (simulating experts in sports, nutrition, stress management, etc.) with your existing Google Calendar events. The final integrated schedule, including planned activities, is then automatically added to a designated Google Calendar ('PersonalCoach' by default).

The core workflow involves:
1.  Querying multiple expert AI assistants (defined in the `asistentes/` directory) for weekly recommendations.
2.  Fetching existing events from specified Google Calendars for the upcoming week.
3.  Using another AI assistant to integrate the recommendations and existing events into a coherent weekly plan.
4.  Parsing the final plan and creating new events (marked with `[PLAN]`) in a target Google Calendar, after optionally clearing previous planned events for that week.
5.  Providing a FastAPI backend to trigger these actions and potentially interact with a frontend application.

## Project Structure

```
/personalCoach
|-- asistentes/             # Markdown files defining AI assistant prompts
|   |-- deporte.md
|   |-- estres.md
|   |-- medico.md
|   |-- nutri.md
|   |-- planner.md
|   |-- schedule_integrator.md
|   `-- calendar_formatter.md
|-- .env                    # Environment variables (API keys) - **DO NOT COMMIT**
|-- .gitignore              # Files/directories to ignore in Git
|-- api.py                  # FastAPI application exposing endpoints
|-- calendar_google.py      # Handles Google Calendar API interactions
|-- calendar_processor.py   # Fetches and formats calendar data for AI
|-- delete_planned_events.py # Script to manually delete events
|-- gpt.py                  # Client for interacting with OpenAI API
|-- main_orchestrator.py    # Main script orchestrating the workflow
|-- weekly_planner.py       # Gets recommendations from expert assistants
|-- requirements.txt        # Python dependencies
|-- README.md               # This file
|-- credentials.json        # Google API Credentials - **DO NOT COMMIT**
|-- token.json              # Google API Token - **DO NOT COMMIT**
|-- .pre-commit-config.yaml # Configuration for pre-commit hooks (Optional)
```

## Setup

### 1. Prerequisites
*   **Python:** Version 3.10 or higher recommended.
*   **Git:** For cloning and version control.
*   **Ngrok:** (Optional) For exposing the local API to the internet. Download from [ngrok.com](https://ngrok.com/download).

### 2. Clone the Repository
```bash
git clone <your-repository-url>
cd personalCoach
```

### 3. Set up Python Environment
It's highly recommended to use a virtual environment:
```bash
python -m venv venv
# Activate the environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate
```

### 4. Install Dependencies
```bash
pip install -r requirements.txt
```

### 5. Configure Environment Variables
Create a file named `.env` in the project root directory and add your OpenAI API key:
```
# .env
OPENAI_API_KEY="your_openai_api_key_here"
```

### 6. Google Calendar API Credentials
*   Follow the [Google Calendar API Python Quickstart](https://developers.google.com/calendar/api/quickstart/python) to enable the API and download your `credentials.json` file.
*   Place the downloaded `credentials.json` file in the project root directory.
*   The first time you run a script that interacts with the Google Calendar (`calendar_processor.py`, `main_orchestrator.py`, `api.py`, `delete_planned_events.py`), it will open a browser window for you to authorize access. This will create a `token.json` file storing your authorization token.

**Important:** Add `.env`, `credentials.json`, and `token.json` to your `.gitignore` file to avoid committing sensitive information.

```
# .gitignore
.env
credentials.json
token.json
venv/
__pycache__/
*.pyc
```

## Running the Application

### 1. Start the Backend API Server
The application uses FastAPI. To run the local server:
```bash
uvicorn api:app --reload --host 127.0.0.1 --port 8000
```
*   `--reload`: Automatically restarts the server when code changes (useful for development).
*   `--host 127.0.0.1`: Makes the server accessible only from your local machine.
*   `--port 8000`: Specifies the port to run on.

You can access the API documentation (Swagger UI) at `http://127.0.0.1:8000/docs`.

### 2. Expose the API with Ngrok (Optional)
If you need to access your local API from the internet (e.g., for a frontend application hosted elsewhere or webhooks), you can use Ngrok.

*   **Install Ngrok:** Follow the instructions on the [Ngrok website](https://ngrok.com/download). You might need to authenticate your Ngrok agent with your account token.
*   **Run Ngrok:** Open a *new terminal window* (leave the Uvicorn server running) and run:
    ```bash
    ngrok http 8000
    ```
*   Ngrok will display a public URL (e.g., `https://<random-string>.ngrok-free.app`) that forwards requests to your local server running on port 8000. Use this public URL as your backend endpoint in your frontend application or webhook configuration.

## Development Practices

### Pre-commit Hooks (Recommended)
To ensure code quality and consistency, this project can use `pre-commit` hooks. These hooks automatically run checks (like formatting and linting) before each commit.

1.  **Install pre-commit:**
    ```bash
    pip install pre-commit
    ```
2.  **Set up the git hooks:**
    ```bash
    pre-commit install
    ```

Now, `pre-commit` will run automatically on `git commit`. If any checks fail, fix the issues reported and stage the changes again before committing.

Common tools configured via `.pre-commit-config.yaml` (you might need to create this file) include:
*   **Black:** For code formatting.
*   **Flake8:** For linting (checking for style errors and potential bugs).
*   **isort:** For sorting imports.
*   **ruff:** An extremely fast Python linter and code formatter, written in Rust. Can replace Black, Flake8, isort, and others.

Example `.pre-commit-config.yaml`:
```yaml
# .pre-commit-config.yaml
repos:
-   repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
    -   id: check-yaml
    -   id: end-of-file-fixer
    -   id: trailing-whitespace
-   repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.1.9 # Use the latest version
    hooks:
    # Run the linter.
    -   id: ruff
        args: [--fix, --exit-non-zero-on-fix]
    # Run the formatter.
    -   id: ruff-format
