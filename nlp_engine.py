import os
import re
import pickle
import numpy as np
import nltk
from datetime import datetime
from dotenv import load_dotenv

# Ensure NLTK corpus downloads
for package in ['stopwords', 'vader_lexicon', 'punkt', 'averaged_perceptron_tagger']:
    try:
        nltk.data.find(f'corpora/{package}')
    except LookupError:
        try:
            nltk.download(package, quiet=True)
        except Exception:
            pass

from nltk.corpus import stopwords
from nltk.stem import PorterStemmer
from nltk.sentiment.vader import SentimentIntensityAnalyzer

load_dotenv()

# --- CONVERSATIONAL AI ENGINES INITIALIZATION (v2.5) ---
groq_client = None
GROQ_API_KEY = os.getenv('GROQ_API_KEY')
if GROQ_API_KEY and GROQ_API_KEY.strip():
    try:
        from groq import Groq
        groq_client = Groq(api_key=GROQ_API_KEY)
        print("Groq Llama 3 Inference Client loaded successfully.")
    except Exception as e:
        print(f"WARNING: Groq Client failed to load. Error: {e}")

stop_words = set(stopwords.words('english'))
ps = PorterStemmer()


# Load sentiment analyzer with fallback
try:
    sia = SentimentIntensityAnalyzer()
except Exception:
    sia = None

# --- ML MODELS LOADING ---
MODELS_DIR = 'models'
vectorizer, lr_model, nb_model, pac_model = None, None, None, None

try:
    with open(os.path.join(MODELS_DIR, 'tfidf_vectorizer.pkl'), 'rb') as f:
        vectorizer = pickle.load(f)
    with open(os.path.join(MODELS_DIR, 'logistic_regression_model.pkl'), 'rb') as f:
        lr_model = pickle.load(f)
    with open(os.path.join(MODELS_DIR, 'naive_bayes_model.pkl'), 'rb') as f:
        nb_model = pickle.load(f)
    with open(os.path.join(MODELS_DIR, 'passive_aggressive_model.pkl'), 'rb') as f:
        pac_model = pickle.load(f)
    print("NLP ML models and vectorizer loaded successfully.")
except Exception as e:
    print(f"WARNING: NLP ML Models loading failed. Run train.py. Error: {e}")

# --- TRANSFORMER / BERT SYSTEM DYNAMIC HOOK ---
USE_TRANSFORMERS = os.getenv('USE_TRANSFORMERS', 'false').lower() == 'true'
transformers_pipeline = None

if USE_TRANSFORMERS:
    try:
        from transformers import pipeline
        # Load a fast, lightweight classification model
        transformers_pipeline = pipeline("text-classification", model="distilbert-base-uncased-finetuned-sst-2-english")
        print("DistilBERT model pipeline loaded successfully!")
    except Exception as e:
        print(f"WARNING: Failed to load DistilBERT. Fallback to classical ML ensemble. Error: {e}")

# --- TEXT PREPROCESSING ---
def preprocess_text(text):
    if not isinstance(text, str):
        return ""
    text = text.lower()
    text = re.sub(r'<[^>]*>', '', text)  # Strip HTML tags
    text = re.sub(r'[^a-z\s]', '', text) # Strip numbers and symbols
    words = text.split()
    cleaned = [ps.stem(word) for word in words if word not in stop_words]
    return ' '.join(cleaned)

# --- SENTIMENT ANALYSIS ---
def analyze_sentiment(text):
    """
    Returns polarity (-1 to 1) and subjectivity (0 to 1).
    """
    if not text:
        return 0.0, 0.0
        
    if sia:
        try:
            scores = sia.polarity_scores(text)
            polarity = scores['compound']
            # Heuristic subjectivity: more emotional text has higher positive+negative sentiment intensity
            subjectivity = min(1.0, (abs(scores['pos']) + abs(scores['neg'])) * 2.0)
            return polarity, subjectivity
        except Exception:
            pass
            
    # Fallback Lexicon Sentiment
    positive_words = {'good', 'great', 'excellent', 'amazing', 'happy', 'positive', 'success', 'trust', 'real', 'truth'}
    negative_words = {'bad', 'worst', 'fake', 'awful', 'terrible', 'sad', 'negative', 'failure', 'lie', 'deceit', 'untrue'}
    
    words = text.lower().split()
    pos_count = sum(1 for w in words if w in positive_words)
    neg_count = sum(1 for w in words if w in negative_words)
    total = pos_count + neg_count
    
    if total == 0:
        return 0.0, 0.1
        
    polarity = (pos_count - neg_count) / total
    subjectivity = min(1.0, total / len(words) * 10.0)
    return polarity, subjectivity

# --- KEYWORD & ENTITY EXTRACTION ---
def extract_keywords_and_entities(text, limit=8):
    """
    Extracts proper nouns (Entities) and high frequency keywords.
    """
    if not text:
        return [], []
        
    # Heuristic Named Entity Recognition (Capitalized phrases that are not start of sentence)
    sentences = re.split(r'[.!?]\s+', text)
    entities = set()
    for sentence in sentences:
        # Match capitalized word sequences, ignoring the very first word of the sentence
        words = sentence.split()
        if len(words) > 1:
            for idx in range(1, len(words)):
                word = words[idx]
                # Strip punctuation
                clean_word = re.sub(r'[^a-zA-Z]', '', word)
                if clean_word and clean_word[0].isupper() and clean_word.lower() not in stop_words:
                    # Look ahead to grab multi-word entities (e.g. "Donald Trump")
                    entity = clean_word
                    next_idx = idx + 1
                    while next_idx < len(words) and words[next_idx][0].isupper():
                        next_word = re.sub(r'[^a-zA-Z]', '', words[next_idx])
                        if next_word.lower() not in stop_words:
                            entity += " " + next_word
                        next_idx += 1
                    entities.add(entity)
                    
    # Frequency analysis for general Keywords (excluding stopwords)
    words = re.sub(r'[^a-zA-Z\s]', '', text.lower()).split()
    filtered = [w for w in words if w not in stop_words and len(w) > 3]
    
    freq = {}
    for w in filtered:
        freq[w] = freq.get(w, 0) + 1
        
    sorted_keywords = sorted(freq.items(), key=lambda x: x[1], reverse=True)
    keywords = [k[0] for k in sorted_keywords[:limit]]
    
    # Filter out entities that are too short and limit output
    clean_entities = sorted(list(entities), key=len, reverse=True)[:limit]
    
    return keywords, clean_entities

# --- EXPLAINABLE AI REASONING GENERATOR ---
def generate_ai_explanation(verdict, conf_score, sentiment_sub, domain_cat, text):
    """
    Generates a structured human-like breakdown of why the article was labeled FAKE or REAL.
    """
    explain = []
    
    if verdict == 'FAKE':
        explain.append("⚠️ **Sensationalism & Structural Flags:**")
        if sentiment_sub > 0.4:
            explain.append("• **Subjective Language:** The article contains highly subjective and emotive vocabulary, designed to elicit emotional responses rather than reporting neutral facts.")
        else:
            explain.append("• **Impersonal Context:** The writing exhibits standard characteristics of automated or highly structured biased phrasing.")
            
        # Capitalization / Exclamations check
        excl_count = text.count('!')
        caps_ratio = sum(1 for c in text if c.isupper()) / (len(text) + 1)
        if excl_count > 3:
            explain.append("• **Excessive Punctuation:** Usage of excessive exclamation marks ('!') is indicative of clickbait and unreliable publications.")
        if caps_ratio > 0.08:
            explain.append("• **Shouting Text:** Higher proportion of capitalized words is typical of sensationalist headlines designed to capture attention aggressively.")
            
        # Domain assessment
        if domain_cat == 'blacklist':
            explain.append("• **Source Trust Level:** The publishing domain resides on the system blacklist of satirical, conspiratorial, or discredited platforms.")
        elif domain_cat == 'neutral':
            explain.append("• **Source Trust Level:** The publishing source is unverified with neutral ratings. Cross-referencing is highly recommended.")
            
        explain.append(f"\n🔮 **Model Verdict Consensus:** The AI models parsed the text with a final confidence rating of **{conf_score:.2f}%** based on lexical word distributions matching known patterns of fake news repositories.")
    else:
        explain.append("✅ **Credibility Assessment:**")
        if sentiment_sub < 0.3:
            explain.append("• **Factual Style:** The content uses highly objective and reporting-oriented phrasing, a hallmark of professional journalism.")
        else:
            explain.append("• **Balanced Context:** Tone remains standard without containing excessive clickbait indicators.")
            
        if domain_cat == 'whitelist':
            explain.append("• **Source Trust Level:** The source resides on the system credibility whitelist (highly trusted news agencies).")
        else:
            explain.append("• **Source Trust Level:** The domain is generic or neutral with no active history of publishing fraudulent reporting.")
            
        explain.append(f"\n🔮 **Model Verdict Consensus:** The machine learning pipeline evaluated the article with a consensus confidence rating of **{conf_score:.2f}%**, mapping it strongly into standard factual reports.")
        
    return "\n".join(explain)

# --- ENGINE INFERENCE RUNNER ---
def evaluate_news_article(title, text, url=None, domain_category='neutral'):
    """
    Main evaluation pipeline: ML voting, Sentiment, NER, and Explanations.
    """
    if not title.strip() and not text.strip():
        return None
        
    combined = f"{title} {text}"
    cleaned = preprocess_text(combined)
    
    # Core calculations
    sentiment_pol, sentiment_sub = analyze_sentiment(text)
    keywords, entities = extract_keywords_and_entities(text)
    
    # 1. Classical ML voting predictions
    if not vectorizer or not lr_model or not nb_model or not pac_model:
        # MOCKED Predictions if models are not trained yet
        lr_pred = nb_pred = pac_pred = 1
        lr_conf = nb_conf = pac_conf = 80.0
    else:
        vector = vectorizer.transform([cleaned])
        
        # Logistic Regression
        lr_pred = int(lr_model.predict(vector)[0])
        lr_probs = lr_model.predict_proba(vector)[0]
        lr_conf = float(lr_probs[1] if lr_pred == 1 else lr_probs[0]) * 100
        
        # Naive Bayes
        nb_pred = int(nb_model.predict(vector)[0])
        nb_probs = nb_model.predict_proba(vector)[0]
        nb_conf = float(nb_probs[1] if nb_pred == 1 else nb_probs[0]) * 100
        
        # Passive Aggressive (decision_function + sigmoid calibration)
        pac_pred = int(pac_model.predict(vector)[0])
        pac_decision = pac_model.decision_function(vector)[0]
        prob_real = 1.0 / (1.0 + np.exp(-pac_decision))
        pac_probs = [1.0 - prob_real, prob_real]
        pac_conf = float(pac_probs[1] if pac_pred == 1 else pac_probs[0]) * 100
        
    # Majority Voting
    predictions = [lr_pred, nb_pred, pac_pred]
    final_pred_val = 1 if predictions.count(1) >= 2 else 0
    final_verdict = "REAL" if final_pred_val == 1 else "FAKE"
    
    # Calculate Average Confidence Score
    avg_conf = (lr_conf + nb_conf + pac_conf) / 3.0
    
    # 2. Transformer prediction (if enabled)
    distilbert_result = None
    if USE_TRANSFORMERS and transformers_pipeline:
        try:
            # We classify the first 512 characters to fit model restrictions safely
            tf_res = transformers_pipeline(combined[:512])[0]
            label = tf_res['label'].upper() # e.g. 'POSITIVE' (can mean true/factual in sentiment)
            score = tf_res['score'] * 100
            
            # Map sentiment labels to factuality
            mapped_pred = "REAL" if label == "POSITIVE" else "FAKE"
            distilbert_result = {
                'prediction': mapped_pred,
                'confidence': round(score, 2)
            }
        except Exception as e:
            print(f"Transformers pipeline failed during evaluation: {e}")
            
    # 3. Explainable AI explanation
    ai_explanation = generate_ai_explanation(final_verdict, avg_conf, sentiment_sub, domain_category, text)
    
    # Identify suspicious keywords (keywords matching typical clickbait expressions or spam words)
    suspicious_terms = ['secret', 'shocking', 'unbelievable', 'conspiracy', 'revealed', 'exposed', 'miracle', 'warning', 'scandal', 'banned']
    matched_suspicious = [w for w in keywords if w in suspicious_terms or len(w) > 9] # Flag long convoluted words too
    
    return {
        'verdict': final_verdict,
        'confidence': round(avg_conf, 2),
        'sentiment_polarity': round(sentiment_pol, 2),
        'sentiment_subjectivity': round(sentiment_sub, 2),
        'keywords': keywords,
        'entities': entities,
        'suspicious_keywords': matched_suspicious[:4],
        'explanation': ai_explanation,
        'timestamp': datetime.now().isoformat(),
        'distilbert': distilbert_result,
        'model_wise': {
            'logistic_regression': {
                'prediction': "REAL" if lr_pred == 1 else "FAKE",
                'confidence': round(lr_conf, 2)
            },
            'naive_bayes': {
                'prediction': "REAL" if nb_pred == 1 else "FAKE",
                'confidence': round(nb_conf, 2)
            },
            'passive_aggressive': {
                'prediction': "REAL" if pac_pred == 1 else "FAKE",
                'confidence': round(pac_conf, 2)
            }
        }
    }

# --- REAL-TIME AI INTEGRATION FUNCTIONS (v2.5) ---

def generate_ai_chat_response(messages, stream=False):
    if not groq_client:
        # Fallback Mock Response for offline mode
        class MockChoiceMessage:
            def __init__(self, content):
                self.content = content
        class MockChoice:
            def __init__(self, content):
                self.message = MockChoiceMessage(content)
                self.delta = MockChoiceMessage(content)
        class MockResponse:
            def __init__(self, content):
                self.choices = [MockChoice(content)]
        
        offline_response = (
            "⚠️ **VERIFACT AI - Offline Mode:** The Groq AI API client is not initialized. "
            "Please ensure `GROQ_API_KEY` is correctly configured in your `.env` file.\n\n"
            "**Misinformation Spotting Quick Guide:**\n"
            "- **Lexical Traps:** Look out for clickbait titles with shouting capitalization (\"SHOCKING\", \"MUST SEE\").\n"
            "- **Emotional Language:** Verify if VADER sentiment subjectivity is high, indicating emotional appeal over objective reporting.\n"
            "- **Source reputation:** Always cross-reference news with whitelist registries like Reuters or AP News."
        )
        if stream:
            def mock_stream_generator():
                for word in offline_response.split(" "):
                    yield MockResponse(word + " ")
                    import time
                    time.sleep(0.03)
            return mock_stream_generator()
        return MockResponse(offline_response)
        
    system_prompt = (
        "You are VERIFACT AI, an advanced cyber-intelligence fake news investigation assistant "
        "trained to analyze misinformation, propaganda, clickbait, emotional manipulation, and suspicious media patterns.\n\n"
        "Your role:\n"
        "- Explain fake news detection clearly and help users understand misinformation.\n"
        "- Provide trustworthy reasoning and analyze news articles professionally.\n"
        "- Detect bias and propaganda.\n"
        "- Suggest trusted references.\n\n"
        "Always provide neutral, professional, and human-readable responses. Structure responses in beautiful Markdown format (with bold headers, lists, and quotes where appropriate) to be easy to read."
    )
    
    formatted_messages = []
    if not any(m.get('role') == 'system' for m in messages):
        formatted_messages.append({"role": "system", "content": system_prompt})
    formatted_messages.extend(messages)
    
    try:
        response = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=formatted_messages,
            stream=stream,
            temperature=0.2,
            max_tokens=2048
        )
        return response
    except Exception as e:
        print(f"Error calling Groq API: {e}")
        # Fallback on exception
        class MockChoiceMessage:
            def __init__(self, content):
                self.content = content
        class MockChoice:
            def __init__(self, content):
                self.message = MockChoiceMessage(content)
        class MockResponse:
            def __init__(self, content):
                self.choices = [MockChoice(content)]
        return MockResponse(f"⚠️ **Error contacting AI Brain Center:** {str(e)}")

def analyze_news_with_llm(title, text, url=None, domain='unknown', ml_verdict='UNKNOWN', ml_confidence=50.0, sentiment_pol=0.0, sentiment_sub=0.0, entities=None, domain_category='neutral'):
    if not entities:
        entities = []
        
    prompt = (
        f"You are VERIFACT AI, an advanced misinformation investigation assistant. "
        f"Generate a comprehensive, high-fidelity cyber-intelligence analysis report for the following news item:\n\n"
        f"ARTICLE METRICS:\n"
        f"- Title: \"{title}\"\n"
        f"- Domain: {domain} (Reputation Category: {domain_category})\n"
        f"- URL: {url or 'No URL submitted'}\n"
        f"- ML Consensus Verdict: {ml_verdict}\n"
        f"- ML Consensus Confidence: {ml_confidence:.2f}%\n"
        f"- Sentiment Polarity: {sentiment_pol:.2f} (Scale: -1.0 to 1.0)\n"
        f"- Sentiment Subjectivity: {sentiment_sub:.2f} (Scale: 0.0 to 1.0, higher means more emotional)\n"
        f"- Key Extracted Entities: {', '.join(entities) if entities else 'None detected'}\n\n"
        f"ARTICLE TEXT:\n"
        f"\"\"\"\n{text[:3000]}\n\"\"\"\n\n"
        f"Please structure your report in markdown with the following clear sections:\n"
        f"1. **🔍 Executive Verdict & Trust Score:** A brief assessment and a numerical Trust Score (0-100%) based on the metrics and text content.\n"
        f"2. **⚠️ Why It May Be Fake / Misinformation Indicators:** Explain specific structural clickbait, shouting headers, emotional manipulation, or biased lexical root alignments.\n"
        f"3. **📊 Bias & Emotional Manipulation Analysis:** Rate the subjectivity level and emotional tone (e.g. fear-mongering, partisan bias, fake hype).\n"
        f"4. **🛡️ Propaganda Techniques Detected:** Flag any logical fallacies, cherry-picking, appeal to authority, or framing techniques found.\n"
        f"5. **📰 Source & Domain Reputation:** Explain domain credibility whitelists/blacklists and tell the user if the site is a known satire, conspiracy, or reputable source.\n"
        f"6. **🔎 Suggested Verification References:** Recommend trusted sources (e.g., Reuters, AP News, fact-check sites) to verify this news item.\n\n"
        f"Keep the analysis highly objective, professional, and clear."
    )
    
    messages = [
        {"role": "user", "content": prompt}
    ]
    
    try:
        response = generate_ai_chat_response(messages, stream=False)
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error in LLM news analysis: {e}")
        # Default fallback string using basic template
        return generate_ai_explanation(ml_verdict, ml_confidence, sentiment_sub, domain_category, text)

    

