from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from docx import Document


DEFAULT_DOCUMENTS = {
    "MRD": "XD.BM.03A - Tai lieu MRD.docx",
    "PRD": "XD.BM.03B - Tai lieu PRD.docx",
    "PROPOSAL": "XD.BM.02A - TTr chu truong cap co so_short.docx",
}

# Các cụm thường xuất hiện trong biểu mẫu/hướng dẫn điền.
# Không dùng chúng để tự kết luận toàn bộ tài liệu là vô giá trị.
PLACEHOLDER_PATTERNS = [
    r"\{[^}]+\}",
    r"\.{3,}",
    r"\b20\d{2}\s*\.\s*\.\s*\.",
    r"\b201\s*\.\s*\.\s*\.",
    r"\btên nhiệm vụ\b",
    r"\btên sản phẩm\b",
    r"\bnêu rõ\b",
    r"\bliệt kê\b",
    r"\bnêu mục tiêu\b",
    r"\bđưa ra kế hoạch\b",
    r"\bchi tiết .* phụ lục\b",
    r"\bđiền .* vào\b",
]

INSTRUCTION_PATTERNS = [
    r"\bnêu rõ\b",
    r"\bliệt kê\b",
    r"\bnêu mục tiêu\b",
    r"\bđưa ra kế hoạch\b",
    r"\bchi tiết .* phụ lục\b",
    r"\bcần .* trình bày\b",
    r"\bđề nghị .* mô tả\b",
]

TOPIC_MAP = {
    "product_requirements": {
        "label": "Yêu cầu và mô tả sản phẩm",
        "MRD": ["yêu cầu sản phẩm", "tính năng", "khách hàng"],
        "PRD": ["tính năng", "chỉ tiêu", "kỹ thuật"],
        "PROPOSAL": ["sản phẩm", "chỉ tiêu kỹ thuật", "mục tiêu"],
    },
    "technology": {
        "label": "Công nghệ lõi và công nghệ phát triển",
        "MRD": ["công nghệ", "sản phẩm"],
        "PRD": ["công nghệ lõi", "công nghệ sử dụng"],
        "PROPOSAL": ["công nghệ lõi", "làm chủ"],
    },
    "schedule": {
        "label": "Lộ trình và thời gian thực hiện",
        "MRD": ["lộ trình sản phẩm", "mốc phát triển"],
        "PRD": ["phiên bản tiếp theo"],
        "PROPOSAL": ["thời gian thực hiện", "mốc chính", "kế hoạch thực hiện"],
    },
    "finance": {
        "label": "Kinh phí và hiệu quả kinh tế",
        "MRD": ["chi phí nghiên cứu", "điểm hoàn vốn", "hiệu quả kinh doanh"],
        "PRD": [],
        "PROPOSAL": ["kinh phí dự kiến", "hiệu quả kinh tế", "tổng kinh phí"],
    },
    "market": {
        "label": "Thị trường và hiệu quả dự kiến",
        "MRD": ["thị trường mục tiêu", "khách hàng", "phân khúc thị trường"],
        "PRD": ["so sánh với các sản phẩm trên thế giới"],
        "PROPOSAL": ["thị trường và hiệu quả", "nhu cầu của thị trường"],
    },
}


def normalize_text(value: str) -> str:
    """Chuẩn hóa khoảng trắng, giữ nguyên Unicode tiếng Việt."""
    return re.sub(r"\s+", " ", value or "").strip()


def find_matches(text: str, patterns: list[str]) -> list[str]:
    matches = []
    for pattern in patterns:
        if re.search(pattern, text, flags=re.IGNORECASE):
            matches.append(pattern)
    return matches


def load_docx(path: Path) -> dict[str, Any]:
    document = Document(path)
    paragraphs = [normalize_text(p.text) for p in document.paragraphs if normalize_text(p.text)]

    table_text: list[str] = []
    for table in document.tables:
        for row in table.rows:
            cells = [normalize_text(cell.text) for cell in row.cells]
            row_text = " | ".join(cell for cell in cells if cell)
            if row_text:
                table_text.append(row_text)

    all_parts = paragraphs + table_text
    full_text = "\n".join(all_parts)
    searchable_text = normalize_text(full_text)
    lowered = searchable_text.casefold()

    placeholders = find_matches(lowered, PLACEHOLDER_PATTERNS)
    instruction_matches = find_matches(lowered, INSTRUCTION_PATTERNS)
    word_count = len(re.findall(r"\b[\wÀ-ỹ]+\b", searchable_text, flags=re.UNICODE))

    return {
        "filename": path.name,
        "paragraph_count": len(paragraphs),
        "table_count": len(document.tables),
        "word_count": word_count,
        "placeholders": placeholders,
        "instruction_count": len(instruction_matches),
        "text": searchable_text,
    }


def assess_document(doc: dict[str, Any], doc_type: str) -> dict[str, Any]:
    text = doc.get("text", "")
    lowered = text.casefold()

    topic_coverage: dict[str, Any] = {}
    for topic_id, topic in TOPIC_MAP.items():
        keywords = topic.get(doc_type, [])
        found = [keyword for keyword in keywords if keyword.casefold() in lowered]
        topic_coverage[topic_id] = {
            "label": topic["label"],
            "keywords_found": found,
            "keyword_count": len(found),
            "keyword_total": len(keywords),
            "status": (
                "not_applicable"
                if not keywords
                else "keywords_found"
                if found
                else "keywords_not_found"
            ),
        }

    if doc.get("word_count", 0) == 0:
        status = "empty_or_unreadable"
    elif doc.get("placeholders") or doc.get("instruction_count", 0) >= 5:
        status = "template_or_incomplete"
    else:
        status = "content_extracted_needs_review"

    return {
        "filename": doc["filename"],
        "document_type": doc_type,
        "status": status,
        "paragraph_count": doc["paragraph_count"],
        "table_count": doc["table_count"],
        "word_count": doc["word_count"],
        "placeholders": doc["placeholders"],
        "instruction_count": doc["instruction_count"],
        "topic_coverage": topic_coverage,
    }


def cross_check(documents: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    """Kiểm tra độ phủ từ khóa theo từng chủ đề; chưa kết luận ngữ nghĩa."""
    findings: list[dict[str, Any]] = []

    for topic_id, topic in TOPIC_MAP.items():
        participants = []
        missing_required_docs = []

        for doc_type in ("MRD", "PRD", "PROPOSAL"):
            if doc_type not in documents:
                continue

            keywords = topic.get(doc_type, [])
            text = documents[doc_type].get("text", "")
            lowered = text.casefold()
            found = [keyword for keyword in keywords if keyword.casefold() in lowered]

            # Chủ đề có danh sách từ khóa rỗng được xem là không áp dụng,
            # không phải bằng chứng thiếu nội dung.
            if keywords and not found:
                missing_required_docs.append(doc_type)

            participants.append({
                "document_type": doc_type,
                "filename": documents[doc_type]["filename"],
                "keywords": keywords,
                "found": found,
                "coverage": (
                    "not_applicable"
                    if not keywords
                    else "found"
                    if found
                    else "not_found"
                ),
            })

        if missing_required_docs:
            status = "keywords_missing_in_some_documents"
            explanation = (
                "Chưa tìm thấy từ khóa cấu hình cho chủ đề này trong: "
                + ", ".join(missing_required_docs)
                + ". Cần kiểm tra thủ công vì cách diễn đạt khác vẫn có thể đáp ứng chủ đề."
            )
        else:
            status = "keyword_coverage_only"
            explanation = (
                "Đã kiểm tra độ phủ từ khóa theo cấu hình. "
                "Kết quả không chứng minh nội dung đầy đủ, đúng hoặc nhất quán về ngữ nghĩa."
            )

        findings.append({
            "topic_id": topic_id,
            "topic": topic["label"],
            "status": status,
            "explanation": explanation,
            "documents": participants,
        })

    return findings


def analyze_folder(folder: Path, output: Path) -> dict[str, Any]:
    loaded: dict[str, dict[str, Any]] = {}

    for doc_type, filename in DEFAULT_DOCUMENTS.items():
        path = folder / filename
        if not path.is_file():
            raise FileNotFoundError(f"Thiếu file {filename} trong thư mục {folder}")

        doc = load_docx(path)
        doc["doc_type"] = doc_type
        loaded[doc_type] = doc

    assessments = [
        assess_document(doc, doc_type)
        for doc_type, doc in loaded.items()
    ]

    report = {
        "project": "JEV Document Analyst",
        "generated_at": datetime.now().astimezone().isoformat(),
        "status": "completed",
        "document_count": len(assessments),
        "documents": assessments,
        "cross_document_checks": cross_check(loaded),
        "limitations": [
            "Từ khóa không chứng minh nội dung đúng hoặc đầy đủ.",
            "Chưa đối chiếu ngữ nghĩa tự động.",
            "Dấu hiệu biểu mẫu được báo riêng; không tự động chặn kiểm tra từ khóa ở mọi chủ đề.",
            "Cần người dùng xác minh các điểm thiếu hoặc nghi vấn trước khi đưa ra kết luận.",
        ],
    }

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser(
        description="JEV Document Analyst — phân tích 3 file Word"
    )
    parser.add_argument(
        "--documents",
        default="data/documents",
        help="Thư mục chứa đúng 3 file DOCX",
    )
    parser.add_argument(
        "--output",
        default="reports/document_analysis.json",
        help="Đường dẫn báo cáo JSON",
    )
    args = parser.parse_args()

    folder = Path(args.documents)
    output = Path(args.output)

    try:
        report = analyze_folder(folder, output)
    except Exception as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1

    print("=== JEV DOCUMENT ANALYST ===")
    print(f"Documents: {report['document_count']}")
    print(f"Status: {report['status']}")
    print(f"Report: {output}")
    for doc in report["documents"]:
        print(f"- {doc['document_type']}: {doc['filename']} -> {doc['status']}")
    print("Lưu ý: keyword coverage chưa phải đối chiếu ngữ nghĩa.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
