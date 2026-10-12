"""
Quy tắc phân loại và xác thực ngành hàng (BA §3.2, §3.4, §4).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from leadharvest.models.enums import Segment
from leadharvest.validators.text import clean_whitespace

INACTIVE_PATTERNS: tuple[str, ...] = (
    "giải thể", "ngừng hoạt động", "tạm ngừng hoạt động", "ngung hoat dong",
    "đã đóng cửa", "da dong cua", "ngừng kinh doanh", "ngung kinh doanh",
    "bị đóng mst", "khoá mã số thuế", "khoa mst", "chấm dứt hoạt động"
)


@dataclass(frozen=True)
class SegmentRule:
    segment: Segment
    positive_keywords: tuple[str, ...]
    negative_keywords: tuple[str, ...]


SEGMENT_RULES: dict[Segment, SegmentRule] = {
    Segment.NONG_SAN: SegmentRule(
        segment=Segment.NONG_SAN,
        positive_keywords=(
            "nông sản", "vựa trái cây", "vựa rau củ", "vựa nông sản", "htx nông nghiệp",
            "hợp tác xã nông nghiệp", "sơ chế nông sản", "đóng gói nông sản",
            "chế biến nông sản", "xuất khẩu nông sản", "nông sản xuất khẩu",
            "kho nông sản", "trái cây sấy", "rau củ quả", "hạt điều", "cà phê", "hồ tiêu"
        ),
        negative_keywords=(
            "cửa hàng hoa quả nhập khẩu", "trái cây dĩa", "nước ép",
            "sinh tố", "quán nước", "tiệm chè", "quán chè"
        ),
    ),
    Segment.THUY_SAN: SegmentRule(
        segment=Segment.THUY_SAN,
        positive_keywords=(
            "thủy sản", "thuỷ sản", "hải sản", "thủy hải sản", "thuỷ hải sản",
            "chế biến thủy sản", "chế biến thuỷ sản", "chế biến hải sản",
            "thủy hải sản đông lạnh", "thuỷ hải sản đông lạnh",
            "vựa tôm", "vựa cá", "vựa cua", "xuất khẩu hải sản",
            "xuất khẩu thủy sản", "xuất khẩu thuỷ sản",
            "thủy sản đông lạnh", "thuỷ sản đông lạnh", "hải sản đông lạnh",
            "nhà máy thủy sản", "nhà máy thuỷ sản",
            "nuôi trồng thủy sản", "nuôi trồng thuỷ sản",
            "chế biến tôm", "chế biến cá tra", "cá tra", "basa",
            "tôm đông lạnh", "mực đông lạnh", "chả cá đông lạnh", "surimi", "cá ngừ", "bạch tuộc"
        ),
        negative_keywords=(
            "quán ăn hải sản", "nhà hàng hải sản", "quán ốc", "hồ câu",
            "câu cá giải trí", "quán nhậu", "hải sản tươi sống mang về", "lẩu hải sản"
        ),
    ),
    Segment.CAO_SU: SegmentRule(
        segment=Segment.CAO_SU,
        positive_keywords=(
            "cao su", "chế biến mủ cao su", "mủ cao su", "đại lý mủ cao su", "thu mua mủ",
            "cao su thiên nhiên", "nông trường cao su", "nhà máy mủ", "mủ tờ", "mủ chén"
        ),
        negative_keywords=(
            "vá vỏ xe", "săm lốp", "nệm cao su", "đệm cao su",
            "thay lốp", "gara ô tô", "vá xe lưu động"
        ),
    ),
    Segment.DET_MAY: SegmentRule(
        segment=Segment.DET_MAY,
        positive_keywords=(
            "dệt may", "may mặc", "xưởng may gia công", "sản xuất may mặc", "xưởng cắt may",
            "công ty may xuất khẩu", "xưởng may", "may xuất khẩu",
            "gia công may mặc", "chuyền may", "xưởng thêu", "xưởng in vải"
        ),
        negative_keywords=(
            "tiệm sửa quần áo", "sửa quần áo", "shop thời trang", "thời trang bán lẻ",
            "cho thuê trang phục", "cho thuê áo dài", "shop quần áo", "boutique"
        ),
    ),
    Segment.PHAN_BON: SegmentRule(
        segment=Segment.PHAN_BON,
        positive_keywords=(
            "phân bón", "nhà máy phân bón", "sản xuất phân bón", "phân bón npk", "phân bón hữu cơ",
            "phối trộn phân bón", "đại lý vtnn cấp 1", "đại lý vật tư nông nghiệp cấp 1",
            "phân vi sinh", "nhà máy hóa chất nông nghiệp", "vật tư nông nghiệp"
        ),
        negative_keywords=(
            "cửa hàng hoa kiểng lẻ", "hoa cảnh mini", "tiệm cây cảnh mini"
        ),
    ),
    Segment.CAY_TRONG: SegmentRule(
        segment=Segment.CAY_TRONG,
        positive_keywords=(
            "cây trồng", "vườn ươm", "cây giống", "trại ươm cây", "cây lâm nghiệp",
            "cây ăn trái", "sản xuất cây giống", "trại cây giống", "ươm giống cây"
        ),
        negative_keywords=(
            "hoa tươi", "shop hoa tươi", "cây cảnh để bàn", "sen đá", "tiệm hoa tươi"
        ),
    ),
}

GLOBAL_EXCLUDED_KEYWORDS: tuple[str, ...] = (
    "sạp chợ", "quán nước", "quán cơm", "nhà hàng", "quán cà phê", "cafe"
)


def is_record_inactive(text: str | None) -> bool:
    if not text:
        return False
    lower = text.lower()
    return any(p in lower for p in INACTIVE_PATTERNS)


def classify_text_to_segment(
    name: str,
    description: str = "",
    default_segment: Segment | None = None
) -> tuple[Segment | None, list[str]]:
    combined_text = f"{name} {description}".lower()

    # 1. Kiểm tra từ khóa loại trừ chung
    for kw in GLOBAL_EXCLUDED_KEYWORDS:
        if re.search(rf"\b{re.escape(kw)}\b", combined_text):
            return None, [f"Chứa từ khóa loại trừ chung: '{kw}'"]

    # 2. Tính điểm phân loại cho từng ngành và kiểm tra từ khóa cấm
    scores: dict[Segment, int] = {seg: 0 for seg in Segment}
    violations: dict[Segment, str] = {}
    name_lower = (name or "").lower()
    desc_lower = (description or "").lower()

    for seg, rule in SEGMENT_RULES.items():
        for neg_kw in rule.negative_keywords:
            if re.search(rf"\b{re.escape(neg_kw)}\b", combined_text):
                violations[seg] = f"Vi phạm từ khóa loại trừ của ngành {seg.value}: '{neg_kw}'"
                break

        if seg in violations:
            continue

        for pos_kw in rule.positive_keywords:
            # Ưu tiên rất cao (+5 điểm) nếu từ khóa xuất hiện trong Tên Doanh Nghiệp (BA §3.4: hoạt động cốt lõi thể hiện qua tên)
            if re.search(rf"\b{re.escape(pos_kw)}\b", name_lower):
                scores[seg] += 5
            elif re.search(rf"\b{re.escape(pos_kw)}\b", desc_lower):
                scores[seg] += 2

    # Nếu vi phạm từ khóa loại trừ của default_segment -> từ chối ngay
    if default_segment and default_segment in violations:
        return None, [violations[default_segment]]

    # Nếu có default segment hợp lệ từ nguồn cào chuyên ngành -> ưu tiên thêm +3 điểm
    if default_segment and default_segment not in violations:
        scores[default_segment] += 3

    best_seg = max(scores, key=lambda s: scores[s])
    if scores[best_seg] > 0:
        return best_seg, []

    if default_segment and default_segment not in violations:
        return default_segment, []

    # Nếu không khớp nhưng có vi phạm từ khóa riêng của một ngành nào đó
    if violations:
        return None, list(violations.values())

    return None, ["Không khớp từ khóa phân khúc mục tiêu"]
