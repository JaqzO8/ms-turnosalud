# Subsistema de ajustes (config) del harness de agente IA
import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", "https://api.groq.com/openai/v1")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")
    MOCK_LLM: bool = os.getenv("MOCK_LLM", "true").lower() == "true"

    MS_AGENDA_URL: str = os.getenv("MS_AGENDA_URL", "http://localhost:3001")
    MS_CITAS_URL: str = os.getenv("MS_CITAS_URL", "http://localhost:3002")

    # Guardarraíles
    MAX_TOOL_CALLS: int = int(os.getenv("MAX_TOOL_CALLS", "5"))
    HTTP_TIMEOUT_MS: int = int(os.getenv("HTTP_TIMEOUT_MS", "3000"))

    # Decision D6: fecha fija reproducible para evals/fixtures (lunes)
    FIXED_TODAY: str = os.getenv("FIXED_TODAY", "2026-11-02")

    LOGS_DIR: str = os.getenv("LOGS_DIR", "logs")


CONFIG = Config()
