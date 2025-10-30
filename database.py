from app import app, db, User, MenuItem

def init_db():
    with app.app_context():
        # Create all database tables
        db.create_all()
        
        # Create admin user if not exists
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            from werkzeug.security import generate_password_hash
            admin = User(
                username='admin',
                password=generate_password_hash('admin123', method='sha256'),
                is_admin=True
            )
            db.session.add(admin)
        
        # Add some sample menu items if none exist
        if not MenuItem.query.first():
            items = [
                MenuItem(
                    name='Margherita Pizza',
                    description='Classic pizza with tomato sauce, mozzarella, and basil',
                    price=12.99,
                    gst=5.0,
                    discount=0.0,
                    image_path='uploads/pizza.jpg'
                ),
                MenuItem(
                    name='Caesar Salad',
                    description='Fresh romaine lettuce with Caesar dressing, croutons, and parmesan',
                    price=8.99,
                    gst=5.0,
                    discount=1.00,
                    image_path='uploads/salad.jpg'
                ),
                MenuItem(
                    name='Chocolate Brownie',
                    description='Warm chocolate brownie with vanilla ice cream',
                    price=6.99,
                    gst=5.0,
                    discount=0.50,
                    image_path='uploads/brownie.jpg'
                )
            ]
            db.session.add_all(items)
        
        db.session.commit()
        print("Database initialized successfully!")

# Call the initialization function when this script is run directly
if __name__ == '__main__':
    init_db()
