from app import app, db, User
from werkzeug.security import generate_password_hash

def create_admin_user():
    with app.app_context():
        try:
            # Check if admin already exists
            admin = User.query.filter_by(username='admin').first()
            
            if admin:
                print("Admin user already exists with ID:", admin.id)
                return
            
            # Create new admin user with email
            admin = User(
                username='admin',
                email='admin@example.com',
                password=generate_password_hash('admin123', method='scrypt'),
                is_admin=True
            )
            
            db.session.add(admin)
            db.session.commit()
            print(" Admin user created successfully!")
            print("Username: admin")
            print("Password: admin123")
            print("\n  IMPORTANT: Change the default password after first login!")
            
        except Exception as e:
            print(" Error creating admin user:", str(e))
            db.session.rollback()
        finally:
            db.session.close()

if __name__ == '__main__':
    print(" Creating admin user...")
    create_admin_user()
