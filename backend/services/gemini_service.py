"""
Gemini AI service for generating trivia questions
"""
import os
import json
import httpx
from typing import List, Dict, Optional

class GeminiService:
    """Service for interacting with Google Gemini AI"""

    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY", "")
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent"

    def _make_request(self, prompt: str) -> Optional[str]:
        """Make a request to Gemini API"""
        if not self.api_key:
            return None

        url = f"{self.base_url}?key={self.api_key}"

        payload = {
            "contents": [{
                "parts": [{
                    "text": prompt
                }]
            }],
            "generationConfig": {
                "temperature": 0.9,
                "topK": 1,
                "topP": 1,
                "maxOutputTokens": 2048,
            }
        }

        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()

                # Extract text from response
                if "candidates" in data and len(data["candidates"]) > 0:
                    candidate = data["candidates"][0]
                    if "content" in candidate and "parts" in candidate["content"]:
                        parts = candidate["content"]["parts"]
                        if len(parts) > 0 and "text" in parts[0]:
                            return parts[0]["text"]

                return None
        except Exception as e:
            print(f"Gemini API error: {e}")
            return None

    def generate_trivia_questions(self, category: str = "general", difficulty: str = "5th_grade", count: int = 10) -> List[Dict]:
        """
        Generate trivia questions using Gemini AI

        Args:
            category: Question category (general, science, history, math, geography)
            difficulty: Difficulty level (5th_grade by default)
            count: Number of questions to generate

        Returns:
            List of question dictionaries with format:
            {
                "question": "What is...",
                "options": ["A", "B", "C", "D"],
                "correct_answer": 0,  # index of correct option
                "explanation": "The answer is... because...",
                "category": "science"
            }
        """
        prompt = f"""Generate {count} multiple-choice trivia questions suitable for {difficulty} level students.
Category: {category}

Return ONLY a valid JSON array with this exact format (no markdown, no code blocks, just pure JSON):
[
  {{
    "question": "Question text here?",
    "options": ["Option A", "Option B", "Option C", "Option D"],
    "correct_answer": 0,
    "explanation": "Brief explanation why this is correct",
    "category": "{category}"
  }}
]

Requirements:
- Questions should be appropriate for 5th grade level (ages 10-11)
- Make questions fun and educational
- Ensure exactly 4 options per question
- correct_answer is the index (0-3) of the correct option
- Keep explanations brief and kid-friendly
- Mix of easy, medium, and slightly challenging questions
- Return ONLY the JSON array, nothing else"""

        response_text = self._make_request(prompt)

        if not response_text:
            # Return fallback questions if API fails
            return self._get_fallback_questions(category, count)

        try:
            # Clean up the response - remove markdown code blocks if present
            response_text = response_text.strip()
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.startswith("```"):
                response_text = response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            response_text = response_text.strip()

            questions = json.loads(response_text)

            # Validate questions
            validated_questions = []
            for q in questions[:count]:
                if self._validate_question(q):
                    validated_questions.append(q)

            return validated_questions if validated_questions else self._get_fallback_questions(category, count)

        except json.JSONDecodeError as e:
            print(f"Failed to parse Gemini response: {e}")
            print(f"Response was: {response_text[:500]}")
            return self._get_fallback_questions(category, count)

    def _validate_question(self, question: Dict) -> bool:
        """Validate question format"""
        required_fields = ["question", "options", "correct_answer", "explanation", "category"]

        if not all(field in question for field in required_fields):
            return False

        if not isinstance(question["options"], list) or len(question["options"]) != 4:
            return False

        if not isinstance(question["correct_answer"], int) or question["correct_answer"] not in [0, 1, 2, 3]:
            return False

        return True

    def _get_fallback_questions(self, category: str, count: int) -> List[Dict]:
        """Fallback questions when API is unavailable"""
        fallback_pool = [
            {
                "question": "What is the largest planet in our solar system?",
                "options": ["Earth", "Jupiter", "Saturn", "Mars"],
                "correct_answer": 1,
                "explanation": "Jupiter is the largest planet, about 11 times wider than Earth!",
                "category": "science"
            },
            {
                "question": "How many continents are there on Earth?",
                "options": ["5", "6", "7", "8"],
                "correct_answer": 2,
                "explanation": "There are 7 continents: Africa, Antarctica, Asia, Australia, Europe, North America, and South America.",
                "category": "geography"
            },
            {
                "question": "What is 12 × 12?",
                "options": ["124", "144", "134", "154"],
                "correct_answer": 1,
                "explanation": "12 × 12 = 144. This is also called 12 squared!",
                "category": "math"
            },
            {
                "question": "Who was the first President of the United States?",
                "options": ["Abraham Lincoln", "Thomas Jefferson", "George Washington", "John Adams"],
                "correct_answer": 2,
                "explanation": "George Washington was the first President, serving from 1789 to 1797.",
                "category": "history"
            },
            {
                "question": "What do plants need to make their own food?",
                "options": ["Only water", "Sunlight, water, and carbon dioxide", "Only sunlight", "Only soil"],
                "correct_answer": 1,
                "explanation": "Plants use photosynthesis, which needs sunlight, water, and carbon dioxide to make food!",
                "category": "science"
            },
            {
                "question": "What is the capital of France?",
                "options": ["London", "Berlin", "Paris", "Rome"],
                "correct_answer": 2,
                "explanation": "Paris is the capital of France and is known as the City of Light!",
                "category": "geography"
            },
            {
                "question": "How many sides does a hexagon have?",
                "options": ["5", "6", "7", "8"],
                "correct_answer": 1,
                "explanation": "A hexagon has 6 sides. Think of a honeycomb - each cell is a hexagon!",
                "category": "math"
            },
            {
                "question": "What is the largest ocean on Earth?",
                "options": ["Atlantic Ocean", "Indian Ocean", "Arctic Ocean", "Pacific Ocean"],
                "correct_answer": 3,
                "explanation": "The Pacific Ocean is the largest, covering about 30% of Earth's surface!",
                "category": "geography"
            },
            {
                "question": "What gas do humans breathe in?",
                "options": ["Carbon dioxide", "Oxygen", "Nitrogen", "Hydrogen"],
                "correct_answer": 1,
                "explanation": "We breathe in oxygen and breathe out carbon dioxide!",
                "category": "science"
            },
            {
                "question": "What is 25% of 100?",
                "options": ["20", "25", "30", "15"],
                "correct_answer": 1,
                "explanation": "25% means 25 out of 100, which equals 25!",
                "category": "math"
            }
        ]

        # Return requested number of questions (cycle if needed)
        return (fallback_pool * ((count // len(fallback_pool)) + 1))[:count]


# Singleton instance
gemini_service = GeminiService()
