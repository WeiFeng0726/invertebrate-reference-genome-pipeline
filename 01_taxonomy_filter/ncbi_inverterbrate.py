#!/usr/bin/env python3
import argparse
import pandas as pd
from pathlib import Path

# -----------------------------
# Step 1. Load NCBI taxonomy
# -----------------------------


def load_taxonomy(nodes_file, names_file):
    parent = {}
    sci_name = {}

    # ---- nodes.dmp ----
    with open(nodes_file) as f:
        for line in f:
            parts = [x.strip() for x in line.split('|')]
            taxid = parts[0]
            parent_id = parts[1]
            parent[taxid] = parent_id

    # ---- names.dmp ----
    with open(names_file) as f:
        for line in f:
            parts = [x.strip() for x in line.split('|')]
            taxid = parts[0]
            name = parts[1]
            name_class = parts[3]

            if name_class == "scientific name":
                sci_name[taxid] = name

    def get_lineage(taxid):
        lineage = []
        while taxid in parent and taxid != parent[taxid]:
            lineage.append(sci_name.get(taxid, taxid))
            taxid = parent[taxid]
        return lineage

    return get_lineage


# -----------------------------
# Step 2. Load assembly_summary
# -----------------------------
def load_assembly_tables(files):
    dfs = []
    for f in files:
        df = pd.read_csv(
            f,
            sep="\t",
            comment="#",
            low_memory=False
        )
        df.columns = [c.strip().lstrip("#") for c in df.columns]
        dfs.append(df)
    return pd.concat(dfs, ignore_index=True)


# -----------------------------
# Step 3. Classification logic
# -----------------------------
def is_invertebrate(lineage):
    s = set(lineage)
    return ("Metazoa" in s) and ("Vertebrata" not in s)


# -----------------------------
# Step 4. Main pipeline
# -----------------------------
def main(args):
    print("[INFO] Loading taxonomy...")
    get_lineage = load_taxonomy(args.nodes, args.names)

    print("[INFO] Loading assembly summaries...")
    asm = load_assembly_tables(args.assembly)

    print("[INFO] Resolving taxonomy & filtering invertebrates...")
    records = []
    for _, r in asm.iterrows():
        taxid = str(r["taxid"])
        lineage = get_lineage(taxid)
        if (
                is_invertebrate(lineage)
                and r["assembly_level"] == "Chromosome"
                ):
            records.append({
                "assembly_accession": r["assembly_accession"],
                "organism_name": r["organism_name"],
                "taxid": taxid,
                "assembly_level": r["assembly_level"],
                "lineage": ";".join(lineage)
            })

    out = pd.DataFrame(records)

    print(f"[INFO] Invertebrate assemblies found: {len(out)}")

    out.to_csv(args.output, sep="\t", index=False)
    print(f"[INFO] Output written to: {args.output}")
    print(asm.columns.tolist())


# -----------------------------
# CLI
# -----------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="NCBI invertebrate assembly paired-accession pipeline"
    )
    parser.add_argument(
        "--assembly",
        nargs="+",
        required=True,
        help="assembly_summary_genbank.txt / assembly_summary_refseq.txt"
    )
    parser.add_argument(
        "--nodes",
        required=True,
        help="NCBI taxonomy nodes.dmp"
    )
    parser.add_argument(
        "--names",
        required=True,
        help="NCBI taxonomy names.dmp"
    )
    parser.add_argument(
        "-o",
        "--output",
        default="invertebrate_assembly_pairs.tsv",
        help="Output TSV file"
    )

    args = parser.parse_args()
    main(args)
