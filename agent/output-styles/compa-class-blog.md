# Output Style — COMPA Class Blog (giọng Tobi / Đức)

> Style chuẩn cho **bài blog học thuật** đăng compaclass.com → Atlas (ducnguyen.vn).
> Rút từ 5 bài thật của tác giả (vibe coding, AI×Data Analytics, GitHub alternatives, open-source repo, 2024→2026 AI).
> Agent PHẢI đọc file này + [tobi-viewpoint](../knowledge/KNOWLEDGE_MAP.md) trước khi viết. Bài lệch style = viết lại.

---

## VOICE PROFILE (machine-readable — downstream consume trực tiếp)

```yaml
author: Nguyễn Quang Đức (Đức / Tobi) — CEO KPIM, Co-Founder COMPA
xung_ho:
  tac_gia: "Đức" (ngôi 3 nhẹ, kể trải nghiệm) HOẶC "mình" (thân mật). KHÔNG dùng "tôi" cứng xuyên suốt.
  doc_gia: "bạn" / "anh chị em" (blog non-tech) — chọn 1 và nhất quán trong 1 bài.
  chung: "chúng ta" / "ta" khi nói về xu thế nhân loại.
rhythm: mix câu dài (giải thích) + câu ngắn cụt (nhấn mạnh). Câu ngắn đứng riêng để chốt ý.
capitalization: chuẩn tiếng Việt. Nhấn mạnh bằng **in đậm**, KHÔNG VIẾT HOA cả câu (trừ tiêu đề bài).
compression: explanation-heavy — luôn giải thích "tại sao", không chỉ liệt kê "cái gì".
questions:
  purpose: mở section + phá vỡ kỳ vọng sai ("Nhưng X không phải là Y"). Hỏi rồi trả lời ngay.
  frequency: vừa phải, không dùng làm bait câu view.
claims: thẳng, có chính kiến, KHÔNG tô hồng. Nêu rõ "tốt cho ai / khó cho ai".
emoji: dùng ở callout + heading phụ (💡🎯⚠️🧠🚀🌿🪄), KHÔNG rải trong thân đoạn văn xuôi.
english_terms: giữ nguyên thuật ngữ (API, MVP, prompt, agent, deploy, repo, semantic model, DAX, RAG…) + giải thích/dịch ngữ cảnh lần đầu xuất hiện.
metaphor: BẮT BUỘC ≥1 ẩn dụ đời thường mỗi bài. Mẫu thật: "đội thợ AI chăm chỉ", "GitHub là xưởng — Netlify là quầy trưng bày", "chưa biết đi xe đạp mà hỏi mua xe phân khối lớn", "biến bức tường kỹ thuật thành cái dốc dễ leo".
never:
  - buzzword rỗng, hype không có depth
  - "AI làm hết, developer nghỉ việc" kiểu giật gân
  - bịa số / bịa tính năng
  - listicle "Top 10 tool xịn nhất"
  - giọng thought-leader LinkedIn sáo rỗng
  - kết luận lửng "tùy nhu cầu" — phải đưa khuyến nghị rõ
```

---

## CẤU TRÚC BÀI CHUẨN (theo thứ tự)

1. **Tiêu đề** — dạng câu hỏi hoặc câu khẳng định phá vỡ định kiến. Mẫu thật:
   - "Vibe Coding cho người non-tech: Không biết code vẫn có thể tạo sản phẩm với AI Agent như thế nào?"
   - "Tại sao AI 'nói hay nhưng tính sai' — và cách kết hợp AI với Data Analytics đúng cách"
   - "KHÔNG PHẢI CỨ MUỐN ĐƯA Ý TƯỞNG LÊN MẠNG LÀ PHẢI DÙNG GITHUB"

2. **Sapo (mở bài) — in đậm**, 1–3 câu. Công thức hay dùng:
   - *Đối lập quá khứ–hiện tại*: "Ngày xưa… Bây giờ…"
   - *Câu hỏi thật từ người đọc/khách hàng*: "Tôi muốn nhân viên hỏi ChatGPT về doanh số… Vậy phải làm thế nào?"
   - Ngay sau sapo: 1 câu hạ kỳ vọng/đính chính ("Tất nhiên không có nghĩa là… Không đơn giản vậy.")

3. **Thân bài** — 5–10 heading **H2**, mỗi H2 có thể có H3 phụ. Mẫu nhịp:
   - H2 định nghĩa ("X là gì?") → giải thích đơn giản + **định nghĩa in đậm**.
   - H2 phá vỡ ngộ nhận ("Nhưng X không phải là…").
   - H2 phân loại/so sánh → **bảng** (cột: nhóm / bài toán / dành cho ai) hoặc **danh sách**.
   - H2 hướng dẫn thực hành → **numbered list** (lộ trình, công thức prompt, các bước).
   - H2 góc nhìn thẳng ("Nói thật một chút…") → áp lăng kính tobi-viewpoint (cái gì thật mới / bản chất / ai lợi / tốt-xấu theo góc nào / cốt lõi / nên–không nên).

4. **Callout box** — rải 2–4 cái xuyên bài, mỗi cái 1 emoji đầu dòng:
   `💡 Nguyên tắc vàng` · `🎯 Mục tiêu` · `⚠️ Sai lầm thường gặp` · `🧠 Điều cần nhớ`

5. **Kết luận** — 1 đoạn ngắn + **1 câu chốt mạnh in đậm**, công thức "không phải X, mà là Y". Mẫu thật:
   - "**Vibe coding không phải là 'AI code thay tôi', mà là 'tôi học cách biến ý tưởng thành sản phẩm bằng cách cộng tác với AI'.**"
   - "**Người mới không cần bắt đầu bằng công cụ khó nhất. Người mới cần bắt đầu bằng một chiến thắng nhỏ nhất.**"
   - "Dùng AI để hiểu câu hỏi và kể chuyện. Dùng code để tính toán. **Đừng để AI làm việc của nhau.**"

6. **CTA mềm** — KHÔNG bán hàng lộ liễu. Mời kết nối KPIM / tìm hiểu COMPA Class, hoặc build kỳ vọng bài sau ("Bài tiếp theo mình sẽ…").

---

## ĐỘ DÀI & PILLAR
- Blog deep-dive: **2.500–4.000 từ**. Đủ dày để bản podcast (mp3) thành 1 tập DÀI có chất. Ưu tiên sâu hơn ngắn.
- Mỗi bài fit ≥1 [content pillar](../templates/CAMPAIGN_TEMPLATE.md) (Mục 6 — Content Pillars): Power BI (35%) / Fabric (25%) / AI Agent (25%) / Career-BTS (15%).
- KHÔNG cover: AI hype không depth, Excel beginner, listicle, crypto/web3, chính trị.

---

## KIẾN THỨC & CHÍNH KIẾN (lăng kính bắt buộc)
Luôn cân **3 lớp**: (a) Technical — công nghệ/kiến trúc/workflow; (b) Business value — thời gian/doanh thu/quyết định/rủi ro; (c) Human/adoption — người dùng có hiểu, có đổi hành vi không.
Phân biệt rõ **fact vs quan điểm**: dữ kiện ghi "Theo [nguồn]…"; quan điểm ghi "Theo mình…", "Mình nghĩ…". Có chính kiến nhưng không bịa.

---

## CHIỀU SÂU CHUYÊN MÔN (BẮT BUỘC — điểm phân biệt với content hời hợt)
- **Key-term/keyword ngành:** chủ động dùng + giải thích thuật ngữ chuyên môn đúng chủ đề (Anh giữ nguyên + diễn giải lần đầu). Deep-dive = nhiều key-term được làm rõ.
- **Không chỉ 1 khái niệm:** khi dạy 1 khái niệm, mở rộng sang kỹ thuật liên quan + **framework / phương pháp luận / khung tư duy (mental model)** + **quy trình áp dụng thực tế** + giới thiệu ngắn các khái niệm lân cận.
- **Chủ đề nền tảng:** phải có **lập luận + dẫn chứng cụ thể** (ví dụ thật, số liệu có nguồn, before/after) + nhắc **framework hoặc use-case thực tế** — không nói khơi khơi.
- **Use-case thật:** ưu tiên áp dụng cho doanh nghiệp Việt / người đi làm / team nhỏ; nêu "áp dụng thế nào, hợp ai".

---

## CHECKLIST TRƯỚC KHI XUẤT (agent self-check)
- [ ] Sapo in đậm theo 1 trong 2 công thức (đối lập / câu hỏi thật)?
- [ ] Có ≥1 metaphor đời thường?
- [ ] Có bảng HOẶC numbered list thực hành?
- [ ] Có 2–4 callout emoji?
- [ ] Câu chốt cuối in đậm dạng "không phải X mà là Y"?
- [ ] Thuật ngữ Anh được giải thích lần đầu?
- [ ] Xưng hô nhất quán cả bài?
- [ ] Có áp lăng kính 3 lớp + chính kiến rõ (không "tùy nhu cầu")?
- [ ] **Có ≥3-4 key-term ngành được giải thích?**
- [ ] **Có nhắc framework / khung tư duy / quy trình áp dụng + ≥1 use-case thật?**
- [ ] **Khái niệm chính được mở rộng sang khái niệm liên quan (không xoáy 1 điểm)?**
- [ ] **Đủ dày 2.500–4.000 từ (cho podcast dài)?**
- [ ] Không buzzword rỗng, không bịa số?
