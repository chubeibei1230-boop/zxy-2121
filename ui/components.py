import streamlit as st
import pandas as pd
from config.constants import ROLE_CONFIG, FEEDING_COLS, WEIGHT_COLS, HEALTH_COLS
from data.processing import (
    validate_and_clean,
    add_period_columns,
    build_yoy_mom_table,
    build_anomaly_yoy_mom_table,
)
from data.sample import generate_sample_data
from charts.visualizations import (
    chart_feeding_trend,
    chart_weight_trend,
    chart_anomaly_ratio,
    chart_pen_comparison,
)
from reports.export import export_html_report
from state.session import clear_all_data, update_merged_data


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
            update_merged_data()
            st.success("示例数据已加载！")

        if st.button("清空所有数据", use_container_width=True):
            clear_all_data()
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
        update_merged_data()


def sidebar_filters(merged_df, feeding_df):
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

    return period, pen_filter, batch_filter


def show_welcome_page():
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
