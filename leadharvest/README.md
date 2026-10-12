# LeadHarvest — Hệ thống Thu thập & Chuẩn hóa Dữ liệu Khách hàng B2B

Dự án cào và chuẩn hóa danh sách khách hàng doanh nghiệp B2B nội địa cho **Bao Bì Hồng Hải** theo tài liệu đặc tả [BA_baoBiHongHai.md](../BA_baoBiHongHai.md).

---

## 1. Cấu trúc thư mục

```
leadharvest/
├── scrapy.cfg                          # Cấu hình Scrapy
├── requirements.txt                    # Thư viện phụ thuộc (scrapy, openpyxl, pytest)
├── pytest.ini                          # Cấu hình kiểm thử tự động
├── README.md                           # Hướng dẫn sử dụng
├── data/
│   ├── raw/                            # Dữ liệu thô cào về (*.jsonl kèm checkpoint)
│   └── output/
│       ├── BaoBiHongHai_Master.xlsx    # Master Excel 6 tab ngành + 1 tab Thong_Ke
│       ├── qa_report.json              # Báo cáo đối soát chất lượng JSON (BA §9)
│       └── csv/                        # 6 file CSV UTF-8-BOM độc lập theo ngành
├── leadharvest/
│   ├── models/
│   │   ├── enums.py                    # Enum 6 phân khúc, loại SĐT, lý do loại bỏ
│   │   ├── raw_lead.py                 # Schema dữ liệu thô nội bộ (kèm tracking URL)
│   │   └── lead_output.py              # Schema 11 cột bàn giao + đầy đủ hàm verify
│   ├── validators/
│   │   ├── phone.py                    # Chuẩn hóa SĐT di động, bàn, hotline, số rác
│   │   ├── tax_code.py                 # MST 10 số, 13 số chi nhánh, chặn CCCD 12 số
│   │   ├── province.py                 # Chuẩn hóa 63 Tỉnh/Thành, alias tên cũ/mới
│   │   ├── text.py                     # Chuẩn hóa tên cty, người đại diện, độ cụ thể địa chỉ
│   │   └── segment.py                  # Bộ từ khóa lọc 6 ngành và từ khóa loại trừ
│   ├── processing/
│   │   ├── normalizer.py               # Chuyển RawLead -> LeadOutput + bắt lỗi
│   │   ├── deduplicator.py             # Khử trùng đa nguồn & đa tab (cross-tab)
│   │   └── qa_report.py                # Sinh QA Report và kiểm tra tiêu chí nghiệm thu
│   ├── exporters/
│   │   ├── excel.py                    # Xuất Excel đa tab, ép kiểu text cho SĐT & MST
│   │   └── csv_export.py               # Xuất 6 CSV UTF-8-BOM không lỗi font
│   ├── spiders/
│   │   ├── base.py                     # BaseLeadSpider
│   │   ├── vasep.py                    # Spider cào hội viên VASEP (Thủy sản)
│   │   └── vietfood.py                 # Spider cào hội viên Vietfood - VFA (Nông sản)
│   ├── pipelines.py                    # Pipeline lưu raw JSONL + checkpoint chống trùng
│   ├── settings.py                     # Cấu hình crawler Scrapy
│   └── cli.py                          # Lệnh build dữ liệu và xuất báo cáo QA
└── tests/                              # Bộ 51 test cases tự động (100% pass)
    ├── fixtures/                       # Dữ liệu HTML mẫu phục vụ kiểm thử offline
    ├── test_phone.py
    ├── test_tax_code.py
    ├── test_lead_output.py
    ├── test_deduplicator.py
    ├── test_normalizer_and_report.py
    ├── test_vasep_spider.py
    └── test_vietfood_spider.py
```

---

## 2. Quy trình 2 pha (2-Phase Architecture)

Do tài liệu BA yêu cầu:
1. **Khử trùng lặp chéo** giữa tất cả các nguồn và giữa 6 tab phân khúc (BA §8.3).
2. Khi trùng lặp phải **giữ lại bản ghi giàu thông tin nhất** (`richness_score` cao nhất: có di động, có người liên hệ, địa chỉ chi tiết) thay vì loại bỏ bản ghi đến sau.
3. Không làm lộ URL nguồn, tên website nội bộ ra file giao khách (BA §6.2).

Do đó hệ thống chạy theo 2 pha tách biệt:

```
[Spiders cào đa nguồn] ──(Pha 1)──> data/raw/*.jsonl (Lưu trữ nội bộ)
                                           │
                                     (Pha 2: build)
                                           ▼
                       ┌───────────────────────────────────────┐
                       │ 1. Normalize & Verify (11 quy tắc BA) │
                       │ 2. Deduplicate Cross-Tab theo SĐT/MST │
                       │ 3. Generate QA Report (BA §9)         │
                       └───────────────────┬───────────────────┘
                                           │
                       ┌───────────────────┴───────────────────┐
                       ▼                                       ▼
            BaoBiHongHai_Master.xlsx                   qa_report.json
         (6 tab ngành + 1 tab Thống kê)               + 6 file CSV UTF-8-BOM
```

---

## 3. Hướng dẫn sử dụng

### 3.1. Danh sách Spiders hỗ trợ

| Tên Spider | Nguồn dữ liệu | Nhóm Ngành (BA §4) | Quy mô | Thông tin bóc tách chi tiết |
| :--- | :--- | :--- | :--- | :--- |
| **`vasep`** | Hiệp hội Chế biến và Xuất khẩu Thủy sản Việt Nam ([vasep.com.vn](https://vasep.com.vn/hoi-vien)) | **Thủy sản** | ~500+ doanh nghiệp | Bảng chi tiết: Tên pháp nhân, MST, Người đại diện, SĐT, Email, Website, Tách địa chỉ xưởng/nhà máy khỏi VPDD. |
| **`vietfood`** | Hiệp hội Lương thực Việt Nam - VFA ([vietfood.org.vn](https://vietfood.org.vn/hoi-vien/danh-sach-hoi-vien/)) | **Nông sản** | 131 doanh nghiệp | Trang chi tiết Elementor: Tên tiếng Việt (xóa dấu `*` liên kết), Tên quốc tế, Địa chỉ, Tỉnh/thành (thẻ SEO tag), Tel (tách số ghép), Email, Website, Fax, Logo. |

---

### 3.2. Chạy Crawler VASEP (Phân khúc Thủy sản)

**Lựa chọn 1: Cào toàn bộ tất cả các trang hội viên VASEP (tự động phân trang đến trang cuối cùng)**:
```bash
cd leadharvest
# Qua Scrapy:
scrapy crawl vasep -a crawl_all=true
# Hoặc alias:
scrapy crawl vasep -a all=true

# Hoặc qua CLI LeadHarvest:
python -m leadharvest.cli crawl --spider vasep --all
```

**Lựa chọn 2: Cào theo khoảng trang chỉ định** (ví dụ từ trang 1 đến trang 5):
```bash
cd leadharvest
scrapy crawl vasep -a start_page=1 -a end_page=5

# Hoặc qua CLI:
python -m leadharvest.cli crawl --spider vasep --start-page 1 --end-page 5
```

**Tùy chọn lưu file cho VASEP**:
```bash
scrapy crawl vasep -a start_page=1 -a end_page=5 -a save_file=vasep_dot1.jsonl
```

---

### 3.3. Chạy Crawler Vietfood (Phân khúc Nông sản)

Hội viên Vietfood được hiển thị danh sách 131 đơn vị trực tiếp tại trang `/hoi-vien/danh-sach-hoi-vien/`.

**Lựa chọn 1: Cào toàn bộ 131 hội viên Vietfood**:
```bash
cd leadharvest
# Qua Scrapy:
scrapy crawl vietfood

# Hoặc qua CLI LeadHarvest:
python -m leadharvest.cli crawl --spider vietfood
```

**Lựa chọn 2: Cào thử nghiệm N hội viên (tham số `limit`)**:
```bash
cd leadharvest
# Cào thử nghiệm 10 hội viên:
scrapy crawl vietfood -a limit=10

# Hoặc qua CLI:
python -m leadharvest.cli crawl --spider vietfood --limit 10
```

**Lựa chọn 3: Tùy chọn lưu vào file tùy chỉnh**:
```bash
# Lưu vào file riêng trong data/raw/:
scrapy crawl vietfood -a save_file=vietfood_raw.jsonl

# Hoặc qua CLI:
python -m leadharvest.cli crawl --spider vietfood --save-file vietfood_raw.jsonl
```

Dữ liệu thô cào về sẽ được lưu tự động dạng JSON Lines tại `data/raw/vietfood.jsonl` (hoặc file chỉ định), kèm cơ chế checkpoint theo URL đã cào để không bị trùng bản ghi khi chạy lại.

---

### 3.4. Chạy Build & Xuất Dữ liệu (Pha 2: Chuẩn hóa & Nghiệm thu)

Sau khi có dữ liệu thô trong `data/raw/`, chạy lệnh `build`:

```bash
cd leadharvest
python -m leadharvest.cli build
```

Lệnh này sẽ tự động:
- Đọc tất cả các file trong `data/raw/*.jsonl`.
- Lọc bỏ cơ sở giải thể, sai ngành hoặc không có SĐT hợp lệ.
- Khử trùng số điện thoại chéo tab và khử trùng MST (cho phép tối đa 2 chi nhánh khác tỉnh).
- Sinh file Excel `data/output/BaoBiHongHai_Master.xlsx`.
- Sinh 6 file CSV trong `data/output/csv/`.
- Xuất `data/output/qa_report.json` và in báo cáo nghiệm thu trực tiếp lên màn hình console (bao gồm số lượng và tỷ lệ bản ghi có Mobile).

### 3.5. Xem Thống kê Số Điện Thoại & Tỷ lệ Mobile (Stats Tool)

Bạn có thể kiểm tra nhanh số lượng bản ghi có SĐT, Mobile, máy bàn (Landline) và Hotline bất kỳ lúc nào:

```bash
cd leadharvest

# Xem thống kê tổng hợp toàn bộ các file trong data/raw/:
python -m leadharvest.cli stats

# Xem thống kê cho 1 file cụ thể:
python -m leadharvest.cli stats --file data/raw/vasep_all.jsonl

# Xuất dạng JSON (nếu cần xử lý tự động):
python -m leadharvest.cli stats --file data/raw/vasep_all.jsonl --json
```

*Lưu ý:* Khi kết thúc mỗi lượt chạy crawler (`scrapy crawl ...`), hệ thống cũng tự động in hộp thống kê số bản ghi và số lượng mobile thu thập được ngay trên màn hình.

### 3.6. Chạy Kiểm thử Tự động (Unit Tests)

```bash
cd leadharvest
pytest -v
```

---

## 4. Class Output `LeadOutput` & Toàn bộ Logic Verify

Class `LeadOutput` trong `leadharvest/models/lead_output.py` quản lý đúng 11 trường hiển thị theo BA §6:

| # | Tên hiển thị (Tiếng Việt) | Tên biến | Quy tắc kiểm tra (Validation Rules) |
| --: | :-- | :-- | :-- |
| 1 | **Nhóm Ngành** | `target_segment` | Bắt buộc. Phải thuộc đúng 1 trong 6 phân khúc: *Nông sản, Thủy sản, Cao su, Dệt may, Phân bón, Cây trồng*. |
| 2 | **Tên Doanh Nghiệp / Cơ Sở** | `company_name` | Bắt buộc. Không được trống, bỏ khoảng trắng thừa, không phải từ giữ chỗ (*Đang cập nhật, None...*), dài >= 3 ký tự. |
| 3 | **Người Đại Diện / Chủ Cơ Sở** | `contact_person` | Tùy chọn. Tự động lược bỏ danh xưng (*Ông, Bà, Anh, Chị*), chuẩn hóa viết hoa chữ cái đầu. |
| 4 | **Số Điện Thoại Chính** | `phone_primary` | Bắt buộc 100% dòng. Ưu tiên số di động (*MOBILE*), nếu không có thì dùng số bàn (*LANDLINE*). |
| 5 | **Loại SĐT Chính** | `phone_primary_type` | Bắt buộc. Chỉ nhận `MOBILE` hoặc `LANDLINE`. **Cấm tuyệt đối `HOTLINE`** ở cột này. |
| 6 | **Số Điện Thoại Phụ** | `phone_secondary` | Tùy chọn. Nhận di động thứ 2, số bàn hoặc hotline 1800/1900. **Không được trùng với SĐT chính**. |
| 7 | **Loại SĐT Phụ** | `phone_secondary_type` | Tùy chọn. Nhận `LANDLINE`, `HOTLINE` hoặc `MOBILE`. Phải khớp chính xác với loại của SĐT phụ. |
| 8 | **Mã Số Thuế** | `tax_code` | Tùy chọn. MST 10 số doanh nghiệp hoặc 13 số chi nhánh (*XXXXXXXXXX-YYY*). **Chặn tuyệt đối số CCCD 12 số** của hộ kinh doanh (BA §5.3). |
| 9 | **Tỉnh / Thành Phố** | `province` | Bắt buộc. Chuẩn hóa theo danh mục tỉnh/thành chính thức (tự động nhận diện từ địa chỉ nếu nguồn bị thiếu). |
| 10 | **Địa Chỉ Chi Tiết** | `address` | Bắt buộc. Phải đủ độ cụ thể cấp cơ sở (*xã/phường/ấp/đường/lô/KCN...*), cấm ghi chung chung kiểu chỉ có tên tỉnh. |
| 11 | **Trạng Thái Dữ Liệu** | `data_status` | Bắt buộc. Giá trị duy nhất mặc định: **`Công khai hợp lệ`**. |

---

## 5. Thêm Spider mới cho các nguồn tiếp theo

Kế thừa từ `BaseLeadSpider` và yield `RawLead`:

```python
from leadharvest.spiders.base import BaseLeadSpider
from leadharvest.models.enums import Segment

class VitasSpider(BaseLeadSpider):
    name = "vitas"
    source_name = "VITAS"
    default_segment = Segment.DET_MAY.value

    def parse(self, response):
        # Trích xuất dữ liệu và yield
        yield self.make_raw_lead(
            company_name="...",
            raw_phone="...",
            address="...",
            province="...",
            source_url=response.url,
        )
```
