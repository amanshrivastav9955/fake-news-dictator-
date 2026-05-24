import os
import re
import json
import pickle
import random
import numpy as np
import nltk
from datetime import datetime
from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, Response
from flask_socketio import SocketIO, emit

# Load environments
load_dotenv()

import database as db
import credibility as cred
import nlp_engine as nlp
import news_fetcher

# Initialize Flask & SocketIO Server
app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'verifact_secure_session_key_192837465')
socketio = SocketIO(app, cors_allowed_origins="*", async_mode=None)

# Ensure database structure is fully initialized
db.init_db()

# Hook up background Socket.IO broadcasts
def websocket_broadcast_handler(data):
    # Emit to all connected dashboards
    socketio.emit('new_live_news', data)

news_fetcher.register_socket_callback(websocket_broadcast_handler)

# --- WEB UI INTERFACES ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('index'))
        
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = db.check_user_credentials(username, password)
        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            return redirect(url_for('index'))
        else:
            error = "Invalid username or password."
            
    return render_template('login.html', error=error)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if 'user_id' in session:
        return redirect(url_for('index'))
        
    error = None
    success = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        
        if password != confirm_password:
            error = "Passwords do not match."
        elif len(password) < 6:
            error = "Password must be at least 6 characters."
        else:
            ok, msg = db.register_user(username, password)
            if ok:
                success = msg
            else:
                error = msg
                
    return render_template('signup.html', error=error, success=success)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    user_preds = db.get_user_predictions(session['user_id'])
    
    # Calculate simple stats
    total = len(user_preds)
    fake = sum(1 for p in user_preds if p['final_prediction'] == 'FAKE')
    real = sum(1 for p in user_preds if p['final_prediction'] == 'REAL')
    
    return render_template('dashboard.html', predictions=user_preds, total=total, fake=fake, real=real)

@app.route('/dashboard-realtime')
def dashboard_realtime():
    """
    futuristic live intelligence dashboard.
    """
    if 'user_id' not in session:
        return redirect(url_for('login'))
    # Load initial live news log list (pre-populated by background scanner)
    initial_live_news = db.get_live_news(limit=25)
    return render_template('dashboard_realtime.html', live_news=initial_live_news)

@app.route('/admin')
def admin():
    if 'user_id' not in session or session.get('role') != 'admin':
        return render_template('unauthorized.html'), 403
        
    stats = db.get_admin_stats()
    all_preds = db.get_all_predictions()
    
    # Read metrics.json if exists to show ML accuracies
    metrics = {}
    metrics_path = os.path.join('static', 'data', 'metrics.json')
    if os.path.exists(metrics_path):
        try:
            with open(metrics_path, 'r') as f:
                metrics = json.load(f)
        except Exception:
            pass
            
    # Load credibility whitelist/blacklist
    cred_list = db.get_domain_reputation_list()
    
    return render_template('admin.html', stats=stats, predictions=all_preds, metrics=metrics, credibility_list=cred_list)

@app.route('/admin/credibility/add', methods=['POST'])
def add_credibility_entry():
    if 'user_id' not in session or session.get('role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    domain = request.form.get('domain', '').strip()
    score = float(request.form.get('score', 50))
    category = request.form.get('category', 'neutral')
    description = request.form.get('description', '')
    
    if not domain:
        return jsonify({'error': 'Domain name is required'}), 400
        
    db.add_domain_credibility(domain, score, category, description)
    return redirect(url_for('admin'))

@app.route('/delete_log/<int:pred_id>', methods=['POST'])
def delete_log(pred_id):
    if 'user_id' not in session or session.get('role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
        
    db.delete_prediction(pred_id)
    return jsonify({'success': True})

@app.route('/admin/force_scan', methods=['POST'])
def force_scan():
    if 'user_id' not in session or session.get('role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    import threading
    threading.Thread(target=news_fetcher.run_news_scan, daemon=True).start()
    return jsonify({'success': True, 'message': 'Scan triggered dynamically!'})

@app.route('/download_report/<int:pred_id>')
def download_report(pred_id):
    pred = db.get_prediction_by_id(pred_id)
    if not pred:
        return "Report not found", 404
        
    # Check authorization (only own reports or admins)
    if 'user_id' not in session or (session.get('user_id') != pred['user_id'] and session.get('role') != 'admin'):
        if pred['user_id'] is not None and session.get('user_id') != pred['user_id'] and session.get('role') != 'admin':
            return "Unauthorized to download this report", 403
            
    report_content = f"""======================================================================
                     FAKE NEWS DETECTION REPORT
======================================================================
Report Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Prediction ID: {pred['id']}
Analyzed Source: {pred['source'].upper()}
User: {pred['username'] if pred['username'] else 'Anonymous Guest'}
----------------------------------------------------------------------

NEWS TITLE:
{pred['title']}

----------------------------------------------------------------------
ANALYSIS VERDICT:
>>> THE NEWS IS PREDICTED TO BE: {pred['final_prediction']} <<<
----------------------------------------------------------------------

INDIVIDUAL MODEL CONFIDENCE BREAKDOWN:
- Logistic Regression: {pred['prediction_label']} ({pred['confidence_lr']:.2f}% Confidence)
- Multinomial Naive Bayes: {pred['prediction_label']} ({pred['confidence_nb']:.2f}% Confidence)
- Passive Aggressive Classifier: {pred['prediction_label']} ({pred['confidence_pac']:.2f}% Confidence)

======================================================================
FULL EXTRACTED CONTENT ANALYZED:
======================================================================
{pred['text']}

======================================================================
                        END OF REPORT
======================================================================
"""
    return Response(
        report_content,
        mimetype="text/plain",
        headers={"Content-disposition": f"attachment; filename=FakeNews_Report_ID_{pred_id}.txt"}
    )

# --- CORE PREDICTION ROUTE (UPGRADED) ---

@app.route('/predict', methods=['POST'])
def predict():
    title = request.form.get('title', '')
    text = request.form.get('text', '')
    source = request.form.get('source', 'manual')
    url_input = request.form.get('url', '').strip()
    
    if not title.strip() and not text.strip() and not url_input.strip():
        return jsonify({'error': 'Title, text, or a valid URL is required.'}), 400
        
    # Heuristic URL scraping fallback if URL submitted
    if url_input and not text.strip():
        try:
            import requests
            from bs4 import BeautifulSoup
            # Minimal scraper
            r = requests.get(url_input, timeout=5, headers={'User-Agent': 'Mozilla/5.0'})
            if r.status_code == 200:
                soup = BeautifulSoup(r.text, 'html.parser')
                title = soup.find('h1').text if soup.find('h1') else "Scraped Article URL"
                paragraphs = soup.find_all('p')
                text = " ".join([p.text for p in paragraphs[:8]]) # grab up to 8 paragraphs
                source = 'scraped_url'
        except Exception as e:
            return jsonify({'error': f'Failed to scrape the URL. Technical details: {e}'}), 400
            
    # Extract domain reputation category
    domain = cred.extract_domain(url_input) if url_input else 'manual.local'
    cred_details = cred.check_domain_credibility(domain)
    
    # Run Advanced NLP Multi-Model Pipeline
    res = nlp.evaluate_news_article(title, text, url=url_input or None, domain_category=cred_details['category'])
    if not res:
        return jsonify({'error': 'Evaluation failure. Ensure model objects exist.'}), 500
        
    # Append domain details
    res['domain_credibility'] = cred_details
    
    # Inject compatibility fields for main.js frontend
    res['final_prediction'] = res['verdict']
    res['lr_pred'] = res['model_wise']['logistic_regression']['prediction']
    res['lr_conf'] = round(res['model_wise']['logistic_regression']['confidence'], 2)
    res['nb_pred'] = res['model_wise']['naive_bayes']['prediction']
    res['nb_conf'] = round(res['model_wise']['naive_bayes']['confidence'], 2)
    res['pac_pred'] = res['model_wise']['passive_aggressive']['prediction']
    res['pac_conf'] = round(res['model_wise']['passive_aggressive']['confidence'], 2)
    
    # Save to user prediction logs if authenticated
    user_id = session.get('user_id')
    pred_id = db.add_prediction(
        user_id,
        title,
        text,
        res['verdict'],
        res['model_wise']['logistic_regression']['confidence'],
        res['model_wise']['naive_bayes']['confidence'],
        res['model_wise']['passive_aggressive']['confidence'],
        res['verdict'],
        source
    )
    
    res['pred_id'] = pred_id
    return jsonify(res)

# --- CHATBOT & CONVERSATIONAL INTELLIGENCE (UPGRADED v2.5) ---

@app.route('/chatbot', methods=['POST'])
def chatbot():
    data = request.get_json() or {}
    message = data.get('message', '').strip()
    
    if not message:
        return jsonify({'response': 'Please enter a message.'})
        
    messages = [{"role": "user", "content": message}]
    
    try:
        resp = nlp.generate_ai_chat_response(messages)
        response = resp.choices[0].message.content
    except Exception as e:
        response = f"⚠️ AI Brain offline. Technical details: {e}"
        
    user_id = session.get('user_id')
    if user_id:
        try:
            conn = db.get_db_connection()
            if db.DB_TYPE == 'sqlite':
                cursor = conn.cursor()
                cursor.execute('INSERT INTO chatbot_logs (user_id, message, response) VALUES (?, ?, ?)', (user_id, message, response))
                conn.commit()
                conn.close()
        except Exception:
            pass
            
    return jsonify({'response': response})

@app.route('/api/chatbot', methods=['POST'])
def api_chatbot():
    return chatbot()

@app.route('/api/stream-chat', methods=['POST'])
def stream_chat():
    data = request.get_json() or {}
    message = data.get('message', '').strip()
    history = data.get('history', [])
    
    if not message:
        return jsonify({'error': 'Message is required.'}), 400
        
    # Build context window (last 10 messages)
    messages = []
    for h in history[-10:]:
        messages.append({"role": h['role'], "content": h['content']})
    messages.append({"role": "user", "content": message})
    
    user_id = session.get('user_id')
    
    def generate():
        try:
            stream = nlp.generate_ai_chat_response(messages, stream=True)
            full_response = ""
            for chunk in stream:
                content = ""
                if hasattr(chunk, 'choices') and len(chunk.choices) > 0:
                    delta = chunk.choices[0].delta
                    content = getattr(delta, 'content', '') or ''
                
                if content:
                    full_response += content
                    yield f"data: {json.dumps({'token': content})}\n\n"
            
            # Log completed interaction in the database
            if user_id:
                try:
                    conn = db.get_db_connection()
                    if db.DB_TYPE == 'sqlite':
                        cursor = conn.cursor()
                        cursor.execute('INSERT INTO chatbot_logs (user_id, message, response) VALUES (?, ?, ?)', (user_id, message, full_response))
                        conn.commit()
                        conn.close()
                except Exception as e:
                    print(f"Failed to log stream completion: {e}")
                    
            yield "data: [DONE]\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
            yield "data: [DONE]\n\n"
            
    return Response(generate(), mimetype='text/event-stream', headers={
        'Cache-Control': 'no-cache',
        'Transfer-Encoding': 'chunked',
        'Connection': 'keep-alive'
    })

@app.route('/api/ai-analysis', methods=['POST'])
def ai_analysis():
    title = request.form.get('title', '')
    text = request.form.get('text', '')
    url_input = request.form.get('url', '').strip()
    
    if not title.strip() and not text.strip() and not url_input.strip():
        return jsonify({'error': 'Title, text, or a valid URL is required.'}), 400
        
    if url_input and not text.strip():
        try:
            import requests
            from bs4 import BeautifulSoup
            r = requests.get(url_input, timeout=5, headers={'User-Agent': 'Mozilla/5.0'})
            if r.status_code == 200:
                soup = BeautifulSoup(r.text, 'html.parser')
                title = soup.find('h1').text if soup.find('h1') else "Scraped Article URL"
                paragraphs = soup.find_all('p')
                text = " ".join([p.text for p in paragraphs[:8]])
        except Exception as e:
            return jsonify({'error': f'Failed to scrape the URL. Technical details: {e}'}), 400
            
    domain = cred.extract_domain(url_input) if url_input else 'manual.local'
    cred_details = cred.check_domain_credibility(domain)
    
    res = nlp.evaluate_news_article(title, text, url=url_input or None, domain_category=cred_details['category'])
    if not res:
        return jsonify({'error': 'Evaluation failure.'}), 500
        
    # Generate detailed structural explanation using the advanced AI
    llm_explanation = nlp.analyze_news_with_llm(
        title=title,
        text=text,
        url=url_input,
        domain=domain,
        ml_verdict=res['verdict'],
        ml_confidence=res['confidence'],
        sentiment_pol=res['sentiment_polarity'],
        sentiment_sub=res['sentiment_subjectivity'],
        entities=res['entities'],
        domain_category=cred_details['category']
    )
    
    # Override standard classical explanation with LLM explanation if successful
    res['explanation'] = llm_explanation
    res['domain_credibility'] = cred_details
    
    # Backwards compatibility fields for frontend
    res['final_prediction'] = res['verdict']
    res['lr_pred'] = res['model_wise']['logistic_regression']['prediction']
    res['lr_conf'] = round(res['model_wise']['logistic_regression']['confidence'], 2)
    res['nb_pred'] = res['model_wise']['naive_bayes']['prediction']
    res['nb_conf'] = round(res['model_wise']['naive_bayes']['confidence'], 2)
    res['pac_pred'] = res['model_wise']['passive_aggressive']['prediction']
    res['pac_conf'] = round(res['model_wise']['passive_aggressive']['confidence'], 2)
    
    user_id = session.get('user_id')
    pred_id = db.add_prediction(
        user_id,
        title,
        text,
        res['verdict'],
        res['model_wise']['logistic_regression']['confidence'],
        res['model_wise']['naive_bayes']['confidence'],
        res['model_wise']['passive_aggressive']['confidence'],
        res['verdict'],
        url_input and 'url' or 'manual'
    )
    
    res['pred_id'] = pred_id
    return jsonify(res)

@app.route('/api/fact-explain', methods=['POST'])
def fact_explain():
    data = request.get_json() or {}
    claim = data.get('claim', '').strip()
    
    if not claim:
        return jsonify({'error': 'Claim query is required.'}), 400
        
    import news_fetcher
    claims = news_fetcher.fetch_google_fact_check(claim)
    
    if not claims:
        prompt = (
            f"As VERIFACT AI, write a quick fact-check briefing for the following claim:\n"
            f"\"{claim}\"\n\n"
            f"Provide a Verdict (e.g. TRUE, FALSE, PARTIALLY TRUE, or MISLEADING), "
            f"explain why, and list reputable verification guidelines."
        )
        try:
            resp = nlp.generate_ai_chat_response([{"role": "user", "content": prompt}])
            explanation = resp.choices[0].message.content
        except Exception as e:
            explanation = f"Could not generate claim verification explanation. Technical issue: {e}"
            
        return jsonify({
            'claim': claim,
            'google_api_results': False,
            'explanation': explanation
        })
        
    summary_input = "\n\n".join([f"Claim: {c['title']}\nDetails: {c['text']}" for c in claims[:3]])
    prompt = (
        f"You are VERIFACT AI. A user is asking about the following claim: \"{claim}\".\n"
        f"We found the following verified fact-checking reports:\n\n"
        f"{summary_input}\n\n"
        f"Generate a professional, human-readable fact-check explanation summarizing these reports. "
        f"Clearly state the overall consensus verdict, explain the context, and credit the verifying agencies."
    )
    
    try:
        resp = nlp.generate_ai_chat_response([{"role": "user", "content": prompt}])
        explanation = resp.choices[0].message.content
    except Exception as e:
        explanation = f"Fact-checking reports found, but summary generation failed. Summary of reports: {summary_input}"
        
    return jsonify({
        'claim': claim,
        'google_api_results': True,
        'reports': claims,
        'explanation': explanation
    })

# --- PRODUCTION REST REST API ENDPOINTS ---

@app.route('/api/auth/login', methods=['POST'])

def api_login():
    data = request.get_json() or {}
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({'error': 'Missing username or password'}), 400
        
    user = db.check_user_credentials(username, password)
    if user:
        return jsonify({
            'status': 'authenticated',
            'token': 'mock-jwt-token-verifact-v2',
            'user': user
        })
    return jsonify({'error': 'Invalid credentials'}), 401

@app.route('/api/live-news', methods=['GET'])
def api_live_news():
    limit = request.args.get('limit', 20, type=int)
    news = db.get_live_news(limit=limit)
    return jsonify({
        'status': 'success',
        'count': len(news),
        'articles': news
    })

@app.route('/api/trending', methods=['GET'])
def api_trending():
    stats = db.get_admin_stats()
    # Mock category values for Chart.js
    categories = {
        'Politics': random.randint(15, 30),
        'Technology': random.randint(10, 25),
        'Science': random.randint(5, 15),
        'World': random.randint(20, 40)
    }
    
    return jsonify({
        'status': 'success',
        'metrics': {
            'total_processed': stats['live_news_count'],
            'fake_detected': stats['live_fake_count'],
            'real_detected': max(0, stats['live_news_count'] - stats['live_fake_count']),
            'categories': categories,
            'source_distribution': stats['source_dist']
        }
    })

@app.route('/api/fact-check', methods=['GET'])
def api_fact_check():
    query = request.args.get('query', 'news')
    claims = news_fetcher.fetch_google_fact_check(query)
    return jsonify({
        'status': 'success',
        'query': query,
        'count': len(claims),
        'claims': claims
    })

@app.route('/api/realtime-detection', methods=['POST'])
def api_realtime_detection():
    data = request.get_json() or {}
    url = data.get('url', '')
    title = data.get('title', '')
    text = data.get('text', '')
    
    if not url and not title and not text:
        return jsonify({'error': 'Must supply URL, or both title and text.'}), 400
        
    domain = cred.extract_domain(url) if url else 'api.local'
    cred_details = cred.check_domain_credibility(domain)
    
    eval_res = nlp.evaluate_news_article(title, text, url=url or None, domain_category=cred_details['category'])
    if not eval_res:
        return jsonify({'error': 'Inference engine failed to evaluate'}), 500
        
    eval_res['domain_reputation'] = cred_details
    return jsonify(eval_res)

# --- APP STARTUP & TEARDOWN ---

@app.route('/api/predict', methods=['POST'])
def api_predict():
    # Maintain backwards compatibility
    return predict()

# WebSocket basic listeners
@socketio.on('connect')
def handle_connect():
    print("Client joined the live cyber intelligence dashboard Socket.io feed.")

@socketio.on('disconnect')
def handle_disconnect():
    print("Client disconnected from socket.")

if __name__ == '__main__':
    # Initialize background fetcher scheduler on startup
    news_fetcher.start_background_scheduler()
    
    # Run using socketio wrapper to support live channels
    port = int(os.getenv('PORT', 5000))
    socketio.run(app, host='0.0.0.0', debug=True, port=port, allow_unsafe_werkzeug=True)
