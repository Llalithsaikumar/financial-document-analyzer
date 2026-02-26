from crewai import Task

from agents import financial_analyst


analyze_financial_document_task = Task(
    description=(
        "User query: {query}\n\n"
        "File name: {file_name}\n\n"
        "Financial document content:\n{document_text}\n\n"
        "Instructions:\n"
        "1. Directly answer the user's query.\n"
        "2. Extract key financial signals (revenue, margin/profitability, cash flow, guidance, risks).\n"
        "3. Support each conclusion with evidence from the document.\n"
        "4. If the document lacks a required detail, state that explicitly.\n"
        "5. Do not fabricate numbers, links, or sources."
    ),
    expected_output=(
        "A concise report with sections:\n"
        "- Query Answer\n"
        "- Key Financial Highlights\n"
        "- Investment View (Bull/Base/Bear)\n"
        "- Risk Assessment\n"
        "- Limitations / Missing Data\n"
        "- Final Recommendation (Not financial advice)"
    ),
    agent=financial_analyst,
    async_execution=False,
)
