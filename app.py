import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, flash, session, g
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import openai
from datetime import datetime
from dotenv import load_dotenv
import base64
import psycopg2
from psycopg2.extras import DictCursor
from urllib.parse import urlparse

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', os.urandom(24))
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10MB max file size

# Database configuration
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///database.db')
IS_POSTGRES = DATABASE_URL.startswith('postgres')

# Initialize X.AI configuration
openai.api_key = os.getenv("XAI_API_KEY")
openai.api_base = "https://api.x.ai/v1"

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def get_db():
    if 'db' not in g:
        try:
            if IS_POSTGRES:
                url = urlparse(DATABASE_URL)
                g.db = psycopg2.connect(
                    dbname=url.path[1:],
                    user=url.username,
                    password=url.password,
                    host=url.hostname,
                    port=url.port
                )
                g.db.cursor_factory = DictCursor
            else:
                g.db = sqlite3.connect(DATABASE_URL.replace('sqlite:///', ''))
                g.db.row_factory = sqlite3.Row
        except Exception as e:
            print(f"Database connection error: {str(e)}")
            raise
    return g.db

@app.teardown_appcontext
def close_db(error):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db():
    with app.app_context():
        db = get_db()
        if IS_POSTGRES:
            with app.open_resource('schema_postgres.sql', mode='r') as f:
                db.cursor().execute(f.read())
        else:
            with app.open_resource('schema.sql', mode='r') as f:
                db.cursor().executescript(f.read())
        db.commit()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def format_chat_timestamp(timestamp_str):
    try:
        if 'T' in timestamp_str:
            dt = datetime.fromisoformat(timestamp_str)
            return dt.strftime('%H:%M')
        return timestamp_str.split()[1][:5]
    except:
        return timestamp_str

def encode_image_file(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def process_image_with_grok(image_path, question):
    base64_image = encode_image_file(image_path)
    
    messages = [
        {
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{base64_image}",
                        "detail": "high",
                    },
                },
                {
                    "type": "text",
                    "text": question,
                },
            ],
        },
    ]
    
    completion = openai.ChatCompletion.create(
        model="grok-2-vision-1212",
        messages=messages,
        temperature=0.01,
    )
    
    return completion.choices[0].message.content

# Routes
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('auth/login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        try:
            email = request.form.get('email')
            password = request.form.get('password')
            
            if not email or not password:
                flash('Email and password are required')
                return redirect(url_for('signup'))
            
            db = get_db()
            cursor = db.cursor()
            
            # Check if user exists
            if IS_POSTGRES:
                cursor.execute('SELECT id FROM users WHERE email = %s', (email,))
            else:
                cursor.execute('SELECT id FROM users WHERE email = ?', (email,))
                
            if cursor.fetchone():
                flash('Email already registered')
                return redirect(url_for('signup'))
            
            # Insert new user
            if IS_POSTGRES:
                cursor.execute(
                    'INSERT INTO users (email, password_hash, has_onboarded) VALUES (%s, %s, %s) RETURNING id',
                    (email, generate_password_hash(password), False)
                )
                user_id = cursor.fetchone()[0]
            else:
                cursor.execute(
                    'INSERT INTO users (email, password_hash, has_onboarded) VALUES (?, ?, ?)',
                    (email, generate_password_hash(password), False)
                )
                user_id = cursor.lastrowid
            
            db.commit()
            
            session['user_id'] = user_id
            return redirect(url_for('add_first_pet'))
            
        except Exception as e:
            print(f"Signup error: {str(e)}")
            db.rollback()
            flash('An error occurred during signup. Please try again.')
            return redirect(url_for('signup'))
    
    return render_template('auth/signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        db = get_db()
        cursor = db.cursor()
        if IS_POSTGRES:
            cursor.execute('SELECT * FROM users WHERE email = %s', (email,))
        else:
            cursor.execute('SELECT * FROM users WHERE email = ?', (email,))
        
        user = cursor.fetchone()
        
        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            if not user['has_onboarded']:
                return redirect(url_for('add_first_pet'))
            return redirect(url_for('dashboard'))
        
        flash('Invalid email or password')
    return render_template('auth/login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('index'))

@app.route('/add_first_pet', methods=['GET', 'POST'])
def add_first_pet():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    db = get_db()
    cursor = db.cursor()
    if IS_POSTGRES:
        cursor.execute('SELECT * FROM users WHERE id = %s', (session['user_id'],))
    else:
        cursor.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],))
    
    user = cursor.fetchone()
    if user['has_onboarded']:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        if IS_POSTGRES:
            cursor.execute('''
                INSERT INTO pets (name, species, breed, age, medical_history, user_id)
                VALUES (%s, %s, %s, %s, %s, %s)
            ''', (
                request.form.get('name'),
                request.form.get('species'),
                request.form.get('breed'),
                request.form.get('age'),
                request.form.get('medical_history'),
                session['user_id']
            ))
            cursor.execute('UPDATE users SET has_onboarded = %s WHERE id = %s', (True, session['user_id']))
        else:
            cursor.execute('''
                INSERT INTO pets (name, species, breed, age, medical_history, user_id)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                request.form.get('name'),
                request.form.get('species'),
                request.form.get('breed'),
                request.form.get('age'),
                request.form.get('medical_history'),
                session['user_id']
            ))
            cursor.execute('UPDATE users SET has_onboarded = ? WHERE id = ?', (True, session['user_id']))
        db.commit()
        return redirect(url_for('dashboard'))
    
    return render_template('profile/add_first_pet.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    db = get_db()
    cursor = db.cursor()
    if IS_POSTGRES:
        cursor.execute('SELECT * FROM users WHERE id = %s', (session['user_id'],))
    else:
        cursor.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],))
    
    user = cursor.fetchone()
    if not user['has_onboarded']:
        return redirect(url_for('add_first_pet'))
    
    if IS_POSTGRES:
        cursor.execute('SELECT * FROM pets WHERE user_id = %s', (session['user_id'],))
        pets = cursor.fetchall()
        cursor.execute('''
            SELECT c.*, p.name as pet_name, ci.image_path
            FROM chats c 
            LEFT JOIN pets p ON c.pet_id = p.id 
            LEFT JOIN chat_images ci ON c.id = ci.chat_id
            WHERE c.user_id = %s 
            ORDER BY c.timestamp DESC LIMIT 5
        ''', (session['user_id'],))
        chats = cursor.fetchall()
    else:
        pets = db.execute('SELECT * FROM pets WHERE user_id = ?', (session['user_id'],)).fetchall()
        chats = db.execute('''
            SELECT c.*, p.name as pet_name, ci.image_path
            FROM chats c 
            LEFT JOIN pets p ON c.pet_id = p.id 
            LEFT JOIN chat_images ci ON c.id = ci.chat_id
            WHERE c.user_id = ? 
            ORDER BY c.timestamp DESC LIMIT 5
        ''', (session['user_id'],)).fetchall()
    
    # Format timestamps
    chats = [{**dict(chat), 'formatted_time': format_chat_timestamp(chat['timestamp'])} 
             for chat in chats]
    
    return render_template('dashboard/index.html', user=user, pets=pets, chats=chats)

@app.route('/chat')
def chat():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    db = get_db()
    cursor = db.cursor()
    if IS_POSTGRES:
        cursor.execute('SELECT * FROM users WHERE id = %s', (session['user_id'],))
    else:
        cursor.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],))
    
    user = cursor.fetchone()
    if not user['has_onboarded']:
        return redirect(url_for('add_first_pet'))
    
    if IS_POSTGRES:
        cursor.execute('SELECT * FROM pets WHERE user_id = %s', (session['user_id'],))
        pets = cursor.fetchall()
        cursor.execute('''
            SELECT c.*, p.name as pet_name, ci.image_path
            FROM chats c 
            LEFT JOIN pets p ON c.pet_id = p.id 
            LEFT JOIN chat_images ci ON c.id = ci.chat_id
            WHERE c.user_id = %s 
            ORDER BY c.timestamp DESC LIMIT 10
        ''', (session['user_id'],))
        chats = cursor.fetchall()
    else:
        pets = db.execute('SELECT * FROM pets WHERE user_id = ?', (session['user_id'],)).fetchall()
        chats = db.execute('''
            SELECT c.*, p.name as pet_name, ci.image_path
            FROM chats c 
            LEFT JOIN pets p ON c.pet_id = p.id 
            LEFT JOIN chat_images ci ON c.id = ci.chat_id
            WHERE c.user_id = ? 
            ORDER BY c.timestamp DESC LIMIT 10
        ''', (session['user_id'],)).fetchall()
    
    # Format timestamps
    chats = [{**dict(chat), 'formatted_time': format_chat_timestamp(chat['timestamp'])} 
             for chat in chats]
    
    return render_template('chat/index.html', pets=pets, chats=chats)

@app.route('/chat/send', methods=['POST'])
def send_message():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    message = request.form.get('message')
    pet_id = request.form.get('pet_id')
    image = request.files.get('image')
    
    try:
        db = get_db()
        cursor = db.cursor()
        pet_context = ""
        if pet_id:
            if IS_POSTGRES:
                cursor.execute('SELECT * FROM pets WHERE id = %s AND user_id = %s', 
                           (pet_id, session['user_id']))
            else:
                cursor.execute('SELECT * FROM pets WHERE id = ? AND user_id = ?', 
                           (pet_id, session['user_id']))
            pet = cursor.fetchone()
            if pet:
                pet_context = f"\nCurrent pet context: {pet['name']} is a {pet['age']} year old {pet['breed']} {pet['species']}. Medical history: {pet['medical_history']}"

        # Process image if provided
        image_path = None
        if image and allowed_file(image.filename):
            filename = secure_filename(image.filename)
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            filename = f"{timestamp}_{filename}"
            image_path = os.path.join('uploads', filename)  # Store relative path
            full_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            image.save(full_path)
            
            # Get AI response using X.AI's Grok vision model for image
            ai_response = process_image_with_grok(full_path, 
                f"This is a pet-related image. {message} {pet_context}")
        else:
            # Get AI response using X.AI's Grok model for text only
            completion = openai.ChatCompletion.create(
                model="grok-beta",
                messages=[
                    {"role": "system", "content": f"You are VetX, an advanced AI veterinarian with extensive knowledge in animal health and care. You provide professional, accurate medical advice whil[...] 
                    {"role": "user", "content": message}
                ]
            )
            ai_response = completion.choices[0].message['content']
        
        # Save chat to database
        timestamp = datetime.utcnow().isoformat()
        if IS_POSTGRES:
            cursor.execute('''
                INSERT INTO chats (message, response, user_id, pet_id, timestamp)
                VALUES (%s, %s, %s, %s, %s) RETURNING id
            ''', (message, ai_response, session['user_id'], pet_id, timestamp))
            chat_id = cursor.fetchone()[0]
        else:
            cursor.execute('''
                INSERT INTO chats (message, response, user_id, pet_id, timestamp)
                VALUES (?, ?, ?, ?, ?)
            ''', (message, ai_response, session['user_id'], pet_id, timestamp))
            chat_id = cursor.lastrowid
        
        # Save image path if image was uploaded
        if image_path:
            if IS_POSTGRES:
                cursor.execute('''
                    INSERT INTO chat_images (chat_id, image_path, upload_timestamp)
                    VALUES (%s, %s, %s)
                ''', (chat_id, image_path, timestamp))
            else:
                cursor.execute('''
                    INSERT INTO chat_images (chat_id, image_path, upload_timestamp)
                    VALUES (?, ?, ?)
                ''', (chat_id, image_path, timestamp))
        
        db.commit()
        
        return {
            'message': message, 
            'response': ai_response, 
            'timestamp': timestamp,
            'image_path': image_path
        }
    except Exception as e:
        print(f"Error in AI response: {str(e)}")
        return {'message': message, 'response': "I apologize, but I'm having trouble processing your request at the moment. Please try again later."}, 500

@app.route('/pets', methods=['GET', 'POST'])
def pets():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    db = get_db()
    cursor = db.cursor()
    if IS_POSTGRES:
        cursor.execute('SELECT * FROM users WHERE id = %s', (session['user_id'],))
    else:
        cursor.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],))
    
    user = cursor.fetchone()
    if not user['has_onboarded']:
        return redirect(url_for('add_first_pet'))
    
    if request.method == 'POST':
        if IS_POSTGRES:
            cursor.execute('''
                INSERT INTO pets (name, species, breed, age, medical_history, user_id)
                VALUES (%s, %s, %s, %s, %s, %s)
            ''', (
                request.form.get('name'),
                request.form.get('species'),
                request.form.get('breed'),
                request.form.get('age'),
                request.form.get('medical_history'),
                session['user_id']
            ))
        else:
            cursor.execute('''
                INSERT INTO pets (name, species, breed, age, medical_history, user_id)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                request.form.get('name'),
                request.form.get('species'),
                request.form.get('breed'),
                request.form.get('age'),
                request.form.get('medical_history'),
                session['user_id']
            ))
        db.commit()
        return redirect(url_for('pets'))
    
    if IS_POSTGRES:
        cursor.execute('SELECT * FROM pets WHERE user_id = %s', (session['user_id'],))
        pets = cursor.fetchall()
    else:
        pets = db.execute('SELECT * FROM pets WHERE user_id = ?', (session['user_id'],)).fetchall()
    return render_template('profile/pets.html', pets=pets)

if __name__ == '__main__':
    if not os.path.exists(DATABASE_URL.replace('sqlite:///', '')):
        init_db()
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
