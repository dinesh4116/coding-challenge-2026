DROP DATABASE IF EXISTS campaign_anomaly;
CREATE DATABASE campaign_anomaly CHARACTER SET utf8mb4;
USE campaign_anomaly;

CREATE TABLE campaigns (
  id INT AUTO_INCREMENT PRIMARY KEY,
  external_id VARCHAR(50) NOT NULL UNIQUE,
  name VARCHAR(150) NOT NULL,
  channel VARCHAR(60), vertical VARCHAR(40), landing_page_group VARCHAR(40)
);

CREATE TABLE metrics (
  id INT AUTO_INCREMENT PRIMARY KEY,
  campaign_id INT NOT NULL,
  metric_date DATE NOT NULL,
  spend DECIMAL(12,2) DEFAULT 0,
  impressions INT DEFAULT 0,
  clicks INT DEFAULT 0,
  conversions INT DEFAULT 0,
  revenue DECIMAL(14,2) DEFAULT 0,
  budget DECIMAL(12,2) DEFAULT 0,
  UNIQUE KEY uq_campaign_day (campaign_id, metric_date),
  FOREIGN KEY (campaign_id) REFERENCES campaigns(id) ON DELETE CASCADE
);

CREATE TABLE alerts (
  id INT AUTO_INCREMENT PRIMARY KEY,
  campaign_id INT NOT NULL,
  metric_date DATE NOT NULL,
  metric VARCHAR(20) NOT NULL,
  alert_type VARCHAR(20) NOT NULL,
  severity ENUM('low','medium','high','critical') NOT NULL,
  observed DOUBLE, expected DOUBLE, z_score DOUBLE, pct_change DOUBLE,
  explanation TEXT, recommendation TEXT,
  status ENUM('open','acknowledged') DEFAULT 'open',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_alert (campaign_id, metric_date, metric),
  FOREIGN KEY (campaign_id) REFERENCES campaigns(id) ON DELETE CASCADE
);
