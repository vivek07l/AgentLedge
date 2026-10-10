"""Transparent local examples used when no live model connection is available."""

from typing import Any, Dict


PAYLOAD_KEYS = {
    "code_reviewer": "code_review",
    "resume_reviewer": "resume_review",
    "interview_prep": "interview_prep",
    "writing_assistant": "writing_assistant",
    "technical_troubleshooter": "technical_troubleshooting",
}


def make_demo_response(agent_key: str, request: Dict[str, Any]) -> Dict[str, Any]:
    """Return a useful, deterministic demonstration without claiming AI output."""
    data = request.get(PAYLOAD_KEYS.get(agent_key, ""), request)
    data = data if isinstance(data, dict) else {}
    generic = str(request.get("input_text", "")).strip()

    if agent_key == "code_reviewer":
        lang = data.get("language", "python")
        code = str(data.get("code", generic)).strip()
        output = (
            f"Demo code review ({lang})\n\n"
            f"You submitted {len(code)} characters of code.\n"
            "Before shipping, check edge cases, input validation, error handling, and tests.\n"
            "This local example did not execute or analyze your code. Add an API key for a real review."
        )
    elif agent_key == "resume_reviewer":
        resume = str(data.get("resume_text", generic)).strip()
        output = (
            "Demo resume review\n\n"
            f"You submitted {len(resume)} characters.\n"
            "A real review would check measurable impact, role-specific keywords, clear dates, and concise bullets.\n"
            "This is a checklist only; no AI model reviewed the resume."
        )
    elif agent_key == "interview_prep":
        topic = str(data.get("topic", generic or "your target role")).strip()
        output = (
            f"Demo interview practice for: {topic}\n\n"
            "1. Describe a difficult problem you solved and how you measured the result.\n"
            "2. Explain a trade-off you made and what you would change now.\n"
            "3. Walk through how you would approach a realistic task for this role.\n\n"
            "These are sample prompts, not model-generated role-specific advice."
        )
    elif agent_key == "writing_assistant":
        text = str(data.get("text", generic)).strip()
        output = (
            "Demo writing checklist\n\n"
            f"You submitted {len(text)} characters.\n"
            "Try putting the main point first, shortening long sentences, and replacing vague claims with concrete details.\n"
            "This local example did not rewrite your text. Add an API key for an AI edit."
        )
    else:
        issue = str(data.get("issue", data.get("problem", generic or "your issue"))).strip()
        output = (
            f"Demo troubleshooting checklist for: {issue}\n\n"
            "1. Capture the exact error and the steps that reproduce it.\n"
            "2. Check recent changes, service status, and relevant logs.\n"
            "3. Try one reversible change at a time and record the result.\n"
            "This is a general checklist, not a diagnosis from an AI model."
        )

    return {"output_text": output, "tokens_used": 0, "cost": 0}
