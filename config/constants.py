FEEDING_COLS = ["date", "pen_id", "batch_id", "feed_type", "feed_amount_kg"]
WEIGHT_COLS = ["date", "pen_id", "batch_id", "animal_id", "weight_kg"]
HEALTH_COLS = ["date", "pen_id", "batch_id", "animal_id", "health_status", "is_anomaly"]

ROLE_CONFIG = {
    "运营人员": {"icon": "📋", "desc": "上传饲喂记录", "can_view_efficiency": True, "can_view_detailed": False},
    "兽医助理": {"icon": "💉", "desc": "补充健康标记", "can_view_efficiency": False, "can_view_detailed": False},
    "场长": {"icon": "📊", "desc": "查看趋势报告", "can_view_efficiency": True, "can_view_detailed": True},
}

EFFICIENCY_THRESHOLDS = {
    "good_fcr": 2.5,
    "warning_fcr": 3.5,
    "good_daily_gain": 0.8,
    "warning_daily_gain": 0.4,
    "warning_anomaly_ratio": 15,
    "critical_anomaly_ratio": 25,
}

PAGE_CONFIG = {
    "page_title": "养殖饲喂与体重变化分析看板",
    "layout": "wide",
    "page_icon": "🐄",
}
