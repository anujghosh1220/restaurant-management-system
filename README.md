# Restaurant Management System

A comprehensive web-based restaurant management system that provides a complete solution for both customers and administrators. The system allows customers to browse the menu, place orders, and make payments, while administrators can manage the entire restaurant operations.

## Features

### User Role Management
- **Admin**: Full control over menu items, orders, and system settings
- **User**: Browse menu, place orders, view order history, and download invoices

### Menu Management
- **CRUD Operations**: Add, edit, and delete menu items with images
- **Pricing**: Set base prices, apply GST, and configure discounts
- **Discounts**: Time-based discounts with start/end dates
  - Automatic discount application based on schedule
  - Individual item discounts and site-wide promotions
- **Categories**: Organize menu items by categories
- **Availability**: Toggle item availability

### Order Management
- **Shopping Cart**: Add/remove items, update quantities
- **Checkout Process**: Multiple payment methods (UPI, Card, Net Banking, COD)
- **Order Tracking**: View order status and history
- **Invoice Generation**: Professional PDF invoices with itemized billing

### Payment Processing
- **Secure Payments**: Multiple payment gateway integration
- **Payment Methods**:
  - UPI
  - Credit/Debit Cards
  - Net Banking
  - Cash on Delivery (COD) with two options:
    - **UPI Payment**: Scan QR code provided by delivery agent
    - **Cash Payment**: Pay with physical cash on delivery
- **Automatic Calculations**:
  - Subtotal calculation
  - Discount application (before GST)
  - GST calculation on discounted amount
  - Final total with breakdown

### Reporting & Analytics
- **Sales Reports**: Daily, weekly, monthly sales
- **Popular Items**: Track best-selling menu items
- **Revenue Analysis**: GST and discount impact on revenue

## Prerequisites

- Python 3.8+
- pip (Python package manager)
- SQLite (included in Python)
- Modern web browser (Chrome, Firefox, Safari, Edge)

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/restaurant_management_system.git
   cd restaurant_management_system
   ```

2. Create and activate a virtual environment (recommended):
   ```bash
   # Windows
   python -m venv venv
   .\venv\Scripts\activate
   
   # macOS/Linux
   python3 -m venv venv
   source venv/bin/activate
   ```

3. Install the required packages:
   ```bash
   pip install -r requirements.txt
   ```

4. Initialize the database and create admin user:
   ```bash
   python database.py
   ```
   
5. Run database migrations (if any):
   ```bash
   flask db upgrade
   ```

## Running the Application

1. Start the development server:
   ```bash
   # Development mode with auto-reload
   python app.py
   
   # Or for production:
   # gunicorn -w 4 -b 0.0.0.0:5000 app:app
   ```

2. Open your web browser and visit:
   ```
   http://localhost:5000
   ```

3. Access the admin panel at:
   ```
   http://localhost:5000/admin
   ```

## Default Admin Account

- **Username:** admin@example.com
- **Password:** admin123

> **Security Note**: Change the default password immediately after first login.

## Project Structure

```
restaurant_management_system/
├── app.py                # Main application file
├── config.py             # Configuration settings
├── database.py           # Database initialization
├── requirements.txt      # Python dependencies
├── migrations/           # Database migrations
├── static/               # Static files (CSS, JS, images)
│   ├── css/              # Custom styles
│   ├── js/               # JavaScript files
│   └── uploads/          # Uploaded item images
└── templates/            # HTML templates
    ├── admin/            # Admin panel templates
    │   ├── base.html     # Base admin template
    │   ├── dashboard.html
    │   ├── new_item.html
    │   ├── orders.html
    │   └── edit_item.html
    ├── auth/             # Authentication templates
    │   ├── login.html
    │   └── signup.html
    ├── cart.html         # Shopping cart
    ├── checkout/         # Checkout process
    │   ├── payment_options.html
    │   └── order_confirmation.html
    ├── orders/           # Order management
    │   ├── list.html
    │   └── invoice.html
    ├── base.html         # Base template
    ├── index.html        # Home/Menu page
    └── item_details.html # Item details page
```

## Features in Detail

### User Features
- **Menu Browsing**
  - View all menu items with images and descriptions
  - Filter by categories
  - Search functionality
  - Sort by price, popularity, or name

- **Shopping Cart**
  - Add/remove items
  - Update quantities
  - Real-time price calculation
  - Apply promo codes

- **Order Management**
  - Secure checkout process
  - Multiple payment methods
  - Order tracking
  - Order history
  - Invoice generation

- **User Account**
  - Registration and login
  - Profile management
  - Order history
  - Saved payment methods (optional)

### Admin Features
- **Dashboard**
  - Sales overview
  - Recent orders
  - System status

- **Menu Management**
  - Add/edit/delete menu items
  - Manage categories
  - Set pricing and discounts
  - Upload item images

- **Order Management**
  - View all orders
  - Update order status
  - Process refunds
  - Generate reports

- **Settings**
  - Configure GST rates
  - Set site-wide discounts
  - Manage business hours
  - Configure payment gateways

### Recent Updates

- Added support for multiple COD payment methods (UPI/Cash)
- Enhanced order confirmation page with payment instructions
- Added admin order management with delete functionality
- Improved responsive design with fixed navigation
- Added discount management for menu items
- Enhanced menu item management with image uploads availability
- View all menu items in a sortable table

## Security

- Password hashing with Werkzeug
- CSRF protection
- Secure file upload handling
- Role-based access control

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request
