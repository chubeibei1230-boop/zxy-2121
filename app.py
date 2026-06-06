import streamlit as st

from config.constants import PAGE_CONFIG, ROLE_CONFIG
from state.session import init_session_state
from data.processing import filter_dataframe
from ui.components import (
    sidebar_role_and_upload,
    process_uploads,
    sidebar_filters,
    show_welcome_page,
    show_data_overview,
    show_feeding_analysis,
    show_weight_analysis,
    show_anomaly_analysis,
    show_export,
    show_efficiency_dashboard,
)

st.set_page_config(**PAGE_CONFIG)


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
        show_welcome_page()
        return

    st.divider()

    period, pen_filter, batch_filter = sidebar_filters(merged_df, feeding_df)

    filtered_merged = filter_dataframe(merged_df, pen_filter, batch_filter)
    filtered_weight = filter_dataframe(weight_df, pen_filter, batch_filter)

    show_data_overview(role)

    tab1, tab2, tab3, tab4, tab5 = st.tabs(["🌾 饲喂分析", "⚖️ 体重分析", "⚠️ 异常分析", "� 效率看板", "�📥 数据导出"])

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
        role_info = ROLE_CONFIG.get(role, {})
        if role_info.get("can_view_efficiency", False):
            show_efficiency_dashboard(role, filtered_merged, filtered_weight, period, pen_filter, batch_filter)
        else:
            st.info("🔒 仅运营人员和场长可查看饲喂效率看板，请切换角色")

    with tab5:
        show_export(filtered_merged, filtered_weight, health_df, period, pen_filter, batch_filter)


if __name__ == "__main__":
    main()
