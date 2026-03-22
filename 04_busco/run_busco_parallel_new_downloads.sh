#!/usr/bin/env bash
# 对「新下载」的组装（默认读 test.tsv：assembly_accession<TAB>taxid）批量跑 BUSCO。
#
# 结果输出位置与历史上已跑完的 BUSCO 一致（不含 genomes/ 前缀）：
#   /data/fengwei/download/<taxid>/ncbi_dataset/data/<assembly>/result/run_metazoa_odb10/
#
# 输入基因组 FASTA：优先从「新下载」所在目录读：
#   /data/fengwei/download/genomes/<taxid>/ncbi_dataset/data/<assembly>/*.fna
# 若不存在，再尝试与输出同一路径下的 fna（兼容数据只放在旧目录的情况）。
#
# 修正说明（相对手写 parallel 一行命令）：
#   - 使用 find 得到具体 fna，避免引号内 {1}*.fna 无法展开；
#   - 使用 -o result + --out_path <组装目录>，与 BUSCO 6 语义一致。
#
# 用法：
#   cd /data/fengwei/download
#   ./run_busco_parallel_new_downloads.sh
#   ./run_busco_parallel_new_downloads.sh my_new.tsv
#   JOBS=16 CPU_PER_JOB=16 ./run_busco_parallel_new_downloads.sh test.tsv
#
# 依赖：conda（busco6）、GNU parallel

set -euo pipefail

INPUT="${1:-test.tsv}"
# 新下载的 fna 通常在此树下
GENOMES_BASE="/data/fengwei/download/genomes"
# 与历史 BUSCO 完成样本一致的输出根（顶层 taxid，无 genomes）
OUT_BASE="/data/fengwei/download"
DB="/data/fengwei/busco_db/busco_downloads/lineages/metazoa_odb10"
JOBS="${JOBS:-8}"
CPU_PER_JOB="${CPU_PER_JOB:-12}"
RUN_NAME="result"

if [[ ! -f "$INPUT" ]]; then
  echo "[FATAL] 找不到列表文件: $INPUT" >&2
  exit 1
fi
if [[ ! -d "$DB" ]]; then
  echo "[FATAL] 找不到 lineage: $DB" >&2
  exit 1
fi

if ! command -v conda >/dev/null 2>&1; then
  echo "[FATAL] conda 不在 PATH 中" >&2
  exit 1
fi
# shellcheck source=/dev/null
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate busco6
BUSCO_BIN="${CONDA_PREFIX}/bin/busco"
echo "[INFO] $("$BUSCO_BIN" --version 2>&1 | tail -1)"

run_one() {
  local assembly="$1"
  local taxid="$2"
  local adir_g="${GENOMES_BASE}/${taxid}/ncbi_dataset/data/${assembly}"
  local adir_out="${OUT_BASE}/${taxid}/ncbi_dataset/data/${assembly}"

  local search_root=""
  if [[ -d "$adir_g" ]]; then
    search_root="$adir_g"
  elif [[ -d "$adir_out" ]]; then
    search_root="$adir_out"
  else
    echo "[WARN] 无组装目录（genomes 与历史路径均不存在）: ${assembly} taxid=${taxid}" >&2
    return 0
  fi

  local fna=""
  fna="$(find "$search_root" -maxdepth 1 -type f -name "${assembly}*.fna" 2>/dev/null | sort | head -n 1 || true)"
  if [[ -z "$fna" ]]; then
    fna="$(find "$search_root" -type f -name "${assembly}*.fna" 2>/dev/null | sort | head -n 1 || true)"
  fi
  if [[ -z "$fna" ]]; then
    echo "[WARN] 无 fna: taxid=${taxid} assembly=${assembly}（已查 ${search_root}）" >&2
    return 0
  fi

  # 保证输出目录存在，且 BUSCO 写在「历史格式」路径下
  mkdir -p "$adir_out"

  if [[ -f "${adir_out}/${RUN_NAME}/run_metazoa_odb10/short_summary.txt" ]]; then
    echo "[SKIP] 已有 result/run_metazoa_odb10: ${assembly}" >&2
    return 0
  fi

  "$BUSCO_BIN" \
    -i "$fna" \
    -l "$DB" \
    -f \
    -o "$RUN_NAME" \
    --out_path "$adir_out" \
    -m genome \
    -c "$CPU_PER_JOB"
}

export -f run_one
export GENOMES_BASE OUT_BASE DB CPU_PER_JOB RUN_NAME BUSCO_BIN

awk -F'\t' 'NR==1{if(tolower($0) ~ /assembly|taxid/){next}} NF>=2{print $1"\t"$2}' "$INPUT" | \
  parallel -j "$JOBS" --colsep '\t' run_one {1} {2}

echo "[OK] 完成。"
