# ĐẶC TẢ NGHIỆP VỤ BA — DỰ ÁN DATA B2B BAO BÌ HỒNG HẢI

**Tên dự án:** Hệ thống thu thập và chuẩn hóa dữ liệu khách hàng B2B nội địa  
**Đơn vị sử dụng dữ liệu:** Bao Bì Hồng Hải.  
**Người quyết định cuối cùng:** Anh Thành — Project Manager / Solution Architect  
**Đối tượng phối hợp:** BA, Dev, đội Sales và đại diện khách hàng Bảo Ngọc  
**Phiên bản:** BA Draft — dùng để trao đổi và chốt với Dev trước khi triển khai chính thức  
**Phạm vi tài liệu:** Yêu cầu nghiệp vụ, dữ liệu đầu ra và tiêu chí nghiệm thu; chưa phải thiết kế kỹ thuật triển khai.

---

## 1\. Mục tiêu dự án

Xây dựng danh sách khách hàng B2B nội địa có khả năng sử dụng sản phẩm bao bì của Bao Bì Hồng Hải, tập trung vào:

- Nhà máy, xưởng, cơ sở sản xuất hoặc sơ chế.  
- Hợp tác xã, hộ kinh doanh, vựa thu mua.  
- Vườn ươm và cơ sở cây giống.  
- Các cơ sở có nhu cầu sử dụng bao bì thường xuyên trong hoạt động kinh doanh.

Dữ liệu đầu ra phục vụ đội Sales tiếp cận khách hàng bằng Zalo và telesales. Trọng tâm là số điện thoại di động hợp lệ, đồng thời giữ số bàn hoặc hotline khi có.

Dự án ưu tiên nguyên tắc:

1. Đúng ngành hơn là tăng số lượng ảo.  
2. Dữ liệu công khai phục vụ giao thương B2B.  
3. Không thu thập thông tin nhạy cảm hoặc thông tin cá nhân không cần thiết.  
4. Không cào rác để đạt chỉ tiêu.  
5. Không đưa dữ liệu chưa chuẩn hóa vào file bàn giao.

---

## 2\. Phạm vi dữ liệu bàn giao

### 2.1. Sản lượng nghiệm thu

- Sản lượng sàn: **5.000 dòng dữ liệu duy nhất** sau khi làm sạch và khử trùng.  
- Có thể bù trừ giữa các phân khúc nếu nguồn một ngành không đủ, nhưng không được bù bằng dữ liệu sai ngành.  
- Số lượng tối thiểu theo phân khúc:

| Phân khúc | Số lượng tối thiểu |
| :---- | ----: |
| Nông sản | 1.200 |
| Dệt may | 1.200 |
| Thủy sản | 500 |
| Phân bón | 500 |
| Cao su | 400 |
| Cây trồng | 500 |
| **Tổng tối thiểu theo ngành** | **4.300** |

&nbsp;

Phần còn thiếu để đạt 5.000 dòng được ưu tiên bổ sung vào **Nông sản** và **Dệt may**, là hai nhóm có độ phủ dự kiến lớn hơn.

Nếu không thể đạt sản lượng tối thiểu do nguồn công khai không đủ, PM phải chốt với khách hàng một trong các phương án:

- Mở rộng phạm vi nguồn hoặc địa lý.  
- Điều chỉnh chỉ tiêu ngành.  
- Điều chỉnh tổng sản lượng nghiệm thu.

Không sử dụng cơ sở sai ngành, số điện thoại giả hoặc bản ghi không đủ điều kiện để bù sản lượng.

### 2.2. Phạm vi địa lý

Phạm vi tổng thể là toàn quốc. Giai đoạn chính ưu tiên các địa phương sau:

| Phân khúc | Tỉnh/thành phố ưu tiên |
| :---- | :---- |
| Thủy sản | Cà Mau, Bạc Liêu, Sóc Trăng, Đồng Tháp, An Giang, Kiên Giang, Bà Rịa \- Vũng Tàu, Khánh Hòa, TP.HCM |
| Nông sản | Tiền Giang, Bến Tre, Lâm Đồng, Đắk Lắk, Đồng Nai, Long An, Hải Dương |
| Dệt may | TP.HCM, Bình Dương, Đồng Nai, Nam Định, Long An, Hà Nội, Hải Phòng |
| Cao su | Bình Phước, Tây Ninh, Bình Dương, Đồng Nai, Gia Lai, Đắk Lắk |
| Phân bón | Long An, Đồng Nai, Bà Rịa \- Vũng Tàu, Cần Thơ, TP.HCM, Bắc Giang |
| Cây trồng | Bến Tre, đặc biệt huyện Chợ Lách; Lâm Đồng, Đồng Nai, Đắk Lắk, Tiền Giang |

&nbsp;

Quy tắc địa lý:

- Tỉnh/thành bàn giao được xác định theo **địa chỉ thực tế của xưởng, kho hoặc cơ sở sản xuất**.  
- Không dùng tỉnh đặt trụ sở văn phòng nếu địa điểm hoạt động thực tế ở tỉnh khác.  
- Có thể dùng tên địa phương cũ và tên địa phương mới làm từ khóa tìm kiếm.  
- Cột tỉnh/thành trong file giao khách phải được chuẩn hóa thống nhất theo quy ước địa giới hiện hành tại thời điểm bàn giao.  
- Địa chỉ gốc và thông tin đối soát nguồn được giữ ở dữ liệu nội bộ, không đưa vào file giao khách nếu không thuộc schema chính thức.

### 2.3. Thời điểm dữ liệu

Ưu tiên cơ sở có dấu hiệu hoạt động hoặc được ghi nhận trên nguồn công khai trong khoảng **12–24 tháng gần nhất**.

Không tự động loại bản ghi chỉ vì website trả về lỗi 404\. Chỉ loại khi có bằng chứng rõ ràng về một trong các trạng thái sau:

- Đã giải thể.  
- Đã ngừng hoạt động.  
- Mã số thuế bị đóng hoặc không còn hoạt động.  
- Cơ sở được nguồn tin cậy ghi nhận đã đóng cửa vĩnh viễn.

---

## 3\. Đối tượng dữ liệu hợp lệ

### 3.1. Đối tượng được chấp nhận

Có thể thu thập các loại hình sau nếu phù hợp ngành và có thông tin liên hệ công khai:

- Công ty/doanh nghiệp.  
- Hợp tác xã.  
- Hộ kinh doanh cá thể.  
- Vựa thu mua.  
- Nhà máy, xưởng sản xuất hoặc cơ sở sơ chế.  
- Vườn ươm, trại cây giống.

Ưu tiên đơn vị trực tiếp sản xuất, sơ chế, đóng gói hoặc thu mua với quy mô B2B.

### 3.2. Đối tượng loại trừ

Loại khỏi dữ liệu bàn giao:

- Cửa hàng bán lẻ nhỏ lẻ không thể hiện nhu cầu bao bì B2B.  
- Sạp chợ dân sinh.  
- Nhà hàng, quán ăn, hồ câu trong nhóm Thủy sản.  
- Shop thời trang bán lẻ, tiệm sửa quần áo, nơi cho thuê trang phục trong nhóm Dệt may.  
- Cửa hàng hoa quả nhập khẩu, trái cây dĩa, cửa hàng nước ép trong nhóm Nông sản.  
- Cửa hàng hoa kiểng lẻ, hoa tươi, cây cảnh để bàn, sen đá trong nhóm Phân bón/Cây trồng.  
- Cơ sở vá vỏ xe, săm lốp, nệm cao su trong nhóm Cao su.  
- Bản ghi không xác định được tên cơ sở hoặc không có địa chỉ cụ thể.  
- Bản ghi có trạng thái giải thể/ngừng hoạt động.  
- Bản ghi chứa số điện thoại không hợp lệ và không có số thay thế hợp lệ.

### 3.3. Cơ sở không có mã số thuế

Cơ sở không có mã số thuế vẫn được chấp nhận nếu có đủ:

- Tên cơ sở rõ ràng.  
- Địa chỉ cụ thể.  
- Ít nhất một số điện thoại hợp lệ.  
- Dấu hiệu phù hợp với phân khúc mục tiêu.

### 3.4. Doanh nghiệp đa ngành

Một doanh nghiệp hoặc cơ sở chỉ được đưa vào **một phân khúc chính duy nhất**.

Phân khúc chính được xác định theo hoạt động cốt lõi thể hiện qua tên, mô tả, ngành nghề hoặc nội dung nguồn. Không đưa cùng một doanh nghiệp vào nhiều tab chỉ vì doanh nghiệp có nhiều ngành đăng ký.

Ví dụ: doanh nghiệp chuyên chế biến thủy sản nhưng có đăng ký thêm hoạt động buôn bán nông sản thì xếp vào tab **Thủy sản**.

---

## 4\. Sáu phân khúc mục tiêu

| Phân khúc | Đối tượng cần lấy | Từ khóa gợi ý | Từ khóa loại trừ chính |
| :---- | :---- | :---- | :---- |
| **Nông sản** | Vựa trái cây, vựa rau củ, HTX nông nghiệp, cơ sở sơ chế/đóng gói nông sản | `vựa trái cây`, `vựa rau củ`, `HTX nông nghiệp`, `sơ chế nông sản`, `đóng gói nông sản` | `cửa hàng hoa quả nhập khẩu`, `trái cây dĩa`, `nước ép` |
| **Thủy sản** | Nhà máy chế biến, cơ sở đông lạnh, vựa tôm/cá, đơn vị xuất khẩu | `chế biến thủy sản`, `thủy hải sản đông lạnh`, `vựa tôm`, `vựa cá`, `xuất khẩu hải sản` | `quán ăn hải sản`, `nhà hàng`, `hồ câu` |
| **Cao su** | Cơ sở chế biến mủ, đại lý/đơn vị thu mua mủ, cao su thiên nhiên | `chế biến mủ cao su`, `đại lý mủ cao su`, `cao su thiên nhiên` | `vá vỏ xe`, `săm lốp`, `nệm cao su` |
| **Dệt may** | Xưởng may gia công, cơ sở sản xuất may mặc, xưởng cắt may | `xưởng may gia công`, `sản xuất may mặc`, `xưởng cắt may`, `công ty may xuất khẩu` | `tiệm sửa quần áo`, `shop thời trang bán lẻ`, `cho thuê trang phục` |
| **Phân bón** | Nhà máy, cơ sở sản xuất/phối trộn, đại lý vật tư nông nghiệp cấp 1 | `nhà máy phân bón`, `sản xuất phân bón NPK`, `phân bón hữu cơ`, `đại lý VTNN cấp 1` | `cửa hàng hoa kiểng lẻ` |
| **Cây trồng** | Vườn ươm, cơ sở cây giống, trại ươm cây lâm nghiệp/ăn trái | `vườn ươm`, `cây giống`, `trại ươm cây`, `cây lâm nghiệp`, `cây ăn trái` | `hoa tươi`, `cây cảnh để bàn`, `sen đá` |

&nbsp;

Bộ từ khóa là cơ sở ban đầu. BA và Dev có thể bổ sung từ khóa trong quá trình lọc dữ liệu, nhưng mọi thay đổi làm thay đổi phạm vi ngành phải được PM chốt.

---

## 5\. Nguồn dữ liệu được phép sử dụng

### 5.1. Nguồn P0 bắt buộc

- VASEP — Hiệp hội Chế biến và Xuất khẩu Thủy sản Việt Nam.  
- VITAS — Hiệp hội Dệt May Việt Nam.  
- Trang Vàng Việt Nam (`yellowpages.vn`).  
- Cổng Liên minh Hợp tác xã Việt Nam (`vca.org.vn`).

### 5.2. Nguồn bổ sung

- Google Maps và bản đồ địa điểm kinh doanh.  
- Cổng thông tin Sở Công Thương.  
- Trung tâm Khuyến công các tỉnh trọng điểm.  
- Cổng thông tin hiệp hội ngành nghề hoặc danh bạ công khai phù hợp.

### 5.3. Nguyên tắc sử dụng nguồn

- Chỉ sử dụng thông tin liên hệ công khai phục vụ giao thương B2B.  
- Không sử dụng LinkedIn, Apollo hoặc dữ liệu đoán email.  
- Không dùng nguồn yêu cầu trả phí hoặc tài khoản đăng nhập trong P0.  
- Không thu thập CCCD, thông tin tài chính, đời tư hoặc thông tin nhạy cảm.  
- Nếu một nguồn hiển thị CAPTCHA hoặc hạn chế truy cập dày đặc, chuyển sang nguồn dự phòng được phép; không cố bypass phức tạp.  
- Dữ liệu nội bộ phải lưu tên nguồn, URL và thời điểm thu thập để đối soát. Các trường này không xuất trong file giao khách.

---

## 6\. Schema file bàn giao chính thức

File Google Sheets và file Excel/CSV phải sử dụng 11 cột theo đúng thứ tự sau. Tên hiển thị trên file giao khách là tiếng Việt; tên biến nội bộ tương ứng được ghi trong ngoặc.

| STT | Tên cột hiển thị | Tên nội bộ | Bắt buộc | Quy tắc nghiệp vụ |
| ----: | :---- | :---- | :---- | :---- |
| 1 | Nhóm Ngành | `target_segment` | Có | Một trong 6 giá trị: Nông sản, Thủy sản, Cao su, Dệt may, Phân bón, Cây trồng. |
| 2 | Tên Doanh Nghiệp / Cơ Sở | `company_name` | Có | Tên pháp nhân, HTX, hộ kinh doanh hoặc tên cơ sở rõ ràng; bỏ khoảng trắng thừa. |
| 3 | Người Đại Diện / Chủ Cơ Sở | `contact_person` | Không | Tên người đại diện/chủ cơ sở nếu nguồn công khai có cung cấp. |
| 4 | Số Điện Thoại Chính | `phone_primary` | Có | Ưu tiên số di động hợp lệ để Sales sử dụng cho Zalo. Nếu không có di động thì dùng số bàn hợp lệ. |
| 5 | Loại SĐT Chính | `phone_primary_type` | Có | `MOBILE` hoặc `LANDLINE`. Không dùng `HOTLINE` ở cột chính. |
| 6 | Số Điện Thoại Phụ | `phone_secondary` | Không | Số bàn, hotline 1800/1900 hoặc số di động thứ hai hợp lệ. |
| 7 | Loại SĐT Phụ | `phone_secondary_type` | Không | `LANDLINE`, `HOTLINE` hoặc `MOBILE`. |
| 8 | Mã Số Thuế | `tax_code` | Không | MST 10 số hoặc mã phù hợp sau chuẩn hóa; để trống nếu cơ sở không có MST công khai. |
| 9 | Tỉnh / Thành Phố | `province` | Có | Tỉnh/thành của địa chỉ thực tế cơ sở, chuẩn hóa thống nhất. |
| 10 | Địa Chỉ Chi Tiết | `address` | Có | Địa chỉ xưởng, kho, vựa, vườn ươm hoặc cơ sở hoạt động. |
| 11 | Trạng Thái Dữ Liệu | `data_status` | Có | Giá trị mặc định duy nhất: `Công khai hợp lệ`. |

&nbsp;

### 6.1. Ý nghĩa trạng thái dữ liệu

`Công khai hợp lệ` xác nhận rằng:

- Dữ liệu được lấy từ nguồn công khai được phép.  
- Thông tin đạt quy tắc chuẩn hóa đã thống nhất.  
- Cơ sở phù hợp phân khúc nghiệp vụ.  
- Số điện thoại đạt chuẩn kỹ thuật nếu bản ghi được bàn giao.

Trạng thái này **không cam kết** cơ sở chắc chắn đang mở cửa tại thời điểm Sales gọi và không thay thế cho việc telesales xác minh thực tế.

### 6.2. Các trường không bàn giao cho khách

Các trường sau chỉ lưu trong dữ liệu nội bộ để QA và đối soát, không xuất trong 6 tab giao khách:

- `source_name`.  
- `source_url`.  
- `crawled_at`.  
- Lý do loại bản ghi.  
- Khóa checkpoint hoặc mã kỹ thuật nội bộ.

---

## 7\. Quy tắc số điện thoại

### 7.1. Số hợp lệ

- Số di động Việt Nam hợp lệ theo đầu số hiện hành: 03, 05, 07, 08, 09\.  
- Số bàn hợp lệ theo mã vùng hiện hành, bắt đầu bằng 02x và đúng độ dài sau chuẩn hóa.  
- Số hotline 1800/1900 được chấp nhận ở cột phụ.  
- Không chấp nhận chuỗi số giả lập hoặc rõ ràng là số rác như toàn số 0, chuỗi tăng tuần tự, số thiếu/thừa chữ số.

### 7.2. Làm sạch số

- Loại bỏ dấu chấm, gạch ngang, khoảng trắng, gạch dưới và dấu phân cách.  
- Chuyển `+84`, `0084` hoặc `84` về đầu số `0` tương ứng.  
- Nếu nguồn chứa nhiều số, tách từng số để kiểm tra độc lập.  
- Không gộp nhiều số vào cùng một ô bằng dấu `;`.  
- Nếu có 2–3 số di động: số đầu tiên vào `phone_primary`, số thứ hai vào `phone_secondary`; bỏ số thứ ba.  
- Nếu không có số di động nhưng có số bàn: đưa số bàn vào `phone_primary`, gán `LANDLINE`.  
- Nếu chỉ có 1800/1900: đưa vào `phone_secondary`, gán `HOTLINE`; bản ghi vẫn được giữ nếu tên và địa chỉ đầy đủ.

### 7.3. Điều kiện bàn giao

- 100% dòng bàn giao phải có ít nhất một số điện thoại hợp lệ ở cột chính hoặc cột phụ.  
- Không bàn giao dòng không có số điện thoại.  
- Tối thiểu 90% tổng số dòng bàn giao phải có ít nhất một số di động ở `phone_primary` hoặc `phone_secondary`.  
- Với mốc 5.000 dòng, mục tiêu tối thiểu là 4.500 dòng có số di động.

---

## 8\. Quy tắc khử trùng lặp

### 8.1. Theo mã số thuế

- Cùng MST 10 số gốc và cùng tỉnh/thành: gộp thành một dòng.  
- Ưu tiên dòng có số di động, tên người liên hệ và địa chỉ cơ sở chi tiết hơn.  
- Cùng MST nhưng khác tỉnh và có số điện thoại riêng: được giữ tối đa hai dòng đại diện, với điều kiện mỗi dòng thể hiện một địa điểm hoạt động thực tế khác nhau.  
- Không giữ nhiều dòng chỉ vì khác địa chỉ văn phòng nếu không có cơ sở/xưởng thực tế riêng.

### 8.2. Không có mã số thuế

- Dùng số điện thoại đã chuẩn hóa để phát hiện trùng.  
- Kiểm tra trùng trên cả `phone_primary` và `phone_secondary`.  
- Không để hai dòng trong file giao khách dùng chung một số điện thoại.  
- Nếu cùng số nhưng khác tên, ưu tiên cơ sở có tên thể hiện rõ hoạt động sản xuất/xưởng/chế biến/HTX; loại cơ sở thương mại thuần túy.

### 8.3. Khử trùng giữa các tab

- Một MST chỉ xuất hiện ở một phân khúc chính, ngoại trừ tối đa hai cơ sở khác tỉnh theo quy tắc chi nhánh.  
- Một số điện thoại không được xuất hiện ở hai dòng hoặc hai tab khác nhau.  
- Doanh nghiệp đa ngành chỉ được giữ tại tab ngành kinh doanh cốt lõi.

---

## 9\. Báo cáo chất lượng dữ liệu

Khi xuất Master file, phải có thêm một trong hai hình thức sau:

- File `qa_report.json`; hoặc  
- Tab `Thong_Ke` trong Google Sheets.

Báo cáo tối thiểu phải thể hiện:

- Tổng số bản ghi thô đã thu thập.  
- Số bản ghi bị loại do trùng lặp.  
- Số bản ghi bị loại do thiếu thông tin.  
- Số bản ghi bị loại do sai ngành.  
- Số bản ghi bị loại do trạng thái ngừng hoạt động/giải thể.  
- Số bản ghi bàn giao theo từng tab.  
- Tổng số bản ghi bàn giao.  
- Số dòng có số di động.  
- Số dòng có số bàn.  
- Số dòng có hotline.  
- Tỷ lệ phần trăm số di động.  
- Tỷ lệ bản ghi có ít nhất một số điện thoại hợp lệ.

---

## 10\. Tiêu chí nghiệm thu

### 10.1. Tiêu chí dữ liệu bắt buộc

1. Có tối thiểu 5.000 dòng sau làm sạch và khử trùng, hoặc số lượng điều chỉnh được PM chốt bằng văn bản nếu nguồn không đủ.  
2. Đủ mức sàn theo từng phân khúc đã nêu tại mục 2.1, trừ khi có quyết định điều chỉnh.  
3. 100% dòng có ít nhất một số điện thoại hợp lệ.  
4. Ít nhất 90% dòng có số di động.  
5. Không có hai dòng trùng số điện thoại trong file giao khách.  
6. Không có trùng MST trái với quy tắc chi nhánh.  
7. Mỗi dòng chỉ thuộc một phân khúc chính.  
8. Đúng 11 cột và đúng thứ tự schema.  
9. Không lộ `source_url`, `source_name` hoặc thông tin kỹ thuật nội bộ trong các tab bàn giao.  
10. Có file Excel/CSV hoàn chỉnh và dữ liệu sẵn sàng đưa lên Google Sheets.

### 10.2. Kiểm tra phân loại 100 dòng

BA và PM chọn ngẫu nhiên 100 dòng theo tỷ lệ:

| Phân khúc | Số dòng kiểm tra |
| :---- | ----: |
| Nông sản | 20 |
| Dệt may | 20 |
| Thủy sản | 15 |
| Phân bón | 15 |
| Cao su | 15 |
| Cây trồng | 15 |
| **Tổng** | **100** |

&nbsp;

Tiêu chuẩn đạt: tối thiểu **95/100 dòng** đúng tệp ngành.

Nếu đạt từ 90 đến 94 dòng:

- Dev bổ sung từ khóa loại trừ hoặc điều chỉnh bộ lọc trong thời gian dự kiến 2 giờ.  
- Chạy lọc lại dữ liệu bị ảnh hưởng.  
- BA/PM kiểm tra lại 30 dòng ngẫu nhiên.  
- Đề xuất ngưỡng đạt lần kiểm tra lại là tối thiểu 29/30 dòng.

Nếu dưới 90/100 dòng, PM quyết định phạm vi sửa bộ quy tắc và thời điểm kiểm tra lại.

---

## 11\. Kế hoạch bàn giao

### Giai đoạn 1 — Chuẩn bị dữ liệu và xuất file

- Dev thu thập dữ liệu từ các nguồn P0 và nguồn bổ sung được phép.  
- Làm sạch số điện thoại, phân loại ngành và khử trùng.  
- Xuất file Excel/CSV 6 tab để BA/PM đối soát nội bộ.  
- Xuất báo cáo QA.

### Giai đoạn 2 — Đồng bộ Google Sheets

- Anh Thành tạo Google Sheets trên tài khoản của mình.  
- Anh Thành cấp quyền Editor cho Google Service Account của Dev.  
- Dev đưa dữ liệu đã đối soát vào đúng 6 tab.  
- Không đưa dữ liệu thô hoặc cột nguồn vào file Sales.

### Giai đoạn 3 — Nghiệm thu

- BA và PM bốc mẫu 100 dòng theo tỷ lệ đã thống nhất.  
- Kiểm tra phân loại, số điện thoại, địa chỉ và trùng lặp.  
- Ghi nhận kết quả trong QA Report.  
- PM là người chốt cuối cùng khi có bất đồng giữa BA và khách hàng.

### Lưu trữ sau bàn giao

- Dev giữ database nội bộ và file Excel gốc trên VPS trong 30 ngày.  
- Google Sheets sử dụng Version History để khôi phục khi có thao tác nhầm.  
- Sau thời hạn 30 ngày, việc tiếp tục lưu trữ phải được PM/khách hàng chốt riêng.

---

## 12\. Ngoài phạm vi P0

Các tính năng sau chưa thuộc phạm vi nghiệm thu hiện tại:

- Tự động cập nhật doanh nghiệp mới định kỳ.  
- Link Zalo một chạm.  
- Kiểm tra trạng thái đăng ký Zalo.  
- HLR Lookup kiểm tra thuê bao.  
- Gọi điện xác minh thủ công từng cơ sở.  
- Thu thập doanh thu, sản lượng mua bao bì hoặc nhu cầu mua hàng nội bộ.  
- Bot tự động kết bạn hoặc gửi tin nhắn hàng loạt.  
- Các AI Agent hỗ trợ các phòng ban.

Các tính năng trên chỉ được triển khai nếu có yêu cầu và báo giá riêng.

---

## 13\. Các điểm cần Dev xác nhận trước khi bắt đầu chạy full

Đây là các điểm kỹ thuật cần Dev ước lượng và xác nhận, không phải yêu cầu nghiệp vụ mới:

1. Khả năng thu thập thực tế của từng nguồn P0 và nguồn dự phòng.  
2. Cách xử lý phân trang, giới hạn truy cập và CAPTCHA mà không bypass phức tạp.  
3. Cơ chế checkpoint để chạy tiếp khi VPS hoặc mạng bị gián đoạn.  
4. Cách xác định bản ghi đã xử lý mà không tạo bản ghi trùng.  
5. Cách chuẩn hóa tên tỉnh/thành theo quy ước đã thống nhất.  
6. Cách xử lý MST chi nhánh và xác định cơ sở khác tỉnh.  
7. Cách xuất đồng thời Excel/CSV, `qa_report.json` và dữ liệu Google Sheets.  
8. Ước lượng man-days lập trình, thời gian chạy dữ liệu và chi phí hạ tầng/proxy nếu phát sinh.  
9. Cảnh báo sớm nếu tỷ lệ số di động hoặc sản lượng thực tế không thể đạt bằng các nguồn được phép.  
10. Kế hoạch dừng/chuyển nguồn khi nguồn chính bị giới hạn hoặc thay đổi cấu trúc.

Dev không được tự ý thay đổi tiêu chí ngành, schema hoặc ngưỡng nghiệm thu. Mọi thay đổi ảnh hưởng dữ liệu bàn giao phải được PM chốt lại với BA.

---

## 14\. Quyết định cần PM/BA theo dõi

| Nội dung | Trạng thái |
| :---- | :---- |
| Phạm vi 6 phân khúc | Đã chốt |
| Tổng sản lượng sàn 5.000 dòng | Đã chốt |
| Sản lượng sàn từng phân khúc | Đã chốt theo mục 2.1 |
| Schema 11 cột tiếng Việt | Đã chốt |
| Tỷ lệ có số điện thoại | 100% dòng bàn giao |
| Tỷ lệ số di động | Tối thiểu 90% |
| Khử trùng MST và số điện thoại cross-tab | Đã chốt |
| Nguồn P0 | Đã chốt |
| Excel/CSV trước, Google Sheets sau | Đã chốt |
| QA Report | Bắt buộc |
| Tự động cập nhật/Zalo checker/HLR | Ngoài P0 |
| Khả năng nguồn đạt sản lượng và tỷ lệ MOBILE | Dev cần xác nhận |
| Man-days và timeline chạy full | Dev cần xác nhận |
| Proxy hoặc chi phí hạ tầng phát sinh | Dev cần báo trước |

&nbsp;

---

## 15\. Phê duyệt tài liệu

- **BA:** Xác nhận phạm vi nghiệp vụ và tiêu chí dữ liệu.  
- **Dev:** Xác nhận khả năng kỹ thuật, effort và rủi ro nguồn.  
- **PM/Solution Architect:** Chốt cuối cùng về phạm vi, tiến độ, chi phí và các ngoại lệ nghiệm thu.  
- **Khách hàng:** Xác nhận mục đích sử dụng dữ liệu, quyền truy cập Google Sheets và kết quả nghiệm thu.