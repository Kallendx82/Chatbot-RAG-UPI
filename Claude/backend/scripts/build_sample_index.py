"""Build a tiny synthetic FAISS index so the backend is runnable immediately.

This is a DEVELOPMENT / TESTING fixture, not part of the real pipeline. It lets
you boot the API and exercise every endpoint before you have downloaded the
real index artefacts from 03_vectorstore_rag_evaluation.ipynb.

Usage (from backend/):
    python -m scripts.build_sample_index

It writes faiss.index, chunks_meta.json and index_info.json into app/data/,
which is exactly where .env.example points by default.

When your real notebook artefacts are ready, simply overwrite those three
files - no code change needed.
"""
from __future__ import annotations

import json
from pathlib import Path

# A handful of UPI-flavoured chunks covering several source categories.
SAMPLE_CHUNKS = [
    {
        "chunk_id": "ppid_0", "doc_id": "ppid_doc", "chunk_index": 0,
        "title": "Pedoman Layanan Informasi Publik PPID UPI",
        "category": "PPID", "source_type": "pdf", "page": 1,
        "section": "LAYANAN INFORMASI",
        "source": "Dataset/PPID/pedoman_ppid.pdf",
        "text": "PPID UPI menyediakan layanan informasi publik meliputi "
                "informasi berkala, informasi serta merta, dan informasi yang "
                "wajib tersedia setiap saat bagi sivitas akademika dan masyarakat.",
    },
    {
        "chunk_id": "pmb_0", "doc_id": "pmb_doc", "chunk_index": 1,
        "title": "Panduan Penerimaan Mahasiswa Baru UPI",
        "category": "Dataset_PMB_UPI", "source_type": "pdf", "page": 3,
        "section": "PROSEDUR PENDAFTARAN",
        "source": "Dataset/Dataset_PMB_UPI/panduan_pmb.pdf",
        "text": "Prosedur pendaftaran mahasiswa baru UPI dilakukan secara daring "
                "melalui laman resmi penerimaan, dimulai dengan pembuatan akun, "
                "pengisian biodata, pemilihan program studi, dan unggah berkas.",
    },
    {
        "chunk_id": "lppm_0", "doc_id": "lppm_doc", "chunk_index": 2,
        "title": "Laporan Penelitian dan Pengabdian LPPM UPI",
        "category": "LPPM_UPI", "source_type": "pdf", "page": 7,
        "section": "FOKUS PENELITIAN",
        "source": "Dataset/LPPM_UPI/laporan_lppm.pdf",
        "text": "LPPM UPI memfokuskan kegiatan penelitian dan pengabdian kepada "
                "masyarakat pada bidang pendidikan, sains, teknologi, dan "
                "pemberdayaan masyarakat berbasis kearifan lokal.",
    },
    {
        "chunk_id": "dit_0", "doc_id": "dit_doc", "chunk_index": 3,
        "title": "Surat Edaran Akademik Direktorat Pendidikan UPI",
        "category": "web", "source_type": "html", "page": 1,
        "section": None,
        "source": "https://dit-pendidikan.upi.edu/informasi-akademik/",
        "url": "https://dit-pendidikan.upi.edu/informasi-akademik/",
        "text": "Direktorat Pendidikan UPI menerbitkan surat edaran mengenai "
                "kalender akademik, registrasi perkuliahan, dan ketentuan "
                "pelaksanaan ujian bagi seluruh mahasiswa.",
    },
    {
        "chunk_id": "fas_0", "doc_id": "fas_doc", "chunk_index": 4,
        "title": "Informasi Fasilitas Kampus UPI",
        "category": "web", "source_type": "html", "page": 1,
        "section": "FASILITAS",
        "source": "https://www.upi.edu/fasilitas",
        "url": "https://www.upi.edu/fasilitas",
        "text": "Fasilitas kampus UPI mencakup perpustakaan pusat, laboratorium "
                "terpadu, gedung olahraga, poliklinik, serta layanan asrama "
                "mahasiswa untuk mendukung kegiatan akademik.",
    },
]


def main() -> None:
    import faiss
    import numpy as np
    from sentence_transformers import SentenceTransformer

    out_dir = Path("./app/data")
    out_dir.mkdir(parents=True, exist_ok=True)

    model_name = "intfloat/multilingual-e5-base"
    print(f"Loading embedding model: {model_name} ...")
    model = SentenceTransformer(model_name)
    dim = model.get_sentence_embedding_dimension()

    texts = ["passage: " + c["text"] for c in SAMPLE_CHUNKS]
    print(f"Embedding {len(texts)} sample chunks ...")
    vecs = model.encode(texts, convert_to_numpy=True,
                        normalize_embeddings=True).astype("float32")

    index = faiss.IndexFlatIP(dim)
    index.add(vecs)
    faiss.write_index(index, str(out_dir / "faiss.index"))

    (out_dir / "chunks_meta.json").write_text(
        json.dumps(SAMPLE_CHUNKS, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (out_dir / "index_info.json").write_text(
        json.dumps(
            {
                "embedding_model": model_name,
                "embedding_dim": int(dim),
                "n_vectors": int(index.ntotal),
                "use_e5_prefixes": True,
                "note": "SYNTHETIC fixture from scripts/build_sample_index.py",
            },
            ensure_ascii=False, indent=2,
        ),
        encoding="utf-8",
    )
    print(f"Done. Wrote faiss.index ({index.ntotal} vectors, dim={dim}), "
          f"chunks_meta.json, index_info.json to {out_dir}/")


if __name__ == "__main__":
    main()
