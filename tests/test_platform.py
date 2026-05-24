import unittest
import os
import sys

# Ensure parent directory is in path to allow imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import credibility as cred
import nlp_engine as nlp

class TestVerifactPlatform(unittest.TestCase):
    
    def test_domain_extraction(self):
        """
        Verify domain extraction logic.
        """
        self.assertEqual(cred.extract_domain("https://www.reuters.com/world/news-123.html"), "reuters.com")
        self.assertEqual(cred.extract_domain("http://apnews.com/politics"), "apnews.com")
        self.assertEqual(cred.extract_domain("http://www.sub.blogging.xyz:8080/path"), "sub.blogging.xyz")
        self.assertEqual(cred.extract_domain(""), "")

    def test_domain_credibility_heuristics(self):
        """
        Verify that whitelists, blacklists, and TLD heuristics are evaluated.
        """
        # Whitelist checks
        res_wl = cred.check_domain_credibility("reuters.com")
        self.assertEqual(res_wl['category'], 'whitelist')
        self.assertGreaterEqual(res_wl['score'], 90.0)

        # Blacklist checks
        res_bl = cred.check_domain_credibility("theonion.com")
        self.assertEqual(res_bl['category'], 'blacklist')
        self.assertLessEqual(res_bl['score'], 20.0)

        # TLD Heuristics checks
        res_edu = cred.check_domain_credibility("harvard.edu")
        self.assertEqual(res_edu['category'], 'whitelist')
        self.assertEqual(res_edu['score'], 90.0)
        
        res_xyz = cred.check_domain_credibility("suspicious.xyz")
        self.assertEqual(res_xyz['score'], 40.0)

    def test_nlp_sentiment_analysis(self):
        """
        Verify sentiment analysis is returning correct polarity/subjectivity ranges.
        """
        text = "This is a wonderful, great, happy and highly successful day!"
        pol, sub = nlp.analyze_sentiment(text)
        self.assertGreater(pol, 0.0)
        self.assertGreater(sub, 0.0)
        
        text_neg = "This is a terrible, worst, awful failure and deceit!"
        pol_neg, sub_neg = nlp.analyze_sentiment(text_neg)
        self.assertLess(pol_neg, 0.0)

    def test_keyword_and_entity_extraction(self):
        """
        Verify that proper nouns (Entities) and frequent keywords are extracted.
        """
        text = "Donald Trump traveled to the White House to discuss foreign policy. Russia and the United States held formal sessions."
        keywords, entities = nlp.extract_keywords_and_entities(text)
        
        # Check that proper capitalized words are captured as entities
        self.assertTrue(any("Donald" in e or "Trump" in e for e in entities))
        self.assertTrue(any("White House" in e for e in entities))
        
        # Check that standard stop words are filtered out of keywords
        self.assertNotIn("the", keywords)
        self.assertNotIn("to", keywords)

    def test_ai_consensus_inference(self):
        """
        Verify final mult-model consensus prediction format.
        """
        title = "Severe Warning regarding dynamic global matters"
        text = "Reports declare that severe events are unfolding right now. Click here to read shocking revealed facts!"
        
        eval_res = nlp.evaluate_news_article(title, text, domain_category='neutral')
        self.assertIsNotNone(eval_res)
        self.assertIn(eval_res['verdict'], ['REAL', 'FAKE'])
        self.assertGreaterEqual(eval_res['confidence'], 0.0)
        self.assertIn('logistic_regression', eval_res['model_wise'])
        self.assertIn('explanation', eval_res)
        self.assertTrue(len(eval_res['keywords']) > 0)

if __name__ == '__main__':
    unittest.main()
