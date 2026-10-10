from utils.database import query, execute, executemany

ORDER = ["low", "medium", "high", "critical"]
COLS = ("campaign_id,metric_date,metric,alert_type,severity,observed,expected,"
        "z_score,pct_change,explanation,recommendation").split(",")

def clear_open(cid):
    execute("DELETE FROM alerts WHERE campaign_id=%s AND status='open'", (cid,))

def save_many(alerts):
    sql = (f"INSERT INTO alerts({','.join(COLS)}) VALUES({','.join(['%s']*len(COLS))}) "
           "ON DUPLICATE KEY UPDATE severity=VALUES(severity), observed=VALUES(observed), "
           "expected=VALUES(expected), z_score=VALUES(z_score), pct_change=VALUES(pct_change), "
           "explanation=VALUES(explanation), recommendation=VALUES(recommendation)")
    executemany(sql, [tuple(a[c] for c in COLS) for a in alerts])

def list_alerts(min_sev="medium", status=None, cid=None, days=None, limit=200):
    sev = ORDER[ORDER.index(min_sev) if min_sev in ORDER else 1:]
    where, args = [f"a.severity IN ({','.join(['%s']*len(sev))})"], list(sev)
    if status in ("open", "acknowledged"):
        where.append("a.status=%s"); args.append(status)
    if cid:
        where.append("a.campaign_id=%s"); args.append(cid)
    if days:
        where.append("a.metric_date >= (SELECT MAX(metric_date) FROM metrics) - INTERVAL %s DAY")
        args.append(days)
    return query(f"""SELECT a.*, c.name campaign_name FROM alerts a JOIN campaigns c ON c.id=a.campaign_id
        WHERE {' AND '.join(where)}
        ORDER BY a.metric_date DESC, FIELD(a.severity,'critical','high','medium','low') LIMIT {int(limit)}""", args)

def set_status(aid, status):
    execute("UPDATE alerts SET status=%s WHERE id=%s", (status, aid))

def summary():
    sev = query("""SELECT severity, COUNT(*) n FROM alerts WHERE status='open'
        AND metric_date >= (SELECT MAX(metric_date) FROM metrics) - INTERVAL 14 DAY GROUP BY severity""")
    daily = query("""SELECT metric_date d, COUNT(*) n FROM alerts
        WHERE severity IN ('medium','high','critical')
        AND metric_date >= (SELECT MAX(metric_date) FROM metrics) - INTERVAL 14 DAY
        GROUP BY metric_date ORDER BY metric_date""")
    totals = query("""SELECT (SELECT COUNT(*) FROM campaigns) campaigns,
        (SELECT COUNT(*) FROM metrics) data_points,
        (SELECT COUNT(DISTINCT campaign_id) FROM alerts WHERE status='open'
           AND severity IN ('medium','high','critical')) affected""", one=True)
    return {"severity": {r["severity"]: r["n"] for r in sev}, "daily": daily, "totals": totals}
