from __future__ import annotations

import argparse
import ast
import json
import operator
import re
from pathlib import Path
from typing import Any

from docx import Document
from openpyxl import load_workbook
from openpyxl.utils.cell import range_boundaries


def _project_root() -> Path:
    cwd = Path.cwd()
    if (cwd / "src" / "documents").exists():
        return cwd
    return Path(__file__).resolve().parents[2]


def _find_input(root: Path, filename: str) -> Path:
    for folder in ("data/document", "data/documents"):
        candidate = root / folder / filename
        if candidate.exists():
            return candidate
    matches = list(root.glob(f"data/*/{filename}"))
    if matches:
        return matches[0]
    raise FileNotFoundError(f"Không tìm thấy file '{filename}' trong data/document hoặc data/documents")


def default_files(root: Path | None = None) -> dict[str, Path]:
    root = root or _project_root()
    return {
        "MRD": _find_input(root, "BM.01.01.MRD.NV_2023.docx"),
        "PRD": _find_input(root, "BM.01.02.PRD.NV_2023.docx"),
        "TTR": _find_input(root, "BM.01.03.TTR.NV_2023.docx"),
        "BUDGET": _find_input(root, "BM.01_Dự toán.xlsx"),
    }


DEFAULT_FILES = {
    "MRD": Path("data/documents/BM.01.01.MRD.NV_2023.docx"),
    "PRD": Path("data/documents/BM.01.02.PRD.NV_2023.docx"),
    "TTR": Path("data/documents/BM.01.03.TTR.NV_2023.docx"),
    "BUDGET": Path("data/documents/BM.01_Dự toán.xlsx"),
}

CHECKS = {
    "duration_months": {"label": "Thời gian thực hiện 18 tháng", "patterns": [r"\b18\s*tháng\b", r"\b18\s*months?\b"], "documents": ["MRD", "PRD", "TTR"]},
    "frequency_n78": {"label": "Băng tần n78 / 3.5 GHz", "patterns": [r"\bn78\b", r"3[.,]5\s*GHz", r"3500\s*MHz"], "documents": ["MRD", "PRD", "TTR"]},
    "bandwidth_100mhz": {"label": "Băng thông 100 MHz", "patterns": [r"\b100\s*MHz\b"], "documents": ["MRD", "PRD", "TTR"]},
    "throughput_1_2gbps": {"label": "Thông lượng tối thiểu 1.2 Gbps", "patterns": [r"1[.,]2\s*Gbps", r"1200\s*Mbps"], "documents": ["MRD", "PRD", "TTR"]},
    "evm_3_2": {"label": "EVM không vượt quá 3.2%", "patterns": [r"3[.,]2\s*%", r"3[.,]2\s*percent"], "documents": ["MRD", "PRD", "TTR"]},
    "runtime_72h": {"label": "Chạy liên tục tối thiểu 72 giờ", "patterns": [r"\b72\s*(?:giờ|h|hours?)\b"], "documents": ["MRD", "PRD", "TTR"]},
    "rf_4t4r": {"label": "Cấu hình nguyên mẫu 4T4R", "patterns": [r"\b4T4R\b"], "documents": ["MRD", "PRD", "TTR"]},
    "rf_32t32r": {"label": "Cấu hình tham chiếu 32T32R", "patterns": [r"\b32T32R\b"], "documents": ["MRD", "PRD", "TTR"]},
    "cost_reduction_40": {"label": "Mục tiêu giảm chi phí 40%", "patterns": [r"\b40\s*%", r"\b40\s*percent\b"], "documents": ["MRD", "PRD", "TTR"]},
}


def normalize_text(value: Any) -> str:
    text = "" if value is None else str(value)
    return re.sub(r"\s+", " ", text.replace("\u00a0", " ").replace("–", "-").replace("—", "-")).strip()


def read_docx(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"Không tìm thấy: {path}")
    document = Document(path)
    blocks = []
    for index, paragraph in enumerate(document.paragraphs, start=1):
        value = normalize_text(paragraph.text)
        if value:
            blocks.append({"document": path.name, "location": f"paragraph {index}", "text": value})
    for ti, table in enumerate(document.tables, start=1):
        for ri, row in enumerate(table.rows, start=1):
            value = " | ".join(normalize_text(c.text) for c in row.cells if normalize_text(c.text))
            if value:
                blocks.append({"document": path.name, "location": f"table {ti}, row {ri}", "text": value})
    return blocks


def read_xlsx(path: Path) -> tuple[list[dict[str, str]], dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"Không tìm thấy: {path}")
    value_wb = load_workbook(path, data_only=True, read_only=False)
    formula_wb = load_workbook(path, data_only=False, read_only=False)
    blocks, formulas = [], []
    try:
        for sheet in value_wb.sheetnames:
            vws, fws = value_wb[sheet], formula_wb[sheet]
            for row in vws.iter_rows():
                parts = []
                for cell in row:
                    if cell.value is None:
                        continue
                    parts.append(f"{cell.coordinate}={normalize_text(cell.value)}")
                    formula = fws[cell.coordinate].value
                    if isinstance(formula, str) and formula.startswith("="):
                        formulas.append({"sheet": sheet, "cell": cell.coordinate, "formula": formula, "cached_value": cell.value})
                if parts:
                    blocks.append({"document": path.name, "location": f"sheet {sheet}", "text": " | ".join(parts)})
        return blocks, {"sheets": list(value_wb.sheetnames), "formulas": formulas}
    finally:
        value_wb.close()
        formula_wb.close()


def contains_any(text: str, patterns: list[str]) -> bool:
    return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in patterns)


def run_parameter_checks(documents: dict[str, list[dict[str, str]]]) -> list[dict[str, Any]]:
    results = []
    for check_id, config in CHECKS.items():
        doc_results = []
        for key in config["documents"]:
            matches = [{"location": b["location"], "quote": b["text"]} for b in documents.get(key, []) if contains_any(b["text"], config["patterns"])]
            doc_results.append({"document": key, "status": "found" if matches else "not_found", "matches": matches[:10], "match_count": len(matches)})
        found = sum(d["status"] == "found" for d in doc_results)
        status = "present_in_all" if found == len(doc_results) else ("not_found_in_any" if found == 0 else "incomplete_coverage")
        results.append({"check_id": check_id, "label": config["label"], "status": status, "documents": doc_results,
                        "interpretation": "Chỉ xác nhận chuỗi xuất hiện; chưa xác nhận ngữ cảnh hoặc ý nghĩa."})
    return results


class FormulaEvaluator:
    """Evaluate a conservative subset of Excel formulas; unsupported formulas return None."""
    def __init__(self, formula_wb, value_wb):
        self.formula_wb = formula_wb
        self.value_wb = value_wb
        self._cache: dict[tuple[str, str], Any] = {}
        self._active: set[tuple[str, str]] = set()

    def cell_value(self, sheet: str, cell: str):
        key = (sheet, cell.replace("$", "").upper())
        if key in self._cache:
            return self._cache[key]
        if key in self._active:
            return None
        self._active.add(key)
        try:
            raw = self.formula_wb[sheet][key[1]].value
            if not (isinstance(raw, str) and raw.startswith("=")):
                value = raw
            else:
                value = self._eval_formula(raw[1:], sheet)
            self._cache[key] = value
            return value
        except Exception:
            return None
        finally:
            self._active.discard(key)

    def _split_args(self, text: str) -> list[str]:
        args, start, depth, in_quote = [], 0, 0, False
        i = 0
        while i < len(text):
            ch = text[i]
            if ch == "'":
                in_quote = not in_quote
            elif not in_quote:
                if ch == "(": depth += 1
                elif ch == ")": depth -= 1
                elif ch == "," and depth == 0:
                    args.append(text[start:i].strip())
                    start = i + 1
            i += 1
        args.append(text[start:].strip())
        return args

    def _eval_formula(self, formula: str, current_sheet: str):
        return self._eval_expr(formula.strip(), current_sheet)

    def _range_values(self, expr: str, current_sheet: str):
        ref = self._parse_ref(expr.strip(), current_sheet)
        if not ref:
            return []
        sheet, address = ref
        if ":" not in address:
            val = self.cell_value(sheet, address)
            return [] if val is None else [val]
        min_col, min_row, max_col, max_row = range_boundaries(address)
        out = []
        for row in self.formula_wb[sheet].iter_rows(min_row=min_row, max_row=max_row, min_col=min_col, max_col=max_col):
            for cell in row:
                val = self.cell_value(sheet, cell.coordinate)
                if isinstance(val, (int, float)):
                    out.append(val)
        return out

    def _parse_ref(self, token: str, current_sheet: str):
        token = token.strip()
        m = re.fullmatch(r"(?:(?:'([^']+)'|([A-Za-z0-9_ ]+))!)?\$?([A-Z]{1,3}\$?\d+(?::\$?[A-Z]{1,3}\$?\d+)?)", token, re.I)
        if not m:
            return None
        sheet = m.group(1) or m.group(2) or current_sheet
        address = m.group(3).replace("$", "").upper()
        if sheet not in self.formula_wb.sheetnames:
            return None
        return sheet, address

    def _eval_expr(self, expr: str, current_sheet: str):
        expr = expr.strip()
        # Resolve supported Excel functions recursively, including functions embedded in arithmetic.
        for _ in range(20):
            m = re.search(r"(?i)\b(IF|SUM|ROUND)\s*\(", expr)
            if not m:
                break
            name = m.group(1).upper()
            open_pos = expr.find("(", m.start())
            depth, close_pos, in_quote = 0, None, False
            for i in range(open_pos, len(expr)):
                ch = expr[i]
                if ch == "'": in_quote = not in_quote
                elif not in_quote:
                    if ch == "(": depth += 1
                    elif ch == ")":
                        depth -= 1
                        if depth == 0:
                            close_pos = i
                            break
            if close_pos is None:
                raise ValueError("unclosed function")
            args = self._split_args(expr[open_pos + 1:close_pos])
            if name == "SUM":
                result = sum(self._range_values(args[0], current_sheet), 0)
            elif name == "ROUND":
                if len(args) != 2: raise ValueError("ROUND expects 2 args")
                val = self._eval_expr(args[0], current_sheet)
                digits = int(self._eval_expr(args[1], current_sheet))
                result = round(val, digits)
            else:
                if len(args) != 3: raise ValueError("IF expects 3 args")
                cond = args[0]
                cm = re.fullmatch(r"(.+?)(<=|>=|<>|=|<|>)(.+)", cond)
                if not cm: raise ValueError("unsupported IF condition")
                left = self._eval_expr(cm.group(1), current_sheet)
                right = self._eval_expr(cm.group(3), current_sheet)
                op = cm.group(2)
                truth = {"=": left == right, "<>": left != right, "<": left < right, ">": left > right, "<=": left <= right, ">=": left >= right}[op]
                result = self._eval_expr(args[1] if truth else args[2], current_sheet)
            expr = expr[:m.start()] + str(result) + expr[close_pos + 1:]
        if re.search(r"(?i)\b(IF|SUM|ROUND)\s*\(", expr):
            raise ValueError("function nesting limit exceeded")

        # Replace cell references, including quoted cross-sheet references, with numeric literals.
        pattern = re.compile(r"(?:'([^']+)'!|([A-Za-z0-9_ ]+)!|)(\$?[A-Z]{1,3}\$?\d+)", re.I)
        def replace(match):
            sheet = match.group(1) or match.group(2) or current_sheet
            address = match.group(3).replace("$", "").upper()
            if sheet not in self.formula_wb.sheetnames:
                return match.group(0)
            value = self.cell_value(sheet, address)
            if value is None or not isinstance(value, (int, float)):
                raise ValueError("unresolved or non-numeric cell")
            return str(value)
        expr = pattern.sub(replace, expr)
        expr = expr.replace("^", "**")
        tree = ast.parse(expr, mode="eval")
        binops = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv, ast.Pow: operator.pow}
        def walk(node):
            if isinstance(node, ast.Expression): return walk(node.body)
            if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)): return node.value
            if isinstance(node, ast.BinOp) and type(node.op) in binops: return binops[type(node.op)](walk(node.left), walk(node.right))
            if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)): return walk(node.operand) * (1 if isinstance(node.op, ast.UAdd) else -1)
            raise ValueError("unsupported formula")
        return walk(tree)


def audit_workbook_formulas(path: Path) -> dict[str, Any]:
    formula_wb = load_workbook(path, data_only=False)
    value_wb = load_workbook(path, data_only=True)
    count, missing, details = 0, [], []
    try:
        evaluator = FormulaEvaluator(formula_wb, value_wb)
        for sheet in formula_wb.sheetnames:
            for row in formula_wb[sheet].iter_rows():
                for cell in row:
                    formula = cell.value
                    if not (isinstance(formula, str) and formula.startswith("=")):
                        continue
                    count += 1
                    cached = value_wb[sheet][cell.coordinate].value
                    calculated = evaluator.cell_value(sheet, cell.coordinate)
                    item = {"sheet": sheet, "cell": cell.coordinate, "formula": formula, "cached_value": cached, "calculated_value": calculated}
                    details.append(item)
                    if cached is None:
                        missing.append({"sheet": sheet, "cell": cell.coordinate, "formula": formula})
        return {"formula_count": count, "missing_cached_value_count": len(missing), "missing_cached_values": missing,
                "formulas": details, "limitation": "Chỉ tự tính tập con công thức; công thức không hỗ trợ trả về calculated_value=None. Không thay thế Excel."}
    finally:
        formula_wb.close()
        value_wb.close()


def audit_budget_reconciliation(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Không tìm thấy: {path}")
    wb_f = load_workbook(path, data_only=False)
    wb_v = load_workbook(path, data_only=True)
    try:
        if "Tong hop" not in wb_f.sheetnames:
            return {"status": "incomplete", "reason": "missing_sheet_Tong hop", "checks": []}
        ev = FormulaEvaluator(wb_f, wb_v)
        ws = wb_f["Tong hop"]
        checks = []
        # Known total cells in the workbook template; do not infer other totals.
        for cell in ("F29", "H29", "D32"):
            raw = ws[cell].value
            value = ev.cell_value("Tong hop", cell)
            checks.append({"cell": cell, "formula_or_value": raw, "calculated_value": value})
        vals = [x["calculated_value"] for x in checks]
        complete = all(isinstance(v, (int, float)) for v in vals)
        totals_agree = complete and all(abs(float(v) - float(vals[0])) < 0.01 for v in vals[1:])
        cache_mismatches = []
        for item in checks:
            cached = wb_v["Tong hop"][item["cell"]].value
            calc = item["calculated_value"]
            if isinstance(cached, (int, float)) and isinstance(calc, (int, float)) and abs(float(cached) - float(calc)) >= 0.01:
                cache_mismatches.append({"cell": item["cell"], "cached_value": cached, "calculated_value": calc})
        status = "incomplete" if not complete else ("inconsistent" if not totals_agree or cache_mismatches else "consistent")
        return {"status": status, "checks": checks, "cache_mismatches": cache_mismatches,
                "note": "Đối chiếu tổng F29, H29, D32 và so sánh cache Excel với kết quả tính lại; bộ đánh giá chỉ hỗ trợ một tập con công thức."}
    finally:
        wb_f.close()
        wb_v.close()


def inspect_budget_total(blocks: list[dict[str, str]]) -> dict[str, Any]:
    keywords = ("tổng kinh phí", "tổng cộng", "kinh phí tổng", "tổng dự toán")
    matches = [{"location": b["location"], "text": b["text"]} for b in blocks if any(k in b["text"].casefold() for k in keywords)]
    return {"status": "candidates_found" if matches else "not_found", "candidate_count": len(matches), "candidates": matches[:100],
            "note": "Xác minh đúng dòng tổng và đơn vị trước khi kết luận."}


def build_report(files: dict[str, Path]) -> dict[str, Any]:
    docs = {key: read_docx(files[key]) for key in ("MRD", "PRD", "TTR")}
    budget_blocks, meta = read_xlsx(files["BUDGET"])
    docs["BUDGET"] = budget_blocks
    return {"engine": "JEV Deterministic Cross-Document Audit", "mode": "read-only; no output files",
            "inputs": {key: str(path.resolve()) for key, path in files.items()},
            "document_summary": {key: {"block_count": len(v), "empty": not v} for key, v in docs.items()},
            "parameter_checks": run_parameter_checks(docs), "budget_total_candidates": inspect_budget_total(budget_blocks),
            "workbook": {"sheets": meta["sheets"], "formula_audit": audit_workbook_formulas(files["BUDGET"]),
                         "budget_reconciliation": audit_budget_reconciliation(files["BUDGET"])},
            "limitations": ["Chuỗi xuất hiện không chứng minh hai yêu cầu tương đương.", "Không tìm thấy chuỗi không chứng minh nội dung bị thiếu.",
                            "Không tự kết luận mâu thuẫn ngữ nghĩa.", "Chỉ hỗ trợ một tập con công thức Excel.", "Mọi kết luận ngữ nghĩa cần người kiểm tra."]}


def main() -> None:
    parser = argparse.ArgumentParser(description="JEV read-only audit for 3 DOCX + 1 XLSX.")
    parser.add_argument("--mrd", type=Path)
    parser.add_argument("--prd", type=Path)
    parser.add_argument("--ttr", type=Path)
    parser.add_argument("--budget", type=Path)
    args = parser.parse_args()
    defaults = default_files()
    files = {"MRD": args.mrd or defaults["MRD"], "PRD": args.prd or defaults["PRD"], "TTR": args.ttr or defaults["TTR"], "BUDGET": args.budget or defaults["BUDGET"]}
    try:
        report = build_report(files)
    except Exception as exc:
        raise SystemExit(f"[JEV AUDIT ERROR] {type(exc).__name__}: {exc}") from exc
    print(json.dumps(report, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
