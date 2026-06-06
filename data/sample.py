import random
from datetime import datetime
import pandas as pd


def generate_sample_data():
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
