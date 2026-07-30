from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session, send_from_directory
from flask_mysqldb import MySQL
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
import os
import json
from datetime import datetime
import base64
import pymysql

load_dotenv()

app = Flask(__name__, static_folder='static', static_url_path='/static')
CORS(app, resources={r"/api/*": {"origins": "*"}, r"/static/*": {"origins": "*"}})
app.secret_key = os.urandom(24)

# MySQL Configuration
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'Ak@120799'
app.config['MYSQL_DB'] = 'grillista_admin'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

# First, create the database if it doesn't exist
try:
    conn = pymysql.connect(
        host=app.config['MYSQL_HOST'],
        user=app.config['MYSQL_USER'],
        password=app.config['MYSQL_PASSWORD']
    )
    with conn.cursor() as cursor:
        cursor.execute("CREATE DATABASE IF NOT EXISTS grillista_admin CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
    conn.close()
    print("Database 'grillista_admin' created or already exists.")
except Exception as e:
    print(f"Could not create database: {e}")

mysql = MySQL(app)

# Get the parent directory (project root) for serving static frontend files
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Upload configuration
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ============ DATABASE INITIALIZATION ============
def init_db():
    try:
        cursor = mysql.connection.cursor()
        
        # Create admin user table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS admin_users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create gallery table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS gallery (
                id INT AUTO_INCREMENT PRIMARY KEY,
                title VARCHAR(200) NOT NULL,
                image_path VARCHAR(500) NOT NULL,
                sort_order INT DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create inquiries table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS inquiries (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                mobile VARCHAR(15) NOT NULL,
                email VARCHAR(100) NOT NULL,
                city VARCHAR(100) NOT NULL,
                budget VARCHAR(50) NOT NULL,
                message TEXT,
                status ENUM('new', 'contacted', 'closed') DEFAULT 'new',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create testimonials table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS testimonials (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                role VARCHAR(100) DEFAULT '',
                content TEXT NOT NULL,
                rating INT DEFAULT 5,
                avatar_path VARCHAR(500) DEFAULT '',
                is_active TINYINT(1) DEFAULT 1,
                sort_order INT DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create site_content table for dynamic content
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS site_content (
                id INT AUTO_INCREMENT PRIMARY KEY,
                section_key VARCHAR(100) UNIQUE NOT NULL,
                content TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            )
        ''')
        
        # Create navbar_links table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS navbar_links (
                id INT AUTO_INCREMENT PRIMARY KEY,
                label VARCHAR(100) NOT NULL,
                href VARCHAR(200) NOT NULL,
                sort_order INT DEFAULT 0,
                is_active TINYINT(1) DEFAULT 1
            )
        ''')
        
        # Insert default admin if not exists
        cursor.execute("SELECT * FROM admin_users WHERE username = 'admin'")
        if not cursor.fetchone():
            hashed = generate_password_hash('admin123')
            cursor.execute("INSERT INTO admin_users (username, password_hash) VALUES (%s, %s)", ('admin', hashed))
        
        # Insert default navbar links if not exists
        cursor.execute("SELECT COUNT(*) as cnt FROM navbar_links")
        if cursor.fetchone()['cnt'] == 0:
            default_links = [
                ('Home', '#home', 1),
                ('About Us', '#about', 2),
                ('Why Choose Us', '#why', 3),
                ('Franchise Benefits', '#benefits', 4),
                ('Gallery', '#gallery', 5),
                ('Contact Us', '#contact', 6),
            ]
            cursor.executemany(
                "INSERT INTO navbar_links (label, href, sort_order) VALUES (%s, %s, %s)",
                default_links
            )
        
        # Insert default site content
        default_content = {
            'hero_title': 'Grillista',
            'hero_subtitle': 'Food franchise restaurant',
            'hero_description': 'Launch a modern quick-service food outlet with burgers, wraps, fries, bowls, shakes, and a brand system made for repeat customers.',
            'about_title': 'A fresh 100% veg food brand built for growing franchise partners.',
            'about_text': 'Grillista is a quick-service restaurant concept focused on high-demand vegetarian comfort food, simple operations, consistent recipes, and local-store marketing.',
            'about_text2': 'Our model helps entrepreneurs open attractive food outlets in malls, high streets, colleges, offices, and delivery-friendly neighborhoods.',
            'stats_menu': '28+',
            'stats_menu_label': '100% Veg Menu Items',
            'stats_formats': '4',
            'stats_formats_label': 'store formats',
            'stats_service': '15 min',
            'stats_service_label': 'average service time',
            'stats_support': '360',
            'stats_support_label': 'launch support',
            'contact_phone': '+91 7081346666',
            'contact_email': 'grillistakanpur@gmail.com',
            'contact_website': 'shreegroup.com',
            'contact_response': 'Within 24 Hours',
            'footer_text': '100% vegetarian food franchise restaurant concept for burgers, wraps, fries, bowls, shakes, and quick-service meals.',
        }
        
        for key, value in default_content.items():
            cursor.execute(
                "INSERT IGNORE INTO site_content (section_key, content) VALUES (%s, %s)",
                (key, value)
            )
        
        mysql.connection.commit()
        cursor.close()
        print("Database initialized successfully!")
    except Exception as e:
        print(f"Database init error: {e}")

# ============ ROUTES ============

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM admin_users WHERE username = %s", [username])
        user = cursor.fetchone()
        cursor.close()
        
        if user and check_password_hash(user['password_hash'], password):
            session['admin_logged_in'] = True
            session['admin_username'] = username
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password!', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully!', 'success')
    return redirect(url_for('login'))

def login_required_decorator(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_logged_in'):
            flash('Please login first!', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# ============ DASHBOARD ============
@app.route('/dashboard')
@login_required_decorator
def dashboard():
    cursor = mysql.connection.cursor()
    
    cursor.execute("SELECT COUNT(*) as cnt FROM inquiries")
    total_inquiries = cursor.fetchone()['cnt']
    
    cursor.execute("SELECT COUNT(*) as cnt FROM inquiries WHERE status = 'new'")
    new_inquiries = cursor.fetchone()['cnt']
    
    cursor.execute("SELECT COUNT(*) as cnt FROM gallery")
    total_gallery = cursor.fetchone()['cnt']
    
    cursor.execute("SELECT COUNT(*) as cnt FROM testimonials WHERE is_active = 1")
    active_testimonials = cursor.fetchone()['cnt']
    
    cursor.execute("SELECT * FROM inquiries ORDER BY created_at DESC LIMIT 5")
    recent_inquiries = cursor.fetchall()
    
    cursor.close()
    
    return render_template('dashboard.html',
                         total_inquiries=total_inquiries,
                         new_inquiries=new_inquiries,
                         total_gallery=total_gallery,
                         active_testimonials=active_testimonials,
                         recent_inquiries=recent_inquiries)

# ============ GALLERY MANAGEMENT ============
@app.route('/gallery')
@login_required_decorator
def gallery():
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM gallery ORDER BY sort_order ASC, created_at DESC")
    images = cursor.fetchall()
    cursor.close()
    return render_template('gallery.html', images=images)

@app.route('/gallery/upload', methods=['POST'])
@login_required_decorator
def gallery_upload():
    if 'image' not in request.files:
        flash('No file selected!', 'danger')
        return redirect(url_for('gallery'))
    
    file = request.files['image']
    title = request.form.get('title', '')
    
    if file.filename == '':
        flash('No file selected!', 'danger')
        return redirect(url_for('gallery'))
    
    if file and allowed_file(file.filename):
        filename = secure_filename(f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{file.filename}")
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Get max sort order
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT COALESCE(MAX(sort_order), 0) + 1 as next_order FROM gallery")
        next_order = cursor.fetchone()['next_order']
        
        cursor.execute(
            "INSERT INTO gallery (title, image_path, sort_order) VALUES (%s, %s, %s)",
            (title, f'uploads/{filename}', next_order)
        )
        mysql.connection.commit()
        cursor.close()
        
        flash('Image uploaded successfully!', 'success')
    else:
        flash('Invalid file type! Allowed: png, jpg, jpeg, gif, webp', 'danger')
    
    return redirect(url_for('gallery'))

@app.route('/gallery/delete/<int:id>')
@login_required_decorator
def gallery_delete(id):
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM gallery WHERE id = %s", [id])
    image = cursor.fetchone()
    
    if image:
        # Delete file
        filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', image['image_path'])
        if os.path.exists(filepath):
            os.remove(filepath)
        
        cursor.execute("DELETE FROM gallery WHERE id = %s", [id])
        mysql.connection.commit()
        flash('Image deleted successfully!', 'success')
    
    cursor.close()
    return redirect(url_for('gallery'))

@app.route('/gallery/reorder', methods=['POST'])
@login_required_decorator
def gallery_reorder():
    data = request.get_json()
    if data and 'order' in data:
        cursor = mysql.connection.cursor()
        for item in data['order']:
            cursor.execute(
                "UPDATE gallery SET sort_order = %s WHERE id = %s",
                (item['order'], item['id'])
            )
        mysql.connection.commit()
        cursor.close()
        return jsonify({'success': True})
    return jsonify({'success': False}), 400

# ============ INQUIRIES MANAGEMENT ============
@app.route('/inquiries')
@login_required_decorator
def inquiries():
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM inquiries ORDER BY created_at DESC")
    all_inquiries = cursor.fetchall()
    cursor.close()
    return render_template('inquiries.html', inquiries=all_inquiries)

@app.route('/inquiries/update-status/<int:id>', methods=['POST'])
@login_required_decorator
def update_inquiry_status(id):
    status = request.form.get('status')
    cursor = mysql.connection.cursor()
    cursor.execute("UPDATE inquiries SET status = %s WHERE id = %s", (status, id))
    mysql.connection.commit()
    cursor.close()
    flash('Inquiry status updated!', 'success')
    return redirect(url_for('inquiries'))

@app.route('/inquiries/delete/<int:id>')
@login_required_decorator
def delete_inquiry(id):
    cursor = mysql.connection.cursor()
    cursor.execute("DELETE FROM inquiries WHERE id = %s", [id])
    mysql.connection.commit()
    cursor.close()
    flash('Inquiry deleted!', 'success')
    return redirect(url_for('inquiries'))

# ============ TESTIMONIALS MANAGEMENT ============
@app.route('/testimonials')
@login_required_decorator
def testimonials():
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM testimonials ORDER BY sort_order ASC, created_at DESC")
    all_testimonials = cursor.fetchall()
    cursor.close()
    return render_template('testimonials.html', testimonials=all_testimonials)

@app.route('/testimonials/add', methods=['POST'])
@login_required_decorator
def add_testimonial():
    name = request.form.get('name')
    role = request.form.get('role', '')
    content = request.form.get('content')
    rating = request.form.get('rating', 5)
    
    avatar_path = ''
    if 'avatar' in request.files and request.files['avatar'].filename:
        file = request.files['avatar']
        if allowed_file(file.filename):
            filename = secure_filename(f"avatar_{datetime.now().strftime('%Y%m%d%H%M%S')}_{file.filename}")
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            avatar_path = f'uploads/{filename}'
    
    cursor = mysql.connection.cursor()
    cursor.execute(
        "INSERT INTO testimonials (name, role, content, rating, avatar_path) VALUES (%s, %s, %s, %s, %s)",
        (name, role, content, rating, avatar_path)
    )
    mysql.connection.commit()
    cursor.close()
    flash('Testimonial added successfully!', 'success')
    return redirect(url_for('testimonials'))

@app.route('/testimonials/edit/<int:id>', methods=['POST'])
@login_required_decorator
def edit_testimonial(id):
    name = request.form.get('name')
    role = request.form.get('role', '')
    content = request.form.get('content')
    rating = request.form.get('rating', 5)
    is_active = 1 if request.form.get('is_active') else 0
    
    cursor = mysql.connection.cursor()
    
    if 'avatar' in request.files and request.files['avatar'].filename:
        file = request.files['avatar']
        if allowed_file(file.filename):
            filename = secure_filename(f"avatar_{datetime.now().strftime('%Y%m%d%H%M%S')}_{file.filename}")
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            avatar_path = f'uploads/{filename}'
            cursor.execute(
                "UPDATE testimonials SET name=%s, role=%s, content=%s, rating=%s, avatar_path=%s, is_active=%s WHERE id=%s",
                (name, role, content, rating, avatar_path, is_active, id)
            )
    else:
        cursor.execute(
            "UPDATE testimonials SET name=%s, role=%s, content=%s, rating=%s, is_active=%s WHERE id=%s",
            (name, role, content, rating, is_active, id)
        )
    
    mysql.connection.commit()
    cursor.close()
    flash('Testimonial updated!', 'success')
    return redirect(url_for('testimonials'))

@app.route('/testimonials/delete/<int:id>')
@login_required_decorator
def delete_testimonial(id):
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT avatar_path FROM testimonials WHERE id = %s", [id])
    testimonial = cursor.fetchone()
    
    if testimonial and testimonial['avatar_path']:
        filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', testimonial['avatar_path'])
        if os.path.exists(filepath):
            os.remove(filepath)
    
    cursor.execute("DELETE FROM testimonials WHERE id = %s", [id])
    mysql.connection.commit()
    cursor.close()
    flash('Testimonial deleted!', 'success')
    return redirect(url_for('testimonials'))

# ============ SITE CONTENT MANAGEMENT ============
@app.route('/site-content')
@login_required_decorator
def site_content():
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM site_content ORDER BY section_key")
    contents = cursor.fetchall()
    cursor.close()
    return render_template('site_content.html', contents=contents)

@app.route('/site-content/update', methods=['POST'])
@login_required_decorator
def update_site_content():
    data = request.form
    cursor = mysql.connection.cursor()
    
    for key, value in data.items():
        if key.startswith('content_'):
            section_key = key.replace('content_', '')
            cursor.execute(
                "INSERT INTO site_content (section_key, content) VALUES (%s, %s) ON DUPLICATE KEY UPDATE content = %s",
                (section_key, value, value)
            )
    
    mysql.connection.commit()
    cursor.close()
    flash('Site content updated successfully!', 'success')
    return redirect(url_for('site_content'))

# ============ NAVBAR MANAGEMENT ============
@app.route('/navbar')
@login_required_decorator
def navbar():
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM navbar_links ORDER BY sort_order ASC")
    links = cursor.fetchall()
    cursor.close()
    return render_template('navbar.html', links=links)

@app.route('/navbar/add', methods=['POST'])
@login_required_decorator
def add_navbar_link():
    label = request.form.get('label')
    href = request.form.get('href')
    
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT COALESCE(MAX(sort_order), 0) + 1 as next_order FROM navbar_links")
    next_order = cursor.fetchone()['next_order']
    
    cursor.execute(
        "INSERT INTO navbar_links (label, href, sort_order) VALUES (%s, %s, %s)",
        (label, href, next_order)
    )
    mysql.connection.commit()
    cursor.close()
    flash('Navbar link added!', 'success')
    return redirect(url_for('navbar'))

@app.route('/navbar/edit/<int:id>', methods=['POST'])
@login_required_decorator
def edit_navbar_link(id):
    label = request.form.get('label')
    href = request.form.get('href')
    is_active = 1 if request.form.get('is_active') else 0
    
    cursor = mysql.connection.cursor()
    cursor.execute(
        "UPDATE navbar_links SET label=%s, href=%s, is_active=%s WHERE id=%s",
        (label, href, is_active, id)
    )
    mysql.connection.commit()
    cursor.close()
    flash('Navbar link updated!', 'success')
    return redirect(url_for('navbar'))

@app.route('/navbar/delete/<int:id>')
@login_required_decorator
def delete_navbar_link(id):
    cursor = mysql.connection.cursor()
    cursor.execute("DELETE FROM navbar_links WHERE id = %s", [id])
    mysql.connection.commit()
    cursor.close()
    flash('Navbar link deleted!', 'success')
    return redirect(url_for('navbar'))

@app.route('/navbar/reorder', methods=['POST'])
@login_required_decorator
def navbar_reorder():
    data = request.get_json()
    if data and 'order' in data:
        cursor = mysql.connection.cursor()
        for item in data['order']:
            cursor.execute(
                "UPDATE navbar_links SET sort_order = %s WHERE id = %s",
                (item['order'], item['id'])
            )
        mysql.connection.commit()
        cursor.close()
        return jsonify({'success': True})
    return jsonify({'success': False}), 400

# ============ API ENDPOINTS FOR FRONTEND ============
@app.route('/api/gallery')
def api_gallery():
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM gallery ORDER BY sort_order ASC")
    images = cursor.fetchall()
    cursor.close()
    return jsonify(images)

@app.route('/api/testimonials')
def api_testimonials():
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM testimonials WHERE is_active = 1 ORDER BY sort_order ASC")
    testimonials = cursor.fetchall()
    cursor.close()
    return jsonify(testimonials)

@app.route('/api/navbar-links')
def api_navbar_links():
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM navbar_links WHERE is_active = 1 ORDER BY sort_order ASC")
    links = cursor.fetchall()
    cursor.close()
    return jsonify(links)

@app.route('/api/site-content')
def api_site_content():
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM site_content")
    contents = cursor.fetchall()
    cursor.close()
    result = {}
    for item in contents:
        result[item['section_key']] = item['content']
    return jsonify(result)

@app.route('/api/submit-inquiry', methods=['POST'])
def api_submit_inquiry():
    try:
        data = request.get_json()
        cursor = mysql.connection.cursor()
        cursor.execute(
            "INSERT INTO inquiries (name, mobile, email, city, budget, message) VALUES (%s, %s, %s, %s, %s, %s)",
            (data['name'], data['mobile'], data['email'], data['city'], data['budget'], data.get('message', ''))
        )
        mysql.connection.commit()
        cursor.close()
        return jsonify({'success': True, 'message': 'Inquiry submitted successfully!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# ============ CHANGE PASSWORD ============
@app.route('/change-password', methods=['GET', 'POST'])
@login_required_decorator
def change_password():
    if request.method == 'POST':
        current_pw = request.form.get('current_password')
        new_pw = request.form.get('new_password')
        confirm_pw = request.form.get('confirm_password')
        
        if new_pw != confirm_pw:
            flash('New passwords do not match!', 'danger')
            return redirect(url_for('change_password'))
        
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM admin_users WHERE username = %s", [session['admin_username']])
        user = cursor.fetchone()
        
        if user and check_password_hash(user['password_hash'], current_pw):
            hashed = generate_password_hash(new_pw)
            cursor.execute("UPDATE admin_users SET password_hash = %s WHERE username = %s",
                         (hashed, session['admin_username']))
            mysql.connection.commit()
            cursor.close()
            flash('Password changed successfully!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Current password is incorrect!', 'danger')
        
        cursor.close()
    
    return render_template('change_password.html')

# ============ SERVE MAIN WEBSITE PAGES (catch-all at the end) ============
# This must be the LAST route to avoid intercepting admin routes
@app.route('/<path:filename>')
def serve_frontend(filename):
    # Block access to admin internal paths
    if filename.startswith('admin/') or filename.startswith('static/'):
        return "Not found", 404
    
    filepath = os.path.join(PROJECT_ROOT, filename)
    if os.path.exists(filepath) and os.path.isfile(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        return content
    
    return "Not found", 404

if __name__ == '__main__':
    with app.app_context():
        init_db()
    app.run(debug=True, port=5000)