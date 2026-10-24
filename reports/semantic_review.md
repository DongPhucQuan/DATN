# JEV — Semantic Document Review

- Generated: 2026-10-20T04:25:17.282932+00:00
- Model: local-model
- Documents: 4
- Evidence blocks: 1303
- Pairs reviewed: 6
- Pairs failed: 3
- Findings retained: 0
- Findings rejected: 3

> Finding do mô hình đề xuất chưa phải kết luận cuối cùng. Cần người có trách nhiệm xác minh.

## Pair execution

- BM.01.01.MRD.NV_2023.docx ↔ BM.01.02.PRD.NV_2023.docx: 0 finding(s)
  - Rejected: Scope Gap: Chỉ định tiêu chuẩn RF và an toàn — Thiếu evidence_relationship.
- BM.01.01.MRD.NV_2023.docx ↔ BM.01.03.TTR.NV_2023.docx: 0 finding(s)
  - Rejected: Lộ trình sản phẩm không nhất quán với yêu cầu — Thiếu evidence_relationship.
- BM.01.01.MRD.NV_2023.docx ↔ BM.01_Dự toán.xlsx: 0 finding(s)
  - Error: JSONDecodeError: Expecting ',' delimiter: line 19 column 10 (char 1156)
- BM.01.02.PRD.NV_2023.docx ↔ BM.01.03.TTR.NV_2023.docx: 0 finding(s)
  - Error: JSONDecodeError: Expecting ',' delimiter: line 40 column 6 (char 3726)
- BM.01.02.PRD.NV_2023.docx ↔ BM.01_Dự toán.xlsx: 0 finding(s)
  - Rejected: Scope Gap: Chi phí nhân công — Không có bằng chứng về yêu cầu cụ thể bắt buộc tài liệu bị cho là thiếu phải bao gồm nội dung đó.
- BM.01.03.TTR.NV_2023.docx ↔ BM.01_Dự toán.xlsx: 0 finding(s)
  - Error: JSONDecodeError: Expecting ',' delimiter: line 26 column 8 (char 2074)

## Limitations

- Lựa chọn evidence dùng heuristic từ khóa, chưa dùng embedding.
- Mỗi cặp chỉ gửi một tập con bằng chứng, không phải toàn bộ tài liệu.
- Có thể bỏ sót vấn đề nằm ngoài các đoạn được chọn.
- Xác minh trích dẫn không chứng minh rằng suy luận logic là đúng.
- Các finding được giữ lại vẫn cần con người xác minh.
- scope_gap guard là heuristic bảo thủ; có thể bỏ sót cách diễn đạt đồng nghĩa.
- numeric_guard chỉ kiểm tra sơ bộ việc có số liệu ở hai tài liệu.
- Chỉ xử lý văn bản đã được analyzer trích xuất.
