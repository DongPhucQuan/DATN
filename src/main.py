
from __future__ import annotations

import argparse
import csv
import json
import sys

from datetime import datetime
from pathlib import Path
from typing import Any

from src.core.engine import JEVEngine
from src.jev.chat import JEVChat


APP_NAME = "JEV Finance"
APP_VERSION = "1.0.1"
DEFAULT_THRESHOLD = 0.15

DEFAULT_INVOICES = [
    {
        "invoice_id": "INV001",
        "expected_price": 100,
        "actual_price": 120,
    },
    {
        "invoice_id": "INV002",
        "expected_price": 100,
        "actual_price": 105,
    },
]


def configure_terminal() -> None:
    """Ưu tiên UTF-8 để hiển thị tiếng Việt trên Windows."""
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            try:
                reconfigure(encoding="utf-8")
            except (OSError, ValueError):
                pass


def load_json_input(
    path: Path,
) -> tuple[list[dict[str, Any]], float | None]:
    try:
        with path.open("r", encoding="utf-8-sig") as file:
            payload = json.load(file)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"JSON không hợp lệ tại dòng {exc.lineno}, "
            f"cột {exc.colno}: {exc.msg}"
        ) from exc

    if isinstance(payload, list):
        return payload, None

    if isinstance(payload, dict):
        invoices = payload.get("invoices")
        threshold = payload.get("threshold")

        if not isinstance(invoices, list):
            raise ValueError(
                'File JSON phải có trường "invoices" là một mảng.'
            )

        return invoices, threshold

    raise ValueError(
        'JSON phải là mảng hóa đơn hoặc object chứa trường "invoices".'
    )


def load_csv_input(path: Path) -> list[dict[str, Any]]:
    invoices: list[dict[str, Any]] = []

    try:
        with path.open(
            "r",
            encoding="utf-8-sig",
            newline="",
        ) as file:
            reader = csv.DictReader(file)

            required = {
                "invoice_id",
                "expected_price",
                "actual_price",
            }

            headers = set(reader.fieldnames or [])
            missing = required - headers

            if missing:
                raise ValueError(
                    "CSV thiếu các cột bắt buộc: "
                    + ", ".join(sorted(missing))
                )

            for line_number, row in enumerate(reader, start=2):
                try:
                    invoices.append(
                        {
                            "invoice_id": row["invoice_id"],
                            "expected_price": float(
                                row["expected_price"]
                            ),
                            "actual_price": float(
                                row["actual_price"]
                            ),
                        }
                    )
                except (TypeError, ValueError) as exc:
                    raise ValueError(
                        f"Dữ liệu số không hợp lệ ở dòng CSV {line_number}."
                    ) from exc

    except UnicodeDecodeError as exc:
        raise ValueError(
            f"Không thể đọc mã hóa của file CSV: {path}"
        ) from exc

    return invoices


def load_input(
    input_path: Path | None,
) -> tuple[list[dict[str, Any]], float | None, str]:
    if input_path is None:
        return DEFAULT_INVOICES, None, "built_in_sample"

    if not input_path.is_file():
        raise FileNotFoundError(
            f"Không tìm thấy file đầu vào: {input_path}"
        )

    suffix = input_path.suffix.lower()

    if suffix == ".json":
        invoices, threshold = load_json_input(input_path)
        return invoices, threshold, str(input_path)

    if suffix == ".csv":
        return load_csv_input(input_path), None, str(input_path)

    raise ValueError(
        "Định dạng đầu vào được hỗ trợ: .json và .csv"
    )


def save_report(
    report: dict[str, Any],
    output_path: Path,
) -> None:
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary_path = output_path.with_suffix(
        output_path.suffix + ".tmp"
    )

    try:
        with temporary_path.open(
            "w",
            encoding="utf-8",
        ) as file:
            json.dump(
                report,
                file,
                ensure_ascii=False,
                indent=2,
                allow_nan=False,
            )
            file.write("\n")

        temporary_path.replace(output_path)

    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def print_banner() -> None:
    print()
    print("=" * 60)
    print("              JEV AI — TRỢ LÝ CỤC BỘ")
    print(f"                    Phiên bản {APP_VERSION}")
    print("=" * 60)
    print("Ngôn ngữ mặc định : Tiếng Việt")
    print("Mô hình           : Qwen qua llama.cpp")
    print("Nhập /help để xem lệnh.")
    print("Nhập /exit để kết thúc phiên.")
    print("=" * 60)
    print()


def print_help() -> None:
    print(
        """
CÁC LỆNH JEV
------------
/help              Hiển thị trợ giúp
/status            Xem trạng thái phiên
/clear             Xóa lịch sử hội thoại
/hoadon            Phân tích bộ hóa đơn mẫu
/nguong 0.15       Đặt ngưỡng phát hiện 15%
/exit              Thoát chương trình

CÁCH SỬ DỤNG
------------
- Nhập câu hỏi bình thường để trò chuyện với Qwen.
- Lệnh /hoadon gọi pipeline phân tích hóa đơn JEV Finance.
- Ngưỡng 0.15 tương ứng 15%.
- Lịch sử hội thoại chỉ được giữ trong phiên hiện tại.
"""
    )


def interactive_mode(
    engine: JEVEngine,
    threshold: float = DEFAULT_THRESHOLD,
) -> int:
    print_banner()

    # D?ng chung QwenClient v?i engine, kh?ng t?o client th? hai.
    jev_chat = JEVChat(qwen=engine.qwen)

    history: list[dict[str, str]] = []
    turn = 0

    while True:
        try:
            user_text = input("Bạn > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nJEV > Đã kết thúc phiên làm việc.")
            return 0

        if not user_text:
            continue

        command_parts = user_text.split(maxsplit=1)
        command = command_parts[0].casefold()
        argument = (
            command_parts[1].strip()
            if len(command_parts) > 1
            else ""
        )

        if command in {"/exit", "/quit", "/q"}:
            print("JEV > Hẹn gặp lại!")
            return 0

        if command == "/help":
            print_help()
            continue

        if command == "/status":
            print("\n--- TRẠNG THÁI JEV ---")
            print(f"Phiên bản       : {APP_VERSION}")
            print("Chế độ          : Interactive")
            print("Ngôn ngữ        : Tiếng Việt mặc định")
            print(f"Số lượt chat    : {turn}")
            print(f"Ngưỡng hóa đơn  : {threshold:.0%}")
            print(f"Số tin lịch sử  : {len(history)}")
            print("----------------------\n")
            continue

        if command == "/clear":
            history.clear()
            turn = 0
            print("JEV > Đã xóa lịch sử hội thoại trong phiên.\n")
            continue

        if command == "/nguong":
            if not argument:
                print(
                    f"JEV > Ngưỡng hiện tại là {threshold:.0%}. "
                    "Ví dụ: /nguong 0.15\n"
                )
                continue

            try:
                new_threshold = float(argument)
            except ValueError:
                print(
                    "JEV > Ngưỡng phải là số. "
                    "Ví dụ: /nguong 0.15\n"
                )
                continue

            if not 0 < new_threshold <= 1:
                print(
                    "JEV > Ngưỡng phải lớn hơn 0 và không vượt quá 1.\n"
                )
                continue

            threshold = new_threshold
            print(
                f"JEV > Đã đặt ngưỡng thành {threshold:.0%}.\n"
            )
            continue

        if command in {"/hoadon", "/invoices"}:
            print("\nJEV > Đang phân tích bộ hóa đơn mẫu...\n")

            try:
                result = engine.run_invoices(
                    DEFAULT_INVOICES,
                    threshold=threshold,
                )

                print(
                    json.dumps(
                        result,
                        ensure_ascii=False,
                        indent=2,
                    )
                )

                result_text = json.dumps(
                    result,
                    ensure_ascii=False,
                )

                history.append(
                    {
                        "role": "user",
                        "content": (
                            "Tôi yêu cầu phân tích bộ hóa đơn mẫu "
                            f"với ngưỡng {threshold:.0%}."
                        ),
                    }
                )
                history.append(
                    {
                        "role": "assistant",
                        "content": (
                            "Kết quả pipeline phân tích hóa đơn: "
                            + result_text
                        ),
                    }
                )

                turn += 1

            except Exception as exc:
                print(
                    f"JEV LỖI [{type(exc).__name__}]: {exc}"
                )

            print()
            continue

        # Hội thoại thông thường: không dùng engine.run(),
        # vì run() parse đầu ra thành quyết định JSON.
        print("\nJEV > ", end="", flush=True)

        try:
            output = jev_chat.process(
                message=user_text,
                history=history,
            )
            answer = output["answer"]

            print(answer)

            history.append(
                {
                    "role": "user",
                    "content": user_text,
                }
            )
            history.append(
                {
                    "role": "assistant",
                    "content": answer,
                }
            )

            # Giữ lịch sử có giới hạn để tránh prompt tăng vô hạn.
            if len(history) > 20:
                history = history[-20:]

            turn += 1

        except KeyboardInterrupt:
            print("\nJEV > Đã ngắt yêu cầu hiện tại.")

        except Exception as exc:
            print(
                f"\nJEV LỖI [{type(exc).__name__}]: {exc}"
            )
            print(
                "JEV > Yêu cầu chưa hoàn thành. "
                "Mày có thể thử lại."
            )

        print()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="jev",
        description="JEV Finance — phân tích hóa đơn và hội thoại",
    )

    parser.add_argument(
        "--input",
        type=Path,
        default=None,
        help="Đường dẫn file .json hoặc .csv",
    )

    parser.add_argument(
        "--threshold",
        type=float,
        default=None,
        help="Ngưỡng bất thường, ví dụ 0.15 là 15%%",
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Đường dẫn lưu báo cáo JSON",
    )

    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Mở chế độ hội thoại liên tục",
    )

    return parser.parse_args()


def main() -> int:
    configure_terminal()
    args = parse_args()

    try:
        engine = JEVEngine()

        if args.interactive:
            threshold = (
                args.threshold
                if args.threshold is not None
                else DEFAULT_THRESHOLD
            )

            return interactive_mode(
                engine,
                threshold=threshold,
            )

        invoices, input_threshold, input_source = load_input(
            args.input
        )

        if args.threshold is not None:
            threshold = args.threshold
        elif input_threshold is not None:
            threshold = input_threshold
        else:
            threshold = DEFAULT_THRESHOLD

        result = engine.run_invoices(
            invoices=invoices,
            threshold=threshold,
        )

        report = {
            "application": APP_NAME,
            "version": APP_VERSION,
            "created_at": datetime.now().astimezone().isoformat(),
            "input_source": input_source,
            **result,
        }

        output_path = args.output

        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = (
                Path("reports")
                / f"jev_report_{timestamp}.json"
            )

        save_report(report, output_path)

        print("\n=== KẾT QUẢ JEV FINANCE ===")
        print(
            json.dumps(
                report,
                ensure_ascii=False,
                indent=2,
                allow_nan=False,
            )
        )
        print(f"\nĐã lưu báo cáo: {output_path.resolve()}")

        return 0

    except KeyboardInterrupt:
        print(
            "\nJEV đã bị dừng bởi người dùng.",
            file=sys.stderr,
        )
        return 130

    except Exception as exc:
        print(
            f"\nJEV LỖI [{type(exc).__name__}]: {exc}",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
