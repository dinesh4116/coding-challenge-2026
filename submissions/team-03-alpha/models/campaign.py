from utils.database import query, execute

def upsert(ext_id, name, channel=None, vertical=None, lp=None):
    execute("INSERT INTO campaigns(external_id,name,channel,vertical,landing_page_group) VALUES(%s,%s,%s,%s,%s) "
            "ON DUPLICATE KEY UPDATE name=VALUES(name), channel=VALUES(channel), vertical=VALUES(vertical), "
            "landing_page_group=VALUES(landing_page_group)", (ext_id, name, channel, vertical, lp))
    return query("SELECT id FROM campaigns WHERE external_id=%s", (ext_id,), one=True)["id"]

def all_with_stats():
    return query("""SELECT c.id, c.external_id, c.name, c.channel, c.vertical,
        COUNT(m.id) days, ROUND(COALESCE(SUM(m.spend),0),2) spend,
        COALESCE(SUM(m.conversions),0) conversions,
        (SELECT COUNT(*) FROM alerts a WHERE a.campaign_id=c.id AND a.status='open'
           AND a.severity IN ('medium','high','critical')) open_alerts
        FROM campaigns c LEFT JOIN metrics m ON m.campaign_id=c.id
        GROUP BY c.id ORDER BY c.name""")

def get(cid):
    return query("SELECT * FROM campaigns WHERE id=%s", (cid,), one=True)
