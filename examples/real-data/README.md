# Five real-data examples in Python and R

Each row shows the same data in both languages. [Python script](plots.py) · [R script](plots.R)

| Example | What the plot shows | Python PDF | R PDF |
|---|---|---|---|
| Tree scatter | Diameter and timber volume for 31 black cherry trees. The source field `Girth` is diameter. | [PDF](pdfs/python/trees_scatter.pdf) | [PDF](pdfs/r/trees_scatter.pdf) |
| Paired sleep | Extra hours of sleep for 10 participants under two drugs, with one line per participant and each drug's median and interquartile range. | [PDF](pdfs/python/sleep_paired.pdf) | [PDF](pdfs/r/sleep_paired.pdf) |
| Iris boxplot | Petal length for 150 flowers from three species, with individual observations, quartiles and medians. | [PDF](pdfs/python/iris_box.pdf) | [PDF](pdfs/r/iris_box.pdf) |
| PBMC3k marker dot plot | Mean log1p expression by colour and the fraction of cells with expression above zero by dot area, for eight reference annotations and 12 genes. | [PDF](pdfs/python/pbmc3k_dot.pdf) | [PDF](pdfs/r/pbmc3k_dot.pdf) |
| PBMC3k marker heatmap | The same mean log1p expression values on a positive colour scale. | [PDF](pdfs/python/pbmc3k_heatmap.pdf) | [PDF](pdfs/r/pbmc3k_heatmap.pdf) |

## Run the examples

Clone the repository and run these commands from its root. Follow the [installation instructions](../../README.md#install-the-current-python-or-r-source) for either language. The saved PDFs were generated with the [CellStyle v0.4.0 release assets](https://github.com/nbatada/cellstyle/releases/tag/v0.4.0).

### Python

Download the two small CSVs from a fixed Rdatasets revision, then run the script. The script uses `[export]` for PDF export and also writes a CellStyle receipt beside each PDF.

```bash
data_dir=$(mktemp -d)
rdatasets=https://raw.githubusercontent.com/vincentarelbundock/Rdatasets/1dcc2bf5f955cc1224a3e1307256e1fe86b68dae/csv/datasets
curl -fLsS "$rdatasets/trees.csv" -o "$data_dir/trees.csv"
curl -fLsS "$rdatasets/iris.csv" -o "$data_dir/iris.csv"
python examples/real-data/plots.py "$data_dir" real-data-python
```

The default 90 × 60 mm Python iris boxplot triggered Seaborn swarm-packing warnings for 28–32% of observations per species in the verified run. The plot still contained all 150 observations. The script uses a 180 × 105 mm canvas, which resolved the warnings by changing only the plot geometry.

### R

Install `ggbeeswarm` for the iris observation layer. R loads `trees`, `sleep` and `iris` from its built-in `datasets` package.

```r
install.packages("ggbeeswarm")
```

```bash
Rscript --vanilla examples/real-data/plots.R real-data-r
```

## Data sources

- Python loads the R `trees` and `iris` datasets via Rdatasets and the repository's existing Sleep CSV. The pinned CSVs were checked against R's built-in data. [Trees](https://stat.ethz.ch/R-manual/R-devel/library/datasets/html/trees.html) · [Iris](https://stat.ethz.ch/R-manual/R-devel/library/datasets/html/iris.html) · [Sleep](https://stat.ethz.ch/R-manual/R-devel/library/datasets/html/sleep.html) · [Sleep CSV](../sleep.csv)
- PBMC3k comes from 10x Genomics under CC BY 4.0. The two CSVs summarize 2,638 cells in Scanpy's processed tutorial dataset. Rows are the supplied `obs["louvain"]` reference annotations. For each annotation and gene, the values are the mean of the normalized log1p values in `.raw.X` and the fraction of cells in that annotation with values above zero. The CSVs contain group summaries. [10x Genomics dataset](https://www.10xgenomics.com/datasets/3-k-pbm-cs-from-a-healthy-donor-1-standard-1-1-0) · [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) · [Scanpy documentation](https://scanpy.scverse.org/en/stable/api/generated/scanpy.datasets.pbmc3k_processed.html) · [Mean CSV](inputs/mean_log1p_expression.csv) · [Fraction CSV](inputs/fraction_positive.csv)
- The processed source file has SHA-256 `0db367b991dd95809732b218539ede489bea99113807f62ebd7ccc970025fe38`. Both CSVs were checked against this file. [Processed H5AD](https://exampledata.scverse.org/scanpy/pbmc3k.h5ad)
