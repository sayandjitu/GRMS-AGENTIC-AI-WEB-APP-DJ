from flask import Flask, request, jsonify, g, send_from_directory
import sqlite3
import os
import json
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, 'grms.db')

app = Flask(__name__, static_folder=BASE_DIR, static_url_path='')

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    with app.app_context():
        db = get_db()
        cursor = db.cursor()
        
        # Create users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                password TEXT NOT NULL,
                role TEXT NOT NULL,
                name TEXT NOT NULL,
                email TEXT,
                phone TEXT,
                studentId TEXT,
                avatar TEXT
            )
        ''')
        
        # Create grievances table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS grievances (
                id TEXT PRIMARY KEY,
                citizenUser TEXT NOT NULL,
                citizen TEXT NOT NULL,
                category TEXT NOT NULL,
                subject TEXT NOT NULL,
                location TEXT NOT NULL,
                desc TEXT NOT NULL,
                priority TEXT NOT NULL,
                status TEXT NOT NULL,
                date TEXT NOT NULL,
                assignedTo TEXT,
                files TEXT,
                timeline TEXT
            )
        ''')
        
        # Insert default users if empty
        cursor.execute("SELECT COUNT(*) FROM users")
        if cursor.fetchone()[0] == 0:
            cursor.execute("INSERT INTO users VALUES (?, ?, ?, ?, ?, ?, ?, ?)", 
                           ('user', 'pass123', 'complainant', 'Rajesh Kumar', 'rajesh@email.com', '9876543210', 'KTU2021CS001', None))
            cursor.execute("INSERT INTO users VALUES (?, ?, ?, ?, ?, ?, ?, ?)", 
                           ('admin', 'admin123', 'admin', 'Priya Sharma', 'admin@grms.edu.in', '9800000001', 'N/A', None))
            cursor.execute("INSERT INTO users VALUES (?, ?, ?, ?, ?, ?, ?, ?)", 
                           ('officer', 'off123', 'officer', 'Suresh Pattnaik', 'officer@grms.edu.in', '9800000002', 'N/A', None))
            
            # Default grievance
            tl = json.dumps([
                {"s": "Filed", "d": "Jan 10", "done": True, "current": False},
                {"s": "Acknowledged", "d": "Jan 11", "done": True, "current": False},
                {"s": "Officer Assigned", "d": "Jan 12", "done": True, "current": False},
                {"s": "Under Investigation", "d": "Jan 13", "done": True, "current": False},
                {"s": "Resolved", "d": "Jan 15", "done": True, "current": False}
            ])
            cursor.execute('''INSERT INTO grievances 
                (id, citizenUser, citizen, category, subject, location, desc, priority, status, date, assignedTo, files, timeline) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', 
                ('GRM-2024-001', 'user', 'Rajesh Kumar', 'Academic Issues', 'Internal marks not updated', 'CSE Dept, Block A', 'Marks for 3 subjects not updated', 'Urgent', 'Resolved', '2024-01-10', 'Suresh Pattnaik', '[]', tl))
            
        db.commit()

@app.route('/')
def serve_index():
    return send_from_directory(BASE_DIR, 'GRMS PPD Date and Time new Amazing Version.html')

# Endpoints
@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE username = ? AND password = ?", (data['username'], data['password'])).fetchone()
    if user and user['role'] == data['role']:
        return jsonify(dict(user))
    return jsonify({"error": "Invalid credentials or role"}), 401

@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    db = get_db()
    try:
        db.execute("INSERT INTO users (username, password, role, name, email, phone, studentId, avatar) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                   (data['username'], data['password'], 'complainant', data['name'], data.get('email'), data.get('phone'), data.get('studentId'), None))
        db.commit()
        return jsonify({"success": True})
    except sqlite3.IntegrityError:
        return jsonify({"error": "Username already exists"}), 400

@app.route('/api/users/<username>', methods=['GET'])
def get_user(username):
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    if user:
        return jsonify(dict(user))
    return jsonify({"error": "User Not Found"}), 404

@app.route('/api/grievances', methods=['GET'])
def get_grievances():
    username = request.args.get('username')
    role = request.args.get('role')
    
    db = get_db()
    if role == 'complainant':
        grs = db.execute("SELECT * FROM grievances WHERE citizenUser = ? ORDER BY id DESC", (username,)).fetchall()
    elif role == 'officer':
        grs = db.execute("SELECT * FROM grievances WHERE assignedTo = (SELECT name FROM users WHERE username=?) ORDER BY id DESC", (username,)).fetchall()
    else:
        grs = db.execute("SELECT * FROM grievances ORDER BY id DESC").fetchall()
        
    result = []
    for g in grs:
        d = dict(g)
        d['files'] = json.loads(d['files']) if d['files'] else []
        d['timeline'] = json.loads(d['timeline']) if d['timeline'] else []
        result.append(d)
    return jsonify(result)

@app.route('/api/grievances', methods=['POST'])
def add_grievance():
    data = request.json
    db = get_db()
    
    cursor = db.cursor()
    cursor.execute("SELECT COUNT(*) FROM grievances")
    cnt = cursor.fetchone()[0]
    new_id = f"GRM-{datetime.now().year}-{str(cnt+1).zfill(3)}"
    today = datetime.now().strftime("%Y-%m-%d")
    
    timeline = [
        {'s': 'Filed', 'd': today, 'done': True, 'current': False},
        {'s': 'Acknowledged', 'd': '-', 'done': False, 'current': True},
        {'s': 'Officer Assigned', 'd': '-', 'done': False, 'current': False},
        {'s': 'Under Investigation', 'd': '-', 'done': False, 'current': False},
        {'s': 'Resolved', 'd': '-', 'done': False, 'current': False}
    ]
    
    db.execute('''INSERT INTO grievances 
        (id, citizenUser, citizen, category, subject, location, desc, priority, status, date, assignedTo, files, timeline) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', 
        (new_id, data['username'], data['citizen'], data['category'], data['subject'], data['location'], data['desc'], data['priority'], 'Open', today, None, json.dumps(data.get('files', [])), json.dumps(timeline)))
    
    db.commit()
    return jsonify({"id": new_id, "date": today})

@app.route('/api/grievances/<id>', methods=['PUT'])
def update_grievance(id):
    data = request.json
    db = get_db()
    
    gr = db.execute("SELECT * FROM grievances WHERE id = ?", (id,)).fetchone()
    if not gr:
        return jsonify({"error": "Not Found"}), 404
        
    status = data.get('status', gr['status'])
    assigned = data.get('assignedTo', gr['assignedTo'])
    timeline = json.loads(gr['timeline']) if gr['timeline'] else []
    
    if status == 'Resolved':
        for t in timeline:
            t['done'] = True
            t['current'] = False
            if t['d'] == '-':
                 t['d'] = datetime.now().strftime("%Y-%m-%d")
            
    db.execute("UPDATE grievances SET status = ?, assignedTo = ?, timeline = ? WHERE id = ?", (status, assigned, json.dumps(timeline), id))
    db.commit()
    return jsonify({"success": True})

if __name__ == '__main__':
    init_db()
    print("Starting Flask application on port 5000...")
    app.run(debug=True, host='0.0.0.0', port=5000)
