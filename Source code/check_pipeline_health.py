"""
Pipeline health-check + repair tool.

Run after any unclean shutdown (kernel crash, power off, Ctrl-C during write).
Detects corruption across the four stages and offers --fix to repair what is
safe to repair automatically.

USAGE
    python check_pipeline_health.py              # report only
    python check_pipeline_health.py --fix        # also repair safe issues
    python check_pipeline_health.py --base "D:/Project/RAG_UPI/Dataset"

CHECKS

  STAGE 1 (extraction)
    - manifest.json parses
    - every raw/*.json parses, has required keys, page-order intact
    - all manifest 'extracted' rows have a corresponding raw json
    - no leftover .tmp files in raw/

  STAGE 2 (cleaning)
    - every cleaned/*.json parses
    - .txt and .md sidecar files exist for every cleaned/*.json
    - cleaned_manifest.json parses and matches actual files on disk

  STAGE 3 (chunking)
    - chunks.jsonl: every line is valid JSON
    - no duplicate chunk_index
    - chunk_index contiguous from 0 (no gaps)
    - every chunk has required schema fields
    - every chunk's doc_id has a matching cleaned/<id>.json

  STAGE 4 (vector index)
    - faiss.index loads
    - chunks_meta.json parses
    - index.ntotal == len(meta)
    - index dim matches index_info.json
    - shards/: every .npy loads, total row count matches index size
    - no orphan .tmp / partial shard files

REPAIRS (only with --fix)
    - delete leftover .tmp files
    - truncate chunks.jsonl tail if last line(s) are corrupt
    - delete orphan partial shard files
    - cannot rebuild missing files; report only those.
"""
import argparse
import json
import sys
from pathlib import Path
from collections import Counter

# ----------------------------- terminal colors ----------------------------- #
class C:
    GREEN  = "\033[92m"
    YELLOW = "\033[93m"
    RED    = "\033[91m"
    BOLD   = "\033[1m"
    DIM    = "\033[2m"
    END    = "\033[0m"
    # disable on Windows terminals without ANSI support
    if sys.platform == "win32":
        import os as _os
        if not _os.environ.get("WT_SESSION"):  # crude heuristic
            GREEN = YELLOW = RED = BOLD = DIM = END = ""


def ok(msg):    print(f"{C.GREEN}[OK]{C.END}    {msg}")
def warn(msg):  print(f"{C.YELLOW}[WARN]{C.END}  {msg}")
def err(msg):   print(f"{C.RED}[FAIL]{C.END}  {msg}")
def info(msg):  print(f"        {msg}")
def hdr(msg):   print(f"\n{C.BOLD}{msg}{C.END}\n{'-' * len(msg)}")


# ----------------------------- helpers ------------------------------------- #
def load_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8")), None
    except Exception as e:
        return None, str(e)


def iter_jsonl_safely(path):
    """Yield (lineno, parsed-or-None, error-or-None) for every line in JSONL."""
    with path.open("r", encoding="utf-8", errors="replace") as f:
        for i, ln in enumerate(f, 1):
            ln = ln.rstrip("\n")
            if not ln.strip():
                continue
            try:
                yield i, json.loads(ln), None
            except json.JSONDecodeError as e:
                yield i, None, str(e)


# ----------------------------- stage checks -------------------------------- #
def check_stage1_extraction(pipe, fix, problems):
    hdr("STAGE 1 — Extraction (manifest + raw/)")
    raw_dir = pipe / "raw"
    manifest_path = pipe / "manifest.json"

    if not manifest_path.exists():
        err(f"manifest.json missing at {manifest_path}")
        problems["manifest_missing"] = True
        return
    manifest, e = load_json(manifest_path)
    if e:
        err(f"manifest.json is corrupt: {e}")
        problems["manifest_corrupt"] = True
        return
    ok(f"manifest.json parses — {len(manifest)} rows")

    # raw/*.json sanity
    bad, empty = [], []
    raw_files = sorted(raw_dir.glob("*.json")) if raw_dir.exists() else []
    for f in raw_files:
        d, e = load_json(f)
        if e or not d:
            bad.append((f, e or "empty"))
            continue
        if "pages" not in d or "id" not in d:
            bad.append((f, "missing required keys"))
            continue
        nums = [p.get("page") for p in d["pages"]]
        if nums != sorted(nums):
            bad.append((f, "pages out of order"))
        if d.get("total_chars", 0) == 0:
            empty.append(f)
    (err if bad else ok)(
        f"raw/ files parse: {len(raw_files) - len(bad)}/{len(raw_files)} OK"
    )
    for f, e in bad[:5]:
        info(f"{C.RED}corrupt{C.END} {f.name}: {e}")
    if len(bad) > 5:
        info(f"...and {len(bad) - 5} more")
    if empty:
        warn(f"{len(empty)} raw files have total_chars=0 (extraction was empty)")

    # Manifest claims vs disk
    extracted_ids = {r["id"] for r in manifest if r.get("status") == "extracted"}
    disk_ids = {f.stem for f in raw_files}
    missing = extracted_ids - disk_ids
    if missing:
        err(f"{len(missing)} docs marked 'extracted' but raw/<id>.json missing")
        for i in list(missing)[:5]:
            info(f"  missing: {i}.json")
    else:
        ok("every 'extracted' manifest row has its raw file")

    # Leftover .tmp
    tmps = list(raw_dir.glob("*.tmp")) if raw_dir.exists() else []
    if tmps:
        msg = f"{len(tmps)} leftover .tmp files in raw/"
        if fix:
            for t in tmps:
                t.unlink()
            ok(msg + " — DELETED")
        else:
            warn(msg + " (use --fix to delete)")
    else:
        ok("no leftover .tmp in raw/")

    problems["stage1_corrupt_raws"] = [str(f) for f, _ in bad]
    problems["stage1_missing_raws"] = list(missing)


def check_stage2_cleaning(pipe, fix, problems):
    hdr("STAGE 2 — Cleaning + Markdown (cleaned/)")
    cleaned_dir = pipe / "cleaned"
    if not cleaned_dir.exists():
        warn(f"cleaned/ does not exist at {cleaned_dir}")
        return

    json_files = sorted(f for f in cleaned_dir.glob("*.json")
                        if f.name != "cleaned_manifest.json")
    bad = []
    missing_sidecar = {"txt": [], "md": []}
    for f in json_files:
        d, e = load_json(f)
        if e or not d:
            bad.append((f, e or "empty"))
            continue
        stem = f.stem
        for ext in (".txt", ".md"):
            if not (cleaned_dir / f"{stem}{ext}").exists():
                missing_sidecar[ext.lstrip(".")].append(stem)

    (err if bad else ok)(
        f"cleaned/*.json parse: {len(json_files) - len(bad)}/{len(json_files)} OK"
    )
    for f, e in bad[:5]:
        info(f"{C.RED}corrupt{C.END} {f.name}: {e}")
    if len(bad) > 5:
        info(f"...and {len(bad) - 5} more")

    for ext, missing in missing_sidecar.items():
        if missing:
            warn(f"{len(missing)} cleaned docs missing the .{ext} sidecar")
            for s in missing[:3]:
                info(f"  missing: {s}.{ext}")
        else:
            ok(f"every cleaned doc has its .{ext} sidecar")

    # cleaned_manifest
    cm = cleaned_dir / "cleaned_manifest.json"
    if cm.exists():
        m, e = load_json(cm)
        if e:
            err(f"cleaned_manifest.json corrupt: {e}")
        else:
            disk_ids = {f.stem for f in json_files}
            manifest_ids = {r["id"] for r in m}
            stale = manifest_ids - disk_ids
            new_on_disk = disk_ids - manifest_ids
            if stale:
                warn(f"cleaned_manifest has {len(stale)} rows not on disk")
            if new_on_disk:
                warn(f"cleaned/ has {len(new_on_disk)} json files not in cleaned_manifest")
            if not (stale or new_on_disk):
                ok("cleaned_manifest matches disk")

    # Leftover .tmp
    tmps = list(cleaned_dir.glob("*.tmp"))
    if tmps:
        msg = f"{len(tmps)} leftover .tmp files in cleaned/"
        if fix:
            for t in tmps: t.unlink()
            ok(msg + " — DELETED")
        else:
            warn(msg + " (use --fix to delete)")

    problems["stage2_corrupt_cleaned"] = [str(f) for f, _ in bad]


def check_stage3_chunks(pipe, fix, problems):
    hdr("STAGE 3 — Chunking (chunks.jsonl)")
    chunks_path = pipe / "chunked" / "chunks.jsonl"
    cleaned_dir = pipe / "cleaned"
    if not chunks_path.exists():
        warn(f"chunks.jsonl missing at {chunks_path}")
        return

    required = {"chunk_id", "chunk_index", "doc_id", "text", "title", "page",
                "chunk_length"}
    bad_lines = []           # (lineno, raw_error)
    seen_indices = []
    seen_chunk_ids = set()
    dup_chunk_ids = []
    dup_indices = []
    missing_field_lines = []
    doc_ids = set()

    for lineno, rec, e in iter_jsonl_safely(chunks_path):
        if e is not None:
            bad_lines.append((lineno, e))
            continue
        if required - set(rec.keys()):
            missing_field_lines.append(lineno)
            continue
        if rec["chunk_id"] in seen_chunk_ids:
            dup_chunk_ids.append(rec["chunk_id"])
        else:
            seen_chunk_ids.add(rec["chunk_id"])
        idx = rec["chunk_index"]
        if idx in seen_indices:
            dup_indices.append(idx)
        seen_indices.append(idx)
        doc_ids.add(rec["doc_id"])

    total = len(seen_indices) + len(bad_lines) + len(missing_field_lines)
    ok(f"chunks.jsonl total lines (incl. bad): {total}")

    if bad_lines:
        err(f"{len(bad_lines)} corrupt JSON line(s)")
        for ln, e in bad_lines[:5]:
            info(f"  line {ln}: {e}")
        # Auto-fix: truncate file at last good line if all bad lines are at the tail
        if fix:
            good_lines = []
            with chunks_path.open("r", encoding="utf-8", errors="replace") as f:
                raw_lines = [ln for ln in f.read().splitlines() if ln.strip()]
            last_good = 0
            for i, ln in enumerate(raw_lines, 1):
                try:
                    json.loads(ln); last_good = i
                except json.JSONDecodeError:
                    pass
            # truncate to last_good lines (drops any bad-or-later lines)
            kept = []
            for i, ln in enumerate(raw_lines, 1):
                if i > last_good: break
                try:
                    json.loads(ln); kept.append(ln)
                except json.JSONDecodeError:
                    continue   # drop mid-file corrupt line
            backup = chunks_path.with_suffix(".jsonl.bak")
            chunks_path.rename(backup)
            chunks_path.write_text("\n".join(kept) + "\n", encoding="utf-8")
            ok(f"  truncated to {len(kept)} clean lines "
               f"(backup at {backup.name})")
    else:
        ok("every chunks.jsonl line is valid JSON")

    if missing_field_lines:
        err(f"{len(missing_field_lines)} chunks miss required fields "
            f"(first: {missing_field_lines[:5]})")
    else:
        ok("every chunk has the required schema")

    if dup_chunk_ids:
        err(f"{len(dup_chunk_ids)} duplicate chunk_id (e.g. {dup_chunk_ids[:3]})")
    else:
        ok("no duplicate chunk_id")

    if dup_indices:
        err(f"{len(dup_indices)} duplicate chunk_index (e.g. {dup_indices[:3]})")
    else:
        ok("no duplicate chunk_index")

    # contiguity
    if seen_indices:
        expected = set(range(min(seen_indices), max(seen_indices) + 1))
        gaps = sorted(expected - set(seen_indices))
        if gaps:
            warn(f"{len(gaps)} gaps in chunk_index (first: {gaps[:5]})")
        else:
            ok("chunk_index contiguous (no gaps)")

    # doc_id ↔ cleaned/<id>.json
    if cleaned_dir.exists():
        cleaned_ids = {f.stem for f in cleaned_dir.glob("*.json")
                       if f.name != "cleaned_manifest.json"}
        orphan = doc_ids - cleaned_ids
        if orphan:
            warn(f"{len(orphan)} chunk doc_ids have no cleaned/<id>.json")
            for i in list(orphan)[:3]:
                info(f"  orphan doc_id: {i}")
        else:
            ok("every chunk doc_id has a cleaned source file")

    problems["stage3_bad_lines"] = len(bad_lines)
    problems["stage3_missing_fields"] = len(missing_field_lines)


def check_stage4_index(pipe, fix, problems):
    hdr("STAGE 4 — FAISS index + shards")
    idx_dir = pipe / "index"
    index_path = idx_dir / "faiss.index"
    meta_path = idx_dir / "chunks_meta.json"
    info_path = idx_dir / "index_info.json"
    shard_dir = idx_dir / "shards"

    files_status = [
        ("faiss.index", index_path),
        ("chunks_meta.json", meta_path),
        ("index_info.json", info_path),
    ]
    any_missing = False
    for name, p in files_status:
        if not p.exists():
            warn(f"{name} missing — Notebook 3 likely incomplete")
            any_missing = True
    if any_missing:
        info("(this is expected if you're still embedding)")

    # FAISS
    index = None
    if index_path.exists():
        try:
            import faiss
            index = faiss.read_index(str(index_path))
            ok(f"faiss.index loads — {index.ntotal} vectors, dim={index.d}")
        except Exception as e:
            err(f"faiss.index fails to load: {e}")
            problems["stage4_index_unreadable"] = True

    # Meta
    meta = None
    if meta_path.exists():
        meta, e = load_json(meta_path)
        if e:
            err(f"chunks_meta.json corrupt: {e}")
            problems["stage4_meta_corrupt"] = True
        else:
            ok(f"chunks_meta.json parses — {len(meta)} rows")

    if index is not None and meta is not None:
        if index.ntotal != len(meta):
            err(f"MISMATCH: index has {index.ntotal} vectors but meta has "
                f"{len(meta)} rows — retrieval will be wrong")
            problems["stage4_misaligned"] = True
        else:
            ok("index ↔ meta aligned")

    if info_path.exists():
        info_obj, e = load_json(info_path)
        if e:
            err(f"index_info.json corrupt: {e}")
        elif index is not None:
            if info_obj.get("embedding_dim") != index.d:
                warn(f"recorded dim {info_obj.get('embedding_dim')} != "
                     f"actual {index.d}")
            else:
                ok(f"recorded model = {info_obj.get('embedding_model')}, "
                   f"dim = {info_obj.get('embedding_dim')}")

    # Shards
    if shard_dir.exists():
        import numpy as np
        shards = sorted(shard_dir.glob("shard_*.npy"))
        delta = sorted(shard_dir.glob("delta_*.npy"))
        bad_shards = []
        total_rows = 0
        for s in shards + delta:
            try:
                arr = np.load(s, mmap_mode="r")
                total_rows += arr.shape[0]
            except Exception as e:
                bad_shards.append((s, str(e)))
        if shards or delta:
            (err if bad_shards else ok)(
                f"shards/: {len(shards) + len(delta) - len(bad_shards)} "
                f"OK ({len(shards)} main + {len(delta)} delta), {total_rows} rows total"
            )
            for s, e in bad_shards[:3]:
                info(f"  bad: {s.name}: {e}")
        else:
            info("(no shards on disk — already cleaned up)")

        # leftovers
        tmps = list(shard_dir.glob("*.tmp")) + list(shard_dir.glob("*.tmp.npy"))
        if tmps:
            msg = f"{len(tmps)} leftover tmp/partial shard files"
            if fix:
                for t in tmps: t.unlink()
                ok(msg + " — DELETED")
            else:
                warn(msg + " (use --fix to delete)")
        else:
            ok("no leftover tmp/partial shard files")

        # shard row count cross-check
        if index is not None and (shards or delta):
            # Total shard rows should match index, allowing delta shards (which
            # may have been added on top of an older index size).
            if total_rows == index.ntotal:
                ok("shard row total matches index.ntotal exactly")
            elif total_rows >= index.ntotal:
                info(f"shard rows ({total_rows}) >= index ({index.ntotal}) — "
                     f"some shards may not yet have been merged")
            else:
                warn(f"shard rows ({total_rows}) < index ({index.ntotal}) — "
                     f"some shards may have been deleted to save disk")


# ----------------------------- entrypoint ---------------------------------- #
def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", default=r"D:/Project/RAG_UPI/Dataset",
                    help="Dataset base dir (parent of _pipeline/)")
    ap.add_argument("--fix", action="store_true",
                    help="Apply safe automatic repairs")
    args = ap.parse_args()

    base = Path(args.base)
    pipe = base / "_pipeline"
    print(f"{C.BOLD}Pipeline health check{C.END}")
    info(f"base: {base}")
    info(f"pipeline: {pipe}")
    if args.fix:
        info(f"{C.YELLOW}--fix mode ON: safe repairs WILL be applied{C.END}")
    if not pipe.exists():
        err(f"pipeline dir not found: {pipe}")
        sys.exit(2)

    problems = {}
    check_stage1_extraction(pipe, args.fix, problems)
    check_stage2_cleaning(pipe, args.fix, problems)
    check_stage3_chunks(pipe, args.fix, problems)
    check_stage4_index(pipe, args.fix, problems)

    hdr("SUMMARY")
    if not problems:
        ok("no critical issues detected")
        sys.exit(0)
    print(json.dumps(problems, indent=2, default=str)[:4000])
    # Non-zero exit only if something definitely needs attention
    critical = ["manifest_corrupt", "manifest_missing",
                "stage4_index_unreadable", "stage4_misaligned"]
    sys.exit(1 if any(problems.get(k) for k in critical) else 0)


if __name__ == "__main__":
    main()
