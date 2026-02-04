from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import sqlite3
from werkzeug.security import check_password_hash, generate_password_hash
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your-secret-key-here-change-this-in-production'

# Setup Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Use absolute path for DB to avoid issues
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'news_bot.db')

@app.route('/force_run', methods=['POST'])
@login_required
def force_run():
    try:
        from news_bot import check_and_post_news
        # Run the news check manually
        check_and_post_news()
        flash('News check triggered successfully!', 'success')
    except Exception as e:
        flash(f'Error running news check: {e}', 'error')
    
    return redirect(url_for('dashboard'))

class User(UserMixin):
    def __init__(self, id, username):
        self.id = id
        self.username = username

@login_manager.user_loader
def load_user(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, username FROM users WHERE id = ?", (user_id,))
    user_data = c.fetchone()
    conn.close()
    if user_data:
        return User(user_data[0], user_data[1])
    return None

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = get_db_connection()
        user_data = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        conn.close()
        
        if user_data and check_password_hash(user_data['password_hash'], password):
            user = User(user_data['id'], user_data['username'])
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('Login Failed. Check username and password.')
            
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    conn = get_db_connection()
    
    # Get stats
    total_news = conn.execute('SELECT COUNT(*) FROM published_news').fetchone()[0]
    feeds_count = conn.execute('SELECT COUNT(*) FROM rss_feeds WHERE is_active = 1').fetchone()[0]
    recent_news = conn.execute('SELECT * FROM published_news ORDER BY created_at DESC LIMIT 10').fetchall()
    feeds = conn.execute('SELECT * FROM rss_feeds').fetchall()
    
    conn.close()
    return render_template('dashboard.html', total_news=total_news, feeds_count=feeds_count, recent_news=recent_news, feeds=feeds)

@app.route('/add_feed', methods=['POST'])
@login_required
def add_feed():
    name = request.form['name']
    url = request.form['url']
    
    try:
        conn = get_db_connection()
        conn.execute('INSERT INTO rss_feeds (name, url) VALUES (?, ?)', (name, url))
        conn.commit()
        conn.close()
        flash('Feed added successfully!', 'success')
    except sqlite3.IntegrityError:
        flash('Feed URL already exists!', 'error')
    except Exception as e:
        flash(f'Error: {e}', 'error')
        
    return redirect(url_for('dashboard'))

@app.route('/delete_feed/<int:id>')
@login_required
def delete_feed(id):
    conn = get_db_connection()
    conn.execute('DELETE FROM rss_feeds WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    flash('Feed deleted.', 'success')
    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    # Initialize DB if run directly this way
    if not os.path.exists(DB_PATH):
        import setup_db
        setup_db.init_db()
    else:
        # Ensure users table exists
        try:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute('''CREATE TABLE IF NOT EXISTS users
                         (id INTEGER PRIMARY KEY AUTOINCREMENT,
                          username TEXT UNIQUE NOT NULL,
                          password_hash TEXT NOT NULL)''')
            # Check if admin user exists
            admin_check = c.execute("SELECT COUNT(*) FROM users WHERE username = ?", ("admin",)).fetchone()[0]
            if admin_check == 0:
                from werkzeug.security import generate_password_hash
                password = generate_password_hash("admin123")
                c.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", ("admin", password))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Warning: {e}")
        
    print("\n" + "="*60)
    print("Web Interface is running!")
    print("Open your browser and go to: http://localhost:5000")
    print("Default login: admin / admin123")
    print("="*60 + "\n")
    app.run(debug=True, host='0.0.0.0', port=5000)
