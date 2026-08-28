from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import database
import payment_config
import functools
import os
import hashlib
import hmac
import urllib.parse

# Payment SDK Imports (with fallback handling)
try:
    import razorpay
except ImportError:
    razorpay = None

try:
    import stripe
except ImportError:
    stripe = None

app = Flask(__name__)
app.secret_key = 'dairy_secret_key_super_secure_2025'

# Initialize database tables on start
database.init_db()

# Session decorator helpers
def login_required(f):
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or session.get('role') != 'admin':
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated_function

# --- Page Routes ---

@app.route('/')
def home():
    if 'user_id' not in session:
        return redirect(url_for('login_page'))
    conn = database.get_db()
    featured = conn.execute("SELECT * FROM products WHERE is_active = 1 LIMIT 6").fetchall()
    conn.close()
    return render_template('index.html', featured_products=featured)

@app.route('/products')
def products_page():
    if 'user_id' not in session:
        return redirect(url_for('login_page'))
    category = request.args.get('category', '')
    return render_template('products.html', selected_category=category)

@app.route('/cart')
def cart_page():
    if 'user_id' not in session:
        return redirect(url_for('login_page'))
    return render_template('cart.html')

@app.route('/orders')
@login_required
def orders_page():
    return render_template('orders.html')

@app.route('/admin')
@admin_required
def admin_page():
    return render_template('admin.html')

@app.route('/wishlist')
@login_required
def wishlist_page():
    return render_template('wishlist.html')

@app.route('/login')
def login_page():
    return render_template('login.html')

@app.route('/owner-login')
def owner_login_page():
    return render_template('owner_login.html')

def send_order_email_notification(to_email, order_id, status_title, details):
    """Simulates sending transactional HTML email receipts to customers."""
    safe_details = str(details).replace('₹', 'Rs.')
    print(f"\n[EMAIL NOTIFICATION DISPATCHED]")
    print(f"To: {to_email}")
    print(f"Subject: FreshDairy Order #{order_id} - {status_title}")
    print(f"Details: {safe_details}")
    print(f"Status: Sent successfully via SMTP mock pipeline.\n")

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login_page'))

# --- Auth APIs ---

@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.get_json() or {}
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')

    if not email or not password:
        return jsonify({'success': False, 'message': 'Email and password are required.'}), 400

    conn = database.get_users_db()
    pwd_hash = database.hash_password(password)
    user = conn.execute("SELECT * FROM users WHERE email = ? AND password_hash = ?", (email, pwd_hash)).fetchone()
    conn.close()

    if user:
        session['user_id'] = user['id']
        session['user_name'] = user['name']
        session['user_email'] = user['email']
        session['role'] = user['role']
        return jsonify({
            'success': True,
            'message': 'Login successful',
            'user': {
                'id': user['id'],
                'name': user['name'],
                'email': user['email'],
                'role': user['role']
            }
        })
    else:
        return jsonify({'success': False, 'message': 'Invalid email or password.'}), 401

@app.route('/api/register', methods=['POST'])
def api_register():
    data = request.get_json() or {}
    name = data.get('name', '').strip()
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    phone = data.get('phone', '').strip()
    address = data.get('address', '').strip()

    if not name or not email or not password:
        return jsonify({'success': False, 'message': 'Name, email, and password are required.'}), 400

    conn = database.get_users_db()
    existing = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
    if existing:
        conn.close()
        return jsonify({'success': False, 'message': 'An account with this email already exists.'}), 400

    pwd_hash = database.hash_password(password)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO users (name, email, password_hash, role, phone, address)
        VALUES (?, ?, ?, 'customer', ?, ?)
    ''', (name, email, pwd_hash, phone, address))
    user_id = cursor.lastrowid
    conn.commit()
    conn.close()

    session['user_id'] = user_id
    session['user_name'] = name
    session['user_email'] = email
    session['role'] = 'customer'

    return jsonify({'success': True, 'message': 'Registration successful!'})

@app.route('/api/demo-login', methods=['POST'])
def api_demo_login():
    data = request.get_json() or {}
    role = data.get('role', 'customer')

    target_email = 'admin@dairy.com' if role == 'admin' else 'customer@dairy.com'
    conn = database.get_users_db()
    user = conn.execute("SELECT * FROM users WHERE email = ?", (target_email,)).fetchone()
    conn.close()

    if user:
        session['user_id'] = user['id']
        session['user_name'] = user['name']
        session['user_email'] = user['email']
        session['role'] = user['role']
        return jsonify({
            'success': True,
            'message': f'Logged in as demo {role.capitalize()}',
            'role': user['role']
        })
    return jsonify({'success': False, 'message': 'Demo account not found.'}), 404

# --- Products APIs ---

@app.route('/api/products')
def api_get_products():
    category = request.args.get('category', '')
    search = request.args.get('search', '').strip()

    conn = database.get_db()
    query = "SELECT * FROM products WHERE is_active = 1"
    params = []

    if category and category != 'All':
        query += " AND category = ?"
        params.append(category)

    if search:
        query += " AND (name LIKE ? OR description LIKE ?)"
        params.append(f"%{search}%")
        params.append(f"%{search}%")

    query += " ORDER BY category ASC, id ASC"

    products = conn.execute(query, params).fetchall()
    conn.close()

    result = [dict(p) for p in products]
    return jsonify({'success': True, 'products': result})

# --- Wishlist APIs ---

@app.route('/api/wishlist/toggle', methods=['POST'])
@login_required
def api_toggle_wishlist():
    data = request.get_json() or {}
    product_id = data.get('product_id')
    user_id = session['user_id']

    if not product_id:
        return jsonify({'success': False, 'message': 'Product ID required.'}), 400

    conn = database.get_db()
    cursor = conn.cursor()

    existing = cursor.execute("SELECT id FROM wishlist WHERE user_id = ? AND product_id = ?", (user_id, product_id)).fetchone()
    if existing:
        cursor.execute("DELETE FROM wishlist WHERE id = ?", (existing['id'],))
        is_wishlisted = False
        msg = 'Removed from Wishlist'
    else:
        cursor.execute("INSERT INTO wishlist (user_id, product_id) VALUES (?, ?)", (user_id, product_id))
        is_wishlisted = True
        msg = 'Saved to Wishlist'

    conn.commit()
    conn.close()

    return jsonify({'success': True, 'message': msg, 'is_wishlisted': is_wishlisted})

@app.route('/api/wishlist')
@login_required
def api_get_wishlist():
    user_id = session['user_id']
    conn = database.get_db()

    rows = conn.execute('''
        SELECT p.*
        FROM wishlist w
        JOIN products p ON w.product_id = p.id
        WHERE w.user_id = ? AND p.is_active = 1
    ''', (user_id,)).fetchall()

    conn.close()
    return jsonify({'success': True, 'products': [dict(r) for r in rows]})

# --- Coupon Validation API ---

@app.route('/api/coupon/validate', methods=['POST'])
def api_validate_coupon():
    data = request.get_json() or {}
    code = data.get('code', '').strip().upper()
    subtotal = float(data.get('subtotal', 0))

    if not code:
        return jsonify({'success': False, 'message': 'Please enter a coupon code.'}), 400

    conn = database.get_db()
    coupon = conn.execute("SELECT * FROM coupons WHERE code = ? AND is_active = 1", (code,)).fetchone()
    conn.close()

    if not coupon:
        return jsonify({'success': False, 'message': 'Invalid or expired coupon code.'}), 400

    if subtotal < coupon['min_order_amount']:
        return jsonify({
            'success': False,
            'message': f"Coupon '{code}' requires a minimum order amount of ₹{coupon['min_order_amount']:.2f}."
        }), 400

    discount_amount = 0.0
    if coupon['discount_type'] == 'percent':
        discount_amount = round((subtotal * coupon['discount_value']) / 100.0, 2)
    elif coupon['discount_type'] == 'fixed':
        discount_amount = min(coupon['discount_value'], subtotal)

    final_total = max(0.0, round(subtotal - discount_amount, 2))

    return jsonify({
        'success': True,
        'message': f"Coupon '{code}' applied successfully!",
        'coupon_code': code,
        'discount_amount': discount_amount,
        'final_total': final_total
    })

@app.route('/api/orders', methods=['POST'])
def api_create_order():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Please login to place an order.'}), 401

    data = request.get_json() or {}
    items = data.get('items', [])
    order_type = data.get('order_type', 'one-time') # 'one-time' or 'subscription'
    delivery_address = (data.get('delivery_address') or '').strip()
    delivery_slot = data.get('delivery_slot', 'Morning (6 AM - 8 AM)')
    payment_method = data.get('payment_method', 'Cash on Delivery')
    sub_start_date = data.get('sub_start_date')
    sub_frequency = data.get('sub_frequency', 'Daily')

    if not items:
        return jsonify({'success': False, 'message': 'Your cart is empty.'}), 400

    if not delivery_address:
        return jsonify({'success': False, 'message': 'Delivery address is required.'}), 400

    conn = database.get_db()
    cursor = conn.cursor()

    # Calculate total and verify stock
    total_amount = 0.0
    order_items_to_insert = []

    for item in items:
        p_id = item.get('id')
        qty = int(item.get('quantity', 1))
        
        prod = cursor.execute("SELECT * FROM products WHERE id = ? AND is_active = 1", (p_id,)).fetchone()
        if not prod:
            conn.close()
            return jsonify({'success': False, 'message': f"Product ID {p_id} no longer available."}), 400
        
        if prod['stock'] < qty:
            conn.close()
            return jsonify({'success': False, 'message': f"Insufficient stock for '{prod['name']}'. Available: {prod['stock']}."}), 400
        
        subtotal = prod['price'] * qty
        total_amount += subtotal
        order_items_to_insert.append((p_id, prod['name'], qty, prod['price'], subtotal))

    raw_coupon = data.get('coupon_code')
    coupon_code = raw_coupon.strip().upper() if (raw_coupon and isinstance(raw_coupon, str)) else None
    discount_amount = float(data.get('discount_amount') or 0)

    if discount_amount > 0:
        total_amount = max(0.0, total_amount - discount_amount)

    payment_status = 'Pending'

    # Insert Order
    cursor.execute('''
        INSERT INTO orders (
            user_id, order_type, total_amount, status, payment_method, payment_status, 
            delivery_address, delivery_slot, sub_start_date, sub_frequency, coupon_code, discount_amount
        )
        VALUES (?, ?, ?, 'Pending', ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        session['user_id'],
        order_type,
        total_amount,
        payment_method,
        payment_status,
        delivery_address,
        delivery_slot,
        sub_start_date if order_type == 'subscription' else None,
        sub_frequency if order_type == 'subscription' else None,
        coupon_code,
        discount_amount
    ))

    order_id = cursor.lastrowid

    # Insert Order Items & Deduct Stock
    for p_id, p_name, qty, price, subtotal in order_items_to_insert:
        cursor.execute('''
            INSERT INTO order_items (order_id, product_id, product_name, quantity, price_per_unit, subtotal)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (order_id, p_id, p_name, qty, price, subtotal))

        cursor.execute('''
            UPDATE products SET stock = stock - ? WHERE id = ?
        ''', (qty, p_id))

    conn.commit()
    conn.close()

    # Trigger Email Notification
    send_order_email_notification(
        session.get('user_email', 'customer@dairy.com'),
        order_id,
        'Order Placed Successfully',
        f'Total: ₹{total_amount:.2f} | Slot: {delivery_slot}'
    )

    return jsonify({
        'success': True,
        'message': 'Order placed successfully!',
        'order_id': order_id
    })

@app.route('/api/user/orders')
@login_required
def api_user_orders():
    user_id = session['user_id']
    conn = database.get_db()

    orders_rows = conn.execute('''
        SELECT * FROM orders WHERE user_id = ? ORDER BY id DESC
    ''', (user_id,)).fetchall()

    orders_list = []
    for o in orders_rows:
        order_dict = dict(o)
        items_rows = conn.execute('''
            SELECT oi.*, p.image_symbol, p.unit
            FROM order_items oi
            LEFT JOIN products p ON oi.product_id = p.id
            WHERE oi.order_id = ?
        ''', (o['id'],)).fetchall()
        order_dict['items'] = [dict(i) for i in items_rows]
        orders_list.append(order_dict)

    conn.close()
    return jsonify({'success': True, 'orders': orders_list})

@app.route('/api/orders/<int:order_id>/cancel', methods=['POST'])
@login_required
def api_cancel_order(order_id):
    user_id = session['user_id']
    conn = database.get_db()
    cursor = conn.cursor()

    order = cursor.execute("SELECT * FROM orders WHERE id = ? AND user_id = ?", (order_id, user_id)).fetchone()
    if not order:
        conn.close()
        return jsonify({'success': False, 'message': 'Order not found.'}), 404

    if order['status'] not in ['Pending', 'Processing']:
        conn.close()
        return jsonify({'success': False, 'message': f'Cannot cancel order with status "{order["status"]}".'}), 400

    # Restore product stock
    items = cursor.execute("SELECT product_id, quantity FROM order_items WHERE order_id = ?", (order_id,)).fetchall()
    for item in items:
        cursor.execute("UPDATE products SET stock = stock + ? WHERE id = ?", (item['quantity'], item['product_id']))

    cursor.execute("UPDATE orders SET status = 'Cancelled' WHERE id = ?", (order_id,))
    conn.commit()
    conn.close()

    return jsonify({'success': True, 'message': 'Order cancelled successfully.'})

# --- Admin APIs ---

@app.route('/api/admin/stats')
@admin_required
def api_admin_stats():
    conn = database.get_db()

    total_revenue = conn.execute("SELECT SUM(total_amount) FROM orders WHERE status != 'Cancelled'").fetchone()[0] or 0.0
    total_orders = conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
    active_subscriptions = conn.execute("SELECT COUNT(*) FROM orders WHERE order_type = 'subscription' AND status != 'Cancelled'").fetchone()[0]
    low_stock_count = conn.execute("SELECT COUNT(*) FROM products WHERE stock < 20 AND is_active = 1").fetchone()[0]
    u_conn = database.get_users_db()
    total_customers = u_conn.execute("SELECT COUNT(*) FROM users WHERE role = 'customer'").fetchone()[0]
    u_conn.close()

    # Category breakdown for stock chart
    categories = conn.execute("SELECT category, COUNT(*) as count, SUM(stock) as total_stock FROM products GROUP BY category").fetchall()

    conn.close()

    return jsonify({
        'success': True,
        'stats': {
            'total_revenue': round(total_revenue, 2),
            'total_orders': total_orders,
            'active_subscriptions': active_subscriptions,
            'low_stock_count': low_stock_count,
            'total_customers': total_customers,
            'categories': [dict(c) for c in categories]
        }
    })

@app.route('/api/admin/products', methods=['GET', 'POST'])
@admin_required
def api_admin_products():
    conn = database.get_db()
    cursor = conn.cursor()

    if request.method == 'POST':
        data = request.get_json() or {}
        name = data.get('name', '').strip()
        category = data.get('category', 'Milk').strip()
        price = float(data.get('price', 0))
        unit = data.get('unit', '500 ml').strip()
        stock = int(data.get('stock', 0))
        description = data.get('description', '').strip()
        image_symbol = data.get('image_symbol', '🥛')

        if not name or price <= 0:
            conn.close()
            return jsonify({'success': False, 'message': 'Product name and valid price are required.'}), 400

        cursor.execute('''
            INSERT INTO products (name, category, price, unit, stock, description, image_symbol)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (name, category, price, unit, stock, description, image_symbol))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': 'Product added successfully!'})

    products = conn.execute("SELECT * FROM products ORDER BY id DESC").fetchall()
    conn.close()
    return jsonify({'success': True, 'products': [dict(p) for p in products]})

@app.route('/api/admin/products/<int:product_id>', methods=['PUT', 'DELETE'])
@admin_required
def api_admin_product_detail(product_id):
    conn = database.get_db()
    cursor = conn.cursor()

    if request.method == 'DELETE':
        # Soft delete / toggle active status
        cursor.execute("UPDATE products SET is_active = CASE WHEN is_active = 1 THEN 0 ELSE 1 END WHERE id = ?", (product_id,))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': 'Product status updated.'})

    if request.method == 'PUT':
        data = request.get_json() or {}
        name = data.get('name', '').strip()
        category = data.get('category', 'Milk').strip()
        price = float(data.get('price', 0))
        unit = data.get('unit', '').strip()
        stock = int(data.get('stock', 0))
        description = data.get('description', '').strip()
        image_symbol = data.get('image_symbol', '🥛')

        cursor.execute('''
            UPDATE products
            SET name=?, category=?, price=?, unit=?, stock=?, description=?, image_symbol=?
            WHERE id=?
        ''', (name, category, price, unit, stock, description, image_symbol, product_id))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': 'Product updated successfully!'})

@app.route('/api/admin/orders')
@admin_required
def api_admin_orders():
    conn = database.get_db()
    u_conn = database.get_users_db()
    users_dict = {u['id']: dict(u) for u in u_conn.execute("SELECT * FROM users").fetchall()}
    u_conn.close()

    status_filter = request.args.get('status', '')
    type_filter = request.args.get('type', '')

    query = "SELECT * FROM orders WHERE 1=1"
    params = []

    if status_filter and status_filter != 'All':
        query += " AND status = ?"
        params.append(status_filter)

    if type_filter and type_filter != 'All':
        query += " AND order_type = ?"
        params.append(type_filter)

    query += " ORDER BY id DESC"

    raw_orders = conn.execute(query, params).fetchall()

    orders_list = []
    for o in raw_orders:
        order_dict = dict(o)
        u_info = users_dict.get(order_dict['user_id'], {})
        order_dict['customer_name'] = u_info.get('name', f"Customer #{order_dict['user_id']}")
        order_dict['customer_email'] = u_info.get('email', '')
        order_dict['customer_phone'] = u_info.get('phone', '')

        items_rows = conn.execute('''
            SELECT oi.*, p.image_symbol
            FROM order_items oi
            LEFT JOIN products p ON oi.product_id = p.id
            WHERE oi.order_id = ?
        ''', (order_dict['id'],)).fetchall()
        order_dict['items'] = [dict(item) for item in items_rows]
        orders_list.append(order_dict)

    conn.close()
    return jsonify({'success': True, 'orders': orders_list})

@app.route('/api/admin/orders/<int:order_id>/status', methods=['PUT'])
@admin_required
def api_admin_update_order_status(order_id):
    data = request.get_json() or {}
    new_status = data.get('status', '')

    valid_statuses = ['Pending', 'Processing', 'Out for Delivery', 'Delivered', 'Cancelled']
    if new_status not in valid_statuses:
        return jsonify({'success': False, 'message': 'Invalid order status.'}), 400

    conn = database.get_db()
    cursor = conn.cursor()

    cursor.execute("UPDATE orders SET status = ? WHERE id = ?", (new_status, order_id))
    conn.commit()
    conn.close()

    return jsonify({'success': True, 'message': f'Order status updated to "{new_status}".'})

# --- Payment Gateway APIs (Razorpay, Stripe & Direct Merchant UPI) ---

@app.route('/api/payment/config')
def api_payment_config():
    cfg = payment_config.load_payment_settings()
    return jsonify({
        'success': True,
        'merchant_name': cfg.get('merchant_name', 'Fresh Dairy Products'),
        'merchant_upi_id': cfg.get('merchant_upi_id', '41837498566@sbi'),
        'razorpay_key_id': cfg.get('razorpay_key_id', ''),
        'stripe_publishable_key': cfg.get('stripe_publishable_key', ''),
        'bank_name': cfg.get('bank_name', 'State Bank of India'),
        'account_number': cfg.get('account_number', '41837498566'),
        'ifsc_code': cfg.get('ifsc_code', 'SBIN0000784'),
        'is_real_razorpay': payment_config.is_real_razorpay(cfg),
        'is_real_stripe': payment_config.is_real_stripe(cfg)
    })

@app.route('/api/admin/payment-settings', methods=['GET', 'POST'])
@admin_required
def api_admin_payment_settings():
    if request.method == 'POST':
        data = request.get_json() or {}
        updated = payment_config.save_payment_settings(data)
        return jsonify({'success': True, 'message': 'Merchant payment settings updated successfully!', 'settings': updated})

    settings = payment_config.load_payment_settings()
    return jsonify({
        'success': True,
        'settings': settings,
        'is_real_razorpay': payment_config.is_real_razorpay(settings),
        'is_real_stripe': payment_config.is_real_stripe(settings)
    })

@app.route('/api/payment/create-order', methods=['POST'])
@login_required
def api_create_payment_order():
    data = request.get_json() or {}
    gateway = data.get('payment_gateway', 'razorpay') # 'razorpay', 'stripe', or 'upi'
    amount = float(data.get('amount', 0))
    order_id = data.get('order_id')

    if amount <= 0:
        return jsonify({'success': False, 'message': 'Invalid payment amount.'}), 400

    cfg = payment_config.load_payment_settings()
    amount_in_paise = int(round(amount * 100))

    if gateway == 'upi':
        upi_id = cfg.get('merchant_upi_id', '41837498566@sbi')
        merchant_name = cfg.get('merchant_name', 'Fresh Dairy Products')
        note = f"Order #{order_id}" if order_id else "Fresh Dairy Order"
        upi_uri = f"upi://pay?pa={upi_id}&pn={urllib.parse.quote(merchant_name)}&am={amount:.2f}&cu=INR&tn={urllib.parse.quote(note)}"
        qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=250x250&data={urllib.parse.quote(upi_uri)}"
        return jsonify({
            'success': True,
            'gateway': 'upi',
            'upi_id': upi_id,
            'merchant_name': merchant_name,
            'upi_uri': upi_uri,
            'qr_url': qr_url,
            'amount': amount,
            'bank_name': cfg.get('bank_name', ''),
            'account_number': cfg.get('account_number', ''),
            'ifsc_code': cfg.get('ifsc_code', '')
        })

    elif gateway == 'razorpay':
        rzp_key_id = cfg.get('razorpay_key_id', '').strip() or 'rzp_test_dairy2025demo'
        rzp_key_secret = cfg.get('razorpay_key_secret', '').strip() or 'test_secret_key_dairy_12345'
        rzp_order_id = f"order_rzp_{os.urandom(8).hex()}"

        if razorpay and payment_config.is_real_razorpay(cfg):
            try:
                client = razorpay.Client(auth=(rzp_key_id, rzp_key_secret))
                rzp_order = client.order.create({
                    'amount': amount_in_paise,
                    'currency': 'INR',
                    'payment_capture': '1',
                    'notes': {'user_id': str(session.get('user_id')), 'order_id': str(order_id or '')}
                })
                rzp_order_id = rzp_order['id']
            except Exception as e:
                return jsonify({'success': False, 'message': f'Razorpay API error: {str(e)}'}), 400

        return jsonify({
            'success': True,
            'gateway': 'razorpay',
            'order_id': rzp_order_id,
            'amount': amount_in_paise,
            'currency': 'INR',
            'key_id': rzp_key_id,
            'is_live': payment_config.is_real_razorpay(cfg)
        })

    elif gateway == 'stripe':
        stripe_pub_key = cfg.get('stripe_publishable_key', '').strip() or 'pk_test_51DairyDemoPublishableKey123'
        stripe_sec_key = cfg.get('stripe_secret_key', '').strip() or 'sk_test_51DairyDemoSecretKey123'

        if stripe and payment_config.is_real_stripe(cfg):
            try:
                stripe.api_key = stripe_sec_key
                host_base = request.host_url.rstrip('/')
                checkout_session = stripe.checkout.Session.create(
                    payment_method_types=['card'],
                    line_items=[{
                        'price_data': {
                            'currency': 'inr',
                            'product_data': {
                                'name': f'Fresh Dairy Products Order #{order_id or ""}',
                                'description': 'Fresh dairy items purchase',
                            },
                            'unit_amount': amount_in_paise,
                        },
                        'quantity': 1,
                    }],
                    mode='payment',
                    success_url=f"{host_base}/payment/stripe/success?session_id={{CHECKOUT_SESSION_ID}}&order_id={order_id or ''}",
                    cancel_url=f"{host_base}/cart",
                    client_reference_id=str(order_id or '')
                )
                return jsonify({
                    'success': True,
                    'gateway': 'stripe',
                    'checkout_url': checkout_session.url,
                    'session_id': checkout_session.id,
                    'publishable_key': stripe_pub_key,
                    'is_live': True
                })
            except Exception as e:
                return jsonify({'success': False, 'message': f'Stripe API error: {str(e)}'}), 400

        # Fallback test response if secret key is mock
        return jsonify({
            'success': True,
            'gateway': 'stripe',
            'session_id': f"cs_test_{os.urandom(8).hex()}",
            'client_secret': f"pi_test_{os.urandom(8).hex()}_secret_{os.urandom(6).hex()}",
            'amount': amount_in_paise,
            'currency': 'INR',
            'publishable_key': stripe_pub_key,
            'is_live': False
        })

    return jsonify({'success': False, 'message': 'Unsupported payment gateway.'}), 400

@app.route('/payment/stripe/success')
@login_required
def stripe_payment_success():
    session_id = request.args.get('session_id')
    order_id = request.args.get('order_id')
    cfg = payment_config.load_payment_settings()

    if stripe and payment_config.is_real_stripe(cfg) and session_id:
        try:
            stripe.api_key = cfg.get('stripe_secret_key')
            checkout_session = stripe.checkout.Session.retrieve(session_id)
            if checkout_session.payment_status == 'paid' and order_id:
                conn = database.get_db()
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE orders
                    SET payment_status = 'Paid',
                        status = 'Processing',
                        payment_gateway = 'stripe',
                        transaction_id = ?
                    WHERE id = ?
                ''', (checkout_session.payment_intent or session_id, order_id))
                conn.commit()
                conn.close()
        except Exception:
            pass

    return redirect(url_for('orders_page'))

@app.route('/api/payment/webhook/razorpay', methods=['POST'])
def api_razorpay_webhook():
    """Real-time Webhook capture from Razorpay server."""
    payload = request.get_data()
    sig = request.headers.get('X-Razorpay-Signature', '')
    cfg = payment_config.load_payment_settings()
    webhook_secret = cfg.get('razorpay_webhook_secret', '').strip()

    if webhook_secret and razorpay and sig:
        try:
            client = razorpay.Client(auth=(cfg.get('razorpay_key_id'), cfg.get('razorpay_key_secret')))
            client.utility.verify_webhook_signature(payload.decode('utf-8'), sig, webhook_secret)
        except Exception as e:
            return jsonify({'status': 'invalid signature', 'error': str(e)}), 400

    data = request.get_json() or {}
    event = data.get('event', '')

    if event in ['payment.captured', 'order.paid']:
        payload_entity = data.get('payload', {}).get('payment', {}).get('entity', {}) or data.get('payload', {}).get('order', {}).get('entity', {})
        notes = payload_entity.get('notes', {})
        order_id = notes.get('order_id')
        payment_id = payload_entity.get('id')

        if order_id:
            conn = database.get_db()
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE orders
                SET payment_status = 'Paid',
                    status = 'Processing',
                    payment_gateway = 'razorpay',
                    transaction_id = ?
                WHERE id = ?
            ''', (payment_id or f"pay_wh_{os.urandom(6).hex()}", order_id))
            conn.commit()
            conn.close()

    return jsonify({'status': 'ok'})

@app.route('/api/payment/verify', methods=['POST'])
@login_required
def api_verify_payment():
    data = request.get_json() or {}
    order_id = data.get('order_id')
    gateway = data.get('payment_gateway', 'razorpay')
    payment_method = data.get('payment_method') or gateway.upper()
    transaction_id = data.get('transaction_id', '')
    razorpay_order_id = data.get('razorpay_order_id', '')
    signature = data.get('signature', '')

    if not order_id:
        return jsonify({'success': False, 'message': 'Missing order ID.'}), 400

    conn = database.get_db()
    cursor = conn.cursor()

    order = cursor.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
    if not order:
        conn.close()
        return jsonify({'success': False, 'message': 'Order not found.'}), 404

    cfg = payment_config.load_payment_settings()
    rzp_key_id = cfg.get('razorpay_key_id', '').strip()
    rzp_key_secret = cfg.get('razorpay_key_secret', '').strip()

    # Verify signature if Razorpay real credentials are active
    verified = True
    if gateway == 'razorpay' and payment_config.is_real_razorpay(cfg):
        try:
            if razorpay:
                client = razorpay.Client(auth=(rzp_key_id, rzp_key_secret))
                client.utility.verify_payment_signature({
                    'razorpay_order_id': razorpay_order_id,
                    'razorpay_payment_id': transaction_id,
                    'razorpay_signature': signature
                })
            else:
                msg = f"{razorpay_order_id}|{transaction_id}".encode('utf-8')
                generated_sig = hmac.new(rzp_key_secret.encode('utf-8'), msg, hashlib.sha256).hexdigest()
                if generated_sig != signature:
                    verified = False
        except Exception as e:
            verified = False

    if not verified:
        conn.close()
        return jsonify({'success': False, 'message': 'Payment signature verification failed.'}), 400

    txn_ref = transaction_id or f"pay_{os.urandom(8).hex()}"
    sig_ref = signature or f"sig_{os.urandom(8).hex()}"

    # Update Order in Database
    cursor.execute('''
        UPDATE orders
        SET payment_status = 'Paid',
            status = 'Processing',
            payment_gateway = ?,
            payment_method = ?,
            transaction_id = ?,
            signature = ?
        WHERE id = ?
    ''', (gateway, payment_method, txn_ref, sig_ref, order_id))

    conn.commit()
    conn.close()

    # Trigger Email Notification Receipt
    send_order_email_notification(
        session.get('user_email', 'customer@dairy.com'),
        order_id,
        f'Payment Received ({payment_method})',
        f'Transaction ID: {txn_ref} | Amount: ₹{order["total_amount"]:.2f}'
    )

    return jsonify({
        'success': True,
        'message': 'Payment verified and order marked as Paid!',
        'order_id': order_id,
        'transaction_id': txn_ref
    })

@app.route('/orders/<int:order_id>/invoice')
@login_required
def get_order_invoice(order_id):
    """Generates a Zomato / Swiggy style printable Tax Invoice receipt."""
    conn = database.get_db()
    order = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
    
    if not order:
        conn.close()
        return "Order not found", 404

    # Security check: User must own the order or be admin
    if order['user_id'] != session.get('user_id') and session.get('role') != 'admin':
        conn.close()
        return "Unauthorized", 403

    u_conn = database.get_users_db()
    customer = u_conn.execute("SELECT * FROM users WHERE id = ?", (order['user_id'],)).fetchone()
    u_conn.close()

    items = conn.execute('''
        SELECT oi.*, p.unit, p.image_symbol
        FROM order_items oi
        LEFT JOIN products p ON oi.product_id = p.id
        WHERE oi.order_id = ?
    ''', (order_id,)).fetchall()
    conn.close()

    cfg = payment_config.load_payment_settings()
    merchant_name = cfg.get('merchant_name', 'Fresh Dairy Products')

    # Invoice HTML template
    invoice_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Tax Invoice - Order #{order['id']} - {merchant_name}</title>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #f8fafc; color: #1e293b; padding: 2rem; margin: 0; }}
        .invoice-card {{ max-width: 750px; margin: 0 auto; background: white; border-radius: 16px; border: 1px solid #e2e8f0; box-shadow: 0 10px 25px -5px rgba(0,0,0,0.05); padding: 2.5rem; position: relative; }}
        .header {{ display: flex; justify-content: space-between; align-items: flex-start; border-bottom: 2px solid #38bdf8; padding-bottom: 1.5rem; margin-bottom: 1.5rem; }}
        .logo-title {{ font-size: 1.6rem; font-weight: 800; color: #0284c7; margin: 0; }}
        .badge-paid {{ background: #dcfce7; color: #15803d; padding: 0.4rem 1rem; border-radius: 99px; font-weight: 800; font-size: 0.85rem; text-transform: uppercase; letter-spacing: 0.5px; display: inline-block; }}
        .badge-pending {{ background: #fef9c3; color: #a16207; padding: 0.4rem 1rem; border-radius: 99px; font-weight: 800; font-size: 0.85rem; text-transform: uppercase; letter-spacing: 0.5px; display: inline-block; }}
        .grid-2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 2rem; margin-bottom: 1.5rem; font-size: 0.9rem; line-height: 1.6; }}
        .table {{ width: 100%; border-collapse: collapse; margin-bottom: 1.5rem; font-size: 0.9rem; }}
        .table th {{ background: #f1f5f9; text-align: left; padding: 0.75rem; color: #475569; font-size: 0.8rem; text-transform: uppercase; font-weight: 700; }}
        .table td {{ padding: 0.85rem 0.75rem; border-bottom: 1px solid #f1f5f9; }}
        .total-box {{ background: #f8fafc; border-radius: 12px; padding: 1.25rem; width: 280px; margin-left: auto; font-size: 0.95rem; }}
        .total-row {{ display: flex; justify-content: space-between; margin-bottom: 0.5rem; }}
        .total-row.final {{ border-top: 2px solid #e2e8f0; padding-top: 0.5rem; font-size: 1.25rem; font-weight: 800; color: #0284c7; margin-bottom: 0; }}
        .footer-note {{ text-align: center; margin-top: 2.5rem; padding-top: 1.5rem; border-top: 1px solid #f1f5f9; color: #94a3b8; font-size: 0.8rem; }}
        .print-btn {{ position: absolute; top: 1.5rem; right: 1.5rem; background: #0284c7; color: white; border: none; padding: 0.5rem 1rem; border-radius: 8px; font-weight: 700; cursor: pointer; }}
        @media print {{ .print-btn {{ display: none; }} body {{ background: white; padding: 0; }} .invoice-card {{ border: none; box-shadow: none; padding: 0; }} }}
    </style>
</head>
<body>
    <div class="invoice-card">
        <button class="print-btn" onclick="window.print()">🖨️ Print Invoice</button>
        <div class="header">
            <div>
                <h1 class="logo-title">🥛 {merchant_name}</h1>
                <div style="font-size: 0.85rem; color: #64748b; margin-top: 0.25rem;">Official Tax Invoice & Payment Receipt</div>
            </div>
            <div style="text-align: right;">
                <div class="{'badge-paid' if order['payment_status'] == 'Paid' else 'badge-pending'}">{order['payment_status']}</div>
                <div style="font-size: 0.85rem; color: #64748b; margin-top: 0.5rem;">Invoice #: <strong>INV-{order['id']:06d}</strong></div>
                <div style="font-size: 0.85rem; color: #64748b;">Date: {order['created_at']}</div>
            </div>
        </div>

        <div class="grid-2">
            <div>
                <strong style="color: #0284c7; text-transform: uppercase; font-size: 0.8rem;">Billed To Customer</strong><br>
                <strong>{customer['name'] if customer else 'Valued Customer'}</strong><br>
                {order['delivery_address']}<br>
                Email: {customer['email'] if customer else 'customer@dairy.com'}<br>
                Phone: {customer['phone'] if customer and customer['phone'] else 'N/A'}
            </div>
            <div>
                <strong style="color: #0284c7; text-transform: uppercase; font-size: 0.8rem;">Merchant & Payment Details</strong><br>
                <strong>{merchant_name}</strong><br>
                Payment Gateway: <strong>{order['payment_gateway'].upper()}</strong><br>
                Payment Method: <strong>{order['payment_method']}</strong><br>
                Transaction Ref / UTR: <span style="font-family: monospace;">{order['transaction_id'] or 'N/A'}</span>
            </div>
        </div>

        <table class="table">
            <thead>
                <tr>
                    <th>Item Description</th>
                    <th>Unit Price</th>
                    <th style="text-align: center;">Qty</th>
                    <th style="text-align: right;">Amount</th>
                </tr>
            </thead>
            <tbody>
                {''.join([f'''
                <tr>
                    <td>{item['image_symbol'] or '🥛'} <strong>{item['product_name']}</strong> ({item['unit'] or ''})</td>
                    <td>₹{item['price_per_unit']:.2f}</td>
                    <td style="text-align: center;">{item['quantity']}</td>
                    <td style="text-align: right; font-weight: 700;">₹{item['subtotal']:.2f}</td>
                </tr>
                ''' for item in items])}
            </tbody>
        </table>

        <div class="total-box">
            <div class="total-row">
                <span>Subtotal:</span>
                <span>₹{(order['total_amount'] + (order['discount_amount'] or 0)):.2f}</span>
            </div>
            {f'''
            <div class="total-row" style="color: #16a34a; font-weight: 700;">
                <span>Discount ({order['coupon_code']}):</span>
                <span>-₹{order['discount_amount']:.2f}</span>
            </div>
            ''' if order['discount_amount'] and order['discount_amount'] > 0 else ''}
            <div class="total-row">
                <span>GST (0% Exempted Fresh Dairy):</span>
                <span>₹0.00</span>
            </div>
            <div class="total-row final">
                <span>Total Paid:</span>
                <span>₹{order['total_amount']:.2f}</span>
            </div>
        </div>

        <div class="footer-note">
            Thank you for ordering with {merchant_name}! This is a computer-generated tax invoice receipt.<br>
            For assistance, email support@dairy.com or contact merchant UPI {cfg.get('merchant_upi_id')}.
        </div>
    </div>
</body>
</html>"""
    return invoice_html

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)


