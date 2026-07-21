# Prompt — đề xuất chủ đề cho chiến dịch

Dùng ở stage `topics`.

---

Bạn đề xuất chủ đề cho chiến dịch **{{CAMPAIGN_NAME}}** của kênh {{BRAND_NAME}}.

## Bối cảnh

- Big idea: {{BIG_IDEA}}
- Mục tiêu: {{OBJECTIVE}}
- Persona chính: {{PERSONA}}
- Pillar được phép: {{PILLARS}} (tỷ trọng mục tiêu: {{PILLAR_SHARES}})
- KPI chính: {{PRIMARY_KPI}}
- Khoảng thời gian: {{START_DATE}} → {{END_DATE}}
- Số asset cần: {{NUM_ASSETS}}

## Đã có, KHÔNG đề xuất trùng

{{PRIOR_TOPICS}}

## Luật

1. **Pillar gate.** Chủ đề không map được vào pillar nào ở trên thì loại. Không có ngoại lệ.
2. **Chấm TOS trước.** Công thức và ngưỡng ở `agent/knowledge/SCORING.md`.
   **TOS < 2.5 thì không đề xuất** — thà đưa 6 chủ đề tốt còn hơn 15 chủ đề cho đủ số.
   Nếu không đủ chủ đề đạt ngưỡng, nói thẳng là chỉ có N chủ đề đạt.
3. **Chấm HRS.** ≥3 thì ghi rõ và nêu cần nguồn sơ cấp nào trước khi sản xuất.
4. **Mỗi asset một chức năng riêng** (`function_role`). Xem cây atomization trong
   `MULTICHANNEL_MATRIX.md`. Hai asset cùng hook + cùng luận điểm = một cái thừa.
5. **Tôn trọng tỷ trọng pillar.** Lệch quá nhiều so `target_share` thì nêu rõ và giải thích.

## Định dạng trả về

JSON array, mỗi phần tử một asset:

```json
[
  {
    "title_draft": "",
    "angle": "góc tiếp cận, 1 câu — khác gì cách nói thông thường",
    "pillar_primary": "",
    "pillar_secondary": "",
    "format": "long_video | short | fb_post | fb_reel | yt_community",
    "platform": "youtube | facebook",
    "funnel_stage": "discovery | packaging | consumption | engagement | conversion | retention | business",
    "function_role": "vai trò riêng của asset này trong chiến dịch",
    "persona_target": "",
    "planned_publish_date": "YYYY-MM-DD",
    "cta_type": "",
    "tos_score": 0.0,
    "tos_breakdown": {"R":0,"T":0,"I":0,"O":0,"E":0,"S":0,"B":0},
    "hrs_score": 0.0,
    "detail_prompt": "yêu cầu riêng khi viết asset này — sẽ đưa vào prompt content-write",
    "evidence_needed": ["nguồn sơ cấp cần tìm trước khi sản xuất"]
  }
]
```

Sau JSON, viết ngắn:
- Chủ đề nào bạn đã **loại** và vì sao (TOS thấp / trùng / ngoài pillar).
- Chỗ nào bạn không chắc và cần người quyết.

Đừng làm tròn điểm cho đủ ngưỡng. Điểm thấp là thông tin có ích.
