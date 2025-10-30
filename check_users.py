from app import app, db, User

with app.app_context():
    # List all users
    users = User.query.all()
    if not users:
        print("No users found in the database!")
    else:
        print("Users in the database:")
        for user in users:
            print(f"ID: {user.id}, Username: {user.username}, Is Admin: {user.is_admin}")
    
    # Check if admin exists
    admin = User.query.filter_by(username='admin').first()
    if admin:
        print("\nAdmin user exists!")
    else:
        print("\nAdmin user does not exist. Creating one...")
        from werkzeug.security import generate_password_hash
        admin = User(
            username='admin',
            password=generate_password_hash('admin123', method='sha256'),
            is_admin=True
        )
        db.session.add(admin)
        db.session.commit()
        print("Admin user created successfully!")
