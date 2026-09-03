"""
Central place to instantiate Flask extensions so they can be imported
by models/blueprints without circular-import issues, then bound to the
real app inside the application factory (app/__init__.py).
"""
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_cors import CORS
from flask import Flask, render_template

from app.config import Config
from app.extensions import cors, db, login_manager

def create_app(config_class=Config):
	app = Flask(__name__)
	app.config.from_object(config_class)

	db.init_app(app)
	login_manager.init_app(app)
	cors.init_app(app)

	from app.models import User

	@login_manager.user_loader
	def load_user(user_id):
		return db.session.get(User, int(user_id))

	@app.route("/")
	def index():
		return render_template("index.html")

	from app.auth import auth_bp
	from app.chat import chat_bp
	from app.routes import documents_bp

	app.register_blueprint(auth_bp)
	app.register_blueprint(chat_bp)
	app.register_blueprint(documents_bp)

	with app.app_context():
		from app import models  # noqa: F401
		db.create_all()

	return app