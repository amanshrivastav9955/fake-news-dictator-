import sqlite3
import os
import json
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

# Load env configuration
load_dotenv()

DB_TYPE = os.getenv('DATABASE_TYPE', 'sqlite').lower()
DB_NAME = os.getenv('DATABASE_NAME', 'database.db')
MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017/verifact')
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/verifact')

# --- MONGO / POSTGRES DYNAMIC IMPORT HELPERS ---
_mongo_client = None
_postgres_pool = None

def get_mongodb():
    global _mongo_client
    if _mongo_client is None:
        from pymongo import MongoClient
        _mongo_client = MongoClient(MONGO_URI)
    # Extract database name from URI or default
    db_name = MONGO_URI.split('/')[-1] if '/' in MONGO_URI.replace('://', '') else 'verifact'
    if '?' in db_name:
        db_name = db_name.split('?')[0]
    return _mongo_client[db_name or 'verifact']

def get_pg_connection():
    global _postgres_pool
    if _postgres_pool is None:
        from psycopg2.pool import SimpleConnectionPool
        _postgres_pool = SimpleConnectionPool(1, 10, DATABASE_URL)
    return _postgres_pool.getconn()

def put_pg_connection(conn):
    if _postgres_pool:
        _postgres_pool.putconn(conn)

# --- UNIFIED CONNECTION ROUTER ---
def get_db_connection():
    if DB_TYPE == 'sqlite':
        conn = sqlite3.connect(DB_NAME)
        conn.row_factory = sqlite3.Row
        return conn
    elif DB_TYPE == 'postgres':
        return get_pg_connection()
    else:
        # MongoDB uses pymongo client directly
        return get_mongodb()

# --- INITIALIZATION ENGINE ---
def init_db():
    print(f"Initializing Database Layer. Engine Selected: {DB_TYPE.upper()}")
    
    if DB_TYPE == 'sqlite':
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # 1. Users Table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT DEFAULT 'user',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # 2. Predictions Table (Manual/File)
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            title TEXT,
            text TEXT,
            prediction_label TEXT,
            confidence_lr REAL,
            confidence_nb REAL,
            confidence_pac REAL,
            final_prediction TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            source TEXT,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE SET NULL
        )
        ''')
        
        # 3. Chatbot Logs
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS chatbot_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            message TEXT,
            response TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE SET NULL
        )
        ''')
        
        # 4. Live News Monitoring Table (NEW)
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS live_news (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            text TEXT,
            summary TEXT,
            entities TEXT,
            sentiment_polarity REAL,
            sentiment_subjectivity REAL,
            final_prediction TEXT,
            confidence_lr REAL,
            confidence_nb REAL,
            confidence_pac REAL,
            source TEXT,
            domain TEXT,
            url TEXT UNIQUE,
            is_alert_triggered INTEGER DEFAULT 0,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # 5. Domain Credibility Directory (NEW)
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS source_credibility (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            domain TEXT UNIQUE NOT NULL,
            score REAL,
            category TEXT, -- 'whitelist', 'blacklist', 'neutral'
            description TEXT,
            last_checked TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Seed default admin user if not exists
        cursor.execute('SELECT * FROM users WHERE username = ?', ('admin',))
        if not cursor.fetchone():
            admin_pass_hash = generate_password_hash('admin123')
            cursor.execute(
                'INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)',
                ('admin', admin_pass_hash, 'admin')
            )
            print("Admin user seeded in SQLite: admin / admin123")
            
        # Seed a default user for convenience
        cursor.execute('SELECT * FROM users WHERE username = ?', ('user',))
        if not cursor.fetchone():
            user_pass_hash = generate_password_hash('user123')
            cursor.execute(
                'INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)',
                ('user', user_pass_hash, 'user')
            )
            print("Default user seeded in SQLite: user / user123")
            
        # Seed Source Credibility List
        _seed_source_credibility_sqlite(cursor)

        conn.commit()
        conn.close()
        print("SQLite Database initialized successfully.")
        
    elif DB_TYPE == 'mongodb':
        db = get_mongodb()
        # Create indexes
        db.users.create_index("username", unique=True)
        db.live_news.create_index("url", unique=True)
        db.source_credibility.create_index("domain", unique=True)
        
        # Seed Admin/Users
        if db.users.count_documents({"username": "admin"}) == 0:
            db.users.insert_one({
                "username": "admin",
                "password_hash": generate_password_hash("admin123"),
                "role": "admin",
                "created_at": datetime.utcnow()
            })
            print("Admin user seeded in MongoDB: admin / admin123")
            
        if db.users.count_documents({"username": "user"}) == 0:
            db.users.insert_one({
                "username": "user",
                "password_hash": generate_password_hash("user123"),
                "role": "user",
                "created_at": datetime.utcnow()
            })
            print("Default user seeded in MongoDB: user / user123")
            
        _seed_source_credibility_mongodb(db)
        print("MongoDB Collections initialized successfully.")
        
    elif DB_TYPE == 'postgres':
        conn = get_pg_connection()
        cursor = conn.cursor()
        
        # Create tables (Postgres syntax)
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(100) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            role VARCHAR(50) DEFAULT 'user',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS predictions (
            id SERIAL PRIMARY KEY,
            user_id INTEGER,
            title TEXT,
            text TEXT,
            prediction_label VARCHAR(50),
            confidence_lr REAL,
            confidence_nb REAL,
            confidence_pac REAL,
            final_prediction VARCHAR(50),
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            source VARCHAR(50)
        );
        CREATE TABLE IF NOT EXISTS chatbot_logs (
            id SERIAL PRIMARY KEY,
            user_id INTEGER,
            message TEXT,
            response TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS live_news (
            id SERIAL PRIMARY KEY,
            title TEXT,
            text TEXT,
            summary TEXT,
            entities TEXT,
            sentiment_polarity REAL,
            sentiment_subjectivity REAL,
            final_prediction VARCHAR(50),
            confidence_lr REAL,
            confidence_nb REAL,
            confidence_pac REAL,
            source VARCHAR(50),
            domain VARCHAR(100),
            url TEXT UNIQUE,
            is_alert_triggered INTEGER DEFAULT 0,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS source_credibility (
            id SERIAL PRIMARY KEY,
            domain VARCHAR(255) UNIQUE NOT NULL,
            score REAL,
            category VARCHAR(50),
            description TEXT,
            last_checked TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        ''')
        
        # Seed Admin/Users
        cursor.execute('SELECT * FROM users WHERE username = %s', ('admin',))
        if not cursor.fetchone():
            cursor.execute(
                'INSERT INTO users (username, password_hash, role) VALUES (%s, %s, %s)',
                ('admin', generate_password_hash('admin123'), 'admin')
            )
            print("Admin user seeded in Postgres: admin / admin123")
            
        cursor.execute('SELECT * FROM users WHERE username = %s', ('user',))
        if not cursor.fetchone():
            cursor.execute(
                'INSERT INTO users (username, password_hash, role) VALUES (%s, %s, %s)',
                ('user', generate_password_hash('user123'), 'user')
            )
            print("Default user seeded in Postgres: user / user123")
            
        _seed_source_credibility_postgres(cursor)
        
        conn.commit()
        cursor.close()
        put_pg_connection(conn)
        print("PostgreSQL Database initialized successfully.")

# --- WHITELIST & BLACKLIST DATA SEEDERS ---
WHITELIST = [
    ('reuters.com', 98.0, 'whitelist', 'Reuters News Agency - Global standard in fact-based journalism.'),
    ('apnews.com', 98.0, 'whitelist', 'Associated Press - Highly objective and factual reporting.'),
    ('bbc.com', 95.0, 'whitelist', 'British Broadcasting Corporation - High credibility, public broadcaster.'),
    ('nytimes.com', 90.0, 'whitelist', 'The New York Times - Trusted record, minor political skew.'),
    ('npr.org', 92.0, 'whitelist', 'National Public Radio - High factual reporting standard.'),
    ('bloomberg.com', 94.0, 'whitelist', 'Bloomberg - High quality business and global analytics.')
]

BLACKLIST = [
    ('theonion.com', 10.0, 'blacklist', 'The Onion - Parody and satire site, completely fictional.'),
    ('infowars.com', 15.0, 'blacklist', 'InfoWars - Conspiracy theories, high factual inaccuracies.'),
    ('nationalreport.net', 12.0, 'blacklist', 'National Report - Known satirical publisher posing as news.'),
    ('worldnewsdailyreport.com', 5.0, 'blacklist', 'World News Daily Report - Direct hoax and sensational fake site.'),
    ('yournewswire.com', 15.0, 'blacklist', 'YourNewsWire - High volume fabrication and fake clickbait.')
]

def _seed_source_credibility_sqlite(cursor):
    for domain, score, cat, desc in WHITELIST + BLACKLIST:
        cursor.execute('''
            INSERT OR IGNORE INTO source_credibility (domain, score, category, description) 
            VALUES (?, ?, ?, ?)
        ''', (domain, score, cat, desc))

def _seed_source_credibility_mongodb(db):
    for domain, score, cat, desc in WHITELIST + BLACKLIST:
        db.source_credibility.update_one(
            {"domain": domain},
            {"$setOnInsert": {"domain": domain, "score": score, "category": cat, "description": desc, "last_checked": datetime.utcnow()}},
            upsert=True
        )

def _seed_source_credibility_postgres(cursor):
    for domain, score, cat, desc in WHITELIST + BLACKLIST:
        cursor.execute('''
            INSERT INTO source_credibility (domain, score, category, description) 
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (domain) DO NOTHING
        ''', (domain, score, cat, desc))

# --- USER MANAGEMENT WRAPPERS ---
def register_user(username, password, role='user'):
    password_hash = generate_password_hash(password)
    if DB_TYPE == 'sqlite':
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)', (username, password_hash, role))
            conn.commit()
            return True, "Registration successful."
        except sqlite3.IntegrityError:
            return False, "Username already exists."
        finally:
            conn.close()
    elif DB_TYPE == 'mongodb':
        db = get_db_connection()
        try:
            db.users.insert_one({
                "username": username,
                "password_hash": password_hash,
                "role": role,
                "created_at": datetime.utcnow()
            })
            return True, "Registration successful."
        except Exception:
            return False, "Username already exists."
    elif DB_TYPE == 'postgres':
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('INSERT INTO users (username, password_hash, role) VALUES (%s, %s, %s)', (username, password_hash, role))
            conn.commit()
            return True, "Registration successful."
        except Exception:
            return False, "Username already exists."
        finally:
            cursor.close()
            put_pg_connection(conn)

def check_user_credentials(username, password):
    if DB_TYPE == 'sqlite':
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
        user = cursor.fetchone()
        conn.close()
        if user and check_password_hash(user['password_hash'], password):
            return {'id': user['id'], 'username': user['username'], 'role': user['role']}
    elif DB_TYPE == 'mongodb':
        db = get_db_connection()
        user = db.users.find_one({"username": username})
        if user and check_password_hash(user['password_hash'], password):
            return {'id': str(user['_id']), 'username': user['username'], 'role': user['role']}
    elif DB_TYPE == 'postgres':
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username = %s', (username,))
        user = cursor.fetchone()
        cursor.close()
        put_pg_connection(conn)
        if user and check_password_hash(user[2], password):  # user[2] is password_hash
            return {'id': user[0], 'username': user[1], 'role': user[3]}
    return None

# --- MANUAL PREDICTIONS WRAPPERS ---
def add_prediction(user_id, title, text, prediction_label, conf_lr, conf_nb, conf_pac, final_pred, source):
    if DB_TYPE == 'sqlite':
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO predictions 
            (user_id, title, text, prediction_label, confidence_lr, confidence_nb, confidence_pac, final_prediction, source) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, title, text, prediction_label, conf_lr, conf_nb, conf_pac, final_pred, source))
        pred_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return pred_id
    elif DB_TYPE == 'mongodb':
        db = get_db_connection()
        res = db.predictions.insert_one({
            "user_id": user_id,
            "title": title,
            "text": text,
            "prediction_label": prediction_label,
            "confidence_lr": conf_lr,
            "confidence_nb": conf_nb,
            "confidence_pac": conf_pac,
            "final_prediction": final_pred,
            "source": source,
            "timestamp": datetime.utcnow()
        })
        return str(res.inserted_id)
    elif DB_TYPE == 'postgres':
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO predictions 
            (user_id, title, text, prediction_label, confidence_lr, confidence_nb, confidence_pac, final_prediction, source) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
        ''', (user_id, title, text, prediction_label, conf_lr, conf_nb, conf_pac, final_pred, source))
        pred_id = cursor.fetchone()[0]
        conn.commit()
        cursor.close()
        put_pg_connection(conn)
        return pred_id

def get_user_predictions(user_id):
    if DB_TYPE == 'sqlite':
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM predictions WHERE user_id = ? ORDER BY timestamp DESC', (user_id,))
        preds = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return preds
    elif DB_TYPE == 'mongodb':
        db = get_db_connection()
        preds = list(db.predictions.find({"user_id": user_id}).sort("timestamp", -1))
        for p in preds:
            p['id'] = str(p['_id'])
        return preds
    elif DB_TYPE == 'postgres':
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM predictions WHERE user_id = %s ORDER BY timestamp DESC', (user_id,))
        colnames = [desc[0] for desc in cursor.description]
        preds = [dict(zip(colnames, row)) for row in cursor.fetchall()]
        cursor.close()
        put_pg_connection(conn)
        return preds

def get_prediction_by_id(pred_id):
    if DB_TYPE == 'sqlite':
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT p.*, u.username 
            FROM predictions p 
            LEFT JOIN users u ON p.user_id = u.id 
            WHERE p.id = ?
        ''', (pred_id,))
        pred = cursor.fetchone()
        conn.close()
        return dict(pred) if pred else None
    elif DB_TYPE == 'mongodb':
        from bson.objectid import ObjectId
        db = get_db_connection()
        pred = db.predictions.find_one({"_id": ObjectId(pred_id)})
        if pred:
            pred['id'] = str(pred['_id'])
            # Bind username
            if pred.get('user_id'):
                user = db.users.find_one({"_id": ObjectId(pred['user_id'])})
                pred['username'] = user['username'] if user else None
            else:
                pred['username'] = None
        return pred
    elif DB_TYPE == 'postgres':
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT p.*, u.username 
            FROM predictions p 
            LEFT JOIN users u ON p.user_id = u.id 
            WHERE p.id = %s
        ''', (pred_id,))
        colnames = [desc[0] for desc in cursor.description]
        row = cursor.fetchone()
        cursor.close()
        put_pg_connection(conn)
        return dict(zip(colnames, row)) if row else None

def delete_prediction(pred_id):
    if DB_TYPE == 'sqlite':
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM predictions WHERE id = ?', (pred_id,))
        conn.commit()
        conn.close()
    elif DB_TYPE == 'mongodb':
        from bson.objectid import ObjectId
        db = get_db_connection()
        db.predictions.delete_one({"_id": ObjectId(pred_id)})
    elif DB_TYPE == 'postgres':
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM predictions WHERE id = %s', (pred_id,))
        conn.commit()
        cursor.close()
        put_pg_connection(conn)

def get_all_predictions():
    if DB_TYPE == 'sqlite':
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT p.*, u.username 
            FROM predictions p 
            LEFT JOIN users u ON p.user_id = u.id 
            ORDER BY p.timestamp DESC
        ''')
        preds = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return preds
    elif DB_TYPE == 'mongodb':
        db = get_db_connection()
        preds = list(db.predictions.find().sort("timestamp", -1))
        for p in preds:
            p['id'] = str(p['_id'])
            if p.get('user_id'):
                from bson.objectid import ObjectId
                try:
                    user = db.users.find_one({"_id": ObjectId(p['user_id'])})
                    p['username'] = user['username'] if user else None
                except Exception:
                    p['username'] = None
            else:
                p['username'] = None
        return preds
    elif DB_TYPE == 'postgres':
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT p.*, u.username 
            FROM predictions p 
            LEFT JOIN users u ON p.user_id = u.id 
            ORDER BY p.timestamp DESC
        ''')
        colnames = [desc[0] for desc in cursor.description]
        preds = [dict(zip(colnames, row)) for row in cursor.fetchall()]
        cursor.close()
        put_pg_connection(conn)
        return preds

# --- LIVE NEWS DATA WRAPPERS (NEW) ---
def add_live_news(title, text, summary, entities, sentiment_polarity, sentiment_subjectivity, final_prediction, conf_lr, conf_nb, conf_pac, source, domain, url, is_alert):
    entities_str = json.dumps(entities) if isinstance(entities, (list, dict)) else str(entities)
    
    if DB_TYPE == 'sqlite':
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO live_news (
                    title, text, summary, entities, sentiment_polarity, sentiment_subjectivity, 
                    final_prediction, confidence_lr, confidence_nb, confidence_pac, source, domain, url, is_alert_triggered
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (title, text, summary, entities_str, sentiment_polarity, sentiment_subjectivity, 
                  final_prediction, conf_lr, conf_nb, conf_pac, source, domain, url, 1 if is_alert else 0))
            conn.commit()
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            return None  # URL already exists
        finally:
            conn.close()
            
    elif DB_TYPE == 'mongodb':
        db = get_db_connection()
        try:
            res = db.live_news.insert_one({
                "title": title,
                "text": text,
                "summary": summary,
                "entities": entities,
                "sentiment_polarity": sentiment_polarity,
                "sentiment_subjectivity": sentiment_subjectivity,
                "final_prediction": final_prediction,
                "confidence_lr": conf_lr,
                "confidence_nb": conf_nb,
                "confidence_pac": conf_pac,
                "source": source,
                "domain": domain,
                "url": url,
                "is_alert_triggered": is_alert,
                "timestamp": datetime.utcnow()
            })
            return str(res.inserted_id)
        except Exception:
            return None  # Duplicate key
            
    elif DB_TYPE == 'postgres':
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO live_news (
                    title, text, summary, entities, sentiment_polarity, sentiment_subjectivity, 
                    final_prediction, confidence_lr, confidence_nb, confidence_pac, source, domain, url, is_alert_triggered
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
            ''', (title, text, summary, entities_str, sentiment_polarity, sentiment_subjectivity, 
                  final_prediction, conf_lr, conf_nb, conf_pac, source, domain, url, 1 if is_alert else 0))
            new_id = cursor.fetchone()[0]
            conn.commit()
            return new_id
        except Exception:
            return None
        finally:
            cursor.close()
            put_pg_connection(conn)

def get_live_news(limit=50):
    if DB_TYPE == 'sqlite':
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM live_news ORDER BY timestamp DESC LIMIT ?', (limit,))
        news_list = []
        for row in cursor.fetchall():
            d = dict(row)
            try:
                d['entities'] = json.loads(d['entities'])
            except Exception:
                d['entities'] = []
            news_list.append(d)
        conn.close()
        return news_list
        
    elif DB_TYPE == 'mongodb':
        db = get_db_connection()
        news_list = list(db.live_news.find().sort("timestamp", -1).limit(limit))
        for n in news_list:
            n['id'] = str(n['_id'])
        return news_list
        
    elif DB_TYPE == 'postgres':
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM live_news ORDER BY timestamp DESC LIMIT %s', (limit,))
        colnames = [desc[0] for desc in cursor.description]
        news_list = []
        for row in cursor.fetchall():
            d = dict(zip(colnames, row))
            try:
                d['entities'] = json.loads(d['entities'])
            except Exception:
                d['entities'] = []
            news_list.append(d)
        cursor.close()
        put_pg_connection(conn)
        return news_list

# --- SOURCE CREDIBILITY METHODS ---
def get_domain_credibility(domain):
    domain = domain.lower().strip().replace('www.', '')
    if DB_TYPE == 'sqlite':
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM source_credibility WHERE domain = ?', (domain,))
        res = cursor.fetchone()
        conn.close()
        return dict(res) if res else None
    elif DB_TYPE == 'mongodb':
        db = get_db_connection()
        res = db.source_credibility.find_one({"domain": domain})
        if res:
            res['id'] = str(res['_id'])
        return res
    elif DB_TYPE == 'postgres':
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM source_credibility WHERE domain = %s', (domain,))
        colnames = [desc[0] for desc in cursor.description]
        res = cursor.fetchone()
        cursor.close()
        put_pg_connection(conn)
        return dict(zip(colnames, res)) if res else None

def get_domain_reputation_list():
    if DB_TYPE == 'sqlite':
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM source_credibility ORDER BY category ASC, domain ASC')
        res = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return res
    elif DB_TYPE == 'mongodb':
        db = get_db_connection()
        res = list(db.source_credibility.find().sort([("category", 1), ("domain", 1)]))
        for r in res:
            r['id'] = str(r['_id'])
        return res
    elif DB_TYPE == 'postgres':
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM source_credibility ORDER BY category ASC, domain ASC')
        colnames = [desc[0] for desc in cursor.description]
        res = [dict(zip(colnames, row)) for row in cursor.fetchall()]
        cursor.close()
        put_pg_connection(conn)
        return res

def add_domain_credibility(domain, score, category, description):
    domain = domain.lower().strip().replace('www.', '')
    if DB_TYPE == 'sqlite':
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO source_credibility (domain, score, category, description, last_checked) 
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(domain) DO UPDATE SET score=excluded.score, category=excluded.category, description=excluded.description, last_checked=CURRENT_TIMESTAMP
        ''', (domain, score, category, description))
        conn.commit()
        conn.close()
    elif DB_TYPE == 'mongodb':
        db = get_db_connection()
        db.source_credibility.update_one(
            {"domain": domain},
            {"$set": {"domain": domain, "score": score, "category": category, "description": description, "last_checked": datetime.utcnow()}},
            upsert=True
        )
    elif DB_TYPE == 'postgres':
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO source_credibility (domain, score, category, description, last_checked) 
            VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (domain) DO UPDATE SET score=EXCLUDED.score, category=EXCLUDED.category, description=EXCLUDED.description, last_checked=CURRENT_TIMESTAMP
        ''', (domain, score, category, description))
        conn.commit()
        cursor.close()
        put_pg_connection(conn)

# --- GLOBAL TELEMETRY / ADMIN ANALYTICS ---
def get_admin_stats():
    if DB_TYPE == 'sqlite':
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM predictions')
        total_predictions = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM predictions WHERE final_prediction = ?', ('FAKE',))
        fake_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM predictions WHERE final_prediction = ?', ('REAL',))
        real_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM users')
        total_users = cursor.fetchone()[0]
        
        cursor.execute('''
            SELECT u.id, u.username, u.role, u.created_at, COUNT(p.id) as prediction_count 
            FROM users u 
            LEFT JOIN predictions p ON u.id = p.user_id 
            GROUP BY u.id 
            ORDER BY prediction_count DESC
        ''')
        users_list = [dict(row) for row in cursor.fetchall()]
        
        cursor.execute('SELECT source, COUNT(*) as count FROM predictions GROUP BY source')
        source_dist = {row['source']: row['count'] for row in cursor.fetchall()}
        
        # Real-time News Ingestion Counts (NEW)
        cursor.execute('SELECT COUNT(*) FROM live_news')
        live_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM live_news WHERE final_prediction = ?', ('FAKE',))
        live_fake = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            'total_predictions': total_predictions,
            'fake_count': fake_count,
            'real_count': real_count,
            'total_users': total_users,
            'users_list': users_list,
            'source_dist': source_dist,
            'live_news_count': live_count,
            'live_fake_count': live_fake
        }
        
    elif DB_TYPE == 'mongodb':
        db = get_db_connection()
        total_preds = db.predictions.count_documents({})
        fake_c = db.predictions.count_documents({"final_prediction": "FAKE"})
        real_c = db.predictions.count_documents({"final_prediction": "REAL"})
        total_u = db.users.count_documents({})
        
        # Map user lists
        users = list(db.users.find())
        users_list = []
        for u in users:
            p_count = db.predictions.count_documents({"user_id": str(u['_id'])})
            users_list.append({
                "id": str(u['_id']),
                "username": u['username'],
                "role": u['role'],
                "created_at": u['created_at'].isoformat() if isinstance(u['created_at'], datetime) else str(u['created_at']),
                "prediction_count": p_count
            })
        users_list.sort(key=lambda x: x['prediction_count'], reverse=True)
        
        # Source breakdown
        src_dist = {}
        for src in db.predictions.distinct("source"):
            src_dist[src] = db.predictions.count_documents({"source": src})
            
        live_c = db.live_news.count_documents({})
        live_fake = db.live_news.count_documents({"final_prediction": "FAKE"})
        
        return {
            'total_predictions': total_preds,
            'fake_count': fake_c,
            'real_count': real_c,
            'total_users': total_u,
            'users_list': users_list,
            'source_dist': src_dist,
            'live_news_count': live_c,
            'live_fake_count': live_fake
        }
        
    elif DB_TYPE == 'postgres':
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM predictions')
        total_predictions = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM predictions WHERE final_prediction = %s', ('FAKE',))
        fake_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM predictions WHERE final_prediction = %s', ('REAL',))
        real_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM users')
        total_users = cursor.fetchone()[0]
        
        cursor.execute('''
            SELECT u.id, u.username, u.role, u.created_at, COUNT(p.id) as prediction_count 
            FROM users u 
            LEFT JOIN predictions p ON u.id = p.user_id 
            GROUP BY u.id, u.username, u.role, u.created_at 
            ORDER BY prediction_count DESC
        ''')
        colnames = [desc[0] for desc in cursor.description]
        users_list = [dict(zip(colnames, row)) for row in cursor.fetchall()]
        
        cursor.execute('SELECT source, COUNT(*) as count FROM predictions GROUP BY source')
        source_dist = {row[0]: row[1] for row in cursor.fetchall()}
        
        cursor.execute('SELECT COUNT(*) FROM live_news')
        live_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM live_news WHERE final_prediction = %s', ('FAKE',))
        live_fake = cursor.fetchone()[0]
        
        cursor.close()
        put_pg_connection(conn)
        
        return {
            'total_predictions': total_predictions,
            'fake_count': fake_count,
            'real_count': real_count,
            'total_users': total_users,
            'users_list': users_list,
            'source_dist': source_dist,
            'live_news_count': live_count,
            'live_fake_count': live_fake
        }

# Initialize database on load if run directly
if __name__ == '__main__':
    init_db()
