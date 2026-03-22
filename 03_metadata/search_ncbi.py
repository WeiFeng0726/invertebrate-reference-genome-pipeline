#!/usr/bin/env python3
import csv
import json
import subprocess

INPUT = "assemblies.tsv"
OUTPUT = "assemblies.with_gcf_and_rnaseq.tsv"


def run_datasets_summary(acc):
    try:
        p = subprocess.run(
            ["datasets", "summary", "genome", "accession", acc],
            capture_output=True,
            text=True,
            check=True,
        )
        data = json.loads(p.stdout)
        reports = data.get("reports", [])
        return reports[0] if reports else None
    except Exception:
        return None


def get_paired_gcf(report):
    if not report:
        return None

    # 优先从 assembly_relations 取
    rel = report.get("assembly_relations", {})
    gcf = rel.get("refseq_assembly_accession")
    if gcf:
        return gcf

    # 兜底
    asm_info = report.get("assembly_info", {})
    return asm_info.get("refseq_accession")


def has_rnaseq_evidence(report, paired_gcf):
    """
    稳定判定逻辑（方案三）
    """

    if not report:
        return False

    # 1) 已被 RefSeq 接管
    if paired_gcf:
        return True

    # 2) 有 annotation / gene annotation 信息
    if report.get("annotation"):
        return True
    if report.get("annotation_report"):
        return True

    asm_info = report.get("assembly_info", {})

    if asm_info.get("annotation_pipeline"):
        return True

    # 3) 有关联 BioProject
    if asm_info.get("bioproject_accessions"):
        return True

    return False


def main():
    with open(INPUT) as fin, open(OUTPUT, "w", newline="") as fout:
        reader = csv.DictReader(fin, delimiter="\t")
        fieldnames = reader.fieldnames + ["paired_gcf", "has_rnaseq"]
        writer = csv.DictWriter(fout, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()

        for row in reader:
            acc = row["assembly_accession"].strip()

            row["paired_gcf"] = "NA"
            row["has_rnaseq"] = "NA"

            if acc.startswith("GCA_"):
                report = run_datasets_summary(acc)
                paired_gcf = get_paired_gcf(report)

                if paired_gcf:
                    row["paired_gcf"] = paired_gcf

                has_rna = has_rnaseq_evidence(report, paired_gcf)
                row["has_rnaseq"] = "YES" if has_rna else "NO"

            writer.writerow(row)


if __name__ == "__main__":
    main()
