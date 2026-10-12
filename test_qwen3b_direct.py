
import time
import psutil
from src.ai.qwen_client import QwenClient

process = psutil.Process()
start = time.time()

client = QwenClient()
print(f"Load time: {time.time() - start:.1f}s")
print(f"RAM after load: {process.memory_info().rss / 1024**3:.2f} GB")

start = time.time()
answer = client.generate(
    'Return exactly this JSON and nothing else: {"choice":"true"}'
)

print("OUTPUT:", answer)
print(f"Inference time: {time.time() - start:.1f}s")
print(f"RAM after inference: {process.memory_info().rss / 1024**3:.2f} GB")
