from datetime import datetime
from data.processing import build_yoy_mom_table, build_anomaly_yoy_mom_table


def export_html_report(merged_df, weight_df, health_df, period, pen_filter, batch_filter):
    sections = []
    sections.append("<html><head><meta charset='utf-8'>")
    sections.append("<style>body{font-family:sans-serif;margin:20px;background:#f8f9fa;color:#2c3e50}")
    sections.append("h1{color:#2c3e50;border-bottom:3px solid #4ecdc4;padding-bottom:10px}")
    sections.append("h2{color:#34495e;margin-top:30px}table{border-collapse:collapse;width:100%;margin:10px 0}")
    sections.append("th,td{border:1px solid #ddd;padding:8px;text-align:center}th{background:#4ecdc4;color:white}")
    sections.append("tr:nth-child(even){background:#f2f2f2}.positive{color:#27ae60}.negative{color:#e74c3c}</style>")
    sections.append("</head><body>")
    sections.append("<h1>🐄 养殖饲喂与体重变化分析报告</h1>")
    sections.append(f"<p>生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>")
    sections.append(f"<p>筛选条件 - 圈舍: {pen_filter or '全部'}, 批次: {batch_filter or '全部'}, 时段: 按{period}</p>")

    if merged_df is not None and len(merged_df) > 0:
        sections.append("<h2>📊 饲喂量同比环比</h2>")
        tbl = build_yoy_mom_table(merged_df, "total_feed_kg", period)
        sections.append(tbl.to_html(index=False, escape=False))

    if merged_df is not None and "anomaly_ratio" in merged_df.columns and merged_df["anomaly_ratio"].notna().any():
        sections.append("<h2>⚠️ 异常占比同比环比</h2>")
        tbl2 = build_anomaly_yoy_mom_table(merged_df, period)
        sections.append(tbl2.to_html(index=False, escape=False))

    sections.append("</body></html>")
    return "\n".join(sections)
