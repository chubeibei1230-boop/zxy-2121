import io
import base64
from datetime import datetime, timedelta

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="养殖饲喂与体重变化分析看板", layout="wide", page_icon="🐄")

FEEDING_COLS = ["date", "pen_id", "batch_id", "feed_type", "feed_amount_kg"]
WEIGHT_COLS = ["date", "pen_id", "batch_id", "animal_id", "weight_kg"]
HEALTH_COLS = ["date", "pen_id", "batch_id", "animal_id", "health_status", "is_anomaly"]

ROLE_CONFIG = {
    "运营人员": {"icon": "📋", "desc": "上传饲喂记录"},
    "兽医助理": {"icon": "💉", "desc": "补充健康标记"},
    "场长": {"icon": "📊", "desc": "查看趋势报告"},
}


def init_session_state():
    defaults = {
        "feeding_df": None,
        "weight_df": None,
        "health_df": None,
        "merged_df": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def validate_and_clean(df, required_cols, label):
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        st.error(f"{label} 缺少必要列: {', '.join(missing)}")
        return None
    df = df.dropna(subset=["date"]).copy()
    try:
        df["date"] = pd.to_datetime(df["date"])
    except Exception:
        st.error(f"{label} 的 date 列无法解析为日期")
        return None
    if "pen_id" in df.columns:
        df["pen_id"] = df["pen_id"].astype(str).str.strip()
    if "batch_id" in df.columns:
        df["batch_id"] = df["batch_id"].astype(str).str.strip()
    if "animal_id" in df.columns:
        df["animal_id"] = df["animal_id"].astype(str).str.strip()
    if "feed_amount_kg" in df.columns:
        df["feed_amount_kg"] = pd.to_numeric(df["feed_amount_kg"], errors="coerce")
    if "weight_kg" in df.columns:
        df["weight_kg"] = pd.to_numeric(df["weight_kg"], errors="coerce")
    if "is_anomaly" in df.columns:
        df["is_anomaly"] = df["is_anomaly"].astype(str).str.strip().str.lower().map(
            {"true": True, "1": True, "yes": True, "是": True, "false": False, "0": False, "no": False, "否": False}
        )
        df["is_anomaly"] = df["is_anomaly"].fillna(False)
    df = df.drop_duplicates()
    return df


def merge_data(feeding_df, weight_df, health_df):
    parts = []
    if feeding_df is not None:
        feed_agg = feeding_df.groupby(["date", "pen_id", "batch_id"]).agg(
            total_feed_kg=("feed_amount_kg", "sum"),
            feed_count=("feed_amount_kg", "count"),
        ).reset_index()
        parts.append(feed_agg)
    if weight_df is not None:
        weight_agg = weight_df.groupby(["date", "pen_id", "batch_id"]).agg(
            avg_weight_kg=("weight_kg", "mean"),
            min_weight_kg=("weight_kg", "min"),
            max_weight_kg=("weight_kg", "max"),
            animal_count=("animal_id", "nunique"),
        ).reset_index()
        parts.append(weight_agg)
    if health_df is not None:
        health_agg = health_df.groupby(["date", "pen_id", "batch_id"]).agg(
            total_records=("animal_id", "count"),
            anomaly_count=("is_anomaly", "sum"),
        ).reset_index()
        health_agg["anomaly_ratio"] = (
            health_agg["anomaly_count"] / health_agg["total_records"].replace(0, 1)
        )
        parts.append(health_agg)
    if not parts:
        return None
    merged = parts[0]
    for p in parts[1:]:
        merged = merged.merge(p, on=["date", "pen_id", "batch_id"], how="outer")
    merged = merged.sort_values(["date", "pen_id", "batch_id"]).reset_index(drop=True)
    return merged


def add_period_columns(df, period):
    df = df.copy()
    if period == "周":
        df["period"] = df["date"].dt.to_period("W").apply(lambda r: r.start_time)
        df["period_label"] = df["date"].dt.strftime("%Y第%W周")
    else:
        df["period"] = df["date"].dt.to_period("M").apply(lambda r: r.start_time)
        df["period_label"] = df["date"].dt.strftime("%Y年%m月")
    return df


def calc_yoy_mom(df, metric_col, period):
    df = add_period_columns(df, period)
    agg = df.groupby("period").agg({metric_col: "sum"}).reset_index()
    agg = agg.sort_values("period")
    agg["period_label"] = agg["period"].apply(
        lambda x: x.strftime("%Y-%m") if period == "月" else x.strftime("W%W %Y")
    )
    if period == "周":
        agg["环比"] = agg[metric_col].pct_change(1) * 100
        agg["同比"] = agg[metric_col].pct_change(52) * 100
    else:
        agg["环比"] = agg[metric_col].pct_change(1) * 100
        agg["同比"] = agg[metric_col].pct_change(12) * 100
    return agg


def calc_anomaly_ratio_period(df, period):
    df = add_period_columns(df, period)
    agg = df.groupby("period").agg(
        total_records=("total_records", "sum"),
        anomaly_count=("anomaly_count", "sum"),
    ).reset_index()
    agg["anomaly_ratio"] = agg["anomaly_count"] / agg["total_records"].replace(0, 1) * 100
    agg = agg.sort_values("period")
    agg["period_label"] = agg["period"].apply(
        lambda x: x.strftime("%Y-%m") if period == "月" else x.strftime("W%W %Y")
    )
    if period == "周":
        agg["环比"] = agg["anomaly_ratio"].pct_change(1) * 100
        agg["同比"] = agg["anomaly_ratio"].pct_change(52) * 100
    else:
        agg["环比"] = agg["anomaly_ratio"].pct_change(1) * 100
        agg["同比"] = agg["anomaly_ratio"].pct_change(12) * 100
    return agg


def generate_sample_data():
    import random
    random.seed(42)
    pens = [f"P{i:02d}" for i in range(1, 6)]
    batches = [f"B2025-{i:02d}" for i in range(1, 4)]
    animals = [f"A{i:03d}" for i in range(1, 31)]
    feed_types = ["精料", "粗料", "混合料"]
    health_statuses = ["正常", "正常", "正常", "正常", "轻微异常", "需关注"]

    start = datetime(2025, 1, 6)
    end = datetime(2026, 5, 31)
    dates = pd.date_range(start, end, freq="D")

    feeding_rows = []
    weight_rows = []
    health_rows = []
    for d in dates:
        for pen in pens:
            for batch in batches:
                feeding_rows.append({
                    "date": d,
                    "pen_id": pen,
                    "batch_id": batch,
                    "feed_type": random.choice(feed_types),
                    "feed_amount_kg": round(random.uniform(15, 60), 1),
                })
                sampled = random.sample(animals, k=random.randint(3, 8))
                for aid in sampled:
                    base_w = 200 + (d - start).days * 0.3
                    weight_rows.append({
                        "date": d,
                        "pen_id": pen,
                        "batch_id": batch,
                        "animal_id": aid,
                        "weight_kg": round(base_w + random.uniform(-10, 10), 1),
                    })
                    hs = random.choice(health_statuses)
                    health_rows.append({
                        "date": d,
                        "pen_id": pen,
                        "batch_id": batch,
                        "animal_id": aid,
                        "health_status": hs,
                        "is_anomaly": hs != "正常",
                    })
    return pd.DataFrame(feeding_rows), pd.DataFrame(weight_rows), pd.DataFrame(health_rows)


def chart_feeding_trend(merged_df, period):
    metric = "total_feed_kg"
    df_period = add_period_columns(merged_df, period)
    agg = df_period.groupby("period").agg({metric: "sum"}).reset_index().sort_values("period")
    agg["period_label"] = agg["period"].apply(
        lambda x: x.strftime("%Y-%m") if period == "月" else x.strftime("W%W %Y")
    )
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
    agg["period_label"] = agg["period"].apply(
        lambda x: x.strftime("%Y-%m") if period == "月" else x.strftime("W%W %Y")
    )
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
    agg["period_label"] = agg["period"].apply(
        lambda x: x.strftime("%Y-%m") if period == "月" else x.strftime("W%W %Y")
    )
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
    agg["period_label"] = agg["period"].apply(
        lambda x: x.strftime("%Y-%m") if period == "月" else x.strftime("W%W %Y")
    )
    fig = px.bar(agg, x="period_label", y=metric_col, color="pen_id", barmode="group",
                 title=f"各圈舍{metric_col}对比（按{period}）", template="plotly_white")
    fig.update_layout(height=400)
    return fig


def build_yoy_mom_table(merged_df, metric_col, period):
    agg_df = calc_yoy_mom(merged_df, metric_col, period)
    display = agg_df[["period_label", metric_col, "环比", "同比"]].copy()
    display.columns = ["时段", metric_col, "环比(%)", "同比(%)"]
    display["环比(%)"] = display["环比(%)"].round(2)
    display["同比(%)"] = display["同比(%)"].round(2)
    return display


def build_anomaly_yoy_mom_table(merged_df, period):
    agg_df = calc_anomaly_ratio_period(merged_df, period)
    display = agg_df[["period_label", "anomaly_ratio", "环比", "同比"]].copy()
    display.columns = ["时段", "异常占比(%)", "环比(%)", "同比(%)"]
    display["异常占比(%)"] = display["异常占比(%)"].round(2)
    display["环比(%)"] = display["环比(%)"].round(2)
    display["同比(%)"] = display["同比(%)"].round(2)
    return display


def export_html_report(merged_df, weight_df, health_df, period, pen_filter, batch_filter):
    sections = []
    sections.append("<html><head><meta charset='utf-8'>")
    sections.append("<style>body{font-family:sans-serif;margin:20px;background:#f8f9fa;color:#2c3e50}")
    sections.append("h1{color:#2c3e50;border-bottom:3px solid #4ecdc4;padding-bottom:10px}")
    sections.append("h2{color:#34495e;margin-top:30px}table{border-collapse:collapse;width:100%;margin:10px 0}")
    sections.append("th,td{border:1px solid #ddd;padding:8px;text-align:center}th{background:#4ecdc4;color:white}")
    sections.append("tr:nth-child(even){background:#f2f2f2}.positive{color:#27ae60}.negative{color:#e74c3c}</style>")
    sections.append("</head><body>")
    sections.append(f"<h1>🐄 养殖饲喂与体重变化分析报告</h1>")
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


def sidebar_role_and_upload():
    with st.sidebar:
        st.markdown("### 🧑‍💼 角色选择")
        role = st.selectbox("当前角色", list(ROLE_CONFIG.keys()), format_func=lambda x: f"{ROLE_CONFIG[x]['icon']} {x} - {ROLE_CONFIG[x]['desc']}")
        st.divider()
        st.markdown("### 📂 数据上传")
        st.markdown("<small>支持上传 CSV 文件，列名需包含: date, pen_id, batch_id 等</small>", unsafe_allow_html=True)

        feeding_file = st.file_uploader("饲喂记录 CSV", type=["csv"], key="feeding_upload")
        weight_file = st.file_uploader("称重记录 CSV", type=["csv"], key="weight_upload")
        health_file = st.file_uploader("健康记录 CSV", type=["csv"], key="health_upload")

        st.divider()
        st.markdown("### 🎲 示例数据")
        if st.button("加载示例数据", use_container_width=True):
            f, w, h = generate_sample_data()
            st.session_state.feeding_df = f
            st.session_state.weight_df = w
            st.session_state.health_df = h
            st.session_state.merged_df = merge_data(f, w, h)
            st.success("示例数据已加载！")

        if st.button("清空所有数据", use_container_width=True):
            st.session_state.feeding_df = None
            st.session_state.weight_df = None
            st.session_state.health_df = None
            st.session_state.merged_df = None
            st.rerun()

    return role, feeding_file, weight_file, health_file


def process_uploads(feeding_file, weight_file, health_file):
    if feeding_file is not None:
        raw = pd.read_csv(feeding_file)
        cleaned = validate_and_clean(raw, FEEDING_COLS, "饲喂记录")
        if cleaned is not None:
            st.session_state.feeding_df = cleaned
            st.toast("✅ 饲喂记录上传成功", icon="✅")

    if weight_file is not None:
        raw = pd.read_csv(weight_file)
        cleaned = validate_and_clean(raw, WEIGHT_COLS, "称重记录")
        if cleaned is not None:
            st.session_state.weight_df = cleaned
            st.toast("✅ 称重记录上传成功", icon="✅")

    if health_file is not None:
        raw = pd.read_csv(health_file)
        cleaned = validate_and_clean(raw, HEALTH_COLS, "健康记录")
        if cleaned is not None:
            st.session_state.health_df = cleaned
            st.toast("✅ 健康记录上传成功", icon="✅")

    if any([feeding_file, weight_file, health_file]):
        st.session_state.merged_df = merge_data(
            st.session_state.feeding_df,
            st.session_state.weight_df,
            st.session_state.health_df,
        )


def show_data_overview(role):
    st.markdown("## 📋 数据概览")
    cols = st.columns(3)
    with cols[0]:
        st.markdown("#### 🌾 饲喂记录")
        if st.session_state.feeding_df is not None:
            df = st.session_state.feeding_df
            st.metric("记录数", f"{len(df):,}")
            st.metric("覆盖圈舍", df["pen_id"].nunique())
            st.metric("饲喂总量(kg)", f"{df['feed_amount_kg'].sum():,.1f}")
        else:
            st.info("暂无数据，请上传或加载示例")
    with cols[1]:
        st.markdown("#### ⚖️ 称重记录")
        if st.session_state.weight_df is not None:
            df = st.session_state.weight_df
            st.metric("记录数", f"{len(df):,}")
            st.metric("覆盖批次", df["batch_id"].nunique())
            st.metric("平均体重(kg)", f"{df['weight_kg'].mean():.1f}")
        else:
            st.info("暂无数据，请上传或加载示例")
    with cols[2]:
        st.markdown("#### 🏥 健康记录")
        if st.session_state.health_df is not None:
            df = st.session_state.health_df
            anomaly = df["is_anomaly"].sum()
            total = len(df)
            st.metric("记录数", f"{total:,}")
            st.metric("异常标记数", f"{int(anomaly)}")
            st.metric("异常占比", f"{anomaly/total*100:.1f}%" if total else "N/A")
        else:
            st.info("暂无数据，请上传或加载示例")


def show_feeding_analysis(role, merged_df, period, pen_filter, batch_filter):
    st.markdown("## 🌾 饲喂量分析")
    if "total_feed_kg" not in merged_df.columns:
        st.warning("合并数据中无饲喂量字段")
        return
    fig = chart_feeding_trend(merged_df, period)
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("### 📈 同比环比详情")
    tbl = build_yoy_mom_table(merged_df, "total_feed_kg", period)
    st.dataframe(tbl, use_container_width=True, hide_index=True)

    if pen_filter != "全部":
        st.markdown("### 🏠 圈舍饲喂对比")
        fig2 = chart_pen_comparison(merged_df, "total_feed_kg", period)
        st.plotly_chart(fig2, use_container_width=True)


def show_weight_analysis(role, weight_df, period, pen_filter, batch_filter):
    st.markdown("## ⚖️ 体重变化分析")
    if weight_df is None or weight_df.empty:
        st.warning("无称重数据")
        return
    fig = chart_weight_trend(weight_df, period)
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("### 📊 体重统计")
    df_p = add_period_columns(weight_df, period)
    agg = df_p.groupby("period").agg(
        avg_weight=("weight_kg", "mean"),
        min_weight=("weight_kg", "min"),
        max_weight=("weight_kg", "max"),
        std_weight=("weight_kg", "std"),
    ).reset_index().sort_values("period")
    agg["period_label"] = agg["period"].apply(
        lambda x: x.strftime("%Y-%m") if period == "月" else x.strftime("W%W %Y")
    )
    display = agg[["period_label", "avg_weight", "min_weight", "max_weight", "std_weight"]].copy()
    display.columns = ["时段", "平均体重(kg)", "最小体重(kg)", "最大体重(kg)", "标准差"]
    display = display.round(1)
    st.dataframe(display, use_container_width=True, hide_index=True)


def show_anomaly_analysis(role, merged_df, period, pen_filter, batch_filter):
    st.markdown("## ⚠️ 异常占比分析")
    if merged_df is None or "anomaly_ratio" not in merged_df.columns:
        st.warning("无健康异常数据，请上传健康记录")
        return
    fig = chart_anomaly_ratio(merged_df, period)
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("### 📈 异常占比同比环比")
    tbl = build_anomaly_yoy_mom_table(merged_df, period)
    st.dataframe(tbl, use_container_width=True, hide_index=True)


def show_export(merged_df, weight_df, health_df, period, pen_filter, batch_filter):
    st.markdown("## 📥 数据导出")
    cols = st.columns(3)

    with cols[0]:
        if st.session_state.feeding_df is not None:
            csv = st.session_state.feeding_df.to_csv(index=False).encode("utf-8-sig")
            st.download_button("📄 导出饲喂记录(CSV)", csv, "feeding_cleaned.csv", "text/csv", use_container_width=True)

    with cols[1]:
        if st.session_state.weight_df is not None:
            csv = st.session_state.weight_df.to_csv(index=False).encode("utf-8-sig")
            st.download_button("📄 导出称重记录(CSV)", csv, "weight_cleaned.csv", "text/csv", use_container_width=True)

    with cols[2]:
        if st.session_state.health_df is not None:
            csv = st.session_state.health_df.to_csv(index=False).encode("utf-8-sig")
            st.download_button("📄 导出健康记录(CSV)", csv, "health_cleaned.csv", "text/csv", use_container_width=True)

    if merged_df is not None:
        st.divider()
        merged_csv = merged_df.to_csv(index=False).encode("utf-8-sig")
        st.download_button("📊 导出合并数据(CSV)", merged_csv, "merged_data.csv", "text/csv", use_container_width=True)

        html = export_html_report(merged_df, weight_df, health_df, period, pen_filter, batch_filter)
        st.download_button("🌐 导出HTML报告", html.encode("utf-8"), "report.html", "text/html", use_container_width=True)


def main():
    init_session_state()

    role, feeding_file, weight_file, health_file = sidebar_role_and_upload()
    process_uploads(feeding_file, weight_file, health_file)

    st.title("🐄 养殖饲喂与体重变化分析看板")
    role_info = ROLE_CONFIG[role]
    st.markdown(f"**当前角色**: {role_info['icon']} {role} — {role_info['desc']}")

    merged_df = st.session_state.merged_df
    weight_df = st.session_state.weight_df
    health_df = st.session_state.health_df
    feeding_df = st.session_state.feeding_df

    if merged_df is None and feeding_df is None and weight_df is None and health_df is None:
        st.markdown("---")
        st.markdown("### 👋 欢迎使用养殖分析看板")
        st.markdown("请通过左侧栏上传数据文件，或点击 **加载示例数据** 快速体验。")
        st.markdown("#### 📝 CSV 列名规范")
        col_info = {
            "饲喂记录": FEEDING_COLS,
            "称重记录": WEIGHT_COLS,
            "健康记录": HEALTH_COLS,
        }
        for name, cols in col_info.items():
            st.markdown(f"- **{name}**: `{', '.join(cols)}`")
        st.markdown("#### 💡 字段说明")
        st.markdown("- `date`: 日期 (YYYY-MM-DD)")
        st.markdown("- `pen_id`: 圈舍编号")
        st.markdown("- `batch_id`: 批次编号")
        st.markdown("- `animal_id`: 动物编号")
        st.markdown("- `feed_type`: 饲料类型")
        st.markdown("- `feed_amount_kg`: 饲喂量(kg)")
        st.markdown("- `weight_kg`: 体重(kg)")
        st.markdown("- `health_status`: 健康状态")
        st.markdown("- `is_anomaly`: 是否异常 (true/false)")
        return

    st.divider()
    with st.sidebar:
        st.divider()
        st.markdown("### 🔍 筛选条件")
        period = st.radio("统计周期", ["周", "月"], horizontal=True)

        pen_options = ["全部"]
        batch_options = ["全部"]
        if merged_df is not None:
            pen_options += sorted(merged_df["pen_id"].dropna().unique().tolist())
            batch_options += sorted(merged_df["batch_id"].dropna().unique().tolist())
        elif feeding_df is not None:
            pen_options += sorted(feeding_df["pen_id"].dropna().unique().tolist())
            batch_options += sorted(feeding_df["batch_id"].dropna().unique().tolist())

        pen_filter = st.selectbox("圈舍", pen_options)
        batch_filter = st.selectbox("批次", batch_options)

    filtered_merged = merged_df
    filtered_weight = weight_df
    if merged_df is not None:
        if pen_filter != "全部":
            filtered_merged = filtered_merged[filtered_merged["pen_id"] == pen_filter]
        if batch_filter != "全部":
            filtered_merged = filtered_merged[filtered_merged["batch_id"] == batch_filter]
    if weight_df is not None:
        if pen_filter != "全部":
            filtered_weight = filtered_weight[filtered_weight["pen_id"] == pen_filter]
        if batch_filter != "全部":
            filtered_weight = filtered_weight[filtered_weight["batch_id"] == batch_filter]

    show_data_overview(role)

    tab1, tab2, tab3, tab4 = st.tabs(["🌾 饲喂分析", "⚖️ 体重分析", "⚠️ 异常分析", "📥 数据导出"])

    with tab1:
        if role in ("运营人员", "场长"):
            if filtered_merged is not None and "total_feed_kg" in filtered_merged.columns:
                show_feeding_analysis(role, filtered_merged, period, pen_filter, batch_filter)
            else:
                st.info("请先上传饲喂记录数据")
        else:
            st.info("兽医助理无饲喂分析权限，请切换角色")

    with tab2:
        if role in ("场长",):
            if filtered_weight is not None and not filtered_weight.empty:
                show_weight_analysis(role, filtered_weight, period, pen_filter, batch_filter)
            else:
                st.info("请先上传称重记录数据")
        else:
            st.info("仅场长可查看体重趋势报告，请切换角色")

    with tab3:
        if role in ("兽医助理", "场长"):
            if filtered_merged is not None and "anomaly_ratio" in filtered_merged.columns:
                show_anomaly_analysis(role, filtered_merged, period, pen_filter, batch_filter)
            else:
                st.info("请先上传健康记录数据")
        else:
            st.info("运营人员无异常分析权限，请切换角色")

    with tab4:
        show_export(filtered_merged, filtered_weight, health_df, period, pen_filter, batch_filter)


if __name__ == "__main__":
    main()
