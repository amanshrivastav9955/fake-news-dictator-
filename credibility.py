import re
from urllib.parse import urlparse
import database as db

def extract_domain(url):
    """
    Extracts cleaner domain name (e.g., 'nytimes.com') from a URL.
    """
    if not url:
        return ""
    
    # Prepend http if not present to allow proper urlparse
    if not url.startswith(('http://', 'https://')):
        url = 'http://' + url
        
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        # Remove www.
        if domain.startswith('www.'):
            domain = domain[4:]
        # Remove port if exists
        if ':' in domain:
            domain = domain.split(':')[0]
        return domain
    except Exception:
        return ""

def check_domain_credibility(url_or_domain):
    """
    Looks up domain in source credibility database or applies TLD reputation heuristics.
    Returns: {
        'domain': str,
        'score': float (0-100),
        'category': str ('whitelist', 'blacklist', 'neutral'),
        'description': str
    }
    """
    if not url_or_domain:
        return {
            'domain': '',
            'score': 50.0,
            'category': 'neutral',
            'description': 'Unknown or missing domain.'
        }
        
    domain = extract_domain(url_or_domain) if '/' in url_or_domain or '.' not in url_or_domain else url_or_domain.lower().strip()
    domain = domain.replace('www.', '')
    
    # Query database for domain reputation
    db_res = db.get_domain_credibility(domain)
    if db_res:
        return {
            'domain': domain,
            'score': db_res['score'],
            'category': db_res['category'],
            'description': db_res['description']
        }
        
    # Heuristics for unknown domains
    tld = domain.split('.')[-1] if '.' in domain else ""
    
    if tld in ('gov', 'mil'):
        return {
            'domain': domain,
            'score': 95.0,
            'category': 'whitelist',
            'description': 'Official government or military publication domain.'
        }
    elif tld == 'edu':
        return {
            'domain': domain,
            'score': 90.0,
            'category': 'whitelist',
            'description': 'Verified academic institution domain.'
        }
    elif tld in ('info', 'xyz', 'online', 'buzz', 'club', 'click', 'icu', 'news'):
        return {
            'domain': domain,
            'score': 40.0,
            'category': 'neutral',
            'description': 'Custom or generic top-level domain frequently utilized in temporary blogs or clickbait websites.'
        }
    else:
        return {
            'domain': domain,
            'score': 55.0,
            'category': 'neutral',
            'description': 'Neutral domain without recorded credibility flags.'
        }
