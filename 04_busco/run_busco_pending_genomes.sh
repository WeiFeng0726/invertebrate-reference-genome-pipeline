#!/usr/bin/env bash
# 在 conda 环境 busco6 下，对「已有 *_genomic.fna 且尚未有本脚本约定之 BUSCO 输出」的组装运行 BUSCO。
# 参数与路径与 genomes/run_busco.sh 一致：输出在
#   <BASE>/<taxid>/ncbi_dataset/data/<assembly>/genome_busco_metazoa/
#
# 用法：
#   cd /data/fengwei/download
#   ./run_busco_pending_genomes.sh --dry-run
#   ./run_busco_pending_genomes.sh
#   # 仅对「新下载」的组装 accession 列表跑（每行一个 GCA_.../GCF_...，见 new_assemblies_for_busco.example.txt）
#   ./run_busco_pending_genomes.sh --only-list new_assemblies_for_busco.txt --dry-run
#   ./run_busco_pending_genomes.sh --only-list new_assemblies_for_busco.txt
#
# 注意：若不使用 --only-list，会对 TSV 中所有「有 fna 且无 genome_busco_metazoa/short_summary*.txt」的组装跑 BUSCO，
#       数量可能接近全库；首次大规模跑前请先用 --dry-run 看数量。
#
# 依赖：conda（含 busco6）、GNU parallel

set -euo pipefail

TSV="/data/fengwei/download/assemblies.tsv"
BASE="/data/fengwei/download/genomes"
DB="/data/fengwei/busco_db/busco_downloads/lineages/metazoa_odb10"

CPU_PER_JOB="${CPU_PER_JOB:-12}"
JOBS="${JOBS:-8}"
RUN_NAME="genome_busco_metazoa"

DRY_RUN=0
ONLY_LIST=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    --only-list)
      ONLY_LIST="${2:-}"
      if [[ -z "$ONLY_LIST" ]]; then
        echo "[FATAL] --only-list requires a file path" >&2
        exit 1
      fi
      shift 2
      ;;
    *)
      echo "[FATAL] unknown argument: $1 (use --dry-run, --only-list FILE)" >&2
      exit 1
      ;;
  esac
done
# 允许两种顺序：--dry-run --only-list f 与 --only-list f --dry-run（上面已统一解析）

# 与 download_ncbi_assemblies / run_busco.sh 一致：必须用绝对路径作为 --out_path，避免误嵌套目录
if [[ ! -f "$TSV" ]]; then
  echo "[FATAL] TSV not found: $TSV" >&2
  exit 1
fi
if [[ ! -d "$DB" ]]; then
  echo "[FATAL] BUSCO lineage not found: $DB" >&2
  exit 1
fi

# 激活 busco6（与你在终端中手动激活等价）
if ! command -v conda >/dev/null 2>&1; then
  echo "[FATAL] conda not in PATH" >&2
  exit 1
fi
# shellcheck source=/dev/null
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate busco6

if ! command -v busco >/dev/null 2>&1; then
  echo "[FATAL] busco not found after: conda activate busco6" >&2
  exit 1
fi
# parallel 子进程里 PATH 可能不含 conda，用绝对路径调用
BUSCO_BIN="${CONDA_PREFIX}/bin/busco"
echo "[INFO] using ${BUSCO_BIN}"
echo "[INFO] $("$BUSCO_BIN" --version 2>&1 | tail -1)"

run_one() {
  local assembly="$1"
  local taxid="$2"

  local adir="${BASE}/${taxid}/ncbi_dataset/data/${assembly}"
  if [[ ! -d "$adir" ]]; then
    echo "[WARN] missing dir: taxid=${taxid} assembly=${assembly}" >&2
    return 0
  fi

  local fna=""
  fna="$(find "$adir" -maxdepth 1 -type f -name "${assembly}*.fna" 2>/dev/null | sort | head -n 1 || true)"
  if [[ -z "$fna" ]]; then
    fna="$(find "$adir" -type f -name "${assembly}*.fna" 2>/dev/null | sort | head -n 1 || true)"
  fi

  if [[ -z "$fna" ]]; then
    echo "[WARN] missing fna: taxid=${taxid} assembly=${assembly}" >&2
    return 0
  fi

  # 与 genomes/run_busco.sh 一致：存在 short_summary*.txt 即视为已完成
  if compgen -G "${adir}/${RUN_NAME}"/short_summary.*.txt >/dev/null 2>&1; then
    echo "[SKIP] BUSCO already present: taxid=${taxid} assembly=${assembly}" >&2
    return 0
  fi

  if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "[DRY-RUN] would run BUSCO: taxid=${taxid} assembly=${assembly} fna=${fna}" >&2
    return 0
  fi

  "$BUSCO_BIN" \
    -i "$fna" \
    -l "$DB" \
    -o "$RUN_NAME" \
    --out_path "$adir" \
    -m genome \
    -c "$CPU_PER_JOB"
}

export -f run_one
export TSV BASE DB CPU_PER_JOB RUN_NAME DRY_RUN BUSCO_BIN

if [[ -n "$ONLY_LIST" ]]; then
  if [[ ! -f "$ONLY_LIST" ]]; then
    echo "[FATAL] --only-list file not found: $ONLY_LIST" >&2
    exit 1
  fi
  echo "[INFO] restricting to assemblies listed in: $ONLY_LIST"
fi

if [[ "$DRY_RUN" -eq 1 ]]; then
  echo "[INFO] dry-run: listing assemblies that would run (have fna, no ${RUN_NAME}/short_summary.*.txt)"
fi

# 输出 assembly\\ttaxid；若给定 ONLY_LIST，只保留列表中出现的 accession（忽略空行与 # 注释）
FILTER_AWK='NR==1{if(tolower($0) ~ /assembly|taxid/){next}} NF>=2{print $1"\t"$2}'
if [[ -n "$ONLY_LIST" ]]; then
  awk -F'\t' "$FILTER_AWK" "$TSV" | awk -F'\t' -v listfile="$ONLY_LIST" '
    BEGIN {
      while ((getline line < listfile) > 0) {
        sub(/^[[:space:]]+|[[:space:]]+$/, "", line)
        if (line == "" || line ~ /^#/) continue
        allow[line] = 1
      }
      close(listfile)
    }
    $1 in allow { print }
  ' | parallel -j "$JOBS" --colsep '\t' run_one {1} {2}
else
  awk -F'\t' "$FILTER_AWK" "$TSV" | parallel -j "$JOBS" --colsep '\t' run_one {1} {2}
fi

echo "[OK] done."
