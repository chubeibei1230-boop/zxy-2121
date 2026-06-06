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


def calculate_efficiency_metrics(merged_df, weight_df, period):
    if merged_df is None or weight_df is None:
        return None

    df_period = add_period_columns(merged_df, period)
    weight_period = add_period_columns(weight_df, period)

    feed_agg = df_period.groupby(["period", "period_label", "pen_id", "batch_id"]).agg(
        total_feed_kg=("total_feed_kg", "sum"),
        total_records=("total_records", "sum"),
        anomaly_count=("anomaly_count", "sum"),
        avg_animal_count=("animal_count", "mean"),
    ).reset_index()

    weight_agg = weight_period.groupby(["period", "period_label", "pen_id", "batch_id"]).agg(
        avg_weight=("weight_kg", "mean"),
        first_weight=("weight_kg", "first"),
        last_weight=("weight_kg", "last"),
        animal_count=("animal_id", "nunique"),
    ).reset_index()

    merged = feed_agg.merge(weight_agg, on=["period", "period_label", "pen_id", "batch_id"], how="inner")

    merged["weight_gain"] = merged["last_weight"] - merged["first_weight"]
    merged["days_in_period"] = merged["period"].apply(
        lambda x: 7 if period == "周" else pd.Period(x.strftime("%Y-%m"), freq="M").days_in_month
    )
    merged["daily_gain"] = merged["weight_gain"] / merged["days_in_period"]
    merged["feed_per_head"] = merged["total_feed_kg"] / merged["animal_count"].replace(0, 1)
    merged["fcr"] = merged["total_feed_kg"] / (merged["weight_gain"] * merged["animal_count"]).replace(0, 1)
    merged["anomaly_ratio"] = merged["anomaly_count"] / merged["total_records"].replace(0, 1) * 100

    merged = merged.replace([float("inf"), -float("inf")], None)
    merged = merged.round(3)

    return merged


def calculate_pen_batch_efficiency(merged_df, weight_df, period):
    eff = calculate_efficiency_metrics(merged_df, weight_df, period)
    if eff is None:
        return None

    pen_rank = eff.groupby("pen_id").agg(
        avg_fcr=("fcr", "mean"),
        avg_daily_gain=("daily_gain", "mean"),
        avg_anomaly_ratio=("anomaly_ratio", "mean"),
        total_feed=("total_feed_kg", "sum"),
        avg_feed_per_head=("feed_per_head", "mean"),
    ).reset_index()

    batch_rank = eff.groupby("batch_id").agg(
        avg_fcr=("fcr", "mean"),
        avg_daily_gain=("daily_gain", "mean"),
        avg_anomaly_ratio=("anomaly_ratio", "mean"),
        total_feed=("total_feed_kg", "sum"),
        avg_feed_per_head=("feed_per_head", "mean"),
    ).reset_index()

    return pen_rank.round(3), batch_rank.round(3)


def identify_inefficient_pens(pen_rank, thresholds):
    if pen_rank is None:
        return None

    inefficient = pen_rank.copy()
    inefficient["fcr_warning"] = inefficient["avg_fcr"] > thresholds["warning_fcr"]
    inefficient["gain_warning"] = inefficient["avg_daily_gain"] < thresholds["warning_daily_gain"]
    inefficient["anomaly_warning"] = inefficient["avg_anomaly_ratio"] > thresholds["warning_anomaly_ratio"]
    inefficient["anomaly_critical"] = inefficient["avg_anomaly_ratio"] > thresholds["critical_anomaly_ratio"]
    inefficient["warning_count"] = inefficient[["fcr_warning", "gain_warning", "anomaly_warning"]].sum(axis=1)
    inefficient["risk_level"] = inefficient["warning_count"].apply(
        lambda x: "🔴 高风险" if x >= 3 else ("🟡 中风险" if x >= 2 else ("🟢 低风险" if x >= 1 else "✅ 正常"))
    )
    return inefficient.sort_values("warning_count", ascending=False)


def analyze_fluctuation_reasons(eff_df, thresholds):
    if eff_df is None or len(eff_df) < 2:
        return []

    reasons = []
    latest = eff_df.iloc[-1]
    previous = eff_df.iloc[-2]

    fcr_change = (latest["fcr"] - previous["fcr"]) / previous["fcr"] * 100 if previous["fcr"] else 0
    gain_change = (latest["daily_gain"] - previous["daily_gain"]) / previous["daily_gain"] * 100 if previous["daily_gain"] else 0
    anomaly_change = latest["anomaly_ratio"] - previous["anomaly_ratio"]

    if abs(fcr_change) > 10:
        if fcr_change > 0:
            reasons.append({
                "type": "warning",
                "metric": "料重比",
                "change": f"+{fcr_change:.1f}%",
                "reason": "料重比显著上升，可能原因：饲料质量下降、饲喂策略不合理、动物健康问题"
            })
        else:
            reasons.append({
                "type": "success",
                "metric": "料重比",
                "change": f"{fcr_change:.1f}%",
                "reason": "料重比明显改善，饲喂效率提升"
            })

    if abs(gain_change) > 15:
        if gain_change < 0:
            reasons.append({
                "type": "warning",
                "metric": "日增重",
                "change": f"{gain_change:.1f}%",
                "reason": "日增重显著下降，可能原因：营养不足、疾病影响、环境应激"
            })
        else:
            reasons.append({
                "type": "success",
                "metric": "日增重",
                "change": f"+{gain_change:.1f}%",
                "reason": "日增重明显提升，生长状况良好"
            })

    if anomaly_change > 5:
        reasons.append({
            "type": "danger",
            "metric": "异常占比",
            "change": f"+{anomaly_change:.1f}%",
            "reason": "异常占比显著增加，建议立即排查健康问题和环境因素"
        })

    if latest["anomaly_ratio"] > thresholds["critical_anomaly_ratio"]:
        reasons.append({
            "type": "danger",
            "metric": "异常占比",
            "change": f"{latest['anomaly_ratio']:.1f}%",
            "reason": "异常占比超过临界值，需紧急处理！"
        })

    return reasons


def build_efficiency_summary(eff_df, pen_rank, thresholds):
    if eff_df is None:
        return None

    summary = {}
    summary["avg_fcr"] = eff_df["fcr"].mean()
    summary["avg_daily_gain"] = eff_df["daily_gain"].mean()
    summary["avg_anomaly_ratio"] = eff_df["anomaly_ratio"].mean()
    summary["avg_feed_per_head"] = eff_df["feed_per_head"].mean()
    summary["total_feed"] = eff_df["total_feed_kg"].sum()
    summary["total_weight_gain"] = (eff_df["weight_gain"] * eff_df["animal_count"]).sum()

    if pen_rank is not None:
        summary["best_pen_fcr"] = pen_rank.loc[pen_rank["avg_fcr"].idxmin(), "pen_id"] if len(pen_rank) > 0 else "N/A"
        summary["worst_pen_fcr"] = pen_rank.loc[pen_rank["avg_fcr"].idxmax(), "pen_id"] if len(pen_rank) > 0 else "N/A"
        summary["high_risk_pens"] = pen_rank[pen_rank["warning_count"] >= 2]["pen_id"].tolist()

    summary["fcr_status"] = "✅ 优秀" if summary["avg_fcr"] < thresholds["good_fcr"] else ("⚠️ 一般" if summary["avg_fcr"] < thresholds["warning_fcr"] else "🔴 较差")
    summary["gain_status"] = "✅ 优秀" if summary["avg_daily_gain"] > thresholds["good_daily_gain"] else ("⚠️ 一般" if summary["avg_daily_gain"] > thresholds["warning_daily_gain"] else "🔴 较差")

    return summary
