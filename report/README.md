# LaTeX report

Compile the technical report from this directory:

```cmd
pdflatex NASADIYA_LIGHTCONE_Project_Report.tex
bibtex NASADIYA_LIGHTCONE_Project_Report
pdflatex NASADIYA_LIGHTCONE_Project_Report.tex
pdflatex NASADIYA_LIGHTCONE_Project_Report.tex
```

Or, where available:

```cmd
latexmk -pdf NASADIYA_LIGHTCONE_Project_Report.tex
```

The report documents software design and current data products. It is not a peer-reviewed cosmology analysis and does not replace the original survey papers or data-release documentation.
