import pandas as pd
import streamlit as st


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


def _format_period_label(period_date, period):
    if period == "月":
        return period_date.strftime("%Y-%m")
    else:
        return period_date.strftime("W%W %Y")


def calc_yoy_mom(df, metric_col, period):
    df = add_period_columns(df, period)
    agg = df.groupby("period").agg({metric_col: "sum"}).reset_index()
    agg = agg.sort_values("period")
    agg["period_label"] = agg["period"].apply(lambda x: _format_period_label(x, period))
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
    agg["period_label"] = agg["period"].apply(lambda x: _format_period_label(x, period))
    if period == "周":
        agg["环比"] = agg["anomaly_ratio"].pct_change(1) * 100
        agg["同比"] = agg["anomaly_ratio"].pct_change(52) * 100
    else:
        agg["环比"] = agg["anomaly_ratio"].pct_change(1) * 100
        agg["同比"] = agg["anomaly_ratio"].pct_change(12) * 100
    return agg


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


def filter_dataframe(df, pen_filter, batch_filter):
    if df is None:
        return None
    filtered = df
    if pen_filter != "全部":
        filtered = filtered[filtered["pen_id"] == pen_filter]
    if batch_filter != "全部":
        filtered = filtered[filtered["batch_id"] == batch_filter]
    return filtered
