#!/usr/bin/env python3
import argparse
import pandas as pd

# -----------------------------
# Step 1. Load NCBI taxonomy dump
# nodes.dmp: taxid -> parent_taxid
# names.dmp: taxid -> scientific name
# -----------------------------
def load_taxonomy(nodes_file, names_file):
    parent = {}
    sci_name = {}

    # nodes.dmp
    with open(nodes_file, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            parts = [x.strip() for x in line.split("|")]
            if len(parts) < 2:
                continue
            taxid = parts[0]
            parent_id = parts[1]
            parent[taxid] = parent_id

    # names.dmp
    with open(names_file, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            parts = [x.strip() for x in line.split("|")]
            if len(parts) < 4:
                continue
            taxid = parts[0]
            name_txt = parts[1]
            name_class = parts[3]
            if name_class == "scientific name":
                sci_name[taxid] = name_txt

    def get_lineage_names(taxid: str):
        """
        Return lineage as a list of scientific names from leaf->root (excluding root).
        We only need membership checks, so name list is enough.
        """
        lineage = []
        seen = set()
        while taxid in parent and taxid != parent[taxid]:
            # prevent any accidental cycles
            if taxid in seen:
                break
            seen.add(taxid)

            lineage.append(sci_name.get(taxid, taxid))
            taxid = parent[taxid]
        return lineage

    return get_lineage_names


# -----------------------------
# Step 2. Load assembly_summary table(s)
# Clean column names: strip whitespace and leading '#'
# -----------------------------
def load_assembly_tables(files):
    dfs = []
    for f in files:
        df = pd.read_csv(f, sep="\t", comment="#", low_memory=False)
        df.columns = [c.strip().lstrip("#").strip() for c in df.columns]
        dfs.append(df)
    return pd.concat(dfs, ignore_index=True)


# -----------------------------
# Step 3. Filters
# Invertebrate: Metazoa AND NOT Vertebrata
# Assembly level: Chromosome OR Complete Genome
# -----------------------------
def is_invertebrate(lineage_names):
    s = set(lineage_names)
    return ("Metazoa" in s) and ("Vertebrata" not in s)

def is_target_assembly_level(level: str):
    return level in {"Chromosome", "Complete Genome"}


# -----------------------------
# Main
# -----------------------------
def main(args):
    print("[INFO] Loading taxonomy...")
    get_lineage = load_taxonomy(args.nodes, args.names)

    print("[INFO] Loading assembly summaries...")
    asm = load_assembly_tables(args.assembly)

    # sanity check required columns
    required = {"assembly_accession", "taxid", "organism_name", "assembly_level"}
    missing = required - set(asm.columns)
    if missing:
        raise RuntimeError(
            f"[FATAL] Missing required columns in assembly_summary: {sorted(missing)}\n"
            f"Available columns: {list(asm.columns)}"
        )

    print("[INFO] Filtering: invertebrates + assembly_level in {Chromosome, Complete Genome} ...")

    records = []
    for _, r in asm.iterrows():
        # taxid can be numeric; keep as str
        taxid = str(r["taxid"]).strip()
        if taxid == "" or taxid.lower() == "nan":
            continue

        level = str(r["assembly_level"]).strip()
        if not is_target_assembly_level(level):
            continue

        lineage = get_lineage(taxid)
        if not is_invertebrate(lineage):
            continue

        records.append({
            "assembly_accession": r["assembly_accession"],   # GCA_... or GCF_...
            "organism_name": r["organism_name"],
            "taxid": taxid,
            "assembly_level": level,
            # keep lineage for audit / downstream debugging
            "lineage": ";".join(lineage),
        })

    out = pd.DataFrame(records).drop_duplicates(subset=["assembly_accession"])

    print(f"[INFO] Kept assemblies: {len(out)}")
    out.to_csv(args.output, sep="\t", index=False)
    print(f"[INFO] Output written to: {args.output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Filter NCBI assemblies: invertebrate (Metazoa not Vertebrata) "
                    "+ assembly_level in {Chromosome, Complete Genome}."
    )
    parser.add_argument(
        "--assembly",
        nargs="+",
        required=True,
        help="Paths to assembly_summary_genbank.txt and/or assembly_summary_refseq.txt"
    )
    parser.add_argument("--nodes", required=True, help="NCBI taxonomy nodes.dmp")
    parser.add_argument("--names", required=True, help="NCBI taxonomy names.dmp")
    parser.add_argument(
        "-o", "--output",
        default="invertebrate_chrom_or_complete_assemblies.tsv",
        help="Output TSV"
    )
    args = parser.parse_args()
    main(args)
