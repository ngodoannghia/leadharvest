"""
Unit tests kiểm tra toàn bộ luồng Normalizer và sinh QA Report theo BA §6, §9.
"""

from leadharvest.models.enums import DataStatus, PhoneType, RejectReason, Segment
from leadharvest.models.lead_output import LeadOutput
from leadharvest.models.raw_lead import RawLead
from leadharvest.processing.normalizer import normalize_raw_lead
from leadharvest.processing.qa_report import generate_qa_report


def test_normalize_raw_lead_success():
    raw = RawLead(
        company_name="  CÔNG TY TNHH XUẤT NHẬP KHẨU THỦY HẢI SẢN TÍNH THÚY TỶ  ",
        target_segment="Thủy Sản",
        contact_person="Ông Nguyễn Văn Tỷ",
        raw_phone="(+84) 939.096.809 / 0290.3812345",
        tax_code="1900123456",
        province="Cà Mau",
        address="Ấp 14, xã Vĩnh Mỹ, tỉnh Cà Mau",
        source_name="VASEP",
        source_url="https://vasep.com.vn/hoi-vien/1069.html",
    )

    res = normalize_raw_lead(raw)
    assert res.lead is not None
    assert res.reject_reason is None

    lead = res.lead
    assert lead.company_name == "CÔNG TY TNHH XUẤT NHẬP KHẨU THỦY HẢI SẢN TÍNH THÚY TỶ"
    assert lead.target_segment == Segment.THUY_SAN.value
    assert lead.contact_person == "Nguyễn Văn Tỷ"  # Bỏ danh xưng "Ông"
    assert lead.phone_primary == "0939096809"
    assert lead.phone_primary_type == PhoneType.MOBILE.value
    assert lead.phone_secondary == "02903812345"
    assert lead.phone_secondary_type == PhoneType.LANDLINE.value
    assert lead.province == "Cà Mau"
    assert lead.data_status == DataStatus.PUBLIC_VALID.value


def test_normalize_reject_inactive_business():
    raw = RawLead(
        company_name="Công ty TNHH Thủy Sản Đã Ngừng Hoạt Động",
        raw_phone="0909123456",
        province="Cà Mau",
        address="Ấp 1, xã Tắc Vân, TP Cà Mau",
        description="Doanh nghiệp này đã giải thể từ năm 2023.",
    )

    res = normalize_raw_lead(raw)
    assert res.lead is None
    assert res.reject_reason == RejectReason.INACTIVE


def test_normalize_reject_retail_excluded_keyword():
    raw = RawLead(
        company_name="Quán Ăn Hải Sản Biển Xanh",
        raw_phone="0909123456",
        province="Khánh Hòa",
        address="12 Đường Trần Phú, Phường Lộc Thọ, Nha Trang, Khánh Hòa",
    )

    res = normalize_raw_lead(raw)
    assert res.lead is None
    assert res.reject_reason == RejectReason.EXCLUDED_KEYWORD


def test_normalize_multisector_company_prefers_core_name():
    """Kiểm tra doanh nghiệp có tên Thủy Sản nhưng mô tả có rau củ quả vẫn vào Thủy Sản (BA §3.4)."""
    raw = RawLead(
        company_name="CÔNG TY CP THỦY SẢN BẠC LIÊU",
        target_segment="Thủy sản",
        raw_phone="02913849567",
        province="Cà Mau",
        address="Số 89 Quốc Lộ 1A, khóm 2, phường Giá Rai, Tỉnh Cà Mau",
        description="Chế biến, Xuất khẩu. Tôm đông lạnh, mực đông lạnh, chả cá đông lạnh, rau củ quả đông lạnh (đậu bắp, cà tím, ớt chuông, khoai lang, bí ngòi, dưa leo…)",
        source_name="VASEP",
    )

    res = normalize_raw_lead(raw)
    assert res.lead is not None
    assert res.lead.target_segment == Segment.THUY_SAN.value
    assert res.lead.company_name == "CÔNG TY CP THỦY SẢN BẠC LIÊU"



def test_generate_qa_report_metrics():
    # Giả lập 2 leads hợp lệ
    lead1 = LeadOutput(
        target_segment=Segment.THUY_SAN.value,
        company_name="Vựa Tôm Minh Phú",
        phone_primary="0909123456",
        phone_primary_type=PhoneType.MOBILE.value,
        province="Cà Mau",
        address="Ấp 1, Xã Tân Duyệt, Đầm Dơi, Cà Mau",
    )
    lead2 = LeadOutput(
        target_segment=Segment.DET_MAY.value,
        company_name="Xưởng May Nam Định",
        phone_primary="02283845678",
        phone_primary_type=PhoneType.LANDLINE.value,
        province="Nam Định",
        address="Đường Vị Xuyên, Phường Vị Xuyên, TP Nam Định",
    )

    rejected_sample = [
        (None, RejectReason.DUPLICATE_PHONE, "Trùng SĐT"),
        (None, RejectReason.EXCLUDED_KEYWORD, "Quán ăn"),
        (None, RejectReason.INACTIVE, "Đã giải thể"),
        (None, RejectReason.MISSING_ADDRESS, "Thiếu địa chỉ"),
    ]

    report = generate_qa_report(
        total_raw=6,
        delivered_leads=[lead1, lead2],
        all_rejected=rejected_sample,
    )

    assert report.total_raw_records == 6
    assert report.total_delivered_records == 2
    assert report.rejected_duplicates == 1
    assert report.rejected_wrong_segment == 1
    assert report.rejected_inactive == 1
    assert report.rejected_missing_info == 1
    assert report.total_with_mobile == 1
    assert report.total_with_landline == 1
    assert report.mobile_ratio_pct == 50.0  # 1 / 2 = 50%
    assert report.valid_phone_ratio_pct == 100.0


def test_analyze_jsonl_file_stats(tmp_path):
    import json
    from leadharvest.cli import analyze_jsonl_file, run_stats

    # Tạo file test jsonl
    test_file = tmp_path / "test_leads.jsonl"
    lines = [
        {"company_name": "Cty A", "raw_phone": "0983125678"},  # Mobile
        {"company_name": "Cty B", "raw_phone": "02903836138"}, # Landline
        {"company_name": "Cty C", "raw_phone": "19001234"},    # Hotline
        {"company_name": "Cty D", "raw_phone": "0978652314 / 02838123456"}, # Mobile + Landline
        {"company_name": "Cty E", "raw_phone": ""},            # No phone
    ]
    with open(test_file, "w", encoding="utf-8") as f:
        for item in lines:
            f.write(json.dumps(item) + "\n")

    stat = analyze_jsonl_file(str(test_file))
    assert stat["total"] == 5
    assert stat["mobile"] == 2      # Cty A, Cty D
    assert stat["landline"] == 2    # Cty B, Cty D
    assert stat["hotline"] == 1     # Cty C
    assert stat["with_phone"] == 4
    assert stat["no_phone"] == 1
    assert stat["mobile_pct"] == 40.0

    # Test run_stats CLI exit code
    exit_code = run_stats(file_path=str(test_file))
    assert exit_code == 0

