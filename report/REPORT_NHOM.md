# Báo Cáo Nhóm — Lab 7: Embedding & Vector Store

**Nhóm:** TH True Mi
**Thành viên:** Trần Nguyễn Trí Dũng - Mai Huy Hoàng - Nguyễn Đức Tâm - Nguyễn Thị Hải Mi
**Ngày:** 20/09/2026

> **Nộp 1 bản / nhóm.** Phần cá nhân (hướng tiếp cận, kết quả riêng, dự đoán…) mỗi thành viên nộp riêng trong `REPORT_CANHAN.md`. Chi tiết thang điểm: `docs/SCORING.md`.

**Tổng điểm phần nhóm: 40** = Lựa chọn tài liệu (10) + Thiết kế chiến lược (15) + Chất lượng truy xuất (10) + Thuyết trình (5).

---

## 1. Lựa chọn tài liệu (Document Set Quality) — Nhóm (10 điểm)

### Chủ đề (Domain) & Lý Do Chọn

**Chủ đề:** Chính sách Đổi trả, Hoàn tiền & Vận chuyển hoàn trả trên Shopee (góc nhìn Người mua và Người bán)

**Tại sao nhóm chọn chủ đề này?**
> Nhóm chọn chính sách Shopee vì đây là chủ đề thực tế, có nhiều điều kiện, thời hạn và quy trình dành riêng cho người mua/người bán. Bộ corpus cho phép kiểm tra cả retrieval theo nội dung lẫn metadata filter, đặc biệt ở các câu hỏi về phí trả hàng và thời hạn phản hồi.

### Danh sách tài liệu (Data Inventory)

| # | Tên tài liệu | Nguồn (Source URL) | Ngày lấy / Phiên bản | Số ký tự | Metadata đã gán |
|---|--------------|------------|--------------------|----------|-----------------|
| 1 | Chính sách trả hàng và hoàn tiền | [Shopee](https://help.shopee.vn/portal/4/article/77251) | 2026-09-20 / effective-2026-03-11 | 19,609 | both; returns-refunds-policy; vi |
| 2 | Chính sách Vận chuyển Shopee | [Shopee](https://help.shopee.vn/portal/4/article/77250) | 2026-09-20 / 2026-09-15 | 24,376 | both; shipping-policy; vi |
| 3 | Điều Khoản Dịch Vụ của Shopee Mall | [Shopee](https://help.shopee.vn/portal/4/article/77262) | 2026-09-20 / not-stated | 33,568 | both; mall-terms; vi |
| 4 | Các phương thức gửi hàng hoàn trả và phí hoàn trả | [Shopee](https://help.shopee.vn/portal/4/article/189477) | 2026-09-20 / not-stated | 5,723 | buyer; returns-logistics; vi |
| 5 | Những quy định chung về Trả hàng/Hoàn tiền | [Shopee](https://help.shopee.vn/portal/4/article/188931) | 2026-09-20 / not-stated | 6,350 | buyer; returns-refunds-guide; vi |
| 6 | Quản lý đơn trả hàng hoàn tiền (Kênh Quản Lý Shop) | [Shopee](https://help.shopee.vn/portal/1/article/102521) | 2026-09-20 / not-stated | 3,699 | seller; returns-logistics; vi |

**Danh sách kiểm tra quản trị dữ liệu (Data governance checklist):**
- [x] Tập tài liệu (Corpus) chỉ chứa nguồn công khai/được phép dùng và không chứa dữ liệu cá nhân, thông tin đăng nhập hoặc tài liệu nội bộ.
- [x] Mỗi tài liệu có `source_url`, `retrieved_at`, `document_version` (hoặc ngày hiệu lực) trong metadata.

### Cấu trúc Metadata (Metadata Schema)

| Trường metadata | Kiểu | Ví dụ giá trị | Tại sao hữu ích cho truy xuất (retrieval)? |
|----------------|------|---------------|-------------------------------|
| `doc_id` | string | `shopee-quy-dinh-chung-tra-hang-hoan-tien` | Định danh ổn định để truy vết document/chunk và chấm expected source. |
| `audience` | enum | `buyer`, `seller`, `both` | Lọc đúng đối tượng; tránh trộn hướng dẫn buyer và seller. |
| `category` | string | `returns-logistics` | Phân biệt nhóm chính sách khi query có từ vựng gần nhau. |
| `language` | string | `vi` | Xác định ngôn ngữ corpus và chọn embedding phù hợp. |
| `source_url` / `retrieved_at` / `document_version` | string/date | URL Shopee / `2026-09-20` / `not-stated` | Bảo đảm provenance và biết thời điểm/phiên bản dữ liệu. |

---

## 2. Thiết kế chiến lược (Strategy Design) — Nhóm (15 điểm)

> Mỗi thành viên thử **một chiến lược khác nhau** trên cùng bộ tài liệu; nhóm tổng hợp và so sánh ở đây.

### Phân tích đường cơ sở (Baseline Analysis)

Chạy `ChunkingStrategyComparator().compare()` trên 2-3 tài liệu:

| Tài liệu | Chiến lược (Strategy) | Số lượng Chunk | Độ dài trung bình | Giữ được ngữ cảnh không? |
|-----------|----------|-------------|------------|-------------------|
| Chính sách trả hàng và hoàn tiền | FixedSizeChunker (`fixed_size`) | 44 | 494.5 | Chunk đều, nhưng có thể cắt giữa câu/điều khoản. |
| Chính sách trả hàng và hoàn tiền | SentenceChunker (`by_sentences`) | 48 | 405.6 | Giữ câu tốt, phù hợp điều kiện ngắn. |
| Chính sách trả hàng và hoàn tiền | RecursiveChunker (`recursive`) | 62 | 314.3 | Giữ cấu trúc tốt hơn nhưng tạo nhiều chunk hơn. |
| Chính sách Vận chuyển Shopee | FixedSizeChunker (`fixed_size`) | 55 | 492.2 | Độ dài ổn định, dễ kiểm soát chi phí embedding. |
| Chính sách Vận chuyển Shopee | SentenceChunker (`by_sentences`) | 64 | 375.8 | Giữ ranh giới câu, số chunk tăng. |
| Chính sách Vận chuyển Shopee | RecursiveChunker (`recursive`) | 67 | 360.6 | Chia theo separator, giữ đoạn tốt hơn fixed. |
| Điều Khoản Dịch Vụ Shopee Mall | FixedSizeChunker (`fixed_size`) | 75 | 496.9 | Nhiều chunk nhưng độ dài gần mục tiêu. |
| Điều Khoản Dịch Vụ Shopee Mall | SentenceChunker (`by_sentences`) | 56 | 595.2 | Có section/câu dài vượt kích thước mục tiêu. |
| Điều Khoản Dịch Vụ Shopee Mall | RecursiveChunker (`recursive`) | 101 | 330.5 | Nhiều chunk nhỏ hơn, giữ ngữ cảnh theo separator. |

### Chiến lược của từng thành viên

> **Đã kiểm tra lại và sửa trước khi nộp (2026-09-20):** `bench.py` bị crash ngay khi chạy vì import `HeadingChunker` nhưng lớp này chưa từng được code trong `src/chunking.py` — không phải Dũng đã "chạy xong" như bản trước ghi. Đã bổ sung `HeadingChunker` vào `src/chunking.py` (tách theo dòng heading dạng Markdown lẫn heading chữ/số của corpus Shopee, gắn lại tiêu đề khi phải hạ xuống recursive cho section dài) và export trong `src/__init__.py`. `pytest tests/ -v` vẫn 42 passed sau khi thêm.
>
> `bench/recursive.out.txt` trước đó cũng **không phải lỗi môi trường** — file có kết quả đầy đủ nhưng ở format cũ (`Hit@3` thay vì `DocHit@3/EvidenceHit@3/Score`), tức được chạy bằng bản `bench.py` cũ hơn bản hiện tại. Các số 9/10, EvidenceHit@3=5/5, MRR=0.900 ghi cho Hoàng ở bản báo cáo trước **không khớp** với file đó và đã được sửa lại đúng số liệu thật bên dưới.
>
> Artifact cuối cùng dùng cho bảng so sánh: `bench/fixed-size.out.txt`, `bench/sentences.out.txt` (embedder **OpenAI**, do Tâm/Mi chạy) và `bench/heading.out.txt`, `bench/recursive.out.txt` (embedder **local/multilingual**, chạy lại trên máy không có `OPENAI_API_KEY`). **Lưu ý:** Heading và Recursive vì vậy không cùng embedder với Fixed Size/Sentence — so sánh điểm tuyệt đối giữa 2 nhóm cần thận trọng; trước demo nên chạy lại cả 4 với cùng `--provider openai` nếu có key để công bằng tuyệt đối.

**Mi — Hải Mi**
- **Loại chiến lược:** Fixed Size (`fixed_size`, `chunk_size=500`, `overlap=50`)
- **Mô tả & lý do chọn:** Chia văn bản theo kích thước cố định, có overlap để giảm mất ngữ cảnh ở ranh giới chunk. Cách này dễ kiểm soát số chunk và chi phí embedding.

**Dũng — Trần Nguyễn Trí Dũng**
- **Loại chiến lược:** Heading/Section (`heading`, `chunk_size=500`)
- **Mô tả & lý do chọn:** Tách theo heading Markdown hoặc mục chính sách đánh số như `1.`, `1.1.`; section dài được chia tiếp và giữ lại heading để bảo toàn ngữ cảnh điều khoản. Chiến lược này đáp ứng yêu cầu riêng của biến thể L3B.

**Hoàng — Mai Huy Hoàng**
- **Loại chiến lược:** Recursive (`recursive`, `chunk_size=500`)
- **Mô tả & lý do chọn:** Thử separator theo thứ tự đoạn, dòng, câu và từ; nội dung dài tiếp tục được chia ở separator nhỏ hơn. Chiến lược này phù hợp chính sách có nhiều mục và đoạn văn dài.

**Tâm — Nguyễn Đức Tâm**
- **Loại chiến lược:** Sentence (`by_sentences`, tối đa 3 câu/chunk)
- **Mô tả & lý do chọn:** Gom các câu hoàn chỉnh để giữ điều kiện và thời hạn trong cùng chunk. Điểm yếu là câu quá dài hoặc văn bản có dấu chấm đặc biệt có thể tạo chunk vượt kích thước mong muốn.

### So Sánh Giữa Các Thành Viên

| Thành viên | Chiến lược (Strategy) | Điểm truy xuất (/10) | Điểm mạnh | Điểm yếu |
|-----------|----------|----------------------|-----------|----------|
| Mi | Fixed Size | 3 / 10 | Độ dài ổn định, pipeline đơn giản, dễ tái lập. | EvidenceHit@3=3/5, MRR=0.267, chunks=210 (OpenAI); dễ cắt rời bằng chứng khỏi câu hỏi. |
| Dũng | Heading/Section | 5 / 10 | EvidenceHit@3=4/5, MRR=0.433, chunks=265 (local); giữ tên mục cùng điều khoản, Q5 lên rank 1 với evidence chunk. | Q3 top-k đổi theo filter nhưng evidence rank không cải thiện; embedder khác nhóm Fixed/Sentence nên chưa so sánh tuyệt đối được. |
| Hoàng | Recursive | 6 / 10 | EvidenceHit@3=4/5, MRR=0.600, chunks=244 (local); giữ cấu trúc đoạn tốt, Q2 đưa evidence lên rank 2. | Q1 gold doc vào top-3 nhưng evidence không có — bằng chứng bị tách khỏi phần trả lời trực tiếp. |
| Tâm | Sentence | 7 / 10 | EvidenceHit@3=4/5, MRR=0.700, chunks=192 (OpenAI); giữ câu tự nhiên, điểm cao nhất nhóm. | Q3: top-k đổi theo filter nhưng evidence rank không cải thiện. |

**Chiến lược nào tốt nhất cho chủ đề này? Tại sao?**
> Theo số liệu đã xác minh lại trực tiếp từ các file `bench/*.out.txt`: **Sentence (Tâm) đạt điểm cao nhất, 7/10** (EvidenceHit@3=4/5, MRR=0.700), sát nút là Recursive 6/10 (EvidenceHit@3=4/5, MRR=0.600) và Heading 5/10 (EvidenceHit@3=4/5, MRR=0.433) — cả ba đều có EvidenceHit@3=4/5 nhưng khác nhau ở việc evidence xếp hạng cao hay thấp trong top-3 (đó là điều MRR đo). Fixed Size (Mi) thấp nhất, 3/10, vì cắt cứng theo ký tự dễ tách rời con số/mốc thời gian khỏi câu giải thích nó. **Lưu ý quan trọng:** Sentence/Fixed Size dùng embedder OpenAI còn Recursive/Heading dùng embedder local (do máy chạy lại không có `OPENAI_API_KEY`) — thứ hạng giữa 2 nhóm này cần chạy lại cùng backend trước khi kết luận chắc chắn "chiến lược nào thắng tuyệt đối".

**Yêu cầu Heading/Section:** `HeadingChunker` **chưa tồn tại trong codebase khi kiểm tra lại** (khiến `bench.py` crash ngay từ dòng import) — đã được bổ sung vào `src/chunking.py` (tách theo heading Markdown lẫn heading chữ/số kiểu "A. ...", "1.2. ..." của corpus Shopee; section dài hạ xuống `RecursiveChunker` và gắn lại tiêu đề vào từng mảnh con). Kết quả benchmark thật (embedder local) lưu tại `bench/heading.out.txt`. **Dũng cần xác nhận lại cách tiếp cận này có đúng ý tưởng ban đầu không, và nếu có, chạy lại bằng OpenAI để khớp embedder với phần còn lại.**

---

## 3. Câu hỏi đánh giá & Chất lượng truy xuất (Retrieval Quality) — Nhóm (10 điểm)

### Câu hỏi đánh giá & Câu trả lời chuẩn (nhóm thống nhất)

> **Đúng 5 câu hỏi**, đa dạng, có thể kiểm chứng; **ít nhất 1 câu** cần lọc metadata mới trả lời tốt. Đây là bộ câu hỏi chung cho mọi thành viên chạy.

| # | Câu hỏi (Query) | Câu trả lời chuẩn (Gold Answer) | Chunk nào chứa thông tin? |
|---|-------|-------------------------------|--------------------------|
| 1 | Người mua có bao nhiêu ngày gửi yêu cầu Trả hàng/Hoàn tiền cho đơn thường? | 15 ngày kể từ trạng thái “Giao hàng thành công”. | `shopee-quy-dinh-chung-tra-hang-hoan-tien` — mục 1.2 |
| 2 | Đơn thực phẩm tươi sống/đông lạnh thời hạn bao lâu? | Trong vòng 24 giờ. | `shopee-quy-dinh-chung-tra-hang-hoan-tien` — mục 1.2 |
| 3 | Chọn “Tự sắp xếp” thì ai trả phí trước, bao lâu được hoàn? | Người mua trả trước; Shopee hỗ trợ hoàn trong 3–5 ngày làm việc. | `shopee-phuong-thuc-gui-hang-hoan-tra` — mục 2.2 |
| 4 | Shop chưa nhận được hàng hoàn thì sau bao lâu khiếu nại được? | Sau 2 ngày kể từ khi hệ thống cập nhật người mua đã gửi hàng cho ĐVVC. | `shopee-seller-quan-ly-don-tra-hang-hoan-tien` — mục C |
| 5 | Người Bán tại Shopee Mall phải nhận lại hàng hoàn trong bao lâu? | 07 ngày làm việc kể từ quyết định cuối cùng của Shopee. | `shopee-dieu-khoan-shopee-mall` — mục 1.6 |

### Tổng hợp chất lượng truy xuất của nhóm

> Cách chấm (theo `docs/SCORING.md`): **2 điểm/câu** — top-3 chứa chunk liên quan + agent trả lời đúng (2), có liên quan nhưng thiếu/không ở top-1 (1), không có trong top-3 (0).

> Bảng dưới đây đối chiếu trực tiếp từ 4 file `bench/*.out.txt` (evidence-level rubric, không phải naive `doc_id` check).

| # | Câu hỏi | Chiến lược tốt nhất cho câu này | Có chunk liên quan trong top-3? | Ghi chú |
|---|---------|-------------------------------|-------------------------------|---------|
| 1 | Người mua có bao nhiêu ngày gửi yêu cầu Trả hàng/Hoàn tiền cho đơn thường? | **Sentence** (evidence rank 1, 2/2) | Fixed/Recursive: không; Heading: rank 3 (1/2) | Fixed Size và Recursive **không tìm được** chunk chứa "15 ngày" trong top-3 dù `doc_id` đúng vẫn lọt top-3 — đúng ví dụ "naive check thổi phồng kết quả" mà lab cảnh báo. |
| 2 | Đơn thực phẩm tươi sống/đông lạnh thời hạn bao lâu? | **Recursive** (evidence rank 1, 2/2) | Sentence: rank 2 (1/2); Heading: rank 3 (1/2); Fixed: không | Recursive giữ trọn đoạn chứa "24 giờ" ở vị trí cao nhất. |
| 3 | Chọn "Tự sắp xếp" thì ai trả phí trước, bao lâu được hoàn? *(filter `audience=buyer`)* | **Recursive** (evidence rank 2, 1/2) | Fixed: rank 3 (1/2); Sentence/Heading: không dù có filter | Câu khó nhất của cả nhóm — không chiến lược nào đạt evidence rank 1; Sentence và Heading vẫn không tìm được evidence dù đã lọc theo buyer. |
| 4 | Shop chưa nhận được hàng hoàn thì sau bao lâu khiếu nại được? *(filter `audience=seller`)* | **Sentence / Recursive** (evidence rank 1, 2/2) | Fixed/Heading: rank 2 (1/2) | Câu chứng minh rõ nhất tác dụng filter — **xem A/B bên dưới**, không filter thì mất hẳn evidence khỏi top-3 ở cả 4 chiến lược. |
| 5 | Người Bán tại Shopee Mall phải nhận lại hàng hoàn trong bao lâu? | **Sentence / Heading** (evidence rank 1, 2/2) | Fixed/Recursive: rank 2 (1/2) | Mọi chiến lược đều tìm được evidence trong top-3 — câu dễ nhất bộ 5, có thể do văn bản Điều Khoản Shopee Mall lặp lại "07 (bảy) ngày" ở 2 câu liên tiếp. |

**A/B filter — bằng chứng trực tiếp từ cả 4 chiến lược:**

| Câu | Fixed Size | Sentence | Recursive | Heading |
|---|---|---|---|---|
| Q3 (buyer) | IMPROVED | CHANGED (không cải thiện) | IMPROVED | CHANGED (không cải thiện) |
| Q4 (seller) | **IMPROVED** | **IMPROVED** | **IMPROVED** | **IMPROVED** |

**Lọc bằng metadata có giúp ích không? Ở câu hỏi nào?**
> Rất rõ ở **Q4**: cả 4/4 chiến lược đều "IMPROVED" khi bật `metadata_filter={"audience":"seller"}` — không filter, evidence chunk biến mất hoàn toàn khỏi top-3 ở mọi chiến lược vì câu hỏi "khiếu nại" trùng từ vựng với tài liệu Chính sách Vận chuyển (không liên quan). Đây là bằng chứng mạnh nhất cho câu hỏi "metadata filter có giúp ích không" trong cả bộ 5 câu. Ở Q3, filter chỉ giúp Fixed Size và Recursive (đổi thứ hạng, chưa đưa evidence lên rank 1), còn Sentence/Heading dù lọc đúng `audience=buyer` vẫn không tìm được evidence — cho thấy filter giảm nhiễu ứng viên nhưng không tự động sửa được chunk bị cắt sai ranh giới.

### Phân tích lỗi (Failure Analysis)

**Q3 — Chọn "Tự sắp xếp" thì ai trả phí trước, bao lâu được hoàn?** Đây là câu duy nhất **không chiến lược nào đạt evidence rank 1** — điểm cao nhất chỉ là Recursive ở rank 2 (1/2). Với Sentence và Heading, dù đã lọc đúng `audience=buyer`, evidence "bạn cần thanh toán trước phí trả hàng... trong vòng 3-5 ngày làm việc" vẫn không lọt top-3: câu hỏi dùng từ "Tự sắp xếp" (tên 1 trong 3 hình thức trả hàng) nhưng đoạn văn bản gốc liệt kê cả 3 hình thức trước khi nói tới điều kiện phí, nên chunk chứa đúng câu trả lời bị cạnh tranh điểm với các chunk mô tả 2 hình thức còn lại (cùng chủ đề, khác đáp án). Đề xuất sửa: giảm `chunk_size` quanh mục 2.2 để tách riêng từng hình thức trả hàng thành chunk nhỏ hơn, hoặc thử `HeadingChunker` với ngưỡng heading chi tiết hơn (bắt cả heading cấp "2.1.", "2.2.") thay vì chỉ heading cấp 1.

---

## 4. Thuyết trình (Demo) & Bài học nhóm — Nhóm (5 điểm)

**Những phân tích (insights) hay nhất nhóm sẽ trình bày:**
> - Sentence đạt điểm retrieval cao nhất (7/10) trên corpus này, sát nút là Recursive (6/10) và Heading (5/10) — cả ba đều giữ ngữ cảnh tốt hơn cắt cứng theo ký tự.
> - Fixed Size (Mi) thấp nhất (3/10) — bằng chứng đúng (con số/mốc thời gian ngắn) dễ bị cắt rời khỏi câu giải thích nó khi chunk theo ký tự cố định.
> - `HeadingChunker` ban đầu chưa được code (làm `bench.py` crash khi import) — nhóm phát hiện và bổ sung kịp trước khi nộp; đây cũng là bài học về việc phải tự chạy lại `pytest` + `bench.py` trước khi tin vào báo cáo của người khác trong nhóm.
> - Metadata filter buyer/seller giúp giảm nhiễu rõ rệt ở Q4 (không filter thì mất hẳn evidence khỏi top-3, có filter thì lên rank 2) — bằng chứng mạnh nhất cho tác dụng của metadata filter.
> - Nhóm kiểm tra exact evidence (chuỗi đáp án có thật trong top-3 không) thay vì chỉ nhìn `doc_id` — cách chấm ngây thơ theo `doc_id` sẽ thổi phồng kết quả (DocHit@3 luôn ≥ EvidenceHit@3 ở cả 4 chiến lược).

**Bài học rút ra khi so sánh trong nhóm:**
> Cùng corpus nhưng Sentence/Recursive/Heading đều vượt Fixed Size vì tôn trọng ranh giới câu/đoạn/mục thay vì cắt cứng theo ký tự — điều này đặc biệt quan trọng với văn bản chính sách có nhiều mốc thời gian ngắn nằm giữa câu dài. Heading giữ được tên mục trong từng chunk (hữu ích cho Source Traceability) nhưng vẫn thua Sentence/Recursive về điểm evidence trên bộ 5 câu này. Một bài học khác nằm ngoài phần kỹ thuật: báo cáo trước đó ghi nhận số liệu và trạng thái "đã hoàn thành" cho Heading dù code chưa tồn tại — nhắc nhóm luôn xác minh lại bằng cách chạy thật (`pytest`, `bench.py`) trước khi điền báo cáo, không tin theo lời kể.

**Nếu làm lại, nhóm sẽ thay đổi gì trong chiến lược dữ liệu (data strategy)?**
> Nhóm sẽ tách thêm các tài liệu `audience=both` thành các section buyer/seller khi nội dung cho phép, lưu exact evidence span cho từng gold answer và tinh chỉnh kích thước Heading chunks để cải thiện Q3.

---

## Tự Đánh Giá (Phần Nhóm)

| Tiêu chí | Điểm tự đánh giá |
|----------|-------------------|
| Lựa chọn tài liệu (Document Set Quality) | 10 / 10 |
| Thiết kế chiến lược (Strategy Design) | 12 / 15 *(cả 4 chiến lược đúng, khác biệt rõ; trừ điểm vì Heading ban đầu chưa được code thật, phải bổ sung khi soát lại)* |
| Chất lượng truy xuất (Retrieval Quality) | 6 / 10 *(EvidenceHit@3 trung bình 3.75/5 ~ Score trung bình 5.25/10 trên 4 chiến lược; Q4 chứng minh rõ tác dụng filter, Q3 chưa chiến lược nào đạt rank 1)* |
| Thuyết trình (Demo) | 4 / 5 |
| **Tổng phần nhóm** | **32 / 40 (tự đánh giá sau khi xác minh lại toàn bộ số liệu thật)** |
