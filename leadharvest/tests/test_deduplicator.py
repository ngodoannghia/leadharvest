"""
Unit tests kiểm tra toàn bộ logic khử trùng lặp đa nguồn & đa tab theo BA §8.
"""

from leadharvest.models.enums import RejectReason, Segment
from leadharvest.models.lead_output import LeadOutput
from leadharvest.processing.deduplicator import deduplicate_leads


def test_deduplicate_by_phone_across_segments():
    # 2 leads thuộc 2 phân khúc khác nhau nhưng dùng chung 1 số điện thoại
    lead1 = LeadOutput(
        target_segment=Segment.THUY_SAN.value,
        company_name="Vựa Tôm Hùng Cường",
        phone_primary="0909123456",
        phone_primary_type="MOBILE",
        province="Cà Mau",
        address="Ấp 1, Xã Tân Duyệt, Đầm Dơi, Cà Mau",
    )
    lead2 = LeadOutput(
        target_segment=Segment.NONG_SAN.value,
        company_name="Vựa Nông Sản Hùng Cường",
        phone_primary="0909123456",  # Trùng SĐT
        phone_primary_type="MOBILE",
        province="Cà Mau",
        address="Ấp 1, Xã Tân Duyệt, Đầm Dơi, Cà Mau",
    )

    res = deduplicate_leads([lead1, lead2])
    assert len(res.accepted_leads) == 1
    assert len(res.duplicate_leads) == 1
    assert res.duplicate_leads[0][1] == RejectReason.DUPLICATE_PHONE


def test_deduplicate_by_tax_code_same_province_picks_richest():
    # 2 bản ghi cùng MST gốc, cùng tỉnh -> giữ bản ghi giàu thông tin hơn
    lead_rich = LeadOutput(
        target_segment=Segment.DET_MAY.value,
        company_name="CÔNG TY CỔ PHẦN DỆT MAY ĐỒNG NAI",
        contact_person="Nguyễn Thị Mai",
        phone_primary="0918999888",
        phone_primary_type="MOBILE",
        phone_secondary="02513836123",
        phone_secondary_type="LANDLINE",
        tax_code="3600258147",
        province="Đồng Nai",
        address="Đường số 2, KCN Biên Hòa 1, Phường An Bình, TP Biên Hòa, Đồng Nai",
    )
    lead_poor = LeadOutput(
        target_segment=Segment.DET_MAY.value,
        company_name="CTY DET MAY DONG NAI",
        phone_primary="02513836123",
        phone_primary_type="LANDLINE",
        tax_code="3600258147-001",  # Cùng MST gốc 3600258147
        province="Đồng Nai",
        address="KCN Biên Hòa 1, Đồng Nai",
    )

    res = deduplicate_leads([lead_poor, lead_rich])
    assert len(res.accepted_leads) == 1
    # Bản ghi phong phú hơn phải được giữ lại
    assert res.accepted_leads[0].company_name == "CÔNG TY CỔ PHẦN DỆT MAY ĐỒNG NAI"
    assert res.accepted_leads[0].phone_primary == "0918999888"


def test_tax_code_branch_limit():
    # Cùng MST gốc nhưng khác tỉnh: cho phép tối đa 2 chi nhánh (BA §8.1)
    b1 = LeadOutput(
        target_segment=Segment.PHAN_BON.value,
        company_name="Công ty Phân bón Miền Nam - Chi nhánh Long An",
        phone_primary="0901111111",
        phone_primary_type="MOBILE",
        tax_code="0300456789",
        province="Long An",
        address="KCN Đức Hòa 1, Xã Đức Hòa Đông, Huyện Đức Hòa, Long An",
    )
    b2 = LeadOutput(
        target_segment=Segment.PHAN_BON.value,
        company_name="Công ty Phân bón Miền Nam - Chi nhánh Đồng Nai",
        phone_primary="0902222222",
        phone_primary_type="MOBILE",
        tax_code="0300456789-001",
        province="Đồng Nai",
        address="KCN Gò Dầu, Xã Phước Thái, Huyện Long Thành, Đồng Nai",
    )
    b3 = LeadOutput(
        target_segment=Segment.PHAN_BON.value,
        company_name="Công ty Phân bón Miền Nam - Chi nhánh Bà Rịa",
        phone_primary="0903333333",
        phone_primary_type="MOBILE",
        tax_code="0300456789-002",
        province="Bà Rịa - Vũng Tàu",
        address="KCN Phú Mỹ 1, Phường Phú Mỹ, Thị xã Phú Mỹ, Bà Rịa - Vũng Tàu",
    )

    res = deduplicate_leads([b1, b2, b3])
    # Tối đa 2 chi nhánh khác tỉnh được chấp nhận
    assert len(res.accepted_leads) == 2
    assert len(res.duplicate_leads) == 1
    assert res.duplicate_leads[0][1] == RejectReason.TAX_CODE_BRANCH_LIMIT
