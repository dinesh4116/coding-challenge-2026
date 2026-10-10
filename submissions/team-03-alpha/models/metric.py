from utils.database import query, executemany

def upsert_many(rows):
    executemany("""INSERT INTO metrics(campaign_id,metric_date,spend,impressions,clicks,conversions,revenue,budget)
        VALUES(%s,%s,%s,%s,%s,%s,%s,%s)
        ON DUPLICATE KEY UPDATE spend=VALUES(spend), impressions=VALUES(impressions),
        clicks=VALUES(clicks), conversions=VALUES(conversions), revenue=VALUES(revenue), budget=VALUES(budget)""", rows)

def series(cid):
    return query("""SELECT metric_date,spend,impressions,clicks,conversions,revenue,budget
                    FROM metrics WHERE campaign_id=%s ORDER BY metric_date""", (cid,))
