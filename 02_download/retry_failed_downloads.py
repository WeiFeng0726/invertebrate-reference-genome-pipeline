#!/usr/bin/env python3
"""
仅重试 assemblies.tsv 中「尚未成功解压出 FASTA」的组装。
输出目录结构与 download_ncbi_assemblies.py 一致：

  <outdir>/<taxid>/ncbi_dataset/data/<assembly_accession>/*.fna

用法（在存放 assemblies.tsv 的目录下执行，或显式指定路径）：

  python3 retry_failed_downloads.py --dry-run
  python3 retry_failed_downloads.py

依赖：NCBI datasets CLI（datasets）、unzip。
"""
from __future__ import annotations

import argparse
import csv
import glob
import os
import subprocess
import sys


def has_fna(assembly_dir: str) -> bool:
    return bool(
        glob.glob(os.path.join(assembly_dir, "*.fna"))
        or glob.glob(os.path.join(assembly_dir, "*.fna.gz"))
    )


def assembly_dir_for(outdir: str, taxid: str, acc: str) -> str:
    return os.path.join(outdir, taxid, "ncbi_dataset", "data", acc)


def run(cmd: list[str]) -> None:
    print("[CMD]", " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True)


def main() -> int:
    p = argparse.ArgumentParser(
        description="Re-download only failed/missing genome packages (same layout as download_ncbi_assemblies.py)."
    )
    p.add_argument(
        "-i",
        "--input",
        default="assemblies.tsv",
        help="TSV with columns assembly_accession, taxid (default: assemblies.tsv)",
    )
    p.add_argument(
        "-o",
        "--outdir",
        default="genomes",
        help="Output root, same as download_ncbi_assemblies.py OUTDIR (default: genomes)",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="List assemblies that would be retried, do not download",
    )
    p.add_argument(
        "--remove-stale-zip",
        action="store_true",
        help="Before download, remove <outdir>/<taxid>/<accession>.zip if present",
    )
    args = p.parse_args()

    if not os.path.isfile(args.input):
        print(f"[FATAL] input not found: {args.input}", file=sys.stderr)
        return 1

    os.makedirs(args.outdir, exist_ok=True)

    with open(args.input, encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        required = {"assembly_accession", "taxid"}
        if not reader.fieldnames or not required.issubset(set(reader.fieldnames)):
            print(
                f"[FATAL] input must contain columns: {required}; got {reader.fieldnames}",
                file=sys.stderr,
            )
            return 1
        rows = list(reader)

    pending: list[tuple[str, str]] = []
    for row in rows:
        acc = row["assembly_accession"].strip()
        taxid = row["taxid"].strip()
        adir = assembly_dir_for(args.outdir, taxid, acc)
        if os.path.isdir(adir) and has_fna(adir):
            continue
        pending.append((acc, taxid))

    print(f"[INFO] total rows in TSV: {len(rows)}")
    print(f"[INFO] pending retry (no *.fna under .../data/<assembly>/): {len(pending)}")

    if not pending:
        print("[OK] nothing to retry.")
        return 0

    if args.dry_run:
        for acc, taxid in pending:
            print(f"[DRY-RUN] would retry taxid={taxid} assembly={acc}")
        return 0

    failed: list[tuple[str, str, str]] = []

    for acc, taxid in pending:
        print(f"\n=== RETRY taxid={taxid}, assembly={acc} ===", flush=True)
        taxdir = os.path.join(args.outdir, taxid)
        os.makedirs(taxdir, exist_ok=True)
        zip_path = os.path.join(taxdir, f"{acc}.zip")

        if args.remove_stale_zip and os.path.isfile(zip_path):
            print(f"[INFO] removing stale zip: {zip_path}", flush=True)
            os.remove(zip_path)

        cmd = [
            "datasets",
            "download",
            "genome",
            "accession",
            acc,
            "--include",
            "genome,gff3",
            "--filename",
            zip_path,
        ]
        try:
            run(cmd)
        except subprocess.CalledProcessError:
            print(f"[FAIL] datasets download failed for {acc}", flush=True)
            failed.append((acc, taxid, "datasets download"))
            continue

        try:
            run(["unzip", "-q", "-o", zip_path, "-d", taxdir])
        except subprocess.CalledProcessError:
            print(f"[FAIL] unzip failed for {acc}, zip left at {zip_path}", flush=True)
            failed.append((acc, taxid, "unzip"))
            continue

        try:
            os.remove(zip_path)
        except OSError as e:
            print(f"[WARN] could not remove zip {zip_path}: {e}", flush=True)

        adir = assembly_dir_for(args.outdir, taxid, acc)
        if has_fna(adir):
            print(f"[OK] fna present under {adir}", flush=True)
        else:
            print(
                f"[WARN] download finished but no *.fna found under {adir}; check layout",
                flush=True,
            )
            failed.append((acc, taxid, "no fna after unzip"))

    if failed:
        print("\n=== Summary: still problematic ===", flush=True)
        for acc, taxid, reason in failed:
            print(f"  {acc}\t{taxid}\t{reason}", flush=True)
        return 2

    print("\n[OK] all pending retries completed successfully.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
