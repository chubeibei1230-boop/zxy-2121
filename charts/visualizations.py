import plotly.express as px
import plotly.graph_objects as go
from data.processing import add_period_columns


def _format_period_label(period_date, period):
    if period == "月":
        return period_date.strftime("%Y-%m")
    else:
        return period_date.strftime("W%W %Y")


def chart_feeding_trend(merged_df, period):
    metric = "total_feed_kg"
    df_period = add_period_columns(merged_df, period)
    agg = df_period.groupby("period").agg({metric: "sum"}).reset_index().sort_values("period")
    agg["period_label"] = agg["period"].apply(lambda x: _format_period_label(x, period))
    fig = go.Figure()
    fig.add_trace(go.Bar(x=agg["period_label"], y=agg[metric], name="饲喂量(kg)", marker_color="#4ECDC4"))
    if len(agg) > 1:
        change = agg[metric].pct_change() * 100
        fig.add_trace(go.Scatter(
            x=agg["period_label"], y=change, name="环比变化(%)",
            yaxis="y2", mode="lines+markers", line=dict(color="#FF6B6B", width=2),
        ))
    fig.update_layout(
        title=f"饲喂量趋势（按{period}）",
        xaxis_title=period, yaxis_title="饲喂量(kg)",
        yaxis2=dict(title="环比变化(%)", overlaying="y", side="right", showgrid=False),
        template="plotly_white", height=400,
    )
    return fig


def chart_weight_trend(weight_df, period):
    df_period = add_period_columns(weight_df, period)
    agg = df_period.groupby("period").agg(
        avg_weight=("weight_kg", "mean"),
        min_weight=("weight_kg", "min"),
        max_weight=("weight_kg", "max"),
    ).reset_index().sort_values("period")
    agg["period_label"] = agg["period"].apply(lambda x: _format_period_label(x, period))
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=agg["period_label"], y=agg["max_weight"], name="最大体重", mode="lines", line=dict(width=0), showlegend=True))
    fig.add_trace(go.Scatter(x=agg["period_label"], y=agg["min_weight"], name="最小体重", mode="lines", fill="tonexty", fillcolor="rgba(78,205,196,0.2)", line=dict(width=0), showlegend=True))
    fig.add_trace(go.Scatter(x=agg["period_label"], y=agg["avg_weight"], name="平均体重", mode="lines+markers", line=dict(color="#2C3E50", width=3)))
    fig.update_layout(
        title=f"体重变化趋势（按{period}）",
        xaxis_title=period, yaxis_title="体重(kg)",
        template="plotly_white", height=400,
    )
    return fig


def chart_anomaly_ratio(merged_df, period):
    df_period = add_period_columns(merged_df, period)
    agg = df_period.groupby("period").agg(
        total=("total_records", "sum"),
        anomaly=("anomaly_count", "sum"),
    ).reset_index()
    agg["ratio"] = agg["anomaly"] / agg["total"].replace(0, 1) * 100
    agg = agg.sort_values("period")
    agg["period_label"] = agg["period"].apply(lambda x: _format_period_label(x, period))
    fig = go.Figure()
    fig.add_trace(go.Bar(x=agg["period_label"], y=agg["ratio"], name="异常占比(%)", marker_color="#E74C3C"))
    fig.add_trace(go.Scatter(x=agg["period_label"], y=agg["anomaly"], name="异常头数", yaxis="y2", mode="lines+markers", line=dict(color="#F39C12")))
    fig.update_layout(
        title=f"异常占比趋势（按{period}）",
        xaxis_title=period, yaxis_title="异常占比(%)",
        yaxis2=dict(title="异常头数", overlaying="y", side="right", showgrid=False),
        template="plotly_white", height=400,
    )
    return fig


def chart_pen_comparison(merged_df, metric_col, period):
    df_period = add_period_columns(merged_df, period)
    agg = df_period.groupby(["pen_id", "period"]).agg({metric_col: "sum"}).reset_index()
    agg["period_label"] = agg["period"].apply(lambda x: _format_period_label(x, period))
    fig = px.bar(agg, x="period_label", y=metric_col, color="pen_id", barmode="group",
                 title=f"各圈舍{metric_col}对比（按{period}）", template="plotly_white")
    fig.update_layout(height=400)
    return fig


def chart_efficiency_ranking(pen_rank, metric="avg_fcr", ascending=True, top_n=10):
    if pen_rank is None or len(pen_rank) == 0:
        return go.Figure()
    df = pen_rank.sort_values(metric, ascending=ascending).head(top_n)
    metric_label = {
        "avg_fcr": "平均料重比",
        "avg_daily_gain": "平均日增重(kg)",
        "avg_anomaly_ratio": "平均异常占比(%)",
        "avg_feed_per_head": "单头饲喂量(kg)",
    }.get(metric, metric)
    colors = ["#27AE60" if ascending and i < 3 else ("#E74C3C" if not ascending and i < 3 else "#3498DB") for i in range(len(df))]
    fig = go.Figure(go.Bar(
        x=df[metric], y=df["pen_id"], orientation="h",
        marker_color=colors, text=df[metric].round(2), textposition="auto"
    ))
    fig.update_layout(
        title=f"圈舍{metric_label}排行榜",
        xaxis_title=metric_label, yaxis_title="圈舍",
        template="plotly_white", height=400,
        yaxis=dict(autorange="reversed")
    )
    return fig


def chart_fcr_trend(eff_df, period):
    if eff_df is None or len(eff_df) == 0:
        return go.Figure()
    agg = eff_df.groupby("period_label").agg(
        avg_fcr=("fcr", "mean"),
        avg_daily_gain=("daily_gain", "mean"),
    ).reset_index()
    fig = go.Figure()
    fig.add_trace(go.Bar(x=agg["period_label"], y=agg["avg_fcr"], name="料重比", marker_color="#4ECDC4", opacity=0.7))
    fig.add_trace(go.Scatter(
        x=agg["period_label"], y=agg["avg_daily_gain"], name="日增重(kg)",
        yaxis="y2", mode="lines+markers", line=dict(color="#E74C3C", width=3)
    ))
    fig.update_layout(
        title=f"料重比与日增重趋势（按{period}）",
        xaxis_title=period, yaxis_title="料重比",
        yaxis2=dict(title="日增重(kg)", overlaying="y", side="right", showgrid=False),
        template="plotly_white", height=400,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    return fig


def chart_feed_per_head_trend(eff_df, period):
    if eff_df is None or len(eff_df) == 0:
        return go.Figure()
    agg = eff_df.groupby(["period_label", "pen_id"]).agg(
        avg_feed_per_head=("feed_per_head", "mean"),
    ).reset_index()
    fig = px.line(agg, x="period_label", y="avg_feed_per_head", color="pen_id",
                  markers=True, title=f"各圈舍单头饲喂量趋势（按{period}）", template="plotly_white")
    fig.update_layout(yaxis_title="单头饲喂量(kg)", xaxis_title=period, height=400)
    return fig


def chart_anomaly_vs_efficiency(eff_df):
    if eff_df is None or len(eff_df) == 0:
        return go.Figure()
    fig = px.scatter(eff_df, x="anomaly_ratio", y="fcr", color="pen_id",
                     size="daily_gain", hover_data=["period_label", "batch_id"],
                     title="异常占比 vs 料重比关联分析",
                     labels={"anomaly_ratio": "异常占比(%)", "fcr": "料重比", "daily_gain": "日增重"},
                     template="plotly_white")
    fig.update_layout(height=400)
    return fig


def chart_efficiency_heatmap(eff_df, metric="fcr"):
    if eff_df is None or len(eff_df) == 0:
        return go.Figure()
    pivot = eff_df.pivot_table(index="pen_id", columns="period_label", values=metric, aggfunc="mean")
    metric_label = {"fcr": "料重比", "daily_gain": "日增重", "anomaly_ratio": "异常占比(%)"}.get(metric, metric)
    fig = go.Figure(data=go.Heatmap(
        z=pivot.values, x=pivot.columns, y=pivot.index,
        colorscale="RdYlGn_r" if metric == "fcr" else "RdYlGn",
        hoverongaps=False, texttemplate="%{z:.2f}"
    ))
    fig.update_layout(
        title=f"圈舍{metric_label}热力图",
        xaxis_title="时段", yaxis_title="圈舍",
        template="plotly_white", height=400
    )
    return fig


def chart_batch_comparison(batch_rank):
    if batch_rank is None or len(batch_rank) == 0:
        return go.Figure()
    fig = go.Figure()
    fig.add_trace(go.Bar(x=batch_rank["batch_id"], y=batch_rank["avg_fcr"], name="料重比", marker_color="#4ECDC4"))
    fig.add_trace(go.Scatter(x=batch_rank["batch_id"], y=batch_rank["avg_daily_gain"], name="日增重(kg)", yaxis="y2", mode="lines+markers", line=dict(color="#E74C3C", width=3)))
    fig.update_layout(
        title="各批次效率对比",
        xaxis_title="批次", yaxis_title="料重比",
        yaxis2=dict(title="日增重(kg)", overlaying="y", side="right", showgrid=False),
        template="plotly_white", height=400
    )
    return fig
