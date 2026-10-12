from src.ai.qwen_client import QwenClient

client = QwenClient()

prompt = 'Return exactly this JSON object: {"choice":"true"}'

raw = client.generate(prompt)
print("RAW OUTPUT:", repr(raw))

try:
    decision = client.parse_decision(raw)
    print("VALIDATED DECISION:", decision)
except Exception as exc:
    print("VALIDATION FAILED:", type(exc).__name__, str(exc))
