"""
Unit tests kiểm tra toàn bộ logic của class LeadOutput và 11 trường schema BA §6.
"""

from leadharvest.models.enums import DataStatus, PhoneType, RejectReason, Segment
from leadharvest.models.lead_output import LeadOutput


def test_valid_lead_output():
    lead = LeadOutput(
        target_segment=Segment.THUY_SAN.value,
        company_name="CÔNG TY TNHH THỦY HẢI SẢN MINH PHÚ",
        contact_person="Lê Văn Quang",
        phone_primary="0913987654",
        phone_primary_type=PhoneType.MOBILE.value,
        phone_secondary="02903123456",
        phone_secondary_type=PhoneType.LANDLINE.value,
        tax_code="0300588569",
        province="Cà Mau",
        address="Khu công nghiệp Phường 8, Thành phố Cà Mau, Tỉnh Cà Mau",
        data_status=DataStatus.PUBLIC_VALID.value,
    )

    errors = lead.validate()
    assert len(errors) == 0
    assert lead.is_valid is True
    assert lead.has_mobile is True
    assert lead.root_tax_code == "0300588569"

    # Kiểm tra xuất 11 cột hiển thị
    row = lead.to_row()
    assert len(row) == 11
    assert row[0] == "Thủy sản"
    assert row[1] == "CÔNG TY TNHH THỦY HẢI SẢN MINH PHÚ"
    assert row[3] == "0913987654"
    assert row[4] == "MOBILE"
    assert row[10] == "Công khai hợp lệ"


def test_invalid_segment():
    lead = LeadOutput(
        target_segment="Bất Động Sản",  # Không thuộc 6 ngành
        company_name="Công ty ABC",
        phone_primary="0909123456",
        phone_primary_type="MOBILE",
        province="Hà Nội",
        address="123 Phố Huế, Phường Ngô Thì Nhậm, Hà Nội",
    )
    errors = lead.validate()
    assert any(e.reason == RejectReason.WRONG_SEGMENT for e in errors)


def test_missing_phone_primary():
    lead = LeadOutput(
        target_segment=Segment.NONG_SAN.value,
        company_name="Vựa Nông Sản Ba Tri",
        phone_primary="",  # Bị rỗng
        phone_primary_type="",
        province="Bến Tre",
        address="Ấp 1, xã An Đức, huyện Ba Tri, Bến Tre",
    )
    errors = lead.validate()
    assert any(e.reason == RejectReason.NO_VALID_PHONE for e in errors)


def test_hotline_forbidden_in_primary():
    lead = LeadOutput(
        target_segment=Segment.DET_MAY.value,
        company_name="Xưởng May Xuất Khẩu Hà Nam",
        phone_primary="19006789",  # Hotline ở cột chính
        phone_primary_type="HOTLINE",
        province="Hà Nam",
        address="Đường Lê Hoàn, Phường Quang Trung, Phủ Lý, Hà Nam",
    )
    errors = lead.validate()
    assert any(e.reason == RejectReason.HOTLINE_ONLY for e in errors)


def test_duplicate_primary_and_secondary_phone():
    lead = LeadOutput(
        target_segment=Segment.CAO_SU.value,
        company_name="Nông trường Cao su Lộc Ninh",
        phone_primary="0909123456",
        phone_primary_type="MOBILE",
        phone_secondary="0909123456",  # Trùng với số chính
        phone_secondary_type="MOBILE",
        province="Bình Phước",
        address="Xã Lộc Tấn, Huyện Lộc Ninh, Tỉnh Bình Phước",
    )
    errors = lead.validate()
    assert any(e.reason == RejectReason.DUPLICATE_PHONE for e in errors)


def test_unspecific_address():
    lead = LeadOutput(
        target_segment=Segment.CAY_TRONG.value,
        company_name="Vườn Ươm Cây Giống Chợ Lách",
        phone_primary="0918123456",
        phone_primary_type="MOBILE",
        province="Bến Tre",
        address="Bến Tre",  # Quá chung chung, không có cấp xã/phường/đường/ấp
    )
    errors = lead.validate()
    assert any(e.reason == RejectReason.ADDRESS_NOT_SPECIFIC for e in errors)


def test_richness_score():
    lead_rich = LeadOutput(
        target_segment=Segment.PHAN_BON.value,
        company_name="Nhà Máy Phân Bón Bình Điền",
        contact_person="Nguyễn Văn A",
        phone_primary="0909123456",
        phone_primary_type="MOBILE",
        phone_secondary="02839102901",
        phone_secondary_type="LANDLINE",
        tax_code="0300588569",
        province="Long An",
        address="Khu công nghiệp Long Hậu, Xã Long Hậu, Huyện Cần Giuộc, Tỉnh Long An",
    )

    lead_poor = LeadOutput(
        target_segment=Segment.PHAN_BON.value,
        company_name="Nhà Máy Phân Bón Bình Điền",
        phone_primary="02839102901",
        phone_primary_type="LANDLINE",
        province="Long An",
        address="KCN Long Hậu, Cần Giuộc, Long An",
    )

    assert lead_rich.richness_score() > lead_poor.richness_score()
