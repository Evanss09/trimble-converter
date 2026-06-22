# Trimble Converter

Turns Trimble AutoBid raw exports — **sheet metal or plumbing** — into a tight
**Excel workbook** and **PDF**, sorted by floor, system, size, spec/gauge, and
drawing with subtotals at the bottom of each section. The trade is detected
automatically. Drop **several files at once** to combine a big multi-area job, or
to put plumbing and sheet metal into one report as separate sections.

Runs entirely offline. No internet, no Python, no AI connection required.

The desktop app uses a dark "mint" dashboard (Space Grotesk + IBM Plex Mono,
fonts bundled). The generated **reports keep the VR brand** (red, Manrope +
Poppins) — the app skin and the deliverables are intentionally separate.

## Use it (no install)

1. Download **Trimble Converter.exe** from the Releases page.
2. Double-click it. A dashboard home screen opens.
3. Choose one or more raw exports (`.xlsx` / `.xlsm`). Each is tagged Plumbing or
   Sheet Metal. Pick units (Auto is fine) and outputs, then **Generate report**.
4. KPI tiles appear per trade; use **Open Excel / Open PDF / Open folder**.

Output names: `<BidName> - Takeoff Summary.{xlsx,pdf}` for one file, or
`<BidName> - Combined Takeoff Summary.{xlsx,pdf}` when several are combined.

**Combining files.** Drop several at once and they become one report: same-trade
files merge into one section (with a By source/area breakdown), and plumbing vs
sheet metal stay as separate sections in the same workbook / PDF, each with its
own units and metrics.

The dashboard uses the Windows **WebView2** runtime, which is built into
Windows 11 and already present on most updated Windows 10 machines. If a machine
does not have it, the app automatically falls back to a simple built-in window
with the same buttons, so it always works. (Old Windows 10 only: install the
free WebView2 runtime from Microsoft once.)

## Units (metric or imperial)

The tool auto-detects whether a project is metric or imperial from the duct
sizes and labels the columns accordingly (kg / m / m² or lb / ft / ft²). It does
not convert the numbers; Trimble already exports them in the project's units, so
this only fixes the labels. Override with the Units selector or `--units`.

## What's in the report

**Sheet metal:** Summary (KPIs incl. $/ft²), Floor → System → Size (collapsible,
subtotals), By Spec/Gauge, By Size, By Drawing.
Material $ = Fab + Purchase + Quote; Labour Hrs = Adjusted Shop + Field + hand
hours.

**Plumbing:** Summary (KPIs incl. $/hr), an overview by System (Material $,
Mat %, Labour Hrs, Lab %) that drills into per-system **line-item detail**
(Qty, price/ea, mult %, net/ea, hrs/ea, total material, total hours), plus By
Trade (Plumbers vs Fitters) and By Drawing.
Material $ = Material Dollars; Labour Hrs = Hours (the reliable labour metric;
Labour $ is shown only when the export populates it).

Every view reconciles to the same segment total. Units auto-detect per file.

## Command line (optional)

```
"Trimble Converter.exe" "raw.xlsx"                         # one file, Excel + PDF
"Trimble Converter.exe" "plumb.xlsm" "sheetmetal.xlsx" -o "C:\out"   # combined
"Trimble Converter.exe" "a.xlsx" "b.xlsx" --separate       # one report per file
"Trimble Converter.exe" "raw.xlsx" --pdf-only --units metric
```

## Run from source

```
pip install -r requirements.txt
python -m ductsort "Raw Data.xlsx"
```

## Build the .exe

```
pip install pyinstaller
powershell -ExecutionPolicy Bypass -File build\build_exe.ps1
```
The single file appears at `dist\Trimble Converter.exe`.

## Input assumptions

The AutoBid raw export carries a data sheet (`RawDataSM` for sheet metal, `Raw
Data` for plumbing) with a header row matched by column name, plus a `Summary`
sheet (or `QPSummary` defined names) with the bid name/number. The data sheet is
found by its columns, so it works even in the "Pivot" layout where it sits far
right among many extra tabs. The trade is detected from the columns. Amounts vary
project to project; the layout does not.

## Project layout

```
ductsort/        the converter package
  trades.py        trade profiles (sheet metal / plumbing): columns, measures,
                   report columns, hierarchy, breakdowns, KPIs + trade detection
  reader.py        find the raw sheet anywhere, detect trade, map by name
  model.py         shared helpers: measures, size normalization, sort, formatting
  units.py         metric/imperial detection + measure labels
  aggregate.py     one rollup engine used by every view
  views.py         builds all breakdowns once, from one grand total
  excel_report.py  branded workbook (collapsible groups, subtotals)
  pdf_report.py    branded PDF (VR header bar + red triangle, embedded fonts)
  gui.py           pywebview dashboard host (Api exposed to the web UI)
  gui_tk.py        Tkinter fallback home screen (no WebView2 needed)
  cli.py / __main__.py            command line and double-click dispatch
  web/             dashboard HTML/CSS/JS + web/fonts (Space Grotesk, IBM Plex Mono)
  fonts/           Manrope + Poppins (embedded in the PDF report)
build/build_exe.ps1   PyInstaller build script
run.py                .exe entry point
```


