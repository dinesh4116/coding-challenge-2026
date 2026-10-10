from flask import Flask
from config import Config
from routes.dashboard_routes import bp as dashboard_bp
from routes.campaign_routes import bp as campaign_bp
from routes.alert_routes import bp as alert_bp
from routes.upload_routes import bp as upload_bp

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    for bp in (dashboard_bp, campaign_bp, alert_bp, upload_bp):
        app.register_blueprint(bp)
    return app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
