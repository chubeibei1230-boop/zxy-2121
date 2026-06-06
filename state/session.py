import streamlit as st


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


def clear_all_data():
    st.session_state.feeding_df = None
    st.session_state.weight_df = None
    st.session_state.health_df = None
    st.session_state.merged_df = None


def update_merged_data():
    from data.processing import merge_data
    st.session_state.merged_df = merge_data(
        st.session_state.feeding_df,
        st.session_state.weight_df,
        st.session_state.health_df,
    )
