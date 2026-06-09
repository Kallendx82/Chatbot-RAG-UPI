"""
Find duplicate PDFs across the Dataset folder by content hash (MD5).

REPORT MODE (default) - just shows what's duplicated. Safe.
DELETE MODE - actually removes redundant copies, keeping the "best" name.

Heuristic for which copy wins when there are duplicates:
  1. Prefer human-readable names over random hash names (Wqu5jCE... loses).
  2. Prefer paths WITHOUT "RAW" or "raw" subfolders.
  3. Prefer paths WITHOUT spaces (e.g. LPPM_UPI beats "LPPM UPI").
  4. Among equally-good paths, keep the shortest one.

USAGE
    python find_duplicate_pdfs.py
        (just scan, print a report - DOES NOT touch files)

    python find_duplicate_pdfs.py --csv duplicates.csv
        (also write CSV with kept/dropped columns for review)

    python find_duplicate_pdfs.py --delete
        (actually delete the losing copies. Asks for confirmation first.)

    python find_duplicate_pdfs.py --base "D:/Project/RAG_UPI/Dataset"
"""
import argparse
import csv as csv_mod
import hashlib
import sys
from collections import Counter
from pathlib import Path


def md5_of(path: Path, chunk_size: int = 1 << 20) -> str:
    h = hashlib.md5()
    with path.open("rb") as f:
        while True:
            data = f.read(chunk_size)
            if not data:
                break
            h.update(data)
    return h.hexdigest()


def name_quality(p: Path) -> tuple:
    """Lower tuple wins (will be kept). See module docstring."""
    name = p.name
    parts = [s.lower() for s in p.parts]
    # 1) Random-hash filenames lose (no spaces, no underscores, all base62-looking).
    stem = p.stem
    looks_random = (
        len(stem) >= 20
        and stem.isalnum()
        and "_" not in stem
        and "-" not in stem
        and not any(c in stem.lower() for c in "aeiou")  # vowel-less = random
        is False  # we want randoms to LOSE -> higher score
    )
    # Simpler: random hash names are 32+ chars with no separators
    random_score = 1 if (len(stem) >= 24 and "_" not in stem and "-" not in stem) else 0

    raw_score = 1 if any(s in ("raw",) for s in parts) else 0
    space_score = 1 if " " in str(p) else 0
    return (random_score, raw_score, space_score, len(str(p)), str(p).lower())


def scan(base: Path):
    pdfs = sorted(base.rglob("*.pdf"))
    print(f"Scanning {len(pdfs)} PDFs under {base} ...", file=sys.stderr)
    by_hash: dict[str, list[Path]] = {}
    for p in pdfs:
        try:
            h = md5_of(p)
        except (PermissionError, OSError) as e:
            print(f"  skip {p}: {e}", file=sys.stderr)
            continue
        by_hash.setdefault(h, []).append(p)
    return by_hash


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", default=r"D:/Project/RAG_UPI/Dataset",
                    help="Folder to scan recursively for .pdf files")
    ap.add_argument("--csv", default=None,
                    help="Also write CSV with full kept/dropped breakdown")
    ap.add_argument("--delete", action="store_true",
                    help="Actually delete the losing copies (asks for confirmation)")
    args = ap.parse_args()

    base = Path(args.base)
    if not base.exists():
        print(f"Base does not exist: {base}", file=sys.stderr)
        sys.exit(2)

    by_hash = scan(base)
    dup_groups = {h: ps for h, ps in by_hash.items() if len(ps) > 1}

    total = sum(len(ps) for ps in by_hash.values())
    redundant_count = sum(len(ps) - 1 for ps in dup_groups.values())
    redundant_bytes = 0
    for ps in dup_groups.values():
        ps_sorted = sorted(ps, key=name_quality)
        for p in ps_sorted[1:]:
            try: redundant_bytes += p.stat().st_size
            except OSError: pass

    print()
    print(f"== Duplicate scan summary ==")
    print(f"Total PDFs              : {total}")
    print(f"Unique by content (md5) : {len(by_hash)}")
    print(f"Duplicate groups        : {len(dup_groups)}")
    print(f"Redundant files         : {redundant_count}")
    print(f"Disk freeable           : {redundant_bytes/(1024**2):.1f} MB")

    if not dup_groups:
        print("\nNo duplicates. Nothing to do.")
        return

    # Show top 10 duplicate groups
    print("\n== Top 10 duplicate groups (most copies first) ==")
    top = sorted(dup_groups.items(), key=lambda kv: -len(kv[1]))[:10]
    for h, paths in top:
        paths_sorted = sorted(paths, key=name_quality)
        keep = paths_sorted[0]
        drop = paths_sorted[1:]
        print(f"\n  [md5 {h[:8]}]  {len(paths)} copies")
        print(f"    KEEP : {keep.relative_to(base)}")
        for d in drop[:6]:
            print(f"    drop : {d.relative_to(base)}")
        if len(drop) > 6:
            print(f"    ...and {len(drop) - 6} more")

    # By-folder stats
    print("\n== Where the duplicates live (folder of dropped copies) ==")
    folder_counts = Counter()
    for paths in dup_groups.values():
        for d in sorted(paths, key=name_quality)[1:]:
            try:
                folder_counts[d.relative_to(base).parts[0]] += 1
            except (IndexError, ValueError):
                folder_counts["<root>"] += 1
    for folder, n in folder_counts.most_common():
        print(f"  {n:>5}  {folder}")

    if args.csv:
        csv_path = Path(args.csv)
        with csv_path.open("w", newline="", encoding="utf-8") as f:
            w = csv_mod.writer(f)
            w.writerow(["md5", "action", "path", "size_bytes"])
            for h, paths in dup_groups.items():
                paths_sorted = sorted(paths, key=name_quality)
                w.writerow([h, "KEEP", str(paths_sorted[0]),
                            paths_sorted[0].stat().st_size if paths_sorted[0].exists() else ""])
                for d in paths_sorted[1:]:
                    w.writerow([h, "DROP", str(d),
                                d.stat().st_size if d.exists() else ""])
        print(f"\nCSV written to {csv_path.resolve()}")
        print(f"Review the 'DROP' rows in Excel before running with --delete.")

    if args.delete:
        print(f"\n!!! DELETE MODE !!!")
        print(f"About to delete {redundant_count} files "
              f"({redundant_bytes/(1024**2):.1f} MB).")
        ans = input("Type 'YES' to confirm: ").strip()
        if ans != "YES":
            print("Aborted. Nothing was deleted.")
            return
        deleted = 0
        for paths in dup_groups.values():
            paths_sorted = sorted(paths, key=name_quality)
            for d in paths_sorted[1:]:
                try:
                    d.unlink()
                    deleted += 1
                except OSError as e:
                    print(f"  could not delete {d}: {e}")
        print(f"Deleted {deleted} files.")
        print("\nNEXT STEPS:")
        print("  1. Re-run check_pipeline_health.py to see what's now orphan.")
        print("  2. Decide whether to rebuild the FAISS index from scratch")
        print("     (slow - 5+ hours) or just keep the retrieval-time dedup.")


if __name__ == "__main__":
    main()
