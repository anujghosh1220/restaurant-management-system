from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory, make_response, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_migrate import Migrate
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
import os
import json
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from io import BytesIO
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///restaurant.db'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

db = SQLAlchemy(app)
migrate = Migrate(app, db)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@dataclass
class OrderTotals:
    subtotal: float
    discount_amount: float
    net_price: float
    gst_amount: float
    total: float

def calculate_order_totals(items, gst_percentage, discount_percentage=0.0):
    """
    Calculate order totals with consistent GST and discount application.
    
    Args:
        items: List of items with 'price' and 'quantity' attributes or keys
        gst_percentage: GST percentage to apply
        discount_percentage: Discount percentage to apply (default: 0.0)
        
    Returns:
        OrderTotals object with all calculated values
    """
    from decimal import Decimal, ROUND_HALF_UP
    
    def get_price(item):
        # Handle both dictionary and object access
        return item['price'] if isinstance(item, dict) else item.price
    
    def get_quantity(item):
        # Handle both dictionary and object access
        return item['quantity'] if isinstance(item, dict) else item.quantity
    
    # Calculate subtotal (sum of all items * quantity)
    subtotal = float(sum(
        Decimal(str(get_price(item))) * get_quantity(item)
        for item in items
    ))
    
    # Apply discount if any
    discount_amount = 0.0
    net_price = subtotal
    
    if discount_percentage and discount_percentage > 0:
        discount_amount = float((Decimal(str(subtotal)) * Decimal(str(discount_percentage / 100))).quantize(
            Decimal('0.01'), 
            rounding=ROUND_HALF_UP
        ))
        net_price = float((Decimal(str(subtotal)) - Decimal(str(discount_amount))).quantize(
            Decimal('0.01'),
            rounding=ROUND_HALF_UP
        ))
    
    # Calculate GST on the net price (after discount)
    gst_amount = float((Decimal(str(net_price)) * Decimal(str(gst_percentage / 100))).quantize(
        Decimal('0.01'),
        rounding=ROUND_HALF_UP
    ))
    
    # Calculate total
    total = float((Decimal(str(net_price)) + Decimal(str(gst_amount))).quantize(
        Decimal('0.01'),
        rounding=ROUND_HALF_UP
    ))
    
    return OrderTotals(
        subtotal=subtotal,
        discount_amount=discount_amount,
        net_price=net_price,
        gst_amount=gst_amount,
        total=total
    )

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Models
class Cart(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    items = db.relationship('CartItem', backref='cart', lazy=True, cascade='all, delete-orphan')

class OrderItem(db.Model):
    __tablename__ = 'order_item'
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    menu_item_id = db.Column(db.Integer, db.ForeignKey('menu_item.id'), nullable=False)
    menu_item_name = db.Column(db.String(200), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    menu_item = db.relationship('MenuItem')

class Order(db.Model):
    __tablename__ = 'order'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    status = db.Column(db.String(20), default='pending', nullable=False)  # pending, paid, completed, cancelled
    payment_method = db.Column(db.String(20), nullable=True)  # upi, card, netbanking, cod
    cod_payment_method = db.Column(db.String(20), nullable=True)  # upi, cash (only used when payment_method is 'cod')
    payment_status = db.Column(db.String(20), default='pending')  # pending, completed, failed, refunded
    payment_reference = db.Column(db.String(100), nullable=True)  # Transaction ID or reference
    total_amount = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = db.relationship('User', backref=db.backref('orders', lazy=True))
    items = db.relationship('OrderItem', backref='order', lazy=True, cascade='all, delete-orphan')

class CartItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cart_id = db.Column(db.Integer, db.ForeignKey('cart.id'), nullable=False)
    menu_item_id = db.Column(db.Integer, db.ForeignKey('menu_item.id'), nullable=False)
    quantity = db.Column(db.Integer, default=1, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    menu_item = db.relationship('MenuItem')

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)  # New email field
    password = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)  # New field for creation time
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)  # New field for update time
    cart = db.relationship('Cart', backref='user', uselist=False, cascade='all, delete-orphan')
    
    def get_or_create_cart(self):
        if not self.cart:
            self.cart = Cart(user_id=self.id)
            db.session.add(self.cart)
            db.session.commit()
        return self.cart

class Settings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    gst_percentage = db.Column(db.Float, default=18.0)
    discount_percentage = db.Column(db.Float, default=0.0)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @classmethod
    def get_settings(cls):
        settings = cls.query.first()
        if not settings:
            settings = Settings()
            db.session.add(settings)
            db.session.commit()
        return settings

class MenuItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    price = db.Column(db.Float, nullable=False)
    original_price = db.Column(db.Float, nullable=False)  # Store original price here
    discount_percentage = db.Column(db.Float, default=0.0)
    discount_start = db.Column(db.DateTime, nullable=True)
    discount_end = db.Column(db.DateTime, nullable=True)
    category = db.Column(db.String(50), nullable=True)
    image_path = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    gst = db.Column(db.Float, default=18.0)
    
    def __init__(self, **kwargs):
        # Set original_price before calling parent __init__ to ensure it's set before price
        if 'original_price' not in kwargs and 'price' in kwargs:
            kwargs['original_price'] = kwargs['price']
        super(MenuItem, self).__init__(**kwargs)
        # Ensure original_price is always set and matches price if not set
        if not hasattr(self, 'original_price') or self.original_price is None:
            self.original_price = self.price
    
    @property
    def has_active_discount(self):
        now = datetime.utcnow()
        return (self.discount_percentage > 0 and 
                self.discount_start and 
                self.discount_end and
                self.discount_start <= now <= self.discount_end)
    
    @property
    def current_price(self):
        if self.has_active_discount:
            return self.original_price * (1 - (self.discount_percentage / 100))
        return self.original_price
    
    def apply_discount(self, percentage, days):
        # Only update original_price if there's no active discount
        if not self.has_active_discount:
            self.original_price = self.price
        self.discount_percentage = percentage
        self.discount_start = datetime.utcnow()
        self.discount_end = self.discount_start + timedelta(days=days)
        # Update the current price based on the discount
        self.price = self.original_price * (1 - (percentage / 100))
        db.session.commit()
    
    def remove_discount(self):
        if self.original_price:
            self.price = self.original_price
        self.discount_percentage = 0.0
        self.discount_start = None
        self.discount_end = None
        db.session.commit()
        self.discount_start = None
        self.discount_end = None  # Flat discount amount

    def __repr__(self):
        return f'<MenuItem {self.name}>'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# API Routes
@app.route('/api/settings', methods=['GET'])
def get_settings():
    settings = Settings.get_settings()
    return jsonify({
        'gst_percentage': settings.gst_percentage,
        'discount_percentage': settings.discount_percentage
    })

@app.route('/api/cart', methods=['GET'])
@login_required
def get_cart():
    cart = current_user.get_or_create_cart()
    cart_items = [{
        'id': item.menu_item.id,
        'name': item.menu_item.name,
        'price': float(item.menu_item.price),
        'quantity': item.quantity,
        'image_path': item.menu_item.image_path
    } for item in cart.items]
    
    return jsonify(cart_items)

@app.route('/api/cart/add', methods=['POST'])
@login_required
def add_to_cart():
    try:
        data = request.get_json()
        item_id = data.get('menu_item_id')
        quantity = int(data.get('quantity', 1))
        
        if not item_id:
            return jsonify({'error': 'Menu item ID is required'}), 400
        
        menu_item = MenuItem.query.get(item_id)
        if not menu_item:
            return jsonify({'error': 'Item not found'}), 404
        
        cart = current_user.get_or_create_cart()
        
        # Check if item already in cart
        cart_item = CartItem.query.filter_by(cart_id=cart.id, menu_item_id=item_id).first()
        
        if cart_item:
            # Update quantity if item already in cart
            cart_item.quantity += quantity
        else:
            # Add new item to cart
            cart_item = CartItem(
                cart_id=cart.id,
                menu_item_id=item_id,
                quantity=quantity
            )
            db.session.add(cart_item)
        
        db.session.commit()
        
        return jsonify({
            'message': 'Item added to cart',
            'cart_count': sum(item.quantity for item in cart.items)
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/cart/update', methods=['POST'])
@login_required
def update_cart():
    try:
        data = request.get_json()
        item_id = data.get('menu_item_id')
        quantity = int(data.get('quantity', 1))
        
        if not item_id:
            return jsonify({'error': 'Menu item ID is required'}), 400
            
        cart = current_user.get_or_create_cart()
        cart_item = CartItem.query.filter_by(cart_id=cart.id, menu_item_id=item_id).first()
        
        if not cart_item:
            return jsonify({'error': 'Item not found in cart'}), 404
            
        if quantity <= 0:
            # Remove item if quantity is 0 or less
            db.session.delete(cart_item)
        else:
            # Update quantity
            cart_item.quantity = quantity
            
        db.session.commit()
        
        # Calculate cart totals
        cart_items = CartItem.query.filter_by(cart_id=cart.id).all()
        subtotal = sum(item.menu_item.price * item.quantity for item in cart_items)
        
        return jsonify({
            'message': 'Cart updated',
            'cart_count': sum(item.quantity for item in cart_items),
            'subtotal': subtotal
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@app.route('/api/settings', methods=['POST'])
@login_required
def update_settings():
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.get_json()
    settings = Settings.get_settings()
    
    try:
        if 'gst_percentage' in data:
            settings.gst_percentage = float(data['gst_percentage'])
        if 'discount_percentage' in data:
            settings.discount_percentage = float(data['discount_percentage'])
        
        db.session.commit()
        return jsonify({'message': 'Settings updated successfully'})
    except (ValueError, TypeError) as e:
        return jsonify({'error': 'Invalid data format'}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/process-payment', methods=['POST'])
@login_required
def process_payment():
    try:
        data = request.get_json()
        payment_method = data.get('payment_method')
        payment_details = data.get('payment_details', {})
        
        # Validate payment method
        valid_methods = ['upi', 'card', 'netbanking', 'cod']
        if payment_method not in valid_methods:
            return jsonify({'success': False, 'message': 'Invalid payment method'}), 400
        
        # Get user's cart
        cart = current_user.get_or_create_cart()
        cart_items = CartItem.query.filter_by(cart_id=cart.id).all()
        
        if not cart_items:
            return jsonify({'success': False, 'message': 'Your cart is empty'}), 400
        
        # Calculate order totals using the utility function
        settings = Settings.get_settings()
        totals = calculate_order_totals(
            items=[{"price": item.menu_item.price, "quantity": item.quantity} for item in cart_items],
            gst_percentage=settings.gst_percentage,
            discount_percentage=settings.discount_percentage
        )
        total_amount = totals.total
        
        # Validate payment details based on method
        if payment_method == 'upi' and not payment_details.get('upi_id'):
            return jsonify({'success': False, 'message': 'Please enter UPI ID'}), 400
            
        if payment_method == 'card':
            if not all(key in payment_details for key in ['card_number', 'expiry', 'cvv', 'name']):
                return jsonify({'success': False, 'message': 'Please fill in all card details'}), 400
            
            # Simple card validation
            card_number = payment_details['card_number'].replace(' ', '')
            if not (len(card_number) >= 13 and len(card_number) <= 19 and card_number.isdigit()):
                return jsonify({'success': False, 'message': 'Invalid card number'}), 400
                
            if len(payment_details['cvv']) not in [3, 4] or not payment_details['cvv'].isdigit():
                return jsonify({'success': False, 'message': 'Invalid CVV'}), 400
        
        # Process payment (in a real app, this would integrate with a payment gateway)
        # For demo purposes, we'll simulate a successful payment
        
        # Get the COD payment method if it exists
        cod_payment_method = payment_details.get('cod_payment_method') if payment_method == 'cod' else None
        
        with db.session.no_autoflush:
            # Create order
            order = Order(
                user_id=current_user.id,
                status='paid' if payment_method != 'cod' else 'pending',
                total_amount=total_amount,
                payment_method=payment_method,
                payment_status='completed' if payment_method != 'cod' else 'pending',
                cod_payment_method=cod_payment_method if payment_method == 'cod' else None
            )
            db.session.add(order)
            db.session.flush()
            
            # Add items to order
            for item in cart_items:
                order_item = OrderItem(
                    order_id=order.id,
                    menu_item_id=item.menu_item_id,
                    menu_item_name=item.menu_item.name,
                    quantity=item.quantity,
                    price=item.menu_item.price
                )
                order.items.append(order_item)
            
            # Clear the cart
            CartItem.query.filter_by(cart_id=cart.id).delete()
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'Payment successful' if payment_method != 'cod' else 'Order placed successfully. Payment will be collected on delivery.',
                'order_id': order.id,
                'is_cod': payment_method == 'cod'
            })
            
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/cart/checkout', methods=['POST'])
@login_required
def checkout():
    try:
        data = request.get_json()
        payment_method = data.get('payment_method', 'cod')
        
        # This is kept for backward compatibility
        return process_payment()
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/cart/clear', methods=['POST'])
@login_required
def clear_cart():
    try:
        # Delete all items in the user's cart
        CartItem.query.filter_by(cart_id=current_user.cart.id).delete()
        db.session.commit()
        return jsonify({'success': True, 'message': 'Cart cleared successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

# Routes
@app.route('/')
def index():
    category = request.args.get('category')
    if category:
        menu_items = MenuItem.query.filter_by(category=category).all()
    else:
        menu_items = MenuItem.query.all()
    
    # Get all unique categories for the filter buttons
    categories = db.session.query(MenuItem.category).distinct().all()
    categories = [cat[0] for cat in categories if cat[0]]  # Filter out None values
    
    return render_template('index.html', 
                         menu_items=menu_items, 
                         categories=categories,
                         current_category=category)

@app.route('/cart')
def view_cart():
    # Get cart from session storage (handled by client-side JavaScript)
    return render_template('cart.html')

@app.route('/item/<int:item_id>')
def item_details(item_id):
    item = MenuItem.query.get_or_404(item_id)
    return render_template('item_details.html', item=item)

@app.route('/admin')
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('index'))
    
    # Get all menu items ordered by creation date (newest first)
    menu_items = MenuItem.query.order_by(MenuItem.created_at.desc()).all()
    return render_template('admin/dashboard.html', menu_items=menu_items)

@app.route('/orders')
@login_required
def user_orders():
    # Get current user's orders
    orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.created_at.desc()).all()
    return render_template('orders.html', orders=orders)

@app.route('/invoice/<int:order_id>')
@login_required
def view_invoice(order_id):
    # Users can only view their own invoices, admins can view any
    order = Order.query.get_or_404(order_id)
    if not current_user.is_admin and order.user_id != current_user.id:
        flash('You are not authorized to view this invoice.', 'danger')
        return redirect(url_for('index'))
    
    # Get settings
    settings = Settings.get_settings()
    
    # Calculate order totals using the utility function
    totals = calculate_order_totals(
        items=[{"price": item.price, "quantity": item.quantity} for item in order.items],
        gst_percentage=settings.gst_percentage,
        discount_percentage=settings.discount_percentage
    )
    
    return render_template('invoice.html', 
                         order=order,
                         settings=settings,
                         subtotal=totals.subtotal,
                         net_price=totals.net_price,
                         gst_amount=totals.gst_amount,
                         discount_amount=totals.discount_amount,
                         total=totals.total)

# Show list of invoices for the current user
@app.route('/invoices')
@login_required
def list_invoices():
    # Get all paid or completed orders for the current user
    orders = Order.query.filter(
        Order.user_id == current_user.id,
        Order.status.in_(['paid', 'completed', 'delivered'])
    ).order_by(Order.updated_at.desc()).all()
    
    return render_template('invoices.html', orders=orders)

# Redirect root /invoice to invoices list
@app.route('/invoice')
@login_required
def invoice_redirect():
    return redirect(url_for('list_invoices'))


@app.route('/admin/items/<int:item_id>/discount/apply', methods=['POST'])
@login_required
def apply_discount(item_id):
    if not current_user.is_admin:
        flash('You do not have permission to perform this action.', 'danger')
        return redirect(url_for('admin_dashboard'))
    
    try:
        item = MenuItem.query.get_or_404(item_id)
        discount_percentage = float(request.form.get('discount_percentage', 0))
        days = int(request.form.get('discount_days', 7))
        
        if discount_percentage <= 0 or discount_percentage > 100:
            flash('Discount percentage must be between 0.01 and 100', 'danger')
            return redirect(url_for('admin_dashboard'))
        
        item.apply_discount(discount_percentage, days)
        db.session.commit()
        
        flash(f'Successfully applied {discount_percentage}% discount to {item.name} for {days} days', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error applying discount: {str(e)}', 'danger')
    
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/items/<int:item_id>/discount/remove', methods=['POST'])
@login_required
def remove_discount(item_id):
    if not current_user.is_admin:
        flash('You do not have permission to perform this action.', 'danger')
        return redirect(url_for('admin_dashboard'))
    
    try:
        item = MenuItem.query.get_or_404(item_id)
        item.remove_discount()
        db.session.commit()
        flash(f'Successfully removed discount from {item.name}', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error removing discount: {str(e)}', 'danger')
    
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/orders', methods=['GET', 'POST'])
@login_required
def admin_orders():
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('index'))
    
    if request.method == 'POST' and request.is_json:
        data = request.get_json()
        order_id = data.get('order_id')
        action = data.get('action')
        
        if not order_id or not action:
            return jsonify({'success': False, 'message': 'Missing parameters'}), 400
            
        order = Order.query.get(order_id)
        if not order:
            return jsonify({'success': False, 'message': 'Order not found'}), 404
            
        if action == 'mark_paid':
            order.status = 'paid'
            db.session.commit()
            return jsonify({'success': True, 'message': f'Order marked as {order.status}'})
        elif action == 'mark_completed':
            order.status = 'completed'
            db.session.commit()
            return jsonify({'success': True, 'message': f'Order marked as {order.status}'})
        elif action == 'delete':
            try:
                # Delete order items first due to foreign key constraint
                OrderItem.query.filter_by(order_id=order_id).delete()
                # Then delete the order
                db.session.delete(order)
                db.session.commit()
                return jsonify({'success': True, 'message': 'Order deleted successfully'})
            except Exception as e:
                db.session.rollback()
                return jsonify({'success': False, 'message': f'Error deleting order: {str(e)}'}), 500
        else:
            return jsonify({'success': False, 'message': 'Invalid action'}), 400
    
    # Get all orders with user and items data
    orders = Order.query.order_by(Order.created_at.desc()).all()
    return render_template('admin/orders.html', orders=orders)

@app.route('/admin/item/new', methods=['GET', 'POST'])
@login_required
def new_item():
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        name = request.form.get('name')
        price = float(request.form.get('price'))
        description = request.form.get('description', '').strip()
        category = request.form.get('category')
        
        # Handle file upload
        image_path = None
        if 'image' in request.files:
            file = request.files['image']
            if file.filename != '':
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                image_path = f"uploads/{filename}"
        
        new_item = MenuItem(
            name=name,
            price=price,
            description=description if description else None,
            image_path=image_path,
            category=category
        )
        
        db.session.add(new_item)
        db.session.commit()
        flash('Menu item added successfully!', 'success')
        return redirect(url_for('admin_dashboard'))
    
    return render_template('admin/new_item.html')

@app.route('/admin/item/edit/<int:item_id>', methods=['GET', 'POST'])
@login_required
def edit_item(item_id):
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('index'))
    
    item = MenuItem.query.get_or_404(item_id)
    
    if request.method == 'POST':
        item.name = request.form.get('name')
        item.price = float(request.form.get('price'))
        description = request.form.get('description', '').strip()
        item.description = description if description else None
        item.category = request.form.get('category')
        
        # Handle file upload if a new image is provided
        if 'image' in request.files:
            file = request.files['image']
            if file.filename != '':
                # Delete old image if it exists
                if item.image_path:
                    try:
                        os.remove(os.path.join('static', item.image_path))
                    except OSError:
                        pass
                
                # Save new image
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                item.image_path = f"uploads/{filename}"
        
        db.session.commit()
        flash('Menu item updated successfully!', 'success')
        return redirect(url_for('admin_dashboard'))
    
    return render_template('admin/new_item.html', item=item)

@app.route('/admin/item/delete/<int:item_id>', methods=['POST'])
@login_required
def delete_item(item_id):
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('index'))
    
    item = MenuItem.query.get_or_404(item_id)
    
    # Delete the associated image file if it exists
    if item.image_path:
        try:
            os.remove(os.path.join('static', item.image_path))
        except OSError:
            pass
    
    db.session.delete(item)
    db.session.commit()
    
    flash('Menu item deleted successfully!', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/generate_invoice/<int:item_id>')
@login_required
def generate_invoice(item_id):
    item = MenuItem.query.get_or_404(item_id)
    
    # Calculate total
    gst_amount = (item.price * item.gst) / 100
    total = item.price + gst_amount - item.discount
    
    # Create PDF in memory
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    
    # Add content to PDF
    p.setFont("Helvetica-Bold", 16)
    p.drawString(100, 750, "Restaurant Invoice")
    p.line(100, 745, 500, 745)
    
    p.setFont("Helvetica", 12)
    y_position = 700
    
    # Add customer information
    if current_user.is_authenticated:
        p.drawString(100, y_position, f"Customer: {current_user.username}")
        y_position -= 25
    
    # Add invoice details
    p.drawString(100, y_position, f"Item: {item.name}")
    y_position -= 25
    p.drawString(100, y_position, f"Price: ${item.price:.2f}")
    y_position -= 25
    p.drawString(100, y_position, f"GST ({item.gst}%): ${gst_amount:.2f}")
    y_position -= 25
    p.drawString(100, y_position, f"Discount: ${item.discount:.2f}")
    y_position -= 30
    p.line(100, y_position, 300, y_position)
    y_position -= 25
    
    # Add total
    p.setFont("Helvetica-Bold", 14)
    p.drawString(100, y_position, f"Total: ${total:.2f}")
    y_position -= 40
    
    # Add footer
    p.setFont("Helvetica", 10)
    p.drawString(100, y_position, "Thank you for your order!")
    y_position -= 15
    p.drawString(100, y_position, f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    y_position -= 15
    p.drawString(100, y_position, "Restaurant Management System")
    
    p.save()
    
    # Prepare the response
    buffer.seek(0)
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    filename = f"invoice_{item.name.replace(' ', '_')}_{timestamp}.pdf"
    
    response = make_response(buffer.getvalue())
    response.mimetype = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename={filename}'
    
    return response

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        username = request.form['username']
        email = request.form.get('email')  # Get email from form
        password = request.form['password']
        
        # Check if username already exists
        if User.query.filter_by(username=username).first():
            flash('Username already exists. Please choose a different one.', 'danger')
            return redirect(url_for('signup'))
            
        # Check if email already exists
        if email and User.query.filter_by(email=email).first():
            flash('Email already registered. Please use a different email or log in.', 'danger')
            return redirect(url_for('signup'))
        
        # Create new user with email
        hashed_password = generate_password_hash(password, method='sha256')
        new_user = User(
            username=username, 
            email=email if email else None,  # Store email if provided, None otherwise
            password=hashed_password
        )
        db.session.add(new_user)
        db.session.commit()
        
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))
    
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False
        
        if not email or not password:
            flash('Please provide both email and password.', 'danger')
            return redirect(url_for('login'))
            
        user = User.query.filter_by(email=email).first()
        
        # Check if user exists and password is correct
        if not user or not check_password_hash(user.password, password):
            flash('Invalid email or password. Please try again.', 'danger')
            return redirect(url_for('login'))
            
        # If the above check passes, log the user in
        login_user(user, remember=remember)
        next_page = request.args.get('next')
        return redirect(next_page or url_for('index'))
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

def create_admin():
    with app.app_context():
        db.create_all()
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            hashed_password = generate_password_hash('admin123', method='sha256')
            admin = User(username='admin', password=hashed_password, is_admin=True)
            db.session.add(admin)
            db.session.commit()

@app.route('/create-admin')
def create_admin():
    try:
        # Check if admin already exists
        admin = User.query.filter_by(username='admin').first()
        
        if admin:
            return f"Admin user already exists with ID: {admin.id}"
        
        # Create new admin user
        admin = User(
            username='admin',
            email='admin@example.com',  # Add admin email
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
        return f"Error creating admin user: {str(e)}"
    finally:
        db.session.close()

def init_admin():
    """Legacy function - now handled by create_tables()"""
    print("Admin initialization is now handled by create_tables()")
    # The actual admin creation is now handled in create_tables()
    # This function is kept for backward compatibility

@app.route('/order-confirmation')
@login_required
def order_confirmation():
    order_id = request.args.get('order_id')
    if not order_id:
        flash('No order specified', 'danger')
        return redirect(url_for('index'))
    
    order = Order.query.filter_by(id=order_id, user_id=current_user.id).first_or_404()
    settings = Settings.get_settings()
    
    # Calculate order totals using the utility function
    totals = calculate_order_totals(
        items=[{"price": item.price, "quantity": item.quantity} for item in order.items],
        gst_percentage=settings.gst_percentage,
        discount_percentage=settings.discount_percentage
    )
    
    # For backward compatibility, if cod_payment_method is not set, default to 'cash'
    if order.payment_method == 'cod' and not hasattr(order, 'cod_payment_method'):
        order.cod_payment_method = 'cash'
    
    return render_template('order_confirmation.html', 
                         order=order,
                         order_items=order.items,
                         settings=settings,
                         subtotal=totals.subtotal,
                         net_price=totals.net_price,
                         gst_amount=totals.gst_amount,
                         discount_amount=totals.discount_amount,
                         total=totals.total)

@app.route('/payment-options')
@login_required
def payment_options():
    # Get cart items to show order summary
    cart = current_user.get_or_create_cart()
    cart_items = CartItem.query.filter_by(cart_id=cart.id).all()
    
    if not cart_items:
        flash('Your cart is empty', 'warning')
        return redirect(url_for('view_cart'))
    
    # Calculate order totals using the utility function
    settings = Settings.get_settings()
    totals = calculate_order_totals(
        items=[{"price": item.menu_item.price, "quantity": item.quantity} for item in cart_items],
        gst_percentage=settings.gst_percentage,
        discount_percentage=settings.discount_percentage
    )
    
    return render_template('payment_options.html', 
                         cart_items=cart_items,
                         subtotal=totals.subtotal,
                         net_price=totals.net_price,
                         gst_amount=totals.gst_amount,
                         discount_amount=totals.discount_amount,
                         total=totals.total,
                         settings=settings)

def check_expired_discounts():
    """Check for and remove any expired discounts"""
    with app.app_context():
        try:
            now = datetime.utcnow()
            expired_items = MenuItem.query.filter(
                MenuItem.discount_end.isnot(None),
                MenuItem.discount_end < now
            ).all()
            
            for item in expired_items:
                if item.original_price:
                    item.price = item.original_price
                item.discount_percentage = 0.0
                item.discount_start = None
                item.discount_end = None
            
            if expired_items:
                db.session.commit()
                app.logger.info(f"Removed expired discounts from {len(expired_items)} items")
        except Exception as e:
            app.logger.error(f"Error checking expired discounts: {str(e)}")
            db.session.rollback()

# Check for expired discounts when the app starts
check_expired_discounts()

# Schedule periodic check for expired discounts (every hour)
from apscheduler.schedulers.background import BackgroundScheduler
scheduler = BackgroundScheduler()
scheduler.add_job(func=check_expired_discounts, trigger='interval', hours=1)
scheduler.start()

def create_tables():
    """Create database tables if they don't exist and ensure admin user exists."""
    with app.app_context():
        try:
            # This will create all tables that don't exist
            db.create_all()
            print("Database tables created successfully")
            
            # Check if admin user exists, if not create one
            admin_username = os.getenv('ADMIN_USERNAME', 'admin')
            admin_password = os.getenv('ADMIN_PASSWORD', 'admin123')
            admin_email = os.getenv('ADMIN_EMAIL', 'admin@example.com')
            
            admin_user = User.query.filter_by(username=admin_username).first()
            if not admin_user:
                hashed_password = generate_password_hash(admin_password, method='pbkdf2:sha256')
                admin = User(
                    username=admin_username,
                    email=admin_email,
                    password=hashed_password,
                    is_admin=True
                )
                db.session.add(admin)
                db.session.commit()
                print(f"Admin user '{admin_username}' created with password '{admin_password}'")
            
            # Initialize default settings if they don't exist
            if not Settings.query.first():
                default_settings = Settings(
                    gst_percentage=18.0,
                    discount_percentage=0.0
                )
                db.session.add(default_settings)
                db.session.commit()
                print("Default settings created")
                
        except Exception as e:
            print(f"Error during database initialization: {str(e)}")
            db.session.rollback()
            # If there's an error, try to continue anyway

# Create tables when the app starts
create_tables()

if __name__ == '__main__':
    # The app is already initialized with create_tables()
    # which handles both table creation and admin user setup
    app.run(debug=True)
