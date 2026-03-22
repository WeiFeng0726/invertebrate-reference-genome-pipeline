#!/usr/bin/env bash
set -euo pipefail

TSV="/data/fengwei/download/assemblies.tsv"
BASE="/data/fengwei/download/genomes"
DB="/data/fengwei/busco_db/busco_downloads/lineages/metazoa_odb10"

CPU_PER_JOB=12
JOBS=8
RUN_NAME="genome_busco_metazoa"

run_one() {
  local assembly="$1"
  local taxid="$2"

  local adir="${BASE}/${taxid}/ncbi_dataset/data/${assembly}"
  if [[ ! -d "$adir" ]]; then
    echo "[WARN] missing dir: taxid=${taxid} assembly=${assembly} dir=${adir}" >&2
    return 0
  fi

  # 只在 assembly 目录下找：GCA_xxx*.fna
  local fna=""
  fna="$(find "$adir" -maxdepth 1 -type f -name "${assembly}*.fna" | sort | head -n 1 || true)"

  # 若这一层找不到，则递归兜底找一次
  if [[ -z "$fna" ]]; then
    fna="$(find "$adir" -type f -name "${assembly}*.fna" | sort | head -n 1 || true)"
  fi

  if [[ -z "$fna" ]]; then
    echo "[WARN] missing fna: taxid=${taxid} assembly=${assembly} dir=${adir}" >&2
    return 0
  fi

  # 已经跑过就跳过：只要存在 short_summary 就认为完成过
  if ls "${adir}/${RUN_NAME}"/short_summary.*.txt >/dev/null 2>&1; then
    echo "[SKIP] exists: taxid=${taxid} assembly=${assembly}" >&2
    return 0
  fi

  busco \
    -i "$fna" \
    -l "$DB" \
    -o "$RUN_NAME" \
    --out_path "$adir" \
    -m genome \
    -c "$CPU_PER_JOB"
}

export -f run_one
export TSV BASE DB CPU_PER_JOB JOBS RUN_NAME

# 自动跳过表头（如果第一行包含 assembly 或 taxid）
awk -F'\t' 'NR==1{if(tolower($0) ~ /assembly|taxid/){next}} NF>=2{print $1"\t"$2}' "$TSV" | \
  parallel -j "$JOBS" --colsep '\t' run_one {1} {2}
