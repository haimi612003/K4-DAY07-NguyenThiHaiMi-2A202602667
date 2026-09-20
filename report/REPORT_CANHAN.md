# Báo Cáo Cá Nhân — Lab 7: Embedding & Vector Store

**Họ tên:** Nguyễn Thị Hải Mi
**Nhóm:** THTrueMi
**Ngày:** 20/09/2026

> **Nộp 1 bản / sinh viên.** Phần nhóm (lựa chọn tài liệu, thiết kế chiến lược, bộ câu hỏi đánh giá, demo) nộp chung 1 bản trong `REPORT_NHOM.md`. Chi tiết thang điểm: `docs/SCORING.md`.

**Tổng điểm phần cá nhân: 60** = Khởi động (5) + Hướng tiếp cận (10) + Hoàn thiện code (30) + Dự đoán độ tương tự (5) + Kết quả truy xuất của tôi (10).

---

## 1. Khởi động (Warm-up) — Cá nhân (5 điểm)

### Độ tương tự Cosine (Cosine Similarity) (Bài tập 1.1)

**Độ tương tự cosine cao (High cosine similarity) nghĩa là gì?**
> Cosine similarity đo góc giữa hai vector embedding, không đo độ dài của chúng. Similarity gần 1 nghĩa là hai vector gần như cùng hướng trong không gian embedding — tức hai đoạn text được mô hình hiểu là **cùng nghĩa/cùng chủ đề**, dù có thể khác hẳn về mặt từ vựng.

**Ví dụ có độ tương tự CAO:**
- Câu A: "Người mua có thể trả lại sản phẩm trong vòng 7 ngày."
- Câu B: "Khách hàng được hoàn trả hàng hóa trong một tuần kể từ ngày nhận."
- Tại sao tương đồng: hai câu gần như không dùng chung từ vựng nào ("trả lại" vs "hoàn trả", "7 ngày" vs "một tuần") nhưng diễn đạt đúng một ý — thời hạn đổi trả — nên một embedder hiểu ngữ nghĩa tốt sẽ cho điểm cosine cao.

**Ví dụ có độ tương tự THẤP:**
- Câu A: "Chính sách bảo hành áp dụng cho người bán trên sàn."
- Câu B: "Con mèo đang ngủ trên ghế sofa."
- Tại sao khác: hai câu không liên quan gì về chủ đề lẫn ngữ nghĩa, embedding của chúng nên nằm ở hai hướng gần như độc lập trong không gian vector.

**Tại sao độ tương tự cosine (cosine similarity) được ưu tiên hơn khoảng cách Euclid (Euclidean distance) cho text embeddings?**
> Cosine chỉ quan tâm hướng của vector nên không bị ảnh hưởng bởi độ dài văn bản (câu dài thường có norm embedding lớn hơn câu ngắn dù cùng nghĩa). Euclidean distance bị lệch bởi chênh lệch độ lớn đó, nên hai câu cùng nghĩa nhưng độ dài khác nhau có thể bị đo là "xa nhau" một cách sai lệch.

### Bài toán tính toán Chunking (Bài tập 1.2)

**Tài liệu 10,000 ký tự, chunk_size=500, overlap=50. Bao nhiêu chunks?**
> *Trình bày phép tính:* `ceil((10000 − 50) / (500 − 50)) = ceil(9950 / 450) = ceil(22.11) = 23`
> *Đáp án:* **23 chunks** — kiểm lại bằng code thật: `FixedSizeChunker(chunk_size=500, overlap=50).chunk('a'*10000)` → `len(...) == 23`.

**Nếu độ chồng chéo (overlap) tăng lên 100, số lượng chunk thay đổi thế nào? Tại sao muốn độ chồng chéo nhiều hơn?**
> Tăng overlap lên 100 thì bước trượt (`chunk_size − overlap`) giảm từ 450 xuống 400, nên số chunk tăng lên **25** (kiểm bằng code: `chunk(chunk_size=500, overlap=100)` → 25). Overlap lớn hơn tốn thêm chunk (dư thừa dữ liệu) nhưng giảm rủi ro một câu/ý quan trọng bị cắt đúng vào ranh giới hai chunk — thông tin ở mép chunk vẫn xuất hiện trọn vẹn ở chunk liền kề, nên retrieval ít bị mất ngữ cảnh hơn.

---

## 2. Hướng tiếp cận của tôi (My Approach) — Cá nhân (10 điểm)

Giải thích cách tiếp cận của bạn khi lập trình (implement) các phần chính trong gói `src`.

### Các hàm chia nhỏ (Chunking Functions)

**`SentenceChunker.chunk`** — hướng tiếp cận:
> Dùng `re.split(r"(?<=[.!?])\s+", text.strip())` — lookbehind `(?<=[.!?])` chỉ cắt *sau* dấu câu nên dấu `.`/`!`/`?` không bị nuốt mất như khi split bằng `[.!?]\s+` thông thường. Các câu được gom theo nhóm `max_sentences_per_chunk`, mỗi chunk được `strip()` lại. Edge case: text rỗng trả về `[]` ngay từ đầu, tránh crash; edge case **chưa** xử lý được là viết tắt (`TS.`, `v.v.`) hay số thập phân (`3.14`) sẽ bị hiểu nhầm là ranh giới câu và cắt sai.

**`RecursiveChunker.chunk` / `_split`** — hướng tiếp cận:
> Thuật toán thử lần lượt các separator theo độ ưu tiên `["\n\n", "\n", ". ", " ", ""]`. Có 3 base case: text rỗng → `[]`; text đã ngắn hơn `chunk_size` → trả nguyên văn; hết separator (hoặc gặp separator rỗng `""`) → cắt cứng theo `chunk_size`. Thuật toán có hai chiều: **đệ quy xuống** — mảnh nào sau khi split vẫn dài hơn `chunk_size` thì gọi lại `_split` với danh sách separator còn lại; **gom lên** — các mảnh nhỏ liền kề được nối lại (kèm separator) cho tới sát `chunk_size`, tránh sinh ra hàng trăm chunk vụn khi văn bản có nhiều dòng ngắn.

### Lớp EmbeddingStore

**`add_documents` + `search`** — hướng tiếp cận:
> `add_documents` chỉ dùng in-memory (bỏ hẳn nhánh ChromaDB vì `self._use_chroma` bị set `True` trước khi client tồn tại — một cái bẫy đã biết trong code gốc). Mỗi `Document` được chuẩn hoá thành 1 record qua `_make_record`: copy metadata (không dùng trực tiếp object của người gọi) và đảm bảo luôn có `metadata['doc_id']` (mặc định = `doc.id` nếu người gọi chưa cung cấp) để `delete_document` hoạt động đúng. `search` gọi `_search_records`, tính similarity bằng dot product giữa embedding của query và embedding của từng record — vì `MockEmbedder` trả vector đã chuẩn hoá (`||v||=1`) nên dot product đúng bằng cosine, không cần chia lại cho norm. Kết quả được sort giảm dần theo score và cắt `top_k`, bỏ field `embedding` khỏi output để không làm bẩn kết quả in ra.

**`search_with_filter` + `delete_document`** — hướng tiếp cận:
> `search_with_filter` lọc theo `metadata_filter` **trước**, sau đó mới gọi `_search_records` trên tập đã lọc — dùng chung code với `search` nên không thể có kết quả lệch nhau. Lọc trước quan trọng vì nếu lấy top-k rồi mới loại bỏ, k slot có thể đã bị tài liệu sai đối tượng chiếm hết, dẫn tới trả về rỗng dù store vẫn còn tài liệu hợp lệ. `delete_document` duyệt toàn bộ store, giữ lại record có `metadata['doc_id'] != doc_id`, trả `True` nếu kích thước giảm (có xoá) và `False` nếu không tìm thấy gì để xoá.

### Tác tử KnowledgeBaseAgent

**`answer`** — hướng tiếp cận:
> `__init__` chỉ lưu tham chiếu `store` và `llm_fn`. `answer` gồm 3 nhịp: (1) nếu store rỗng trả thông báo cố định, không gọi LLM; (2) lấy top-k chunk qua `store.search`, đánh số `[1] [2] [3]` kèm nguồn (`doc_id`) cho từng chunk để câu trả lời có thể truy vết ngược lại đúng tài liệu; (3) dựng prompt yêu cầu model **chỉ** dùng ngữ cảnh được cung cấp, trích dẫn số `[n]` khi dùng thông tin, và nói rõ "không tìm thấy" nếu ngữ cảnh không đủ — đây là ràng buộc chống bịa thông tin (hallucination).

---

## 3. Hoàn thiện code (Core Implementation) — Cá nhân (30 điểm)

Vượt qua bộ kiểm thử là điều kiện tính điểm phần này.

### Kết Quả Kiểm Thử (Test Results)

```
============================= test session starts ==============================
platform darwin -- Python 3.13.13, pytest-9.1.1, pluggy-1.6.0
collected 42 items

tests/test_solution.py::TestProjectStructure::test_root_main_entrypoint_exists PASSED
tests/test_solution.py::TestProjectStructure::test_src_package_exists PASSED
tests/test_solution.py::TestClassBasedInterfaces::test_chunker_classes_exist PASSED
tests/test_solution.py::TestClassBasedInterfaces::test_mock_embedder_exists PASSED
tests/test_solution.py::TestFixedSizeChunker::test_chunks_respect_size PASSED
tests/test_solution.py::TestFixedSizeChunker::test_correct_number_of_chunks_no_overlap PASSED
tests/test_solution.py::TestFixedSizeChunker::test_empty_text_returns_empty_list PASSED
tests/test_solution.py::TestFixedSizeChunker::test_no_overlap_no_shared_content PASSED
tests/test_solution.py::TestFixedSizeChunker::test_overlap_creates_shared_content PASSED
tests/test_solution.py::TestFixedSizeChunker::test_returns_list PASSED
tests/test_solution.py::TestFixedSizeChunker::test_single_chunk_if_text_shorter PASSED
tests/test_solution.py::TestSentenceChunker::test_chunks_are_strings PASSED
tests/test_solution.py::TestSentenceChunker::test_respects_max_sentences PASSED
tests/test_solution.py::TestSentenceChunker::test_returns_list PASSED
tests/test_solution.py::TestSentenceChunker::test_single_sentence_max_gives_many_chunks PASSED
tests/test_solution.py::TestRecursiveChunker::test_chunks_within_size_when_possible PASSED
tests/test_solution.py::TestRecursiveChunker::test_empty_separators_falls_back_gracefully PASSED
tests/test_solution.py::TestRecursiveChunker::test_handles_double_newline_separator PASSED
tests/test_solution.py::TestRecursiveChunker::test_returns_list PASSED
tests/test_solution.py::TestEmbeddingStore::test_add_documents_increases_size PASSED
tests/test_solution.py::TestEmbeddingStore::test_add_more_increases_further PASSED
tests/test_solution.py::TestEmbeddingStore::test_initial_size_is_zero PASSED
tests/test_solution.py::TestEmbeddingStore::test_search_results_have_content_key PASSED
tests/test_solution.py::TestEmbeddingStore::test_search_results_have_score_key PASSED
tests/test_solution.py::TestEmbeddingStore::test_search_results_sorted_by_score_descending PASSED
tests/test_solution.py::TestEmbeddingStore::test_search_returns_at_most_top_k PASSED
tests/test_solution.py::TestEmbeddingStore::test_search_returns_list PASSED
tests/test_solution.py::TestKnowledgeBaseAgent::test_answer_non_empty PASSED
tests/test_solution.py::TestKnowledgeBaseAgent::test_answer_returns_string PASSED
tests/test_solution.py::TestComputeSimilarity::test_identical_vectors_return_1 PASSED
tests/test_solution.py::TestComputeSimilarity::test_opposite_vectors_return_minus_1 PASSED
tests/test_solution.py::TestComputeSimilarity::test_orthogonal_vectors_return_0 PASSED
tests/test_solution.py::TestComputeSimilarity::test_zero_vector_returns_0 PASSED
tests/test_solution.py::TestCompareChunkingStrategies::test_counts_are_positive PASSED
tests/test_solution.py::TestCompareChunkingStrategies::test_each_strategy_has_count_and_avg_length PASSED
tests/test_solution.py::TestCompareChunkingStrategies::test_returns_three_strategies PASSED
tests/test_solution.py::TestEmbeddingStoreSearchWithFilter::test_filter_by_department PASSED
tests/test_solution.py::TestEmbeddingStoreSearchWithFilter::test_no_filter_returns_all_candidates PASSED
tests/test_solution.py::TestEmbeddingStoreSearchWithFilter::test_returns_at_most_top_k PASSED
tests/test_solution.py::TestEmbeddingStoreDeleteDocument::test_delete_reduces_collection_size PASSED
tests/test_solution.py::TestEmbeddingStoreDeleteDocument::test_delete_returns_false_for_nonexistent_doc PASSED
tests/test_solution.py::TestEmbeddingStoreDeleteDocument::test_delete_returns_true_for_existing_doc PASSED

============================== 42 passed in 0.02s ==============================
```

**Số lượng bài test vượt qua (pass):** 42 / 42

---

## 4. Dự đoán độ tương tự (Similarity Predictions) — Cá nhân (5 điểm)

| Cặp | Câu A | Câu B | Dự đoán | Điểm thực tế | Đúng? |
|------|-----------|-----------|---------|--------------|-------|
| 1 | "Người mua có thể trả lại sản phẩm trong vòng 7 ngày." | "Khách hàng được hoàn trả hàng hóa trong một tuần kể từ ngày nhận." | cao | 0.0862 | Có (tương đối) |
| 2 | "Python is a high-level programming language." | "Python là một ngôn ngữ lập trình bậc cao." | cao | 0.1246 | Có (tương đối) |
| 3 | "Chính sách bảo hành áp dụng cho người bán trên sàn." | "Con mèo đang ngủ trên ghế sofa." | thấp | 0.0139 | Có (tương đối) |
| 4 | "Vector store lưu trữ embedding để tìm kiếm tương đồng." | "Hôm nay trời mưa to ở Hà Nội." | thấp | 0.0355 | Có (tương đối) |
| 5 | "Chunking chia nhỏ văn bản thành nhiều đoạn nhỏ hơn." | "Chunking splits a long document into smaller pieces." | cao | 0.0878 | Có (tương đối) |

> Đo bằng `_mock_embed` (`EMBEDDING_PROVIDER` chưa bật backend thật) nên các con số phía trên **không phản ánh ngữ nghĩa thật** — `MockEmbedder` chỉ băm MD5 chuỗi ký tự rồi sinh vector giả ngẫu nhiên, hoàn toàn không "hiểu" nghĩa câu. Thứ tự cao/thấp ở bảng trên khớp với dự đoán chỉ là trùng hợp ngẫu nhiên qua thang so sánh tương đối (0.07 là mốc tôi tự chọn để chia "cao/thấp" trong tập 5 cặp này), **không phải** bằng chứng cho thấy cosine similarity hoạt động đúng. Cần bật embedder thật (`EMBEDDING_PROVIDER=local/openai/gemini`, xem Phụ lục B) để bảng này có ý nghĩa thật sự.

**Kết quả nào bất ngờ nhất? Điều này nói gì về cách embeddings biểu diễn ý nghĩa?**
> Bất ngờ nhất là cặp 1 và 2 (đồng nghĩa, khác từ vựng hoàn toàn, kể cả khác ngôn ngữ ở cặp 2) vẫn ra điểm số cao hơn các cặp không liên quan — dù đúng là do MockEmbedder không có ngữ nghĩa nên đây chỉ là trùng hợp. Điều này minh hoạ đúng lý do cả lab nhấn mạnh: **phải bật embedder thật** thì mới đo được liệu mô hình có thực sự "hiểu" hai câu khác từ nhưng cùng nghĩa là gần nhau hay không — bản thân công thức cosine đúng không có nghĩa là kết quả đúng, chất lượng phụ thuộc hoàn toàn vào embedder phía dưới.

---

## 5. Kết quả truy xuất của tôi (Competition Results) — Cá nhân (10 điểm)

Chạy **5 câu hỏi đánh giá của nhóm** trên mã nguồn cá nhân của bạn trong gói `src`. **5 câu hỏi này phải trùng với các thành viên cùng nhóm** (xem `REPORT_NHOM.md`).

Chiến lược cá nhân: **`FixedSizeChunker`** (`chunk_size=500`, `overlap=50`) — 210 chunk từ 6 tài liệu. Embedder: **OpenAI** (`text-embedding-3-small`). Chấm theo 2 mức đúng `docs/SCORING.md`: không chỉ kiểm `doc_id` gold có ở top-3 (**DocHit@3 = 5/5** — thổi phồng nếu dừng ở đây), mà kiểm chuỗi bằng chứng thật có nằm trong nội dung top-3 không (**EvidenceHit@3 = 3/5**). Full log: `ket_qua_benchmark.txt`.

| # | Câu hỏi (Query) | Top-1 Chunk truy xuất được (tóm tắt) | Điểm Score | Có liên quan không? (Relevant) | Câu trả lời của Agent (tóm tắt) |
|---|-------|--------------------------------|-------|-----------|------------------------|
| 1 | Người mua có bao nhiêu ngày gửi yêu cầu Trả hàng/Hoàn tiền cho đơn thường? | `shopee-phuong-thuc-gui-hang-hoan-tra#0` (score 0.612) — sai chủ đề (nói về cách gửi hàng, không có mốc 15 ngày) | 0/2 | Không — gold doc lọt top-3 (rank 2) nhưng đúng chunk chứa "15 ngày" thì **không** vào top-3 | Không đủ căn cứ trả lời đúng — ngữ cảnh top-3 thiếu số liệu 15 ngày |
| 2 | Đơn thực phẩm tươi sống/đông lạnh thời hạn bao lâu? | `shopee-chinh-sach-van-chuyen#9` (score 0.545) — nói về hàng dễ vỡ, không phải thời hạn trả hàng | 0/2 | Không — cùng lỗi: gold doc ở top-3 (rank 2) nhưng chunk chứa "24 giờ" không lọt top-3 | Không đủ căn cứ — ngữ cảnh không có mốc 24 giờ |
| 3 | Chọn "Tự sắp xếp" thì ai trả phí trước, bao lâu được hoàn? | *(có filter `audience=buyer`)* `shopee-quy-dinh-chung-tra-hang-hoan-tien#2` (score 0.507) — không khớp, nhưng rank 3 đúng chunk `phuong-thuc-gui-hang-hoan-tra#8` chứa "3-5 ngày làm việc" | 1/2 | Có, nhưng chỉ ở rank 3 (không phải top-1) | Có thể trả lời đúng nếu agent đọc hết 3 đoạn, nhưng bằng chứng xếp hạng thấp |
| 4 | Shop chưa nhận được hàng hoàn thì sau bao lâu khiếu nại được? | *(có filter `audience=seller`)* `shopee-seller-quan-ly-don-tra-hang-hoan-tien#4` (score 0.597) — cùng tài liệu nhưng sai đoạn; rank 2 mới đúng chunk chứa "Sau 2 ngày" | 1/2 | Có, ở rank 2 | Trả lời được nếu agent đọc tới đoạn rank 2 |
| 5 | Người Bán tại Shopee Mall phải nhận lại hàng hoàn trong bao lâu? | `shopee-dieu-khoan-shopee-mall#31` (score 0.715) — nói về khiếu nại, sai đoạn; rank 2 mới đúng chunk chứa "07 (bảy) ngày làm việc" | 1/2 | Có, ở rank 2 | Trả lời được nếu agent đọc tới đoạn rank 2 |

**Tổng điểm rubric (2đ nếu gold ở top-1 và có evidence, 1đ nếu evidence ở top-2/3, 0đ nếu vắng):** **3/10**

**Bao nhiêu câu hỏi trả về chunk có liên quan trong top-3?** 3 / 5 *(tính theo evidence thật trong nội dung, không tính theo `doc_id`)*

**Điều hay nhất tôi học được từ thành viên khác / nhóm khác (qua demo):**
> Cả 3 chiến lược còn lại của nhóm đều vượt Fixed Size của tôi: Sentence (Tâm) cao nhất — EvidenceHit@3=4/5, Score=7/10, MRR=0.700 — rồi đến Recursive (Hoàng) 4/5, 6/10, MRR=0.600, và Heading (Dũng) 4/5, 5/10, MRR=0.433. Fixed Size của tôi thấp nhất: 3/5, 3/10, MRR=0.267. Khác biệt chính: Fixed Size cắt cứng theo ký tự nên câu trả lời (một con số/mốc thời gian ngắn) dễ bị tách khỏi phần văn bản giải thích nó, còn 3 chiến lược kia đều tôn trọng ranh giới câu/đoạn/mục nên giữ được cặp "điều kiện – con số" trong cùng một chunk. Bài học: với văn bản pháp lý/chính sách có nhiều mốc thời gian ngắn nằm giữa câu dài, chunking cố định theo ký tự là lựa chọn yếu nhất trong 4 chiến lược nhóm đã thử. (Lưu ý: Sentence/Fixed Size đo bằng OpenAI embedding, Recursive/Heading đo lại bằng embedder local do máy không có `OPENAI_API_KEY` khi kiểm tra lại — xem ghi chú trong `REPORT_NHOM.md` mục 2.)

---

## Tự Đánh Giá (Phần Cá Nhân)

| Tiêu chí | Điểm tự đánh giá |
|----------|-------------------|
| Khởi động (Warm-up) | 5 / 5 |
| Hướng tiếp cận của tôi (My Approach) | 10 / 10 |
| Hoàn thiện code (Core Implementation — tests) | 30 / 30 |
| Dự đoán độ tương tự (Similarity Predictions) | 5 / 5 |
| Kết quả truy xuất của tôi (Competition Results) | 3 / 10 *(EvidenceHit@3=3/5 với `FixedSizeChunker`, xem `ket_qua_benchmark.txt`)* |
| **Tổng phần cá nhân** | **53 / 60** |
