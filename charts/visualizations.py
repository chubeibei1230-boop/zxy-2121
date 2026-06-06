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
