#!/usr/bin/env bash
# 删除下载失败的组装目录（taxid 1349872 仅对应这一条记录）。
# 执行前请自行确认路径；不会修改 assemblies.tsv（若需从列表中剔除该行，见脚本末尾说明）。
set -euo pipefail

TARGET="/data/fengwei/download/genomes/1349872/ncbi_dataset/data/GCA_963555665.1"

if [[ ! -d "$TARGET" ]]; then
  echo "[INFO] 目录不存在，跳过: $TARGET"
  exit 0
fi

echo "[INFO] 将删除: $TARGET"
rm -rf "$TARGET"
echo "[OK] 已删除。"

cat <<'EOF'

可选：若希望不再被 retry / 全量下载脚本命中，请从 assemblies.tsv 中删除这一行：
  GCA_963555665.1	1349872

例如（请先备份 assemblies.tsv）：
  grep -v $'GCA_963555665.1\t1349872' assemblies.tsv > assemblies.tsv.tmp && mv assemblies.tsv.tmp assemblies.tsv

EOF
