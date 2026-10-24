
from __future__ import annotations

import argparse
import json
import os
import re
import time
import unicodedata
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


DEFAULT_INPUT = Path("reports/document_analysis.json")
DEFAULT_OUTPUT = Path("reports/semantic_review.json")
DEFAULT_MARKDOWN = Path("reports/semantic_review.md")

DEFAULT_BASE_URL = os.getenv(
    "JEV_LLM_BASE_URL",
    "http://127.0.0.1:8080/v1",
).rstrip("/")
DEFAULT_MODEL = os.getenv("JEV_LLM_MODEL", "local-model")

MAX_BLOCK_CHARS = 1800
MAX_EVIDENCE_CHARS = 9000
MAX_PAIR_BLOCKS = 10
REQUEST_TIMEOUT = 300

FINDING_TYPES = {
    "direct_contradiction",
    "numeric_inconsistency",
    "scope_gap",
    "unsupported_claim",
    "ambiguity",
    "risk",
}
SEVERITIES = {"low", "medium", "high", "critical"}


SYSTEM_PROMPT = r"""
Bạn là JEV, hệ thống phản biện chéo tài liệu dự án.

MỤC TIÊU
Phát hiện vấn đề có bằng chứng cụ thể giữa các tài liệu:
- Mâu thuẫn trực tiếp.
- Số liệu không nhất quán.
- Phạm vi thực sự không tương thích.
- Tuyên bố chưa có căn cứ.
- Điểm mơ hồ hoặc rủi ro có thể ảnh hưởng quyết định dự án.

NGUYÊN TẮC BẮT BUỘC

1. Chỉ sử dụng các đoạn trích được cung cấp.
   Không bịa nội dung, số liệu, tên tài liệu, vị trí hoặc trích dẫn.

2. Hai đoạn nói về hai chủ đề khác nhau KHÔNG tự động tạo thành
   mâu thuẫn, scope_gap hoặc unsupported_claim.

3. Không kết luận tài liệu thiếu nội dung chỉ vì nội dung đó
   không xuất hiện trong tập đoạn trích giới hạn được gửi cho bạn.

4. direct_contradiction:
   Phải xác định hai mệnh đề cụ thể, cùng đối tượng, điều kiện
   và phạm vi nhưng không thể đồng thời đúng.

5. numeric_inconsistency:
   Chỉ kết luận khi so sánh cùng đại lượng, đơn vị, đối tượng,
   thời điểm và điều kiện.

6. scope_gap:
   Phải chỉ ra nội dung hoặc yêu cầu cụ thể bị thiếu hoặc hai phạm vi
   không tương thích, đồng thời nêu căn cứ cho thấy tài liệu bị cho là
   thiếu có trách nhiệm hoặc có yêu cầu phải bao gồm nội dung đó.
   Không dùng việc hai tài liệu tập trung vào các chủ đề khác nhau
   để suy ra scope_gap.
   Việc một tài liệu nói một nội dung sẽ được xây dựng trong tương lai
   không tự động chứng minh thiếu sót nếu không có bằng chứng về
   yêu cầu, thời hạn hoặc tiêu chí bắt buộc bị vi phạm.
   Không coi các từ chung như "phân tích", "chỉ tiêu", "tính năng"
   là bằng chứng đủ để kết luận hai phạm vi không tương thích.

7. unsupported_claim:
   Phải xác định chính xác tuyên bố cần kiểm tra và vì sao bằng chứng
   được cung cấp chưa hỗ trợ tuyên bố đó. Không suy diễn sự vắng mặt
   từ vài đoạn trích.

8. ambiguity:
   Phải chỉ ra cụm từ hoặc yêu cầu cụ thể có nhiều cách hiểu,
   cùng hệ quả của sự mơ hồ đó.

9. risk:
   Phải chỉ ra điều kiện hoặc bằng chứng cụ thể tạo ra rủi ro.

10. Mọi bằng chứng phải trích nguyên văn từ đúng đoạn được cung cấp,
    kèm document và location chính xác.

11. Mỗi finding liên tài liệu phải có bằng chứng đã xác minh từ
    ít nhất hai tài liệu khác nhau.

12. Không dùng suy luận của finding làm bằng chứng chứng minh finding.

13. Nếu không đủ căn cứ, bỏ finding. Không tạo finding để làm báo cáo
    có nội dung.

14. Finding mặc định có status "needs_human_review".

15. Tập bằng chứng chỉ là một phần tài liệu. Không được dùng từ
    "chỉ", "toàn bộ", "không có" hoặc kết luận tương đương về toàn bộ
    tài liệu nếu bằng chứng được cung cấp không chứng minh điều đó.

ĐỊNH DẠNG
Chỉ trả về một JSON object hợp lệ, không Markdown, không code fence:

{
  "findings": [
    {
      "type": "direct_contradiction | numeric_inconsistency | scope_gap | unsupported_claim | ambiguity | risk",
      "severity": "low | medium | high | critical",
      "status": "needs_human_review",
      "title": "Tiêu đề ngắn",
      "explanation": "Nêu mệnh đề và quan hệ giữa chúng",
      "evidence": [
        {
          "document": "Tên file chính xác",
          "location": "Vị trí chính xác",
          "quote": "Trích dẫn nguyên văn"
        }
      ],
      "evidence_relationship": {
        "claim_a": "Mệnh đề được hỗ trợ bởi bằng chứng A",
        "claim_b": "Mệnh đề được hỗ trợ bởi bằng chứng B",
        "relationship": "direct_conflict | scope_mismatch | unsupported | ambiguity | risk",
        "reasoning": "Giải thích quan hệ logic"
      },
      "why_it_matters": "Ảnh hưởng có thể xảy ra",
      "question_to_resolve": "Câu hỏi cần xác minh",
      "recommendation": "Hành động đề xuất"
    }
  ],
  "documents_compared": ["Tên file A", "Tên file B"],
  "limitations": ["Giới hạn của lượt phân tích"]
}

Nếu không có finding đủ căn cứ, trả "findings": [].
"""


def normalize_text(value: Any) -> str:
    text = str(value or "").strip().lower()
    text = unicodedata.normalize("NFD", text)
    text = "".join(
        char for char in text
        if unicodedata.category(char) != "Mn"
    )
    return re.sub(r"\s+", " ", text)


def canonical_location(value: Any) -> str:
    location = str(value or "").strip()
    location = re.sub(
        r"\s*\(style:.*?\)\s*$",
        "",
        location,
        flags=re.IGNORECASE,
    )
    return normalize_text(location)


def meaningful_tokens(value: Any) -> set[str]:
    stopwords = {
        "va", "la", "cua", "cho", "trong", "tren", "duoi",
        "voi", "cac", "nhung", "mot", "nhieu", "nay", "do",
        "duoc", "khong", "co", "can", "phai", "se", "da",
        "dang", "theo", "tai", "tu", "den", "khi", "neu",
        "thi", "de", "ve", "giua", "bao", "gom", "muc",
        "noi", "dung", "yeu", "cau", "lieu", "du", "an",
        "pham", "vi", "thuc", "hien", "danh", "gia", "xay",
        "su", "he", "thong", "phuong",
    }
    tokens = set(re.findall(r"[a-z0-9]+", normalize_text(value)))
    return {
        token for token in tokens
        if len(token) >= 3 and token not in stopwords
    }


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8-sig") as file:
        data = json.load(file)

    if not isinstance(data, dict):
        raise ValueError("JSON đầu vào phải là một object.")

    if not isinstance(data.get("documents"), list) and not isinstance(
        data.get("evidence_blocks"), list
    ):
        raise ValueError(
            "JSON đầu vào thiếu danh sách 'documents' hoặc 'evidence_blocks'."
        )

    return data


def documents_from_source(source: dict[str, Any]) -> list[dict[str, Any]]:
    """Chuẩn hóa hai schema đầu vào thành danh sách documents."""
    raw_blocks = source.get("evidence_blocks")

    if isinstance(raw_blocks, list):
        grouped: dict[str, list[dict[str, Any]]] = {}

        for index, block in enumerate(raw_blocks, start=1):
            if not isinstance(block, dict):
                continue

            filename = str(
                block.get("source_file")
                or block.get("filename")
                or block.get("document")
                or block.get("file_name")
                or ""
            ).strip()

            if not filename:
                filename = "unknown"

            text = str(
                block.get("text")
                or block.get("content")
                or block.get("quote")
                or block.get("value")
                or ""
            ).strip()

            if not text:
                continue

            location = str(
                block.get("location")
                or block.get("source_location")
                or block.get("block_id")
                or block.get("id")
                or f"block {index}"
            ).strip()

            grouped.setdefault(filename, []).append({
                "text": text,
                "location": location,
            })

        return [
            {"filename": filename, "blocks": blocks}
            for filename, blocks in grouped.items()
        ]

    documents = source.get("documents", [])
    if not isinstance(documents, list):
        raise ValueError("'documents' phải là một list.")

    return documents


def make_evidence_blocks(
    documents: list[dict[str, Any]],
) -> list[dict[str, str]]:
    result: list[dict[str, str]] = []

    for document in documents:
        if not isinstance(document, dict):
            continue

        filename = str(
            document.get("filename")
            or document.get("name")
            or document.get("document")
            or "unknown"
        ).strip()

        candidates: list[Any] = []

        for key in ("blocks", "evidence", "paragraphs", "tables"):
            value = document.get(key)
            if isinstance(value, list):
                candidates.extend(value)

        for parent_key in ("analysis", "content", "extracted"):
            parent = document.get(parent_key)
            if isinstance(parent, dict):
                for key in ("blocks", "evidence", "paragraphs", "tables"):
                    value = parent.get(key)
                    if isinstance(value, list):
                        candidates.extend(value)

        for index, item in enumerate(candidates, start=1):
            if isinstance(item, str):
                text = item.strip()
                location = f"block {index}"

            elif isinstance(item, dict):
                text = str(
                    item.get("text")
                    or item.get("content")
                    or item.get("quote")
                    or item.get("value")
                    or ""
                ).strip()

                location = str(
                    item.get("location")
                    or item.get("source_location")
                    or item.get("position")
                    or item.get("id")
                    or f"block {index}"
                ).strip()
            else:
                continue

            if text:
                result.append({
                    "document": filename,
                    "location": location,
                    "text": text[:MAX_BLOCK_CHARS],
                })

    unique: list[dict[str, str]] = []
    seen: set[tuple[str, str, str]] = set()

    for block in result:
        key = (
            block["document"],
            canonical_location(block["location"]),
            normalize_text(block["text"]),
        )
        if key not in seen:
            seen.add(key)
            unique.append(block)

    if not unique:
        raise ValueError(
            "Không trích xuất được evidence blocks từ document_analysis.json. "
            "Kiểm tra schema JSON của analyzer."
        )

    return unique


def call_llm(
    messages: list[dict[str, str]],
    base_url: str,
    model: str,
) -> str:
    url = f"{base_url.rstrip('/')}/chat/completions"
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.1,
        "stream": False,
    }

    request = Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urlopen(request, timeout=REQUEST_TIMEOUT) as response:
            body = response.read().decode("utf-8")
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"LLM HTTP {exc.code}: {detail[:1500]}") from exc
    except URLError as exc:
        raise RuntimeError(f"Không kết nối được LLM tại {url}: {exc}") from exc

    try:
        result = json.loads(body)
        content = result["choices"][0]["message"]["content"]
    except (json.JSONDecodeError, KeyError, IndexError, TypeError) as exc:
        raise RuntimeError(
            f"Phản hồi LLM không đúng định dạng chat completion: {body[:1000]}"
        ) from exc

    if not isinstance(content, str) or not content.strip():
        raise RuntimeError("LLM trả về nội dung rỗng.")

    return content.strip()


def parse_llm_json(raw: str) -> dict[str, Any]:
    text = raw.strip()
    text = re.sub(
        r"^\s*```(?:json)?\s*",
        "",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"\s*```$", "", text)

    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end < start:
        raise ValueError("LLM không trả về JSON object hợp lệ.")

    parsed = json.loads(text[start:end + 1])
    if not isinstance(parsed, dict):
        raise ValueError("Kết quả LLM phải là JSON object.")
    if not isinstance(parsed.get("findings", []), list):
        raise ValueError("Trường 'findings' phải là một list.")

    return parsed


def select_evidence(
    blocks: list[dict[str, str]],
    focus: str,
    max_blocks: int,
) -> list[dict[str, str]]:
    focus_tokens = meaningful_tokens(focus)
    scored: list[tuple[float, int, dict[str, str]]] = []

    for index, block in enumerate(blocks):
        text_tokens = meaningful_tokens(block["text"])
        overlap = len(focus_tokens & text_tokens)
        length_bonus = min(len(block["text"]) / 1000, 0.3)
        scored.append((overlap + length_bonus, index, block))

    scored.sort(key=lambda row: (-row[0], row[1]))
    return [row[2] for row in scored[:max_blocks]]


def fit_evidence_budget(
    blocks: list[dict[str, str]],
    max_chars: int = MAX_EVIDENCE_CHARS,
) -> list[dict[str, str]]:
    selected: list[dict[str, str]] = []
    used = 0

    for block in blocks:
        rendered = (
            f"[DOCUMENT: {block['document']}]\n"
            f"[LOCATION: {block['location']}]\n"
            f"[VERBATIM TEXT:]\n{block['text']}\n\n"
        )

        if used + len(rendered) > max_chars:
            remaining = max_chars - used
            if remaining < 150:
                break

            copy = dict(block)
            copy["text"] = block["text"][:max(0, remaining - 100)]
            if copy["text"]:
                selected.append(copy)
            break

        selected.append(block)
        used += len(rendered)

    return selected


def verify_evidence_item(
    evidence: Any,
    source_blocks: list[dict[str, str]],
    allowed_documents: set[str],
) -> dict[str, str] | None:
    if not isinstance(evidence, dict):
        return None

    document = str(evidence.get("document", "")).strip()
    location = str(evidence.get("location", "")).strip()
    quote = str(evidence.get("quote") or evidence.get("text") or "").strip()

    if not document or not location or not quote:
        return None
    if document not in allowed_documents:
        return None

    wanted_location = canonical_location(location)
    wanted_quote = normalize_text(quote)
    if not wanted_quote:
        return None

    for source in source_blocks:
        if source["document"] != document:
            continue
        if canonical_location(source["location"]) != wanted_location:
            continue
        if wanted_quote in normalize_text(source["text"]):
            return {
                "document": source["document"],
                "location": source["location"],
                "quote": quote,
            }

    return None


def evidence_relevance_score(
    evidence: dict[str, str],
    finding: dict[str, Any],
) -> float:
    quote_tokens = meaningful_tokens(evidence.get("quote", ""))
    relationship = finding.get("evidence_relationship", {})
    if not isinstance(relationship, dict):
        relationship = {}

    finding_text = " ".join([
        str(finding.get("title", "")),
        str(finding.get("explanation", "")),
        str(finding.get("why_it_matters", "")),
        str(relationship.get("claim_a", "")),
        str(relationship.get("claim_b", "")),
    ])
    finding_tokens = meaningful_tokens(finding_text)

    if not quote_tokens or not finding_tokens:
        return 0.0

    return len(quote_tokens & finding_tokens) / max(1, len(finding_tokens))


def has_substantive_evidence(
    finding: dict[str, Any],
    evidence: list[dict[str, str]],
    allowed_documents: set[str],
) -> tuple[bool, str]:
    if len(evidence) < 2:
        return False, "Cần ít nhất hai bằng chứng đã xác minh."

    documents = {item["document"] for item in evidence}
    if len(documents) < 2:
        return False, "Finding liên tài liệu cần bằng chứng từ hai tài liệu."
    if not documents.issubset(allowed_documents):
        return False, "Bằng chứng chứa tài liệu ngoài cặp đang so sánh."

    scores = [evidence_relevance_score(item, finding) for item in evidence]
    if not any(score >= 0.08 for score in scores):
        return False, "Các trích dẫn không liên hệ đủ rõ với nội dung finding."

    return True, ""


def scope_gap_guard(
    finding: dict[str, Any],
    evidence: list[dict[str, str]],
) -> tuple[bool, str]:
    by_document: dict[str, list[dict[str, str]]] = {}
    for item in evidence:
        by_document.setdefault(item["document"], []).append(item)

    if len(by_document) < 2:
        return False, "Scope gap cần bằng chứng từ ít nhất hai tài liệu."

    relationship = finding.get("evidence_relationship", {})
    if not isinstance(relationship, dict):
        return False, "Thiếu evidence_relationship."

    claim_a = normalize_text(relationship.get("claim_a", ""))
    claim_b = normalize_text(relationship.get("claim_b", ""))
    reasoning = normalize_text(relationship.get("reasoning", ""))
    explanation = normalize_text(finding.get("explanation", ""))

    combined_claim = " ".join([claim_a, claim_b, reasoning, explanation])

    non_issue_markers = (
        "khong tao ra mau thuan",
        "khong tao ra thieu sot",
        "khong tao ra mau thuan hoac thieu sot",
        "tap trung vao cac chu de khac nhau",
        "khac chu de khong dong nghia",
        "khong tao ra mau thuan, scope_gap",
        "khong tao ra mau thuan, scope_gap hoac unsupported_claim",
        "khong tao ra mau thuan hoac scope_gap",
    )
    if any(marker in combined_claim for marker in non_issue_markers):
        return False, (
            "Lý do cho thấy các tài liệu khác chủ đề nhưng không chỉ ra "
            "một yêu cầu cụ thể bị thiếu hoặc bị vi phạm."
        )

    requirement_markers = (
        "yeu cau bat buoc", "phai bao gom", "bat buoc phai",
        "theo yeu cau", "tieu chi bat buoc", "yeu cau quy dinh",
        "quy dinh phai", "muc tieu bat buoc", "pham vi da duoc xac dinh",
        "dieu kien bat buoc", "cam ket phai", "must include",
        "shall include", "required by", "mandatory requirement",
    )
    if not any(marker in combined_claim for marker in requirement_markers):
        return False, (
            "Không có bằng chứng về yêu cầu cụ thể bắt buộc tài liệu "
            "bị cho là thiếu phải bao gồm nội dung đó."
        )

    gap_markers = (
        "chua co", "chua duoc", "thieu", "bo sot", "khong bao gom",
        "khong dap ung", "khong thuc hien", "chua dap ung",
        "chua bao gom", "khong co noi dung", "missing", "omits",
        "does not satisfy", "not included", "not implemented",
    )
    if not any(marker in combined_claim for marker in gap_markers):
        return False, "Không chỉ ra dấu hiệu thiếu hụt hoặc vi phạm yêu cầu cụ thể."

    generic_tokens = {
        "phan", "tich", "chi", "tieu", "tinh", "nang", "xay",
        "dung", "tai", "lieu", "muc", "thuc", "hien", "du",
        "an", "pham", "vi", "noi", "dung", "yeu", "cau",
        "khong", "chua", "co", "phai", "theo", "bao", "gom",
    }

    substantive_shared_concept = False
    docs = list(by_document)
    for left_doc, right_doc in combinations(docs, 2):
        for left in by_document[left_doc]:
            left_tokens = meaningful_tokens(left["quote"]) - generic_tokens
            for right in by_document[right_doc]:
                right_tokens = meaningful_tokens(right["quote"]) - generic_tokens
                if len(left_tokens & right_tokens) >= 2:
                    substantive_shared_concept = True
                    break
            if substantive_shared_concept:
                break
        if substantive_shared_concept:
            break

    if not substantive_shared_concept:
        return False, (
            "Các trích dẫn không có đủ khái niệm thực chất chung; "
            "không thể suy ra scope gap chỉ từ các chủ đề khác nhau."
        )

    reasoning_tokens = meaningful_tokens(reasoning)
    quote_tokens = set().union(*[
        meaningful_tokens(item["quote"]) - generic_tokens
        for item in evidence
    ])
    if len(reasoning_tokens & quote_tokens) < 2:
        return False, (
            "Reasoning chưa liên kết đủ rõ với nội dung thực tế trong trích dẫn."
        )

    return True, ""


def numeric_guard(
    evidence: list[dict[str, str]],
) -> tuple[bool, str]:
    numeric_evidence = []

    for item in evidence:
        numbers = re.findall(
            r"(?<!\w)\d+(?:[.,]\d+)?"
            r"(?:\s*%|\s*(?:đồng|vnd|triệu|tỷ|ngày|tháng|năm|kg|m|gb|mb))?",
            normalize_text(item["quote"]),
        )
        if numbers:
            numeric_evidence.append(item)

    if len({item["document"] for item in numeric_evidence}) < 2:
        return False, (
            "Không tìm thấy số liệu trong ít nhất hai tài liệu để đối chiếu."
        )

    return True, ""


def relationship_guard(
    finding: dict[str, Any],
) -> tuple[bool, str]:
    relation = finding.get("evidence_relationship")
    if not isinstance(relation, dict):
        return False, "Thiếu evidence_relationship."

    claim_a = str(relation.get("claim_a", "")).strip()
    claim_b = str(relation.get("claim_b", "")).strip()
    reasoning = str(relation.get("reasoning", "")).strip()
    relation_type = str(relation.get("relationship", "")).strip()

    if not claim_a or not claim_b or not reasoning:
        return False, (
            "evidence_relationship phải có claim_a, claim_b và reasoning."
        )
    if not relation_type:
        return False, "Thiếu loại quan hệ trong evidence_relationship."

    return True, ""


def validate_findings(
    parsed: dict[str, Any],
    allowed_documents: set[str],
    source_blocks: list[dict[str, str]],
) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    validated: list[dict[str, Any]] = []
    rejected: list[dict[str, str]] = []

    for index, finding in enumerate(parsed.get("findings", [])):
        if not isinstance(finding, dict):
            rejected.append({"index": str(index), "reason": "Finding không phải object."})
            continue

        finding_type = str(finding.get("type", "")).strip()
        severity = str(finding.get("severity", "low")).lower().strip()

        if finding_type not in FINDING_TYPES:
            rejected.append({
                "index": str(index),
                "reason": f"Loại finding không hợp lệ: {finding_type}",
            })
            continue
        if severity not in SEVERITIES:
            severity = "low"

        raw_evidence = finding.get("evidence", [])
        if not isinstance(raw_evidence, list):
            raw_evidence = []

        verified_evidence: list[dict[str, str]] = []
        seen_evidence: set[tuple[str, str, str]] = set()

        for item in raw_evidence:
            verified = verify_evidence_item(item, source_blocks, allowed_documents)
            if verified is None:
                continue

            key = (
                verified["document"],
                canonical_location(verified["location"]),
                normalize_text(verified["quote"]),
            )
            if key not in seen_evidence:
                seen_evidence.add(key)
                verified_evidence.append(verified)

        ok, reason = has_substantive_evidence(
            finding, verified_evidence, allowed_documents
        )
        if not ok:
            rejected.append({
                "index": str(index),
                "title": str(finding.get("title", ""))[:200],
                "reason": reason,
            })
            continue

        ok, reason = relationship_guard(finding)
        if not ok:
            rejected.append({
                "index": str(index),
                "title": str(finding.get("title", ""))[:200],
                "reason": reason,
            })
            continue

        if finding_type == "scope_gap":
            ok, reason = scope_gap_guard(finding, verified_evidence)
            if not ok:
                rejected.append({
                    "index": str(index),
                    "title": str(finding.get("title", ""))[:200],
                    "reason": reason,
                })
                continue

        if finding_type == "numeric_inconsistency":
            ok, reason = numeric_guard(verified_evidence)
            if not ok:
                rejected.append({
                    "index": str(index),
                    "title": str(finding.get("title", ""))[:200],
                    "reason": reason,
                })
                continue

        relationship = finding.get("evidence_relationship", {})
        if not isinstance(relationship, dict):
            relationship = {}

        validated.append({
            "type": finding_type,
            "severity": severity,
            "status": "needs_human_review",
            "title": str(finding.get("title", ""))[:300],
            "explanation": str(finding.get("explanation", ""))[:3000],
            "evidence": verified_evidence,
            "evidence_relationship": {
                "claim_a": str(relationship.get("claim_a", ""))[:1000],
                "claim_b": str(relationship.get("claim_b", ""))[:1000],
                "relationship": str(relationship.get("relationship", ""))[:100],
                "reasoning": str(relationship.get("reasoning", ""))[:2000],
            },
            "why_it_matters": str(finding.get("why_it_matters", ""))[:1500],
            "question_to_resolve": str(finding.get("question_to_resolve", ""))[:1500],
            "recommendation": str(finding.get("recommendation", ""))[:1500],
        })

    return validated, rejected


def review_pair(
    left: str,
    right: str,
    blocks: list[dict[str, str]],
    base_url: str,
    model: str,
) -> dict[str, Any]:
    left_blocks = [b for b in blocks if b["document"] == left]
    right_blocks = [b for b in blocks if b["document"] == right]

    if not left_blocks or not right_blocks:
        return {
            "documents_compared": [left, right],
            "findings": [],
            "rejected_findings": [],
            "error": "Một trong hai tài liệu không có evidence blocks.",
        }

    focus = (
        "mục tiêu phạm vi đối tượng chức năng yêu cầu số liệu "
        "công nghệ kiến trúc tiến độ điều kiện chi phí"
    )
    left_selected = select_evidence(
        left_blocks, focus=focus, max_blocks=MAX_PAIR_BLOCKS // 2
    )
    right_selected = select_evidence(
        right_blocks, focus=focus, max_blocks=MAX_PAIR_BLOCKS // 2
    )
    selected = fit_evidence_budget(left_selected + right_selected)

    evidence_text = "\n\n".join(
        f"[DOCUMENT: {item['document']}]\n"
        f"[LOCATION: {item['location']}]\n"
        f"[VERBATIM TEXT:]\n{item['text']}"
        for item in selected
    )

    user_prompt = f"""
Phản biện chéo hai tài liệu sau:

Tài liệu A: {left}
Tài liệu B: {right}

Chỉ tạo finding nếu bằng chứng hỗ trợ được mối quan hệ logic cụ thể.
Không suy ra mâu thuẫn chỉ vì hai đoạn nói về hai chủ đề khác nhau.
Không suy ra nội dung bị thiếu từ tập trích dẫn có giới hạn.

Đối với scope_gap, bắt buộc trả lời được:
- Nội dung hoặc yêu cầu cụ thể nào bị thiếu?
- Bằng chứng nào xác định nội dung đó cần có?
- Vì sao tài liệu được cho là thiếu phải bao gồm nội dung đó?
- Bằng chứng nào chứng minh phạm vi không tương thích?

Nếu không trả lời được các câu hỏi trên bằng bằng chứng được cung cấp,
không tạo scope_gap.

Với mỗi finding:
- Trích nguyên văn từ evidence blocks.
- Dùng chính xác tên tài liệu và location đã cung cấp.
- Nêu hai mệnh đề cụ thể trong evidence_relationship.
- Giải thích quan hệ logic, không chỉ lặp lại tiêu đề.
- Không dùng việc hai tài liệu có trọng tâm khác nhau làm bằng chứng
  cho mâu thuẫn hoặc thiếu sót.
- Nếu không đủ căn cứ, bỏ finding.

EVIDENCE BLOCKS:

{evidence_text}

Trả về đúng JSON schema trong system prompt.
"""

    raw = call_llm(
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        base_url=base_url,
        model=model,
    )
    parsed = parse_llm_json(raw)

    findings, rejected = validate_findings(
        parsed=parsed,
        allowed_documents={left, right},
        source_blocks=blocks,
    )

    return {
        "documents_compared": [left, right],
        "evidence_blocks_sent": len(selected),
        "findings": findings,
        "rejected_findings": rejected,
        "limitations": parsed.get("limitations", []),
    }


def render_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# JEV — Semantic Document Review",
        "",
        f"- Generated: {report['generated_at']}",
        f"- Model: {report['model']}",
        f"- Documents: {summary['documents']}",
        f"- Evidence blocks: {summary['evidence_blocks']}",
        f"- Pairs reviewed: {summary['pairs_reviewed']}",
        f"- Pairs failed: {summary['pairs_failed']}",
        f"- Findings retained: {summary['findings']}",
        f"- Findings rejected: {summary['rejected_findings']}",
        "",
        "> Finding do mô hình đề xuất chưa phải kết luận cuối cùng. "
        "Cần người có trách nhiệm xác minh.",
        "",
    ]

    for index, finding in enumerate(report["findings"], start=1):
        lines.extend([
            f"## {index}. [{finding['severity']}] {finding['title']}",
            "",
            f"- Type: `{finding['type']}`",
            f"- Status: `{finding['status']}`",
            f"- Explanation: {finding['explanation']}",
            f"- Why it matters: {finding['why_it_matters']}",
            f"- Question to resolve: {finding['question_to_resolve']}",
            f"- Recommendation: {finding['recommendation']}",
            "",
            "### Evidence relationship",
            "",
            f"- Claim A: {finding['evidence_relationship']['claim_a']}",
            f"- Claim B: {finding['evidence_relationship']['claim_b']}",
            f"- Relationship: `{finding['evidence_relationship']['relationship']}`",
            f"- Reasoning: {finding['evidence_relationship']['reasoning']}",
            "",
            "### Evidence",
            "",
        ])

        for evidence in finding["evidence"]:
            lines.extend([
                f"- `{evidence['document']}` — `{evidence['location']}`",
                f"  > {evidence['quote']}",
            ])
        lines.append("")

    lines.extend(["## Pair execution", ""])
    for pair in report["pair_results"]:
        docs = " ↔ ".join(pair["documents_compared"])
        lines.append(f"- {docs}: {len(pair.get('findings', []))} finding(s)")

        if pair.get("error"):
            lines.append(f"  - Error: {pair['error']}")

        for rejected in pair.get("rejected_findings", []):
            lines.append(
                "  - Rejected: "
                f"{rejected.get('title') or rejected.get('index', '?')} — "
                f"{rejected.get('reason', 'Unknown reason')}"
            )

    lines.extend(["", "## Limitations", ""])
    for limitation in report["limitations"]:
        lines.append(f"- {limitation}")
    lines.append("")

    return "\n".join(lines)


def analyze(
    input_path: Path,
    output_path: Path,
    markdown_path: Path,
    base_url: str,
    model: str,
    max_pairs: int = 20,
) -> dict[str, Any]:
    source = load_json(input_path)
    documents = documents_from_source(source)

    if len(documents) < 2:
        raise ValueError(
            "Cần ít nhất hai tài liệu để phản biện chéo. "
            "Kiểm tra source_file trong evidence_blocks."
        )

    filenames: list[str] = []
    normalized_documents: list[dict[str, Any]] = []

    for index, document in enumerate(documents):
        if not isinstance(document, dict):
            continue

        filename = str(
            document.get("filename")
            or document.get("name")
            or document.get("document")
            or f"document_{index + 1}"
        ).strip()

        filenames.append(filename)
        normalized = dict(document)
        normalized["filename"] = filename
        normalized_documents.append(normalized)

    documents = normalized_documents

    if len(documents) < 2:
        raise ValueError("Cần ít nhất hai tài liệu hợp lệ để phản biện chéo.")

    blocks = make_evidence_blocks(documents)
    pairs = list(combinations(filenames, 2))[:max_pairs]

    pair_results: list[dict[str, Any]] = []
    all_findings: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    rejected_count = 0

    for index, (left, right) in enumerate(pairs, start=1):
        print(
            f"[JEV] Reviewing pair {index}/{len(pairs)}: "
            f"{left} <-> {right}"
        )
        started = time.time()

        try:
            result = review_pair(
                left=left,
                right=right,
                blocks=blocks,
                base_url=base_url,
                model=model,
            )
            result["elapsed_seconds"] = round(time.time() - started, 2)
            pair_results.append(result)
            all_findings.extend(result.get("findings", []))
            rejected_count += len(result.get("rejected_findings", []))

            if result.get("error"):
                errors.append(result)

        except Exception as exc:
            error = {
                "documents_compared": [left, right],
                "findings": [],
                "rejected_findings": [],
                "error": f"{type(exc).__name__}: {exc}",
            }
            pair_results.append(error)
            errors.append(error)
            print(f"[JEV WARNING] {error['error']}")

    report = {
        "schema_version": "1.1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "engine": "JEV Semantic Reviewer",
        "model": model,
        "base_url": base_url,
        "summary": {
            "documents": len(documents),
            "evidence_blocks": len(blocks),
            "pairs_reviewed": len(pair_results),
            "pairs_failed": len(errors),
            "findings": len(all_findings),
            "rejected_findings": rejected_count,
        },
        "pair_results": pair_results,
        "findings": all_findings,
        "errors": errors,
        "limitations": [
            "Lựa chọn evidence dùng heuristic từ khóa, chưa dùng embedding.",
            "Mỗi cặp chỉ gửi một tập con bằng chứng, không phải toàn bộ tài liệu.",
            "Có thể bỏ sót vấn đề nằm ngoài các đoạn được chọn.",
            "Xác minh trích dẫn không chứng minh rằng suy luận logic là đúng.",
            "Các finding được giữ lại vẫn cần con người xác minh.",
            "scope_gap guard là heuristic bảo thủ; có thể bỏ sót cách diễn đạt đồng nghĩa.",
            "numeric_guard chỉ kiểm tra sơ bộ việc có số liệu ở hai tài liệu.",
            "Chỉ xử lý văn bản đã được analyzer trích xuất.",
        ],
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)

    output_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    markdown_path.write_text(render_markdown(report), encoding="utf-8")

    return report


def main() -> None:
    parser = argparse.ArgumentParser(
        description="JEV semantic review for Word documents."
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MARKDOWN)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--max-pairs", type=int, default=20)

    args = parser.parse_args()

    if args.max_pairs < 1:
        raise SystemExit("--max-pairs phải lớn hơn 0.")

    try:
        report = analyze(
            input_path=args.input,
            output_path=args.output,
            markdown_path=args.markdown,
            base_url=args.base_url,
            model=args.model,
            max_pairs=args.max_pairs,
        )
    except Exception as exc:
        raise SystemExit(
            f"[JEV ERROR] {type(exc).__name__}: {exc}"
        ) from exc

    print("=== JEV SEMANTIC REVIEW ===")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    print(f"JSON: {args.output.resolve()}")
    print(f"Markdown: {args.markdown.resolve()}")


if __name__ == "__main__":
    main()
