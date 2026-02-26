import os

from dotenv import load_dotenv

from crewai import Agent, LLM
from tools import get_search_tool

load_dotenv()


def _build_llm() -> LLM:
    provider = os.getenv("LLM_PROVIDER", "ollama").strip().lower()
    temperature = float(os.getenv("LLM_TEMPERATURE", "0.2"))

    # Default: free local model via Ollama (no paid API required).
    if provider == "ollama":
        model = os.getenv("MODEL", "ollama/llama3.2")
        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        return LLM(model=model, base_url=base_url, temperature=temperature)

    if provider == "openai":
        model = os.getenv("MODEL", "gpt-4o-mini")
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY is required when LLM_PROVIDER=openai.")
        return LLM(model=model, api_key=api_key, temperature=temperature)

    if provider == "gemini":
        model = os.getenv("MODEL", "gemini/gemini-1.5-flash")
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY or GOOGLE_API_KEY is required when LLM_PROVIDER=gemini.")
        return LLM(model=model, api_key=api_key, temperature=temperature)

    if provider == "aimlapi":
        raw_model = os.getenv("MODEL", "google/gemma-3-4b-it").strip()
        # LiteLLM needs provider-aware model names for OpenAI-compatible gateways.
        model = raw_model if raw_model.startswith("openai/") else f"openai/{raw_model}"
        api_key = os.getenv("AIMLAPI_API_KEY")
        base_url = os.getenv("AIMLAPI_BASE_URL", "https://api.aimlapi.com/v1")
        if not api_key:
            raise ValueError("AIMLAPI_API_KEY is required when LLM_PROVIDER=aimlapi.")
        return LLM(
            model=model,
            api_key=api_key,
            base_url=base_url,
            api_base=base_url,
            temperature=temperature,
        )

    raise ValueError(
        "Unsupported LLM_PROVIDER. Use one of: ollama, openai, gemini, aimlapi."
    )


def _build_optional_tools():
    tools = []
    search_tool = get_search_tool()
    if search_tool is not None:
        tools.append(search_tool)
    return tools


financial_analyst = Agent(
    role="Senior Financial Analyst",
    goal=(
        "Analyze the provided financial document and answer the user query with "
        "evidence-based, clear, and actionable insights."
    ),
    backstory=(
        "You are a detail-oriented analyst focused on accurate interpretation of "
        "financial statements, business updates, and risk disclosures. You avoid "
        "unsupported claims, flag uncertainty, and communicate clearly."
    ),
    llm=_build_llm(),
    tools=_build_optional_tools(),
    # AIMLAPI route for Gemma can reject system-role messages; keep prompts in user-role flow.
    use_system_prompt=False,
    verbose=True,
    memory=False,
    allow_delegation=False,
)
