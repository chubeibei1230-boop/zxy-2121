import streamlit as st
import pandas as pd
from config.constants import ROLE_CONFIG, FEEDING_COLS, WEIGHT_COLS, HEALTH_COLS, EFFICIENCY_THRESHOLDS
from data.processing import (
    validate_and_clean,
    add_period_columns,
    build_yoy_mom_table,
    build_anomaly_yoy_mom_table,
    calculate_efficiency_metrics,
    calculate_pen_batch_efficiency,
    identify_inefficient_pens,
    analyze_fluctuation_reasons,
    build_efficiency_summary,
)
from data.sample import generate_sample_data
from charts.visualizations import (
    chart_feeding_trend,
    chart_weight_trend,
    chart_anomaly_ratio,
    chart_pen_comparison,
    chart_efficiency_ranking,
    chart_fcr_trend,
    chart_feed_per_head_trend,
    chart_anomaly_vs_efficiency,
    chart_efficiency_heatmap,
    chart_batch_comparison,
)
from reports.export import export_html_report, export_efficiency_brief
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


def show_efficiency_dashboard(role, merged_df, weight_df, period, pen_filter, batch_filter):
    st.markdown("## 📊 饲喂效率与预警看板")
    role_info = ROLE_CONFIG.get(role, {})
    can_view_detailed = role_info.get("can_view_detailed", False)

    if merged_df is None or weight_df is None:
        st.info("请同时上传饲喂记录和称重记录数据以查看效率分析")
        return

    eff_df = calculate_efficiency_metrics(merged_df, weight_df, period)
    if eff_df is None or eff_df.empty:
        st.warning("暂无足够的效率数据进行分析")
        return

    pen_rank, batch_rank = calculate_pen_batch_efficiency(merged_df, weight_df, period)
    inefficient_pens = identify_inefficient_pens(pen_rank, EFFICIENCY_THRESHOLDS) if pen_rank is not None else None
    summary = build_efficiency_summary(eff_df, inefficient_pens, EFFICIENCY_THRESHOLDS)

    eff_agg = eff_df.groupby("period_label").agg(
        avg_fcr=("fcr", "mean"),
        avg_daily_gain=("daily_gain", "mean"),
    ).reset_index()
    fluctuation_reasons = analyze_fluctuation_reasons(eff_agg, EFFICIENCY_THRESHOLDS)

    st.markdown("### 🎯 核心效率指标")
    cols = st.columns(5)
    with cols[0]:
        fcr_val = summary.get("avg_fcr", 0) if summary else eff_df["fcr"].mean()
        fcr_status = "✅ 优秀" if fcr_val < EFFICIENCY_THRESHOLDS["good_fcr"] else ("⚠️ 一般" if fcr_val < EFFICIENCY_THRESHOLDS["warning_fcr"] else "🔴 较差")
        st.metric("平均料重比", f"{fcr_val:.2f}", delta=fcr_status, delta_color="off")
    with cols[1]:
        gain_val = summary.get("avg_daily_gain", 0) if summary else eff_df["daily_gain"].mean()
        gain_status = "✅ 优秀" if gain_val > EFFICIENCY_THRESHOLDS["good_daily_gain"] else ("⚠️ 一般" if gain_val > EFFICIENCY_THRESHOLDS["warning_daily_gain"] else "🔴 较差")
        st.metric("平均日增重(kg)", f"{gain_val:.3f}", delta=gain_status, delta_color="off")
    with cols[2]:
        anomaly_val = summary.get("avg_anomaly_ratio", 0) if summary else eff_df["anomaly_ratio"].mean()
        anomaly_status = "✅ 正常" if anomaly_val < EFFICIENCY_THRESHOLDS["warning_anomaly_ratio"] else ("⚠️ 关注" if anomaly_val < EFFICIENCY_THRESHOLDS["critical_anomaly_ratio"] else "🔴 危险")
        st.metric("平均异常占比", f"{anomaly_val:.1f}%", delta=anomaly_status, delta_color="off")
    with cols[3]:
        feed_val = summary.get("avg_feed_per_head", 0) if summary else eff_df["feed_per_head"].mean()
        st.metric("单头饲喂量(kg)", f"{feed_val:.1f}")
    with cols[4]:
        if pen_rank is not None:
            st.metric("覆盖圈舍数", f"{pen_rank['pen_id'].nunique()}")

    if fluctuation_reasons and len(fluctuation_reasons) > 0:
        st.markdown("### ⚠️ 关键波动提示")
        for r in fluctuation_reasons:
            if r["type"] == "danger":
                st.error(f"**{r['metric']} ({r['change']})**: {r['reason']}")
            elif r["type"] == "warning":
                st.warning(f"**{r['metric']} ({r['change']})**: {r['reason']}")
            else:
                st.success(f"**{r['metric']} ({r['change']})**: {r['reason']}")

    st.divider()

    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📈 效率趋势", "🏆 排行榜", "🚨 低效预警", "🔗 关联分析", "📥 数据导出"])

    with tab1:
        st.markdown("#### 料重比与日增重趋势")
        fig_fcr = chart_fcr_trend(eff_df, period)
        st.plotly_chart(fig_fcr, use_container_width=True)

        st.markdown("#### 单头饲喂量趋势")
        fig_feed = chart_feed_per_head_trend(eff_df, period)
        st.plotly_chart(fig_feed, use_container_width=True)

        if can_view_detailed:
            st.markdown("#### 效率热力图")
            heatmap_metric = st.selectbox("选择指标", ["fcr", "daily_gain", "anomaly_ratio"], format_func=lambda x: {"fcr": "料重比", "daily_gain": "日增重", "anomaly_ratio": "异常占比"}[x])
            fig_heat = chart_efficiency_heatmap(eff_df, heatmap_metric)
            st.plotly_chart(fig_heat, use_container_width=True)
        else:
            st.info("🔒 仅场长可查看热力图详情，请切换角色")

    with tab2:
        col_rank1, col_rank2 = st.columns(2)
        with col_rank1:
            st.markdown("#### 圈舍效率排行榜")
            rank_metric = st.selectbox("排序指标", ["avg_fcr", "avg_daily_gain", "avg_anomaly_ratio", "avg_feed_per_head"],
                                       format_func=lambda x: {
                                           "avg_fcr": "料重比(升序)",
                                           "avg_daily_gain": "日增重(降序)",
                                           "avg_anomaly_ratio": "异常占比(升序)",
                                           "avg_feed_per_head": "单头饲喂量(升序)"
                                       }[x], key="rank_metric")
            ascending = rank_metric in ["avg_fcr", "avg_anomaly_ratio", "avg_feed_per_head"]
            fig_rank = chart_efficiency_ranking(pen_rank, rank_metric, ascending=ascending)
            st.plotly_chart(fig_rank, use_container_width=True)

        with col_rank2:
            st.markdown("#### 批次效率对比")
            fig_batch = chart_batch_comparison(batch_rank)
            st.plotly_chart(fig_batch, use_container_width=True)

        if pen_rank is not None:
            st.markdown("#### 📋 圈舍效率明细")
            display_pen = pen_rank.copy()
            display_pen = display_pen[["pen_id", "avg_fcr", "avg_daily_gain", "avg_anomaly_ratio", "avg_feed_per_head", "total_feed"]]
            display_pen.columns = ["圈舍", "平均料重比", "平均日增重(kg)", "异常占比(%)", "单头饲喂量(kg)", "总饲喂量(kg)"]
            display_pen = display_pen.round(2).sort_values("平均料重比")
            st.dataframe(display_pen, use_container_width=True, hide_index=True)

    with tab3:
        if inefficient_pens is not None:
            st.markdown("#### 🚨 低效圈舍识别")
            risk_counts = inefficient_pens["risk_level"].value_counts()
            cols_risk = st.columns(4)
            risk_order = ["✅ 正常", "🟢 低风险", "🟡 中风险", "🔴 高风险"]
            for i, risk in enumerate(risk_order):
                count = risk_counts.get(risk, 0)
                cols_risk[i].metric(risk, f"{count} 个圈舍")

            display_ineff = inefficient_pens.copy()
            display_ineff = display_ineff[["pen_id", "risk_level", "avg_fcr", "avg_daily_gain", "avg_anomaly_ratio", "warning_count"]]
            display_ineff.columns = ["圈舍", "风险等级", "平均料重比", "平均日增重(kg)", "异常占比(%)", "预警项数"]
            display_ineff = display_ineff.round(2)

            def highlight_risk(row):
                if "高风险" in row["风险等级"]:
                    return ["background-color: #fdecea"] * len(row)
                elif "中风险" in row["风险等级"]:
                    return ["background-color: #fff4e5"] * len(row)
                elif "低风险" in row["风险等级"]:
                    return ["background-color: #e8f5e9"] * len(row)
                return [""] * len(row)

            styled = display_ineff.style.apply(highlight_risk, axis=1)
            st.dataframe(styled, use_container_width=True, hide_index=True)

            high_risk = inefficient_pens[inefficient_pens["warning_count"] >= 2]
            if len(high_risk) > 0:
                st.markdown("#### 💡 改进建议")
                for _, row in high_risk.iterrows():
                    with st.expander(f"🏠 {row['pen_id']} - {row['risk_level']}"):
                        suggestions = []
                        if row["fcr_warning"]:
                            suggestions.append("• ⚠️ 料重比偏高：建议优化饲料配方，检查饲料质量，调整饲喂策略")
                        if row["gain_warning"]:
                            suggestions.append("• ⚠️ 日增重偏低：建议检查营养摄入是否充足，排查健康问题")
                        if row["anomaly_warning"]:
                            suggestions.append("• ⚠️ 异常占比偏高：建议加强健康监测，改善圈舍环境")
                        if row["anomaly_critical"]:
                            suggestions.append("• 🔴 异常占比超临界值：建议立即进行健康排查，隔离异常个体")
                        for s in suggestions:
                            st.markdown(s)
        else:
            st.info("暂无低效圈舍数据")

    with tab4:
        st.markdown("#### 异常占比 vs 料重比关联分析")
        fig_scatter = chart_anomaly_vs_efficiency(eff_df)
        st.plotly_chart(fig_scatter, use_container_width=True)

        st.markdown("#### 📊 效率明细数据")
        display_eff = eff_df.copy()
        if can_view_detailed:
            cols_to_show = ["period_label", "pen_id", "batch_id", "fcr", "daily_gain", "feed_per_head", "weight_gain", "anomaly_ratio", "total_feed_kg"]
            col_names = ["时段", "圈舍", "批次", "料重比", "日增重(kg)", "单头饲喂量(kg)", "周期增重(kg)", "异常占比(%)", "总饲喂量(kg)"]
        else:
            cols_to_show = ["period_label", "pen_id", "batch_id", "fcr", "daily_gain", "feed_per_head", "anomaly_ratio"]
            col_names = ["时段", "圈舍", "批次", "料重比", "日增重(kg)", "单头饲喂量(kg)", "异常占比(%)"]
        display_eff = display_eff[cols_to_show]
        display_eff.columns = col_names
        display_eff = display_eff.round(2)
        st.dataframe(display_eff, use_container_width=True, hide_index=True)

    with tab5:
        st.markdown("#### 📥 数据导出")
        cols_export = st.columns(2)

        with cols_export[0]:
            if eff_df is not None:
                csv_eff = eff_df.to_csv(index=False).encode("utf-8-sig")
                st.download_button("📄 导出效率明细(CSV)", csv_eff, "efficiency_details.csv", "text/csv", use_container_width=True)

        with cols_export[1]:
            if pen_rank is not None:
                csv_rank = pen_rank.to_csv(index=False).encode("utf-8-sig")
                st.download_button("📄 导出圈舍排名(CSV)", csv_rank, "pen_ranking.csv", "text/csv", use_container_width=True)

        st.divider()
        st.markdown("#### 📋 经营简报导出")
        brief_html = export_efficiency_brief(
            eff_df, pen_rank, batch_rank, summary, inefficient_pens,
            fluctuation_reasons, period, pen_filter, batch_filter
        )
        st.download_button(
            "🌐 导出完整经营简报(HTML)",
            brief_html.encode("utf-8"),
            "efficiency_brief.html",
            "text/html",
            use_container_width=True,
            type="primary"
        )
        st.caption("💡 经营简报包含：核心指标、波动提示、排行榜、低效预警、批次对比和明细数据")
