FEEDING_COLS = ["date", "pen_id", "batch_id", "feed_type", "feed_amount_kg"]
WEIGHT_COLS = ["date", "pen_id", "batch_id", "animal_id", "weight_kg"]
HEALTH_COLS = ["date", "pen_id", "batch_id", "animal_id", "health_status", "is_anomaly"]

ROLE_CONFIG = {
    "运营人员": {"icon": "📋", "desc": "上传饲喂记录"},
    "兽医助理": {"icon": "💉", "desc": "补充健康标记"},
    "场长": {"icon": "📊", "desc": "查看趋势报告"},
}

PAGE_CONFIG = {
    "page_title": "养殖饲喂与体重变化分析看板",
    "layout": "wide",
    "page_icon": "🐄",
}
