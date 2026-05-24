import os
import re
import json
import pickle
import time
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import nltk
from nltk.corpus import stopwords
from nltk.stem import PorterStemmer
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.naive_bayes import MultinomialNB
from sklearn.linear_model import PassiveAggressiveClassifier
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, confusion_matrix, ConfusionMatrixDisplay

# Ensure NLTK stopwords are downloaded
print("Checking NLTK resources...")
try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords')

# Define paths
MODELS_DIR = 'models'
STATIC_DIR = 'static'
GRAPHS_DIR = os.path.join(STATIC_DIR, 'graphs')
DATA_DIR = os.path.join(STATIC_DIR, 'data')

# Create necessary directories
os.makedirs(MODELS_DIR, exist_ok=True)
os.makedirs(GRAPHS_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

# Initialize preprocessor helpers
stop_words = set(stopwords.words('english'))
ps = PorterStemmer()

def preprocess_text(text):
    if not isinstance(text, str):
        return ""
    # Convert to lowercase
    text = text.lower()
    # Remove HTML tags and non-alphabetic chars
    text = re.sub(r'<[^>]*>', '', text)
    text = re.sub(r'[^a-z\s]', '', text)
    # Tokenize and remove stopwords and stem
    words = text.split()
    cleaned_words = [ps.stem(word) for word in words if word not in stop_words]
    return ' '.join(cleaned_words)

def main():
    print("Loading datasets...")
    # Read CSVs
    df_true = pd.read_csv('True.csv', low_memory=False)
    df_fake = pd.read_csv('Fake.csv', low_memory=False)
    
    # Keep only required columns and add label (1 for Real, 0 for Fake)
    df_true = df_true[['title', 'text']].copy()
    df_true['label'] = 1
    
    df_fake = df_fake[['title', 'text']].copy()
    df_fake['label'] = 0
    
    print(f"Loaded {len(df_true)} true articles and {len(df_fake)} fake articles.")
    
    # Balance the dataset (take a subset of 10,000 from each for faster execution & efficiency)
    sample_size = min(10000, len(df_true), len(df_fake))
    print(f"Sampling {sample_size} articles from each category for a balanced dataset...")
    df_true_sampled = df_true.sample(n=sample_size, random_state=42)
    df_fake_sampled = df_fake.sample(n=sample_size, random_state=42)
    
    df = pd.concat([df_true_sampled, df_fake_sampled], ignore_index=True)
    
    # Combine title and text to get more context
    print("Combining title and text...")
    df['content'] = df['title'].fillna('') + ' ' + df['text'].fillna('')
    
    # Preprocess text
    print("Preprocessing text (this might take a minute)...")
    start_time = time.time()
    df['cleaned_content'] = df['content'].apply(preprocess_text)
    print(f"Preprocessing completed in {time.time() - start_time:.2f} seconds.")
    
    # Split into train and test sets (80% train, 20% test)
    X = df['cleaned_content']
    y = df['label']
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    
    # TF-IDF Vectorization
    print("Fitting TF-IDF Vectorizer...")
    vectorizer = TfidfVectorizer(max_features=5000, ngram_range=(1, 2))
    X_train_vectorized = vectorizer.fit_transform(X_train)
    X_test_vectorized = vectorizer.transform(X_test)
    
    # Save Vectorizer
    with open(os.path.join(MODELS_DIR, 'tfidf_vectorizer.pkl'), 'wb') as f:
        pickle.dump(vectorizer, f)
    print("TF-IDF Vectorizer saved.")
    
    # Initialize models
    models = {
        'logistic_regression': LogisticRegression(max_iter=1000, random_state=42),
        'naive_bayes': MultinomialNB(),
        'passive_aggressive': PassiveAggressiveClassifier(max_iter=1000, random_state=42)
    }
    
    metrics_summary = {}
    
    for name, model in models.items():
        print(f"Training {name}...")
        t0 = time.time()
        model.fit(X_train_vectorized, y_train)
        training_time = time.time() - t0
        
        # Predict
        y_pred = model.predict(X_test_vectorized)
        
        # Evaluate
        acc = accuracy_score(y_test, y_pred)
        precision, recall, f1, _ = precision_recall_fscore_support(y_test, y_pred, average='binary')
        
        print(f"{name} Results: Accuracy: {acc:.4f}, Precision: {precision:.4f}, Recall: {recall:.4f}, F1: {f1:.4f}")
        
        metrics_summary[name] = {
            'accuracy': float(acc),
            'precision': float(precision),
            'recall': float(recall),
            'f1_score': float(f1),
            'training_time_seconds': float(training_time)
        }
        
        # Save model pickle
        with open(os.path.join(MODELS_DIR, f'{name}_model.pkl'), 'wb') as f:
            pickle.dump(model, f)
            
        # Plot and save confusion matrix
        cm = confusion_matrix(y_test, y_pred)
        plt.figure(figsize=(6, 5))
        disp = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=['FAKE', 'REAL'])
        disp.plot(cmap='Blues', values_format='d')
        plt.title(f'Confusion Matrix - {name.replace("_", " ").title()}')
        plt.tight_layout()
        plt.savefig(os.path.join(GRAPHS_DIR, f'confusion_matrix_{name}.png'))
        plt.close()
        
    # Save metrics JSON
    with open(os.path.join(DATA_DIR, 'metrics.json'), 'w') as f:
        json.dump(metrics_summary, f, indent=4)
    print("Model metrics saved to static/data/metrics.json.")
    
    # Save overall accuracy comparison graph
    model_names = [n.replace('_', ' ').title() for n in metrics_summary.keys()]
    accuracies = [m['accuracy'] * 100 for m in metrics_summary.values()]
    
    plt.figure(figsize=(8, 5))
    colors = ['#5c6bc0', '#26a69a', '#ec407a']
    bars = plt.bar(model_names, accuracies, color=colors, width=0.5)
    plt.ylabel('Accuracy (%)')
    plt.title('Model Accuracy Comparison')
    plt.ylim(80, 100)
    for bar in bars:
        yval = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2.0, yval + 0.5, f"{yval:.2f}%", ha='center', va='bottom', fontweight='bold')
    
    plt.tight_layout()
    plt.savefig(os.path.join(GRAPHS_DIR, 'accuracy_comparison.png'))
    plt.close()
    print("Comparison graph saved to static/graphs/accuracy_comparison.png.")
    print("All models trained and assets successfully saved!")

if __name__ == "__main__":
    main()
