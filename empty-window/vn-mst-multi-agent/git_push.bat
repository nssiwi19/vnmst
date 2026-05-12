@echo off
cd /d "c:\Users\Admin\.cursor\projects\empty-window\vn-mst-multi-agent"
git add -A
git commit -m "feat: Elite-DA Analytics Dashboard - storytelling charts, global filter sync, data quality audit

- Add 4 new storytelling charts: Monthly Heatmap, YoY Growth Rate, Industry Donut, Data Quality Gauges
- Global Filter Bar (Year + Industry) syncs all 8 charts simultaneously
- Backend: Full 12k+ record pagination for accurate stats
- Backend: Dynamic summary (top_industry, industry_share computed from real data)
- Backend: New endpoints /monthly-distribution and /data-quality with filter support
- Frontend: Grid symmetry fix (1.4fr/0.6fr + alignItems stretch)
- Frontend: Industry Top 50 in filter, Top 10 in display chart
- Fix: CSS rgba bug, colSpan mismatch, duplicate API calls removed
- Fix: Duplicate @app.get decorator removed"
git push origin main
echo.
echo Done! Check https://github.com/nssiwi19/vnmst
pause
