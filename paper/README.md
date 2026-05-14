# 论文编译指南

## 快速编译

```bash
cd paper/
pdflatex main.tex
bibtex main
pdflatex main.tex
pdflatex main.tex
```

需要运行两次 `pdflatex` 以正确解析交叉引用。

## 依赖

- LaTeX 发行版：TeX Live 2023+ 或 MikTeX
- 必需宏包：IEEEtran, cite, amsmath, graphicx, booktabs, listings, hyperref

### macOS 安装

```bash
brew install --cask mactex
# 或轻量版（推荐，更快）：
brew install --cask basictex
sudo tlmgr update --self
sudo tlmgr install IEEEtran booktabs listings
```

### Ubuntu 安装

```bash
sudo apt install texlive-latex-recommended texlive-publishers texlive-science
```

## 添加图片

将图片放入 `figures/` 目录，在 LaTeX 中引用：

```latex
\begin{figure}[t]
\centering
\includegraphics[width=\columnwidth]{figures/architecture.pdf}
\caption{System architecture overview.}
\label{fig:architecture}
\end{figure}
```

推荐图片格式：PDF（矢量图）或 PNG（截图，300 DPI）。

## 建议添加的图片

1. **figures/architecture.pdf** — 三层架构图（Python API / 3we-core / ROS2）
2. **figures/sim2real.pdf** — 同一代码在 mock/gazebo/real 三后端的截图对比
3. **figures/hardware.pdf** — 参考硬件照片或 3D 渲染（如果有实物）
4. **figures/benchmark.pdf** — Benchmark 结果柱状图

## 提交 arXiv

1. 将整个 `paper/` 目录打包为 `.tar.gz`（不含 PDF 输出）
2. 上传至 arxiv.org → New Submission
3. 分类选择：`cs.RO`（Primary），`cs.AI`（Secondary）
4. 填写 Abstract（直接复制 LaTeX 中的 abstract 内容）

## 字数参考

当前论文框架约 6 页（IEEE 双栏格式），符合 ICRA/IROS 页数限制。
arXiv 本身无页数限制，但建议控制在 4-8 页以保持可读性。
