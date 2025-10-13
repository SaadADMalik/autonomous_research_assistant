"""
Simple spell checker for common research terms.
"""
import re
from typing import Dict, List

class SpellChecker:
    def __init__(self):
        # Common medical/scientific term corrections
        self.corrections = {
            # Medical terms
            "diebetes": "diabetes",
            "diabetees": "diabetes", 
            "diabeetes": "diabetes",
            "diabets": "diabetes",
            "diabetis": "diabetes",
            
            # Scientific terms
            "quantam": "quantum",
            "quantem": "quantum",
            "qantum": "quantum",
            "quantim": "quantum",
            
            "artifical": "artificial",
            "artifical": "artificial",
            "artficial": "artificial",
            "artificail": "artificial",
            
            "machien": "machine",
            "machin": "machine",
            "mashine": "machine",
            
            "algoritm": "algorithm",
            "algorythm": "algorithm",
            "algorithim": "algorithm",
            
            "computor": "computer",
            "compter": "computer",
            "computre": "computer",
            
            "techology": "technology",
            "tecnology": "technology",
            "technolgy": "technology",
            
            "cancor": "cancer",
            "canser": "cancer",
            "cancre": "cancer",
            
            "climat": "climate",
            "climte": "climate",
            "clmate": "climate",
            
            # Add more as needed
        }
    
    def correct_query(self, query: str) -> str:
        """
        Correct common spelling mistakes in the query.
        
        Args:
            query: Original query that may contain spelling errors
            
        Returns:
            Corrected query
        """
        corrected = query.lower().strip()
        
        # Check each word for corrections
        words = corrected.split()
        corrected_words = []
        
        for word in words:
            # Remove punctuation for checking
            clean_word = re.sub(r'[^\w]', '', word)
            
            if clean_word in self.corrections:
                # Replace with correction, preserving original capitalization pattern
                correction = self.corrections[clean_word]
                
                # Preserve capitalization
                if word.isupper():
                    correction = correction.upper()
                elif word.istitle():
                    correction = correction.title()
                
                corrected_words.append(correction)
            else:
                corrected_words.append(word)
        
        return ' '.join(corrected_words)
    
    def suggest_corrections(self, query: str) -> List[str]:
        """
        Suggest possible corrections for the query.
        
        Args:
            query: Query to check
            
        Returns:
            List of suggested corrections
        """
        suggestions = []
        words = query.lower().split()
        
        for word in words:
            clean_word = re.sub(r'[^\w]', '', word)
            if clean_word in self.corrections:
                suggestions.append(f"'{word}' → '{self.corrections[clean_word]}'")
        
        return suggestions