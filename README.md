# Financial Document Analyzer - Debug Assignment

## Project Overview
A comprehensive financial document analysis system that processes corporate reports, financial statements, and investment documents using AI-powered analysis agents.

## Getting Started

### Install Required Libraries
```sh
pip install -r requirements.txt
```

### Free model setup (default)
This project now defaults to a free local model through Ollama.

1. Install Ollama: https://ollama.com/download
2. Pull a free model:
```sh
ollama pull llama3.2
```
3. Run Ollama server (if not already running):
```sh
ollama serve
```
4. Run the API:
```sh
python main.py
```

### Optional provider switch
Use environment variables to change model/provider:

```sh
# Free local default
$env:LLM_PROVIDER="ollama"
$env:MODEL="ollama/llama3.2"

# OpenAI (paid)
$env:LLM_PROVIDER="openai"
$env:OPENAI_API_KEY="your_key"
$env:MODEL="gpt-4o-mini"

# Gemini (free tier may be available)
$env:LLM_PROVIDER="gemini"
$env:GEMINI_API_KEY="your_key"
$env:MODEL="gemini/gemini-1.5-flash"

# AIMLAPI (free models available)
$env:LLM_PROVIDER="aimlapi"
$env:AIMLAPI_API_KEY="your_key"
$env:AIMLAPI_BASE_URL="https://api.aimlapi.com/v1"
$env:MODEL="google/gemma-3-4b-it"
```

### Sample Document
The system analyzes financial documents like Tesla's Q2 2025 financial update.

**To add Tesla's financial document:**
1. Download the Tesla Q2 2025 update from: https://www.tesla.com/sites/default/files/downloads/TSLA-Q2-2025-Update.pdf
2. Save it as `data/sample.pdf` in the project directory
3. Or upload any financial PDF through the API endpoint

**Note:** Current `data/sample.pdf` is a placeholder - replace with actual Tesla financial document for proper testing.

# You're All Not Set!
🐛 **Debug Mode Activated!** The project has bugs waiting to be squashed - your mission is to fix them and bring it to life.

## Debugging Instructions

1. **Identify the Bug**: Carefully read the code in each file and understand the expected behavior. There is a bug in each line of code. So be careful.
2. **Fix the Bug**: Implement the necessary changes to fix the bug.
3. **Test the Fix**: Run the project and verify that the bug is resolved.
4. **Repeat**: Continue this process until all bugs are fixed.

## Expected Features
- Upload financial documents (PDF format)
- AI-powered financial analysis
- Investment recommendations
- Risk assessment
- Market insights

## Optional Search Tool Compatibility
Web search support is optional and does not block core PDF analysis.

### Check installed versions
```sh
pip show crewai crewai-tools
```

### Minimal Serper import smoke test
```sh
python -c "from crewai_tools.tools.serper_dev_tool import SerperDevTool; print('Serper import OK')"
```

If this import fails, the API still starts and runs PDF analysis; search tool usage is disabled with a warning.
