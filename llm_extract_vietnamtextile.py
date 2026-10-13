#!/usr/bin/env python3
"""
LLM extraction cho vietnamtextile.jsonl — tái hiện đúng cách đã làm.

THỰC TẾ ĐÃ LÀM (2026-10-13):
- Không có script nào gọi LLM trực tiếp. Tôi spawn 8 subagent, mỗi agent xử lý
  một batch 44-50 dòng: đọc file gốc, đọc HIỂU từng description, trích xuất
  5 trường, ghi ra llm_batch_N.jsonl. Sau đó gộp 8 batch lại.
- Prompt dưới đây là nội dung hướng dẫn đã giao cho mỗi subagent, giữ nguyên.

CÁCH DÙNG LẠI:
- Nếu muốn chạy bằng API LLM thật: thay hàm llm_extract() bằng call tới
  model bạn chọn, giữ nguyên SYSTEM_PROMPT và schema.
"""

import json

# 8 batch đã dùng (index 0-based trên file gốc 394 dòng)
BATCHES = [
    (0, 50), (50, 100), (100, 150), (150, 200),
    (200, 250), (250, 300), (300, 350), (350, 394),
]

SYSTEM_PROMPT = """Bạn trích xuất thông tin doanh nghiệp từ trường "description"
trong file vietnamtextile.jsonl. Đọc HIỂU từng description, không dùng regex.

Với mỗi dòng, trích xuất đúng 5 trường sau (thiếu thì để null, KHÔNG bịa):

1. raw_phone: số điện thoại copy NGUYÊN VĂN từ description, không chuẩn hoá
   lại định dạng. Loại trừ số Fax. Nếu có nhiều số, nối bằng " / ".
2. address: địa chỉ công ty ghi trong description, copy nguyên văn.
3. province: tỉnh/thành chuẩn hoá theo tiếng Việt, suy ra từ địa chỉ
   (vd: "TP.HCM", "Hà Nội", "Bình Dương"). Không có địa chỉ thì null.
4. contact_person: người đại diện / người liên hệ của công ty, CHỈ lấy tên,
   bỏ chức danh (vd: bỏ "Ông", "Bà", "Mr.", "- Giám đốc").
   Ưu tiên: người đại diện theo pháp luật / giám đốc / tổng giám đốc
   trước người liên hệ hành chính.
5. tax_code: mã số thuế, CHỈ khi description ghi rõ ràng (vd: "MST:",
   "Mã số thuế:", "Tax code:"). Không suy đoán, không bịa.

QUY TẮC BẮT BUỘC:
- Mọi giá trị phải là chuỗi con có thật trong description (trừ province
  là chuẩn hoá từ địa chỉ).
- Không tra cứu thêm bất kỳ nguồn ngoài nào.
- Giữ đúng thứ tự dòng của file gốc.
- Mỗi dòng output là một JSON object trên một dòng (JSONL), gồm các key:
  company_name, raw_phone, address, province, contact_person, tax_code.
"""

USER_PROMPT_TEMPLATE = """Xử lý các dòng {start} đến {end} (0-based, end không bao gồm)
trong file {src}. Đọc trường "description" của từng dòng và trích xuất
5 trường theo SYSTEM_PROMPT. Ghi kết quả ra file {out}, mỗi dòng một JSON.
Chỉ ghi file, không in kết quả ra màn hình.
"""


def llm_extract(descriptions, start, end):
    """Placeholder: thay bằng call LLM thật nếu muốn chạy tự động.

    Lần làm thật: công việc này do 8 subagent thực hiện thủ công theo
    SYSTEM_PROMPT ở trên, không qua hàm này.
    """
    raise NotImplementedError(
        "Bản gốc do subagent làm thủ công. "
        "Nối API LLM của bạn vào đây nếu muốn chạy tự động."
    )


def merge_batches(batch_files, out_path):
    """Gộp các batch llm_batch_*.jsonl thành một file, kiểm tra đủ 394 dòng."""
    merged = []
    for bf in batch_files:
        with open(bf) as f:
            merged.extend(json.loads(l) for l in f if l.strip())
    assert len(merged) == 394, f"thiếu dòng: {len(merged)}/394"
    with open(out_path, 'w') as f:
        for r in merged:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')
    print(f'merged {len(merged)} lines -> {out_path}')


if __name__ == '__main__':
    print("8 batch đã dùng:")
    for i, (s, e) in enumerate(BATCHES, 1):
        print(f"  batch {i}: dòng {s+1}-{e} -> llm_batch_{i}.jsonl")
        print("  prompt:", USER_PROMPT_TEMPLATE.format(
            start=s, end=e, src='vietnamtextile.jsonl',
            out=f'llm_batch_{i}.jsonl').strip().replace('\n', ' '))
    print()
    print("Chạy gộp batch: python3 llm_extract_vietnamtextile.py --merge")
    import sys
    if '--merge' in sys.argv:
        merge_batches([f'llm_batch_{i}.jsonl' for i in range(1, 9)],
                      'vietnamtextile_llm.jsonl')
