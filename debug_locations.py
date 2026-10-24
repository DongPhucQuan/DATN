import json
from pathlib import Path

path = Path("reports/document_analysis.json")
data = json.loads(path.read_text(encoding="utf-8"))

for document in data.get("documents", []):
    print("\n" + "=" * 80)
    print("FILE:", document.get("filename"))

    for index, block in enumerate(document.get("blocks", [])[:100]):
        print(
            f"BLOCK {index:03d} | "
            f"location={block.get('location')!r} | "
            f"paragraph={block.get('paragraph')!r} | "
            f"style={block.get('style')!r}"
        )