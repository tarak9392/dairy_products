import sqlite3
import hashlib
import os
import shutil

BASE_DIR = os.path.dirname(__file__)
DB_PATH = os.path.join(BASE_DIR, 'dairy.db')
USERS_DB_PATH = os.path.join(BASE_DIR, 'registered_users.db')

# Vercel Serverless Read-Only Filesystem Fallback (/tmp)
if os.environ.get('VERCEL') or not os.access(BASE_DIR, os.W_OK):
    tmp_dir = '/tmp'
    if os.path.exists(tmp_dir):
        tmp_db = os.path.join(tmp_dir, 'dairy.db')
        tmp_users_db = os.path.join(tmp_dir, 'registered_users.db')
        try:
            if not os.path.exists(tmp_db) and os.path.exists(DB_PATH):
                shutil.copy2(DB_PATH, tmp_db)
            if not os.path.exists(tmp_users_db) and os.path.exists(USERS_DB_PATH):
                shutil.copy2(USERS_DB_PATH, tmp_users_db)
            DB_PATH = tmp_db
            USERS_DB_PATH = tmp_users_db
        except Exception:
            pass

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def get_users_db():
    conn = sqlite3.connect(USERS_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def hash_password(password):
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def init_db():
    # Initialize Separate Users Database (registered_users.db)
    u_conn = get_users_db()
    u_cursor = u_conn.cursor()
    u_cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT DEFAULT 'customer',
            phone TEXT,
            address TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    u_conn.commit()

    # Seed Demo Test Accounts for Razorpay Review & Testing
    u_cursor.execute("SELECT id FROM users WHERE email = 'customer@dairy.com'")
    if not u_cursor.fetchone():
        u_cursor.execute('''
            INSERT INTO users (name, email, password_hash, role, phone, address)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', ('Dairy Test Customer', 'customer@dairy.com', hash_password('Password123'), 'customer', '9876543210', 'Flat 402, Royal Palms, RGMCET Road, Nandyal'))

    u_cursor.execute("SELECT id FROM users WHERE email = 'admin@dairy.com'")
    if not u_cursor.fetchone():
        u_cursor.execute('''
            INSERT INTO users (name, email, password_hash, role, phone, address)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', ('Dairy Admin Vendor', 'admin@dairy.com', hash_password('Admin123'), 'admin', '9999999999', 'Main Dairy Plant, Nandyal'))
    u_conn.commit()

    # Initialize Main Dairy Store Database (dairy.db)
    conn = get_db()
    cursor = conn.cursor()

    # Products Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            price REAL NOT NULL,
            unit TEXT NOT NULL,
            stock INTEGER NOT NULL DEFAULT 0,
            description TEXT,
            image_symbol TEXT,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Orders Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            order_type TEXT DEFAULT 'one-time',
            total_amount REAL NOT NULL,
            status TEXT DEFAULT 'Pending',
            payment_method TEXT DEFAULT 'Cash on Delivery',
            payment_status TEXT DEFAULT 'Pending',
            payment_gateway TEXT DEFAULT 'cod',
            transaction_id TEXT,
            signature TEXT,
            delivery_address TEXT NOT NULL,
            delivery_slot TEXT DEFAULT 'Morning (6 AM - 8 AM)',
            sub_start_date TEXT,
            sub_frequency TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Wishlist Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS wishlist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (product_id) REFERENCES products(id),
            UNIQUE(user_id, product_id)
        )
    ''')

    # Coupons Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS coupons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            discount_type TEXT NOT NULL,
            discount_value REAL NOT NULL,
            min_order_amount REAL DEFAULT 0,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Add columns if migrating existing db
    try:
        cursor.execute("ALTER TABLE products ADD COLUMN image_url TEXT")
    except Exception:
        pass

    try:
        cursor.execute("ALTER TABLE orders ADD COLUMN payment_gateway TEXT DEFAULT 'cod'")
    except Exception:
        pass

    try:
        cursor.execute("ALTER TABLE orders ADD COLUMN transaction_id TEXT")
    except Exception:
        pass

    try:
        cursor.execute("ALTER TABLE orders ADD COLUMN signature TEXT")
    except Exception:
        pass

    try:
        cursor.execute("ALTER TABLE orders ADD COLUMN discount_amount REAL DEFAULT 0.0")
    except Exception:
        pass

    try:
        cursor.execute("ALTER TABLE orders ADD COLUMN coupon_code TEXT")
    except Exception:
        pass

    # Order Items Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            product_name TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            price_per_unit REAL NOT NULL,
            subtotal REAL NOT NULL,
            FOREIGN KEY (order_id) REFERENCES orders(id),
            FOREIGN KEY (product_id) REFERENCES products(id)
        )
    ''')

    conn.commit()

    # Migrate any legacy users from dairy.db to registered_users.db
    try:
        legacy_users = cursor.execute("SELECT * FROM users").fetchall()
        for lu in legacy_users:
            u_cursor.execute('''
                INSERT OR IGNORE INTO users (id, name, email, password_hash, role, phone, address, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (lu['id'], lu['name'], lu['email'], lu['password_hash'], lu['role'], lu['phone'], lu['address'], lu['created_at']))
        u_conn.commit()
    except Exception:
        pass

    # Seed Default Users & Products if empty
    seed_demo_data(cursor, conn, u_cursor, u_conn)

    conn.close()
    u_conn.close()

def seed_demo_data(cursor, conn, u_cursor, u_conn):
    # Seed Admin / Owner User in registered_users.db
    u_cursor.execute("SELECT COUNT(*) FROM users WHERE email = 'owner@dairy.com'")
    if u_cursor.fetchone()[0] == 0:
        u_cursor.execute('''
            INSERT INTO users (name, email, password_hash, role, phone, address)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            'Store Owner',
            'owner@dairy.com',
            hash_password('admin123'),
            'admin',
            '+91 98765 43210',
            'Main Dairy HQ, Tech Park Road, Nandyal'
        ))

    u_cursor.execute("SELECT COUNT(*) FROM users WHERE email = 'admin@dairy.com'")
    if u_cursor.fetchone()[0] == 0:
        u_cursor.execute('''
            INSERT INTO users (name, email, password_hash, role, phone, address)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            'Dairy Admin',
            'admin@dairy.com',
            hash_password('admin123'),
            'admin',
            '+91 98765 43210',
            'Main Dairy HQ, Tech Park Road, Nandyal'
        ))

    # Seed Sample Customer in registered_users.db
    u_cursor.execute("SELECT COUNT(*) FROM users WHERE email = 'customer@dairy.com'")
    if u_cursor.fetchone()[0] == 0:
        u_cursor.execute('''
            INSERT INTO users (name, email, password_hash, role, phone, address)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            'Tejaswini M.',
            'customer@dairy.com',
            hash_password('user123'),
            'customer',
            '+91 91234 56789',
            'Flat 402, Royal Palms, RGMCET Road, Nandyal'
        ))
    u_conn.commit()

    # Seed Products
    cursor.execute("SELECT COUNT(*) FROM products")
    if cursor.fetchone()[0] == 0:
        initial_products = [
            ('Farm Fresh Whole Milk', 'Milk', 32.0, '500 ml', 120, '100% pure pasteurized whole cow milk delivered fresh every morning.', '🥛'),
            ('Low Fat Toned Milk', 'Milk', 28.0, '500 ml', 85, 'Healthy, light and delicious toned milk rich in calcium and protein.', '🥛'),
            ('Organic Farm Curd (Dahi)', 'Curd & Yogurt', 45.0, '500 g', 60, 'Traditional thick curd made from natural whole cow milk cultures.', '🥣'),
            ('Fresh Malai Paneer', 'Paneer & Butter', 110.0, '200 g', 40, 'Soft, rich and fresh cottage cheese blocks perfect for cooking.', '🧀'),
            ('Pure Desi Cow Ghee', 'Ghee & Sweets', 350.0, '500 ml', 30, 'Aromatic golden ghee crafted using traditional bilona churn method.', '🧈'),
            ('Artisanal Salted Butter', 'Paneer & Butter', 65.0, '100 g', 50, 'Creamy churned butter with a touch of salt for your morning toast.', '🧈'),
            ('Spiced Masala Butter Milk', 'Beverages', 20.0, '250 ml', 100, 'Refreshing chilled buttermilk spiced with ginger, curry leaves, and cumin.', '🥤'),
            ('Chocolate Flavored Milk', 'Beverages', 35.0, '200 ml', 75, 'Rich cocoa blended with thick cold milk, a favorite delight for all ages.', '🧃'),
            ('Rich Mango Lassi', 'Beverages', 40.0, '250 ml', 45, 'Creamy yogurt drink blended with Alphonso mango pulp.', '🥭'),
            ('Royal Kesar Peda', 'Ghee & Sweets', 180.0, '250 g', 25, 'Traditional milk sweet infused with saffron and cardamom.', '🍬')
        ]

        cursor.executemany('''
            INSERT INTO products (name, category, price, unit, stock, description, image_symbol)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', initial_products)

        conn.commit()

    # Seed Coupons
    cursor.execute("SELECT COUNT(*) FROM coupons")
    if cursor.fetchone()[0] == 0:
        cursor.executemany('''
            INSERT INTO coupons (code, discount_type, discount_value, min_order_amount)
            VALUES (?, ?, ?, ?)
        ''', [
            ('FRESH10', 'percent', 10.0, 0.0),
            ('DAIRY20', 'fixed', 20.0, 100.0),
            ('WELCOME50', 'fixed', 50.0, 200.0)
        ])
        conn.commit()

    # Update image_url for products
    image_mappings = [
        ('/static/images/whole_milk.jpg', 'Farm Fresh Whole Milk'),
        ('/static/images/toned_milk.jpg', 'Low Fat Toned Milk'),
        ('/static/images/farm_curd.jpg', 'Organic Farm Curd (Dahi)'),
        ('/static/images/malai_paneer.jpg', 'Fresh Malai Paneer'),
        ('/static/images/cow_ghee.jpg', 'Pure Desi Cow Ghee'),
        ('/static/images/salted_butter.jpg', 'Artisanal Salted Butter'),
        ('/static/images/masala_buttermilk.jpg', 'Spiced Masala Butter Milk'),
        ('/static/images/chocolate_milk.jpg', 'Chocolate Flavored Milk'),
        ('/static/images/mango_lassi.jpg', 'Rich Mango Lassi'),
        ('/static/images/kesar_peda.jpg', 'Royal Kesar Peda'),
        ('/static/images/buffalo_milk.jpg', 'Organic Buffalo Milk')
    ]
    for img_path, prod_name in image_mappings:
        cursor.execute("UPDATE products SET image_url = ? WHERE name = ?", (img_path, prod_name))
    conn.commit()

    # Seed initial sample orders for demonstration
    cursor.execute("SELECT id FROM users WHERE email = 'customer@dairy.com'")
    user = cursor.fetchone()
    if user:
        user_id = user['id']
        cursor.execute("SELECT COUNT(*) FROM orders WHERE user_id = ?", (user_id,))
        if cursor.fetchone()[0] == 0:
            # Sample past order 1
            cursor.execute('''
                INSERT INTO orders (user_id, order_type, total_amount, status, payment_method, payment_status, delivery_address, delivery_slot, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now', '-2 days'))
            ''', (user_id, 'one-time', 187.0, 'Delivered', 'UPI / Online Payment', 'Paid', 'Flat 402, Royal Palms, RGMCET Road, Nandyal', 'Morning (6 AM - 8 AM)'))
            order1_id = cursor.lastrowid
            cursor.execute('''
                INSERT INTO order_items (order_id, product_id, product_name, quantity, price_per_unit, subtotal)
                VALUES (?, 1, 'Farm Fresh Whole Milk', 2, 32.0, 64.0),
                       (?, 3, 'Organic Farm Curd (Dahi)', 1, 45.0, 45.0),
                       (?, 4, 'Fresh Malai Paneer', 1, 110.0, 110.0)
            ''', (order1_id, order1_id, order1_id))

            # Sample daily subscription order
            cursor.execute('''
                INSERT INTO orders (user_id, order_type, total_amount, status, payment_method, payment_status, delivery_address, delivery_slot, sub_start_date, sub_frequency, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, date('now'), 'Daily', datetime('now', '-1 day'))
            ''', (user_id, 'subscription', 64.0, 'Out for Delivery', 'Monthly Billing', 'Pending', 'Flat 402, Royal Palms, RGMCET Road, Nandyal', 'Morning (6 AM - 8 AM)'))
            order2_id = cursor.lastrowid
            cursor.execute('''
                INSERT INTO order_items (order_id, product_id, product_name, quantity, price_per_unit, subtotal)
                VALUES (?, 1, 'Farm Fresh Whole Milk', 2, 32.0, 64.0)
            ''', (order2_id,))

    conn.commit()

if __name__ == '__main__':
    init_db()
    print("Database initialized successfully.")
