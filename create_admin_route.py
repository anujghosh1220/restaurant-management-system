from app import app, db, User
from werkzeug.security import generate_password_hash

@app.route('/create-admin')
def create_admin():
    try:
        # Check if admin already exists
        admin = User.query.filter_by(username='admin').first()
        
        if admin:
            return f"<h1>Admin user already exists with ID: {admin.id}</h1>"
        
        # Create new admin user
        admin = User(
            username='admin',
            password=generate_password_hash('admin123'),  # Change this to a secure password
            is_admin=True
        )
        
        db.session.add(admin)
        db.session.commit()
        return """
            <h1>Admin User Created Successfully!</h1>
            <p>Username: admin</p>
            <p>Password: admin123</p>
            <p><strong>IMPORTANT:</strong> Change the default password after first login!</p>
            <p><a href="/login">Go to Login Page</a></p>
        """
        
    except Exception as e:
        db.session.rollback()
        return f"<h1>Error creating admin user:</h1><p>{str(e)}</p>"
    finally:
        db.session.close()

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
