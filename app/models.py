from app import db

class Report(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    uploaded_files = db.Column(db.String(255))
