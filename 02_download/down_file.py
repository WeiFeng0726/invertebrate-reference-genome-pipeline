#!/usr/bin/env python3
import os
import csv
import subprocess

INPUT = "assemblies.tsv"
OUTDIR = "genomes"

def run(cmd):
    print(" ".join(cmd))
    subprocess.run(cmd, check=True)

def main():
    os.makedirs(OUTDIR, exist_ok=True)

    with open(INPUT) as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            acc = row["assembly_accession"].strip()
            taxid = row["taxid"].strip()

            taxdir = os.path.join(OUTDIR, taxid)
            os.makedirs(taxdir, exist_ok=True)

            zip_path = os.path.join(taxdir, f"{acc}.zip")

            print(f"\n=== {taxid} | {acc} ===")

            cmd = [
                "datasets", "download", "genome", "accession", acc,
                "--include", "genome,gff3",
                "--filename", zip_path
            ]

            try:
                run(cmd)
            except subprocess.CalledProcessError:
                print(f"[FAIL] download failed: {acc}")
                continue

            # 解压
            run(["unzip", "-q", "-o", zip_path, "-d", taxdir])
            os.remove(zip_path)

if __name__ == "__main__":
    main()
