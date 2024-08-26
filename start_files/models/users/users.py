from os import path
import os
from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
DB_NAME = 'database.db'
SQLALCHEMY_TRACK_MODIFICATIONS = True

class User(UserMixin, db.Model):
    user_id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, index=True)

    def get_id(self):
        return str(self.user_id)

    def __repr__(self):
        return '<User {}>'.format(self.username)

def create_database(app):
    if not path.exists(os.path.join('templates', DB_NAME)):
        with app.app_context():
            db.create_all()
        print('Created Database!')


