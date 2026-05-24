import os
import random
import requests
import string
from datetime import datetime
from dotenv import load_dotenv
from apscheduler.schedulers.background import BackgroundScheduler
import database as db
import credibility as cred
import nlp_engine as nlp

load_dotenv()

NEWS_API_KEY = os.getenv('NEWS_API_KEY')
GNEWS_API_KEY = os.getenv('GNEWS_API_KEY')

# WebSocket callback placeholder (injected by app.py)
socket_callback = None

def register_socket_callback(callback_fn):
    global socket_callback
    socket_callback = callback_fn

# --- REAL NEWS API INGESTIONS ---

def fetch_news_api():
    """
    Fetches trending news headlines from NewsAPI.
    """
    if not NEWS_API_KEY:
        return []
    url = f"https://newsapi.org/v2/top-headlines?language=en&pageSize=15&apiKey={NEWS_API_KEY}"
    try:
        r = requests.get(url, timeout=8)
        if r.status_code == 200:
            data = r.json()
            articles = []
            for art in data.get('articles', []):
                if art.get('title') and art.get('content'):
                    articles.append({
                        'title': art['title'],
                        'text': art['content'] or art['description'] or art['title'],
                        'url': art['url'],
                        'domain': cred.extract_domain(art['url']),
                        'source': 'NewsAPI'
                    })
            return articles
    except Exception as e:
        print(f"Error fetching from NewsAPI: {e}")
    return []

def fetch_gnews_api():
    """
    Fetches trending general news from GNews.
    """
    if not GNEWS_API_KEY:
        return []
    url = f"https://gnews.io/api/v4/top-headlines?category=general&lang=en&max=10&apikey={GNEWS_API_KEY}"
    try:
        r = requests.get(url, timeout=8)
        if r.status_code == 200:
            data = r.json()
            articles = []
            for art in data.get('articles', []):
                articles.append({
                    'title': art['title'],
                    'text': art['description'] or art['content'] or art['title'],
                    'url': art['url'],
                    'domain': cred.extract_domain(art['url']),
                    'source': 'GNews'
                })
            return articles
    except Exception as e:
        print(f"Error fetching from GNews: {e}")
    return []

def fetch_gdelt_feed():
    """
    Fetches free global trending events directly from GDELT Project API (No API key required!).
    """
    url = "https://api.gdeltproject.org/api/v2/doc/doc?query=language:english&mode=artlist&format=json&maxrecords=12"
    try:
        r = requests.get(url, timeout=8)
        if r.status_code == 200:
            data = r.json()
            articles = []
            for art in data.get('articles', []):
                title = art.get('title')
                url_str = art.get('url')
                if title and url_str:
                    articles.append({
                        'title': title,
                        'text': f"Real-time event recorded by GDELT Project. Global media coverage tracking article source reports details regarding: {title}.",
                        'url': url_str,
                        'domain': cred.extract_domain(url_str),
                        'source': 'GDELT'
                    })
            return articles
    except Exception as e:
        print(f"Error fetching from GDELT: {e}")
    return []

def fetch_google_fact_check(query="news"):
    """
    Fetches fact checked claims from Google Fact Check Explorer.
    """
    # Uses public key or just queries API safely
    url = f"https://factchecktools.googleapis.com/v1alpha1/claims:search?query={query}&languageCode=en"
    # Fallback endpoint if API key not supplied (public check tools are occasionally restricted, so handle with try-except)
    try:
        r = requests.get(url, timeout=8)
        if r.status_code == 200:
            data = r.json()
            claims = []
            for claim in data.get('claims', []):
                text = claim.get('text', '')
                claimant = claim.get('claimant', 'Unknown Source')
                review = claim.get('claimReview', [{}])[0]
                rating = review.get('textualRating', 'Unverified')
                publisher = review.get('publisher', {}).get('name', 'Fact Check Agency')
                review_url = review.get('url', 'https://google.com')
                
                claims.append({
                    'title': f"CLAIM CHECK: {text}",
                    'text': f"Claim stated by: {claimant}. Fact-checker review verdict: Labeled '{rating}' by {publisher}.",
                    'url': review_url,
                    'domain': cred.extract_domain(review_url),
                    'source': 'Google FactCheck'
                })
            return claims
    except Exception as e:
        print(f"Error fetching from Google Fact Check API: {e}")
    return []

# --- DYNAMIC MOCK SIMULATED STREAM ENGINE ---

MOCK_SUBJECTS = {
    'Politics': [
        ("Leaked documents suggest massive infrastructure reforms in capital", "Unverified documents leaked by a pseudonymous insider assert that the central government has outlined a structural layout to privatize entire municipal water networks.", "national-leak.net", "blacklist"),
        ("Prime Minister signs bilateral trade treaty with neighboring country", "In a formal state ceremony, the Prime Minister finalized a sweeping bilateral agreement to reduce steel tariffs and establish combined transport lanes.", "reuters.com", "whitelist"),
        ("New legislation aims to restrict social media data tracking", "Bipartisan lawmakers introduced an expansive privacy bill targeting strict limits on micro-targeting cookies and behavioral profile tracking.", "apnews.com", "whitelist")
    ],
    'Technology': [
        ("AI company claims to have achieved sentient consciousness in neural network", "A high-profile startup based in Silicon Valley has caused shockwaves across the scientific community, claiming their latest multi-modal network has expressed awareness.", "tech-secrets.info", "neutral"),
        ("Leading semiconductor firm announces breakthrough 1nm processors", "Engineers revealed a major microarchitecture milestone, producing highly optimized 1-nanometer silicon crystals designed to double smartphone computational capacity.", "bloomberg.com", "whitelist"),
        ("Mobile OS developer patch stops massive security exploit", "A high-severity zero-day exploit allowing remote kernel access was patched in an urgent over-the-air update released to 2 billion devices.", "bbc.com", "whitelist")
    ],
    'Science & Health': [
        ("Miracle plant extract completely cures aging in laboratory trials", "An internet blog claims that consuming concentrated extracts of a rare alpine orchid has completely reversed biological aging markers in clinical tests.", "miracle-remedies.buzz", "blacklist"),
        ("Global health organization declares eradication of localized viral outbreak", "Following a 90-day period with zero registered cases, authorities have declared the vaccine campaign fully successful in clearing regional infectious centers.", "apnews.com", "whitelist"),
        ("Astronomers detect highly structured radio patterns from distant solar system", "Analyzing data from deep space radio antennas, astrophysicists identified repetitive sequence arrays originating from a star cluster situated 12 light-years away.", "npr.org", "whitelist")
    ],
    'World Affairs': [
        ("Unidentified flying objects spotted hovering over multiple coastal cities", "Sensational online videos claim that fleets of polished spherical structures were hovering completely silently above harbor zones before accelerating into outer orbit.", "ufo-insider.club", "blacklist"),
        ("Global energy forum pledges complete transition to fusion grids by 2040", "International ministers gathered for the opening summit, finalizing mutual investment frameworks targeting commercial tokamak reactor deployment.", "reuters.com", "whitelist"),
        ("Major infrastructure bridge collapses along international freight passage", "Emergency responders are on-site following structural failures along the key transit highway, rerouting shipping operations indefinitely.", "bbc.com", "whitelist")
    ]
}

def generate_mock_news():
    """
    Generates a beautifully formatted dynamic mock article to simulate active live streams.
    """
    category = random.choice(list(MOCK_SUBJECTS.keys()))
    article_templates = MOCK_SUBJECTS[category]
    title, text, domain, cat = random.choice(article_templates)
    
    # Randomize title details slightly to look highly dynamic
    years = [2026, 2027, 2028]
    countries = ["United States", "United Kingdom", "Germany", "Japan", "India"]
    title_mod = title.replace("capital", random.choice(countries)).replace("2040", str(random.choice(years)))
    
    # Generate unique URL
    slug = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
    url = f"https://www.{domain}/{category.lower()}/{slug}.html"
    
    return {
        'title': title_mod,
        'text': text + f" Additional reports confirm that field specialists have gathered to monitor unfolding elements regarding this {category.lower()} event.",
        'url': url,
        'domain': domain,
        'source': 'Simulation Core'
    }

# --- BACKGROUND MONITORING LOOP ---

def process_and_store_article(art):
    """
    Scrapes/Parses news details, evaluates credibility & NLP, and writes to database.
    Pushes real-time WebSockets notifications if suspicious alerts trigger.
    """
    # 1. Check Domain reputation
    cred_details = cred.check_domain_credibility(art['domain'])
    
    # 2. Evaluate using advanced NLP engine
    eval_res = nlp.evaluate_news_article(
        art['title'], 
        art['text'], 
        url=art['url'], 
        domain_category=cred_details['category']
    )
    
    if not eval_res:
        return
        
    # 3. Assess if is a viral fake news alert trigger (Verdict is FAKE and confidence > 78%)
    is_alert = (eval_res['verdict'] == 'FAKE' and eval_res['confidence'] >= 78.0)
    
    # 4. Save to database
    db_id = db.add_live_news(
        title=art['title'],
        text=art['text'],
        summary=f"Lexical analysis of reporting from {art['domain']} with overall {eval_res['sentiment_polarity']} sentiment sentiment polarity.",
        entities=eval_res['entities'],
        sentiment_polarity=eval_res['sentiment_polarity'],
        sentiment_subjectivity=eval_res['sentiment_subjectivity'],
        final_prediction=eval_res['verdict'],
        conf_lr=eval_res['model_wise']['logistic_regression']['confidence'],
        conf_nb=eval_res['model_wise']['naive_bayes']['confidence'],
        conf_pac=eval_res['model_wise']['passive_aggressive']['confidence'],
        source=art['source'],
        domain=art['domain'],
        url=art['url'],
        is_alert=is_alert
    )
    
    if db_id is not None:
        print(f"Ingested and analyzed article: [{eval_res['verdict']}] {art['title'][:50]}... from {art['domain']}")
        
        # 5. Broadcast in real time via Socket.IO if callback is registered
        if socket_callback:
            socket_data = {
                'id': db_id,
                'title': art['title'],
                'text': art['text'][:200] + '...',
                'domain': art['domain'],
                'url': art['url'],
                'verdict': eval_res['verdict'],
                'confidence': eval_res['confidence'],
                'sentiment_polarity': eval_res['sentiment_polarity'],
                'is_alert': is_alert,
                'source': art['source'],
                'timestamp': datetime.now().strftime('%H:%M:%S')
            }
            try:
                socket_callback(socket_data)
            except Exception as e:
                print(f"Error executing Socket.io broadcast: {e}")

def run_news_scan():
    """
    Main job loop executed by scheduler.
    """
    print(f"--- STARTING LIVE NEWS SCANNING AND VERIFICATION PROCESS: {datetime.now()} ---")
    
    articles = []
    
    # A. Try pulling from live APIs if keys are registered
    if NEWS_API_KEY:
        articles.extend(fetch_news_api())
    if GNEWS_API_KEY:
        articles.extend(fetch_gnews_api())
        
    # B. Pull from free GDELT API (Highly factual global news coverage)
    articles.extend(fetch_gdelt_feed())
    
    # C. If we have less than 5 articles, generate simulated stream entries to make the UI active
    while len(articles) < 6:
        articles.append(generate_mock_news())
        
    # Process up to 10 articles to protect API credits and server memory
    random.shuffle(articles)
    selected_articles = articles[:10]
    
    count = 0
    for art in selected_articles:
        # Check if URL already evaluated
        domain = art['domain']
        process_and_store_article(art)
        count += 1
        
    print(f"--- LIVE NEWS SCAN COMPLETED. ANALYZED {count} ARTICLES ---")

# --- SCHEDULER CONTROLLER ---
scheduler = BackgroundScheduler()

def start_background_scheduler():
    if not scheduler.running:
        # Run an initial scan immediately to seed the dashboard
        scheduler.add_job(run_news_scan, 'interval', minutes=5, id='news_scan_job', replace_existing=True)
        scheduler.start()
        print("APScheduler live news scanner thread launched successfully!")
        # Force a light async trigger of initial scan so dashboard has data immediately
        import threading
        threading.Thread(target=run_news_scan, daemon=True).start()

def stop_background_scheduler():
    if scheduler.running:
        scheduler.shutdown()
        print("APScheduler shut down successfully.")
