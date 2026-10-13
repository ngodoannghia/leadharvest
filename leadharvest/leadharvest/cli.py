"""
Giao diện dòng lệnh (CLI) của dự án LeadHarvest.

Cung cấp lệnh `build` thực thi Phase 2:
  1. Đọc toàn bộ dữ liệu thô từ `data/raw/*.jsonl`.
  2. Chuẩn hóa và lọc dữ liệu (Normalization).
  3. Khử trùng lặp đa nguồn & đa tab (Cross-tab Deduplication).
  4. Xuất file Excel 6 tab + 1 tab Thống kê (`data/output/BaoBiHongHai_Master.xlsx`).
  5. Xuất 6 file CSV UTF-8-SIG (`data/output/csv/*.csv`).
  6. Xuất báo cáo QA Report (`data/output/qa_report.json`).
  7. In kết quả đối soát trực tiếp ra terminal.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import sys

from leadharvest.exporters.csv_export import export_to_csv_files
from leadharvest.exporters.excel import export_to_excel
from leadharvest.models.enums import PhoneType, Segment
from leadharvest.models.lead_output import LeadOutput
from leadharvest.models.raw_lead import RawLead
from leadharvest.processing.deduplicator import deduplicate_leads
from leadharvest.processing.normalizer import normalize_raw_lead
from leadharvest.processing.qa_report import generate_qa_report
from leadharvest.validators.phone import extract_phones


def run_build(
    raw_dir: str = "data/raw",
    output_excel: str = "data/output/BaoBiHongHai_Master.xlsx",
    output_csv_dir: str = "data/output/csv",
    output_qa_path: str = "data/output/qa_report.json",
) -> int:
    print("=" * 70)
    print("LEADHARVEST — BẮT ĐẦU QUY TRÌNH CHUẨN HÓA & NGHIỆM THU DỮ LIỆU")
    print("=" * 70)

    # 1. Đọc toàn bộ dữ liệu thô
    raw_files = glob.glob(os.path.join(raw_dir, "*.jsonl"))
    if not raw_files:
        print(f"[-] Không tìm thấy file dữ liệu thô nào trong thư mục: {raw_dir}")
        print("    Vui lòng chạy spider trước (ví dụ: scrapy crawl vasep).")
        return 1

    total_raw_leads: list[RawLead] = []
    for fpath in raw_files:
        print(f"[+] Đang nạp dữ liệu thô từ: {fpath}...")
        with open(fpath, "r", encoding="utf-8") as f:
            for line_no, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    total_raw_leads.append(RawLead(**data))
                except Exception as e:
                    print(f"    [!] Cảnh báo lỗi đọc dòng {line_no} file {fpath}: {e}")

    total_raw_count = len(total_raw_leads)
    print(f"[+] Tổng số bản ghi thô đã nạp: {total_raw_count:,}")

    # 2. Chuẩn hóa & Lọc lỗi (Phase 2 - Normalization)
    print("[+] Đang tiến hành chuẩn hóa SĐT, Tỉnh/Thành, MST và Phân khúc...")
    normalized_leads: list[LeadOutput] = []
    all_rejected: list[tuple[any, any, str]] = []

    for raw in total_raw_leads:
        res = normalize_raw_lead(raw)
        if res.lead:
            normalized_leads.append(res.lead)
        else:
            all_rejected.append((raw, res.reject_reason, res.reject_message or ""))

    print(f"[+] Sau bước chuẩn hóa: {len(normalized_leads):,} bản ghi đạt chuẩn sơ bộ, {len(all_rejected):,} bản ghi bị loại.")

    # 3. Khử trùng lặp đa nguồn & đa tab (Phase 2 - Deduplication)
    print("[+] Đang tiến hành khử trùng lặp theo MST và Số điện thoại cross-tab...")
    dedup_res = deduplicate_leads(normalized_leads)
    final_leads = dedup_res.accepted_leads

    for item, reason, msg in dedup_res.duplicate_leads:
        all_rejected.append((item, reason, msg))

    print(f"[+] Sau bước khử trùng lặp: {len(final_leads):,} bản ghi BÀN GIAO CHÍNH THỨC.")

    # 4. Sinh QA Report
    print("[+] Đang tổng hợp báo cáo kiểm định chất lượng (QA Report)...")
    qa_report = generate_qa_report(
        total_raw=total_raw_count,
        delivered_leads=final_leads,
        all_rejected=all_rejected,
    )

    # 5. Xuất file bàn giao
    os.makedirs(os.path.dirname(output_excel), exist_ok=True)
    os.makedirs(output_csv_dir, exist_ok=True)
    os.makedirs(os.path.dirname(output_qa_path), exist_ok=True)

    print(f"[+] Đang xuất Master file Excel 6 tab + 1 tab Thống kê: {output_excel}...")
    export_to_excel(leads=final_leads, qa_report=qa_report, output_path=output_excel)

    print(f"[+] Đang xuất 6 file CSV (UTF-8-BOM): {output_csv_dir}/...")
    export_to_csv_files(leads=final_leads, output_dir=output_csv_dir)

    print(f"[+] Đang xuất báo cáo QA JSON: {output_qa_path}...")
    with open(output_qa_path, "w", encoding="utf-8") as f:
        f.write(qa_report.to_json())

    # 6. In tóm tắt kết quả kiểm định
    print("=" * 70)
    print("KẾT QUẢ KIỂM ĐỊNH CHẤT LƯỢNG NGHIỆM THU (BA §10.1)")
    print("=" * 70)
    print(f"- Tổng bản ghi bàn giao: {qa_report.total_delivered_records:,} (Sàn: 5,000) -> {'ĐẠT' if qa_report.is_total_quota_passed else 'CHƯA ĐẠT'}")
    print(f"- Số bản ghi có di động (Mobile): {qa_report.total_with_mobile:,} / {qa_report.total_delivered_records:,} dòng ({qa_report.mobile_ratio_pct}%) (Mục tiêu: >= 90%) -> {'ĐẠT' if qa_report.is_mobile_ratio_passed else 'CHƯA ĐẠT'}")
    print(f"- Tỷ lệ bản ghi có SĐT: {qa_report.valid_phone_ratio_pct}% (Bắt buộc: 100%) -> {'ĐẠT' if qa_report.is_valid_phone_passed else 'CHƯA ĐẠT'}")
    print("\nChi tiết sản lượng theo phân khúc:")
    for seg in Segment:
        cnt = qa_report.segment_counts.get(seg.value, 0)
        quota = seg.min_quota
        print(f"  + {seg.value:12}: {cnt:6,} dòng (Sàn: {quota:5,}) -> {'ĐẠT' if cnt >= quota else 'CẦN BỔ SUNG'}")

    print("\nKẾT LUẬN CHUNG:")
    if qa_report.is_overall_passed:
        print("  >>> [SUCCESS] TẤT CẢ TIÊU CHÍ NGHIỆM THU ĐẠT CHUẨN!")
    else:
        print("  >>> [WARNING] Chưa đạt đầy đủ mức sàn dự án (cần bổ sung thêm nguồn cào).")
    print("=" * 70)

    return 0 if qa_report.is_overall_passed else 0


def run_crawl(
    spider: str = "vasep",
    crawl_all: bool = False,
    start_page: int = 1,
    end_page: int = 10,
    limit: int | None = None,
    save_file: str | None = None,
    save_folder: str | None = None,
) -> int:
    import subprocess

    print("=" * 70)
    print(f"LEADHARVEST — KHỞI CHẠY SPIDER: {spider.upper()}")
    print("=" * 70)

    cmd = [sys.executable, "-m", "scrapy.cmdline", "crawl", spider]
    if limit is not None:
        cmd.extend(["-a", f"limit={limit}"])
        print(f"[+] Giới hạn số bản ghi: {limit}")

    if crawl_all:
        cmd.extend(["-a", "crawl_all=true"])
        if start_page > 1:
            cmd.extend(["-a", f"start_page={start_page}"])
        print(f"[+] Chế độ: CÀO TOÀN BỘ TẤT CẢ CÁC TRANG (bắt đầu từ trang {start_page})")
    elif spider not in ("vietfood", "vietnamtextile"):
        cmd.extend(["-a", f"start_page={start_page}", "-a", f"end_page={end_page}"])
        print(f"[+] Chế độ: Cào từ trang {start_page} đến trang {end_page}")

    if save_file:
        cmd.extend(["-a", f"save_file={save_file}"])
        print(f"[+] File lưu dữ liệu thô: {save_file}")
    elif save_folder:
        cmd.extend(["-a", f"save_folder={save_folder}"])
        print(f"[+] Thư mục lưu dữ liệu thô: {save_folder}")
    else:
        print("[+] File lưu dữ liệu thô: data/raw/<spider>.jsonl (mặc định)")

    try:
        res = subprocess.run(cmd)
        return res.returncode
    except KeyboardInterrupt:
        print("\n[!] Đã dừng cào theo yêu cầu người dùng.")
        return 0


def analyze_jsonl_file(fpath: str) -> dict[str, any]:
    """Phân tích thống kê số điện thoại & mobile trong một file jsonl."""
    total = 0
    mobile = 0
    landline = 0
    hotline = 0
    with_phone = 0
    no_phone = 0
    error_lines = 0

    with open(fpath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
            except Exception:
                error_lines += 1
                continue

            total += 1

            if "has_mobile" in data:
                has_mob = bool(data.get("has_mobile"))
                pri_type = data.get("phone_primary_type", "")
                sec_type = data.get("phone_secondary_type", "")
                has_land = (
                    pri_type == PhoneType.LANDLINE.value
                    or sec_type == PhoneType.LANDLINE.value
                )
                has_hot = sec_type == PhoneType.HOTLINE.value
                has_any = bool(data.get("phone_primary")) or bool(data.get("phone_secondary"))
            else:
                raw_p = data.get("raw_phone") or data.get("raw_phones")
                extracted = extract_phones(raw_p)
                has_mob = any(p.type is PhoneType.MOBILE for p in extracted)
                has_land = any(p.type is PhoneType.LANDLINE for p in extracted)
                has_hot = any(p.type is PhoneType.HOTLINE for p in extracted)
                has_any = len(extracted) > 0

            if has_mob:
                mobile += 1
            if has_land:
                landline += 1
            if has_hot:
                hotline += 1
            if has_any:
                with_phone += 1
            else:
                no_phone += 1

    return {
        "file": fpath,
        "total": total,
        "mobile": mobile,
        "landline": landline,
        "hotline": hotline,
        "with_phone": with_phone,
        "no_phone": no_phone,
        "error_lines": error_lines,
        "mobile_pct": round((mobile / total * 100.0), 1) if total > 0 else 0.0,
        "landline_pct": round((landline / total * 100.0), 1) if total > 0 else 0.0,
        "hotline_pct": round((hotline / total * 100.0), 1) if total > 0 else 0.0,
        "with_phone_pct": round((with_phone / total * 100.0), 1) if total > 0 else 0.0,
        "no_phone_pct": round((no_phone / total * 100.0), 1) if total > 0 else 0.0,
    }


def run_stats(
    file_path: str | None = None,
    raw_dir: str = "data/raw",
    as_json: bool = False,
) -> int:
    """Thống kê chi tiết tỷ lệ và số lượng bản ghi có SĐT, mobile."""
    target_files = []
    if file_path:
        if os.path.exists(file_path):
            target_files.append(file_path)
        elif os.path.exists(os.path.join(raw_dir, file_path)):
            target_files.append(os.path.join(raw_dir, file_path))
        else:
            print(f"[-] Không tìm thấy file: {file_path}")
            return 1
    else:
        target_files = sorted(glob.glob(os.path.join(raw_dir, "*.jsonl")))
        if not target_files:
            print(f"[-] Không tìm thấy file .jsonl nào trong thư mục: {raw_dir}")
            return 1

    results = [analyze_jsonl_file(f) for f in target_files]

    if as_json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
        return 0

    print("=" * 70)
    print("LEADHARVEST — BÁO CÁO THỐNG KÊ SỐ ĐIỆN THOẠI & MOBILE")
    print("=" * 70)

    for item in results:
        print(f"\n[+] Tệp: {item['file']}")
        print(f"  - Tổng số bản ghi             : {item['total']:,}")
        print(f"  - Bản ghi có di động (Mobile) : {item['mobile']:,} ({item['mobile_pct']}%)")
        print(f"  - Bản ghi có số bàn (Landline): {item['landline']:,} ({item['landline_pct']}%)")
        print(f"  - Bản ghi có Hotline          : {item['hotline']:,} ({item['hotline_pct']}%)")
        print(f"  - Bản ghi có ít nhất 1 SĐT    : {item['with_phone']:,} ({item['with_phone_pct']}%)")
        print(f"  - Bản ghi KHÔNG có SĐT        : {item['no_phone']:,} ({item['no_phone_pct']}%)")
        if item["error_lines"] > 0:
            print(f"  - Dòng lỗi JSON (bỏ qua)      : {item['error_lines']:,}")

    if len(results) > 1:
        total_rec = sum(r["total"] for r in results)
        total_mob = sum(r["mobile"] for r in results)
        total_land = sum(r["landline"] for r in results)
        total_hot = sum(r["hotline"] for r in results)
        total_wp = sum(r["with_phone"] for r in results)
        total_np = sum(r["no_phone"] for r in results)
        mob_pct = round((total_mob / total_rec * 100.0), 1) if total_rec > 0 else 0.0
        land_pct = round((total_land / total_rec * 100.0), 1) if total_rec > 0 else 0.0
        hot_pct = round((total_hot / total_rec * 100.0), 1) if total_rec > 0 else 0.0
        wp_pct = round((total_wp / total_rec * 100.0), 1) if total_rec > 0 else 0.0
        np_pct = round((total_np / total_rec * 100.0), 1) if total_rec > 0 else 0.0

        print("-" * 70)
        print(f"TỔNG CỘNG ({len(results)} tệp):")
        print(f"  - Tổng số bản ghi             : {total_rec:,}")
        print(f"  - Bản ghi có di động (Mobile) : {total_mob:,} ({mob_pct}%)")
        print(f"  - Bản ghi có số bàn (Landline): {total_land:,} ({land_pct}%)")
        print(f"  - Bản ghi có Hotline          : {total_hot:,} ({hot_pct}%)")
        print(f"  - Bản ghi có ít nhất 1 SĐT    : {total_wp:,} ({wp_pct}%)")
        print(f"  - Bản ghi KHÔNG có SĐT        : {total_np:,} ({np_pct}%)")

    print("=" * 70)
    return 0


def main():
    parser = argparse.ArgumentParser(prog="leadharvest", description="LeadHarvest CLI")
    subparsers = parser.add_subparsers(dest="command", help="Lệnh thực thi")

    build_parser = subparsers.add_parser("build", help="Chuẩn hóa, khử trùng lặp và xuất file bàn giao")
    build_parser.add_argument("--raw-dir", default="data/raw", help="Thư mục chứa file .jsonl thô")
    build_parser.add_argument("--out-excel", default="data/output/BaoBiHongHai_Master.xlsx", help="Đường dẫn file Excel đầu ra")
    build_parser.add_argument("--out-csv", default="data/output/csv", help="Thư mục xuất các file CSV")
    build_parser.add_argument("--out-qa", default="data/output/qa_report.json", help="Đường dẫn file qa_report.json")

    crawl_parser = subparsers.add_parser("crawl", help="Chạy Scrapy spider cào dữ liệu hội viên")
    crawl_parser.add_argument("--spider", default="vasep", help="Tên spider (mặc định: vasep)")
    crawl_parser.add_argument(
        "--all",
        "--crawl-all",
        dest="crawl_all",
        action="store_true",
        help="Cào toàn bộ tất cả các trang (tự động phân trang đến cuối)",
    )
    crawl_parser.add_argument("--start-page", type=int, default=1, help="Trang bắt đầu (mặc định: 1)")
    crawl_parser.add_argument(
        "--end-page",
        type=int,
        default=10,
        help="Trang kết thúc khi không dùng --all (mặc định: 10)",
    )
    crawl_parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Giới hạn số lượng bản ghi cần cào (dùng để test thử nghiệm)",
    )
    crawl_parser.add_argument(
        "--save-file",
        "--filename",
        dest="save_file",
        default=None,
        help="Tên file lưu dữ liệu thô (ví dụ: vasep_dot1.jsonl)",
    )
    crawl_parser.add_argument(
        "--save-folder",
        default=None,
        help="Thư mục lưu file .jsonl thô (mặc định: data/raw)",
    )

    stats_parser = subparsers.add_parser(
        "stats", help="Thống kê số lượng bản ghi có SĐT, mobile trong dữ liệu"
    )
    stats_parser.add_argument(
        "--file",
        "-f",
        dest="file_path",
        default=None,
        help="Đường dẫn file .jsonl cụ thể cần kiểm tra (ví dụ: data/raw/vasep_all.jsonl)",
    )
    stats_parser.add_argument(
        "--raw-dir",
        "-d",
        default="data/raw",
        help="Thư mục chứa các file .jsonl thô (mặc định: data/raw)",
    )
    stats_parser.add_argument(
        "--json",
        action="store_true",
        help="Xuất kết quả thống kê định dạng JSON",
    )

    args = parser.parse_args()
    if args.command == "build":
        sys.exit(run_build(
            raw_dir=args.raw_dir,
            output_excel=args.out_excel,
            output_csv_dir=args.out_csv,
            output_qa_path=args.out_qa,
        ))
    elif args.command == "crawl":
        sys.exit(run_crawl(
            spider=args.spider,
            crawl_all=args.crawl_all,
            start_page=args.start_page,
            end_page=args.end_page,
            limit=args.limit,
            save_file=args.save_file,
            save_folder=args.save_folder,
        ))
    elif args.command == "stats":
        sys.exit(run_stats(
            file_path=args.file_path,
            raw_dir=args.raw_dir,
            as_json=args.json,
        ))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()


