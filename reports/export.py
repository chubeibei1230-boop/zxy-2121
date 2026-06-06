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


def export_efficiency_brief(eff_df, pen_rank, batch_rank, summary, inefficient_pens, fluctuation_reasons, period, pen_filter, batch_filter):
    sections = []
    sections.append("<html><head><meta charset='utf-8'>")
    sections.append("<style>")
    sections.append("body{font-family:sans-serif;margin:20px;background:#f8f9fa;color:#2c3e50}")
    sections.append("h1{color:#2c3e50;border-bottom:3px solid #4ecdc4;padding-bottom:10px}")
    sections.append("h2{color:#34495e;margin-top:30px;border-left:4px solid #4ecdc4;padding-left:10px}")
    sections.append("h3{color:#34495e;margin-top:20px}")
    sections.append(".card{background:white;padding:15px;border-radius:8px;margin:10px 0;box-shadow:0 2px 4px rgba(0,0,0,0.1)}")
    sections.append(".card-row{display:flex;gap:15px;flex-wrap:wrap}")
    sections.append(".metric-card{background:white;padding:15px;border-radius:8px;flex:1;min-width:150px;text-align:center;box-shadow:0 2px 4px rgba(0,0,0,0.1)}")
    sections.append(".metric-value{font-size:24px;font-weight:bold;color:#2c3e50}")
    sections.append(".metric-label{color:#7f8c8d;font-size:14px;margin-top:5px}")
    sections.append(".good{color:#27ae60}.warning{color:#f39c12}.danger{color:#e74c3c}")
    sections.append("table{border-collapse:collapse;width:100%;margin:10px 0}")
    sections.append("th,td{border:1px solid #ddd;padding:10px;text-align:center}")
    sections.append("th{background:#4ecdc4;color:white}")
    sections.append("tr:nth-child(even){background:#f2f2f2}")
    sections.append(".alert{padding:12px;border-radius:6px;margin:8px 0}")
    sections.append(".alert-danger{background:#fdecea;border-left:4px solid #e74c3c}")
    sections.append(".alert-warning{background:#fff4e5;border-left:4px solid #f39c12}")
    sections.append(".alert-success{background:#eafaf1;border-left:4px solid #27ae60}")
    sections.append("</style></head><body>")

    sections.append("<h1>📋 饲喂效率与预警经营简报</h1>")
    sections.append(f"<p>生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>")
    sections.append(f"<p>统计周期: 按{period} | 圈舍: {pen_filter} | 批次: {batch_filter}</p>")

    if summary:
        sections.append("<h2>📊 核心指标概览</h2>")
        sections.append("<div class='card-row'>")
        sections.append(f"<div class='metric-card'><div class='metric-value'>{summary.get('avg_fcr', 0):.2f}</div><div class='metric-label'>平均料重比 {summary.get('fcr_status', '')}</div></div>")
        sections.append(f"<div class='metric-card'><div class='metric-value'>{summary.get('avg_daily_gain', 0):.3f} kg</div><div class='metric-label'>平均日增重 {summary.get('gain_status', '')}</div></div>")
        sections.append(f"<div class='metric-card'><div class='metric-value'>{summary.get('avg_anomaly_ratio', 0):.1f}%</div><div class='metric-label'>平均异常占比</div></div>")
        sections.append(f"<div class='metric-card'><div class='metric-value'>{summary.get('avg_feed_per_head', 0):.1f} kg</div><div class='metric-label'>单头饲喂量</div></div>")
        sections.append("</div>")

        sections.append("<div class='card'>")
        sections.append("<h3>🏆 最佳与最差表现</h3>")
        sections.append(f"<p>✅ 料重比最佳圈舍: <strong>{summary.get('best_pen_fcr', 'N/A')}</strong></p>")
        sections.append(f"<p>⚠️ 料重比最差圈舍: <strong>{summary.get('worst_pen_fcr', 'N/A')}</strong></p>")
        high_risk = summary.get('high_risk_pens', [])
        if high_risk:
            sections.append(f"<p>🔴 高风险圈舍: <strong>{', '.join(high_risk)}</strong></p>")
        sections.append("</div>")

    if fluctuation_reasons and len(fluctuation_reasons) > 0:
        sections.append("<h2>⚠️ 关键波动提示</h2>")
        for r in fluctuation_reasons:
            alert_class = "alert-danger" if r["type"] == "danger" else ("alert-warning" if r["type"] == "warning" else "alert-success")
            sections.append(f"<div class='alert {alert_class}'>")
            sections.append(f"<strong>{r['metric']} ({r['change']}):</strong> {r['reason']}")
            sections.append("</div>")

    if pen_rank is not None and len(pen_rank) > 0:
        sections.append("<h2>🏆 圈舍效率排行榜</h2>")
        display_pen = pen_rank[["pen_id", "avg_fcr", "avg_daily_gain", "avg_anomaly_ratio", "avg_feed_per_head"]].copy()
        display_pen.columns = ["圈舍", "平均料重比", "平均日增重(kg)", "异常占比(%)", "单头饲喂量(kg)"]
        display_pen = display_pen.round(2).sort_values("平均料重比")
        sections.append(display_pen.to_html(index=False, escape=False))

    if inefficient_pens is not None and len(inefficient_pens) > 0:
        sections.append("<h2>🚨 低效圈舍识别</h2>")
        display_ineff = inefficient_pens[["pen_id", "risk_level", "avg_fcr", "avg_daily_gain", "avg_anomaly_ratio", "warning_count"]].copy()
        display_ineff.columns = ["圈舍", "风险等级", "平均料重比", "平均日增重(kg)", "异常占比(%)", "预警项数"]
        display_ineff = display_ineff.round(2)
        sections.append(display_ineff.to_html(index=False, escape=False))

    if batch_rank is not None and len(batch_rank) > 0:
        sections.append("<h2>📦 批次效率对比</h2>")
        display_batch = batch_rank[["batch_id", "avg_fcr", "avg_daily_gain", "avg_anomaly_ratio", "avg_feed_per_head"]].copy()
        display_batch.columns = ["批次", "平均料重比", "平均日增重(kg)", "异常占比(%)", "单头饲喂量(kg)"]
        display_batch = display_batch.round(2)
        sections.append(display_batch.to_html(index=False, escape=False))

    if eff_df is not None and len(eff_df) > 0:
        sections.append("<h2>📈 效率明细数据</h2>")
        display_eff = eff_df[["period_label", "pen_id", "batch_id", "fcr", "daily_gain", "feed_per_head", "anomaly_ratio", "weight_gain"]].copy()
        display_eff.columns = ["时段", "圈舍", "批次", "料重比", "日增重(kg)", "单头饲喂量(kg)", "异常占比(%)", "周期增重(kg)"]
        display_eff = display_eff.round(2)
        sections.append(display_eff.to_html(index=False, escape=False))

    sections.append("</body></html>")
    return "\n".join(sections)
