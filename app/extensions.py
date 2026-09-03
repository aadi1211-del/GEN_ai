from flask_cors import CORS
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy


db = SQLAlchemy()
login_manager = LoginManager()
cors = CORS()

login_manager.login_view = "auth.login"
login_manager.login_message_category = "warning"