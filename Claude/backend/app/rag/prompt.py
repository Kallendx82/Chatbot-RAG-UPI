"""Grounded prompt construction.

Strict grounding: model must answer ONLY from the retrieved context, must
admit when info is absent, and must cite sources. Supports auto-detected
Indonesian / English replies.
"""
from __future__ import annotations

import re
from typing import Any

# Indonesian function words - strong signal the user is writing Indonesian.
_ID_MARKERS = set(
    "apa apakah bagaimana berapa kapan dimana siapa mengapa yang di ke dari "
    "dan atau saya kami kita anda mereka itu ini saja juga sudah belum tidak "
    "bisa harus boleh akan untuk dengan pada oleh dalam tentang seperti "
    "adalah berapakah dimanakah kapankah".split()
)
# English markers
_EN_MARKERS = set(
    "what when where how why who which does do is are was were the of a an "
    "in on at to from for with by about can could should would will i my we "
    "you your they their it its".split()
)


def detect_language(text: str) -> str:
    """Return 'en' or 'id' based on a simple word-frequency heuristic.

    Default: 'id' (Indonesian) - the chatbot serves UPI's community.
    Tie / very short queries also default to Indonesian.
    """
    if not text:
        return "id"
    words = re.findall(r"[A-Za-z]+", text.lower())
    id_hits = sum(1 for w in words if w in _ID_MARKERS)
    en_hits = sum(1 for w in words if w in _EN_MARKERS)
    if en_hits > id_hits and en_hits >= 1:
        return "en"
    return "id"


SYSTEM_PROMPT_ID = (
    "Anda adalah asisten informasi resmi Universitas Pendidikan Indonesia "
    "(UPI). Anda HARUS menjawab dalam Bahasa Indonesia yang baku.\n\n"
    "ATURAN KETAT (WAJIB DITAATI):\n"
    "1. Jawab HANYA dari SUMBER bernomor di bawah. Setiap fakta wajib "
    "diikuti nomor sumber dalam kurung siku: [1], [2], dst. Jika satu "
    "kalimat didukung beberapa sumber, tulis [1][3].\n"
    "2. JANGAN gunakan pengetahuan umum di luar SUMBER. JANGAN menebak. "
    "JANGAN melengkapi dengan informasi yang 'masuk akal' jika tidak "
    "tertulis di SUMBER.\n"
    "3. Jika SUMBER tidak memuat jawaban, balas persis: \"Maaf, informasi "
    "tersebut tidak tersedia dalam dokumen yang saya miliki saat ini. "
    "Anda dapat menanyakan langsung ke unit terkait di UPI.\"\n"
    "4. Jika SUMBER memuat tabel angka (mis. biaya, jadwal, kuota), "
    "tampilkan kembali dalam tabel Markdown yang rapi sebelum menyimpulkan.\n"
    "5. Tetap setia pada fakta. Jangan menyalin kalimat panjang dari "
    "sumber; ringkas dengan kata Anda sendiri.\n"
    "6. Pertanyaan lanjutan (mis. 'Kapan tepatnya?', 'Berapa biayanya?') "
    "WAJIB dijawab dengan SUMBER yang relevan dengan pertanyaan TERAKHIR, "
    "bukan informasi acak.\n\n"
    "CONTOH:\n"
    "Pertanyaan: 'Berapa biaya seleksi Magister?'\n"
    "SUMBER [3]: 'Biaya pendaftaran Program Magister (S2) adalah "
    "Rp 750.000 per peserta.'\n"
    "Jawaban yang BENAR: Biaya pendaftaran seleksi Program Magister (S2) "
    "UPI adalah Rp 750.000 per peserta [3]. Catatan: ini adalah biaya "
    "seleksi/pendaftaran, bukan biaya kuliah per semester [3].\n"
)

SYSTEM_PROMPT_EN = (
    "You are the official information assistant of Universitas Pendidikan "
    "Indonesia (UPI). You MUST answer in clear, professional English.\n\n"
    "STRICT RULES (NON-NEGOTIABLE):\n"
    "1. Answer ONLY from the numbered SOURCES below. After EVERY factual "
    "sentence append the source number in brackets like [1] or [2]. If "
    "multiple sources support one sentence, cite them all: [1][3].\n"
    "2. DO NOT use general knowledge beyond the SOURCES. DO NOT guess. "
    "DO NOT fill gaps with 'reasonable-sounding' information that is not "
    "in the SOURCES.\n"
    "3. If the SOURCES do not contain the answer, reply exactly: "
    "\"Sorry, that information is not available in the documents I "
    "currently have. You may want to ask the relevant UPI office "
    "directly.\"\n"
    "4. If the SOURCES contain a table of numbers (e.g. fees, schedule, "
    "quotas), reproduce a clean Markdown table before concluding.\n"
    "5. Stay faithful to facts. Do not copy long sentences verbatim; "
    "summarise in your own words.\n"
    "6. Follow-up questions (e.g. 'When exactly?', 'How much?') MUST be "
    "answered using SOURCES relevant to the MOST RECENT question, not "
    "random unrelated material.\n\n"
    "EXAMPLE:\n"
    "Question: 'How much is the Magister registration fee?'\n"
    "SOURCE [3]: 'The registration fee for the Master program is "
    "Rp 750,000 per applicant.'\n"
    "Correct answer: The registration fee for UPI Master (S2) program is "
    "Rp 750,000 per applicant [3]. Note: this is the application/selection "
    "fee, NOT the per-semester tuition [3].\n"
)


def system_prompt(language: str = "id") -> str:
    return SYSTEM_PROMPT_EN if language == "en" else SYSTEM_PROMPT_ID


def _is_low_content(text: str) -> bool:
    """True if a chunk is mostly digits / punctuation (e.g. corrupted table).

    These chunks hurt the LLM - they get high embedding similarity but contain
    no semantically extractable answer.
    """
    if not text or len(text) < 60:
        return True
    letters = sum(1 for c in text if c.isalpha())
    if letters / len(text) < 0.35:   # < 35% letters -> noisy table dump
        return True
    return False


def format_context(chunks: list[dict[str, Any]]) -> str:
    """Render retrieved chunks as numbered SUMBER blocks. Skip low-content chunks."""
    usable = [c for c in chunks if not _is_low_content(c.get("text", ""))]
    if not usable:
        return "(tidak ada konteks yang dapat dibaca / no readable context)"
    blocks: list[str] = []
    for i, c in enumerate(usable, start=1):
        ref = c.get("title", "Dokumen tanpa judul")
        page = c.get("page")
        if page is not None:
            ref += f", hal. {page}"
        section = c.get("section")
        if section:
            ref += f", bagian: {section}"
        blocks.append(f"[{i}] {ref}\n{c.get('text', '').strip()}")
    return "\n\n".join(blocks)


def build_prompt(
    query: str,
    chunks: list[dict[str, Any]],
    language: str = "id",
) -> str:
    """Full grounded prompt: system rules + numbered context + question."""
    context = format_context(chunks)
    q_label = "PERTANYAAN" if language != "en" else "QUESTION"
    a_label = "JAWABAN" if language != "en" else "ANSWER"
    return (
        f"{system_prompt(language)}\n"
        f"=== SUMBER / SOURCES ===\n{context}\n\n"
        f"=== {q_label} ===\n{query}\n\n"
        f"=== {a_label} (wajib menyertakan [1], [2] dst) ===\n"
    )
