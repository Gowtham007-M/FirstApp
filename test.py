from app import app, db  # Import Flask app and database

with app.app_context():
    db.create_all()
    print("Database tables created successfully!")
