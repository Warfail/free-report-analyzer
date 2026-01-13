import nltk
import re
from collections import Counter
import json

# Download NLTK data
try:
    nltk.data.find('tokenizers/punkt')
except:
    nltk.download('punkt', quiet=True)
    nltk.download('stopwords', quiet=True)

from nltk.tokenize import sent_tokenize, word_tokenize
from nltk.corpus import stopwords

class SimpleAIAnalyzer:
    def __init__(self):
        self.stop_words = set(stopwords.words('english'))
        
        # Keywords for analysis
        self.good_words = ['good', 'great', 'excellent', 'success', 'complete', 
                          'happy', 'progress', 'achieved', 'improved', 'working']
        self.bad_words = ['bad', 'poor', 'failed', 'issue', 'problem', 
                         'difficult', 'slow', 'broken', 'error', 'blocked']
        
        self.accomplishment_words = ['completed', 'finished', 'achieved', 'fixed',
                                    'resolved', 'deployed', 'implemented', 'launched']
        
        self.problem_words = ['issue', 'problem', 'error', 'bug', 'failed',
                             'blocked', 'delayed', 'stuck', 'broken']
        
        self.action_words = ['need', 'must', 'should', 'will', 'plan',
                            'next', 'tomorrow', 'schedule', 'assign']

    def analyze(self, text):
        """Simple AI analysis - returns dictionary with insights"""


        
        
        # Basic stats
        words = text.split()
        sentences = sent_tokenize(text)
        
        # Sentiment analysis
        text_lower = text.lower()
        good_count = sum(1 for word in self.good_words if word in text_lower)
        bad_count = sum(1 for word in self.bad_words if word in text_lower)
        
        total = good_count + bad_count
        if total > 0:
            sentiment_score = (good_count - bad_count) / total
        else:
            sentiment_score = 0
        
        # Determine sentiment label
        if sentiment_score > 0.2:
            sentiment = "positive"
        elif sentiment_score < -0.2:
            sentiment = "negative"
        else:
            sentiment = "neutral"
        
        # Find accomplishments
        accomplishments = []
        for sentence in sentences:
            if any(word in sentence.lower() for word in self.accomplishment_words):
                if len(sentence) > 10:  # Avoid very short sentences
                    accomplishments.append(sentence.strip())
        
        # Find problems
        problems = []
        for sentence in sentences:
            if any(word in sentence.lower() for word in self.problem_words):
                if len(sentence) > 10:
                    problems.append(sentence.strip())
        
        # Find action items
        actions = []
        for sentence in sentences:
            if any(word in sentence.lower() for word in self.action_words):
                if len(sentence) > 10:
                    actions.append(sentence.strip())
        
        # Find topics (most frequent words, excluding common words)
        all_words = [w.lower() for w in words if w.isalpha() and len(w) > 3]
        filtered_words = [w for w in all_words if w not in self.stop_words]
        
        common_words = {'report', 'daily', 'team', 'work', 'project', 'today'}
        word_counts = Counter(filtered_words)
        
        topics = []
        for word, count in word_counts.most_common(10):
            if word not in common_words and count > 1:
                topics.append(word)
        
        # Generate smart summary (first, middle, last sentences)
        summary = ""
        if len(sentences) >= 3:
            summary = sentences[0] + " " + sentences[len(sentences)//2] + " " + sentences[-1]
        elif len(sentences) > 0:
            summary = " ".join(sentences)
        
        # Return analysis results
        return {
            "basic_stats": {
                "word_count": len(words),
                "sentence_count": len(sentences),
                "avg_sentence_length": round(len(words) / max(len(sentences), 1), 1)
            },
            "sentiment": {
                "score": round(sentiment_score, 2),
                "label": sentiment,
                "positive_words": good_count,
                "negative_words": bad_count
            },
            "content_analysis": {
                "accomplishments": accomplishments[:3],  # Top 3
                "problems": problems[:3],
                "action_items": actions[:3]
            },
            "topics": topics[:5],  # Top 5 topics
            "summary": summary[:300]  # First 300 chars
        }

# Create global instance
ai_analyzer = SimpleAIAnalyzer()