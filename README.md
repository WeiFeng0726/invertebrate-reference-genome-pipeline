# Invertebrate reference genomes: filtering, download, and BUSCO

本仓库整理自项目工作流脚本，用于从 NCBI 组装信息中筛选**无脊椎动物**（Metazoa 且非 Vertebrata）、下载参考基因组，并用 **BUSCO**（metazoa_odb10）评估组装完整度。便于论文发表后他人复现；使用前请根据本机路径修改脚本中的目录常量。

**English:** Scripts to (1) filter NCBI assemblies to non-vertebrate metazoans, (2) download genomes with NCBI `datasets`, (3) enrich metadata / RNA-seq hints, (4) run BUSCO metazoa. Paths are currently absolute for a Linux workstation—replace `/data/fengwei/...` for your environment.

---

## 目录结构

| 目录 | 内容 |
|------|------|
| `01_taxonomy_filter/` | 基于 `nodes.dmp` / `names.dmp` + `assembly_summary` 筛选无脊椎、染色体/完整基因组级别组装 |
| `02_download/` | `datasets` 下载基因组（含 gff3 请求）、断点续传、失败重试 |
| `03_metadata/` | 对 GCA 调用 `datasets summary`，补充 RefSeq 配对与 RNA-seq 相关标记 |
| `04_busco/` | BUSCO 批量评估（含与历史输出路径一致的新下载批处理） |
| `config/` | 路径变量示例 `paths.env.example`（可选） |

---

## 依赖

- **系统：** `bash`，GNU **parallel**，**unzip**，[NCBI datasets CLI](https://www.ncbi.nlm.nih.gov/datasets/docs/v2/)（`datasets`）
- **Python：** 见 `requirements.txt`（主要为 **pandas**，用于分类筛选脚本）
- **BUSCO：** Conda 环境示例名 `busco6`；本地 lineage 目录示例：`.../busco_downloads/lineages/metazoa_odb10`
- **输入数据（需自行从 NCBI 获取）：**
  - Taxonomy：`nodes.dmp`，`names.dmp`（taxonomy dump）
  - 组装：`assembly_summary_genbank.txt`，`assembly_summary_refseq.txt`（或其一）

---

## 推荐分析顺序

1. **筛选无脊椎组装**（二选一或组合使用）  
   - `01_taxonomy_filter/filter.ncbi.py`：Metazoa ∩ ¬Vertebrata，组装级别为 **Chromosome 或 Complete Genome** → 如 `invertebrate_chrom_or_complete_assemblies.tsv`  
   - `01_taxonomy_filter/ncbi_inverterbrate.py`：更严，仅 **Chromosome** → 如 `invertebrate_assembly_pairs.tsv`

2. **整理下载列表**  
   - 生成两列 TSV：`assembly_accession`、 `taxid`（如 `assemblies.tsv`），供下载与下游使用。

3. **下载基因组**（在存放 `assemblies.tsv` 的工作目录执行）  
   - `02_download/download_ncbi_assemblies.py`：含「已有 fna 则跳过」  
   - `02_download/down_file.py`：无跳过逻辑的简单版  
   - `02_download/retry_failed_downloads.py`：仅重试未成功解压出 FASTA 的条目  

4. **（可选）元数据**  
   - `03_metadata/search_ncbi.py`：读入 `assemblies.tsv`，写出 `assemblies.with_gcf_and_rnaseq.tsv`（需联网调用 `datasets summary`）。

5. **BUSCO**  
   - `04_busco/run_busco.sh`：对 `genomes/<taxid>/ncbi_dataset/data/<assembly>/` 下 fna 跑 BUSCO，输出 `genome_busco_metazoa/`（参数见脚本内 `TSV`、`BASE`、`DB`）。  
   - `04_busco/run_busco_pending_genomes.sh`：激活 `busco6`，同上逻辑，可 `--only-list` 限制组装列表。  
   - `04_busco/run_busco_parallel_new_downloads.sh`：针对「新下载」列表（如 `test.tsv`），FASTA 可从 `genomes/` 读取，**结果写入与历史一致**：`/.../download/<taxid>/ncbi_dataset/data/<assembly>/result/run_metazoa_odb10/`。  
   - `04_busco/remove_GCA_963555665_directory.sh`：单次失败目录清理示例，一般需改为自己的路径或删除。

---

## 安装 Python 依赖

```bash
cd /path/to/this/repo   # 即包含 requirements.txt 的目录
python3 -m pip install -r requirements.txt
```

---

## 复现时的路径修改

脚本中多处使用绝对路径（例如 `/data/fengwei/download`、`/data/fengwei/busco_db/...`）。在他机复现时请：

- 全局替换为你的项目根目录，或  
- 按 `config/paths.env.example` 自行改为从环境变量读取（需对脚本做小改动）。

---

## 引用

若使用 **BUSCO**，请遵循 [BUSCO 官方引用说明](https://gitlab.com/ezlab/busco)；若使用 **NCBI Datasets**，请引用 NCBI 相应说明。

---

## 许可

脚本版权归原作者；若上传 GitHub，请自行添加 `LICENSE` 文件。
