#!/usr/bin/env python3
import os
import csv
import subprocess
import glob

# ========= 配置 =========
INPUT = "assemblies.tsv"   # 输入文件
OUTDIR = "genomes"         # 输出目录

# ========= 工具函数 =========
def run(cmd):
    print("[CMD]", " ".join(cmd))
    subprocess.run(cmd, check=True)

def has_fna(assembly_dir):
    """判定 assembly 目录中是否已有 fna 文件"""
    return bool(
        glob.glob(os.path.join(assembly_dir, "*.fna")) or
        glob.glob(os.path.join(assembly_dir, "*.fna.gz"))
    )

# ========= 主逻辑 =========
def main():
    os.makedirs(OUTDIR, exist_ok=True)

    with open(INPUT) as f:
        reader = csv.DictReader(f, delimiter="\t")
        required_cols = {"assembly_accession", "taxid"}
        if not required_cols.issubset(reader.fieldnames):
            raise RuntimeError(
                f"Input file must contain columns: {required_cols}"
            )

        for row in reader:
            acc = row["assembly_accession"].strip()
            taxid = row["taxid"].strip()

            print(f"\n=== Processing taxid={taxid}, assembly={acc} ===")

            taxdir = os.path.join(OUTDIR, taxid)
            assembly_dir = os.path.join(
                taxdir, "ncbi_dataset", "data", acc
            )

            # === 核心 skip 条件 ===
            if os.path.isdir(assembly_dir) and has_fna(assembly_dir):
                print("[SKIP] fna already exists, skip download")
                continue

            os.makedirs(taxdir, exist_ok=True)
            zip_path = os.path.join(taxdir, f"{acc}.zip")

            cmd = [
                "datasets", "download", "genome", "accession", acc,
                "--include", "genome,gff3",
                "--filename", zip_path
            ]

            try:
                run(cmd)
            except subprocess.CalledProcessError:
                print(f"[FAIL] datasets download failed for {acc}")
                continue

            # 解压并清理 zip
            run(["unzip", "-q", "-o", zip_path, "-d", taxdir])
            os.remove(zip_path)

            print("[OK] download finished")

if __name__ == "__main__":
    main()

