"""
Gemini AI integration service
Generates trivia questions, categories, and sports predictions
"""
import google.generativeai as genai
from typing import List, Dict, Optional
import json
import logging
from ..core.config import settings

logger = logging.getLogger(__name__)

# Configure Gemini
genai.configure(api_key=settings.GEMINI_API_KEY)


class AIService:
    """Service for AI-powered content generation"""

    def __init__(self):
        self.model = genai.GenerativeModel(settings.GEMINI_MODEL)

    async def generate_trivia_questions(
        self,
        category: str,
        difficulty: str,
        count: int = 5
    ) -> List[Dict]:
        """
        Generate trivia questions using Gemini

        Args:
            category: Question category (e.g., "Science", "History")
            difficulty: Difficulty level (easy, medium, hard, expert)
            count: Number of questions to generate

        Returns:
            List of question dictionaries with structure:
            {
                "question": "Question text",
                "answers": [
                    {"text": "Answer 1", "is_correct": false},
                    {"text": "Answer 2", "is_correct": true},
                    {"text": "Answer 3", "is_correct": false},
                    {"text": "Answer 4", "is_correct": false}
                ],
                "difficulty": "medium",
                "time_limit": 30,
                "points": 100
            }
        """
        prompt = f"""
Generate {count} multiple-choice trivia questions about {category} at {difficulty} difficulty level.

Requirements:
- Each question should have exactly 4 answer options
- Only ONE answer should be correct
- Questions should be appropriate for the {difficulty} difficulty level
- Include a mix of topics within {category}
- Avoid overly obscure or trivial questions
- Make incorrect answers plausible but clearly wrong

Return ONLY a valid JSON array with this exact structure (no additional text):
[
  {{
    "question_text": "The question text here?",
    "answers": [
      {{"answer_text": "Option A", "is_correct": false}},
      {{"answer_text": "Option B", "is_correct": true}},
      {{"answer_text": "Option C", "is_correct": false}},
      {{"answer_text": "Option D", "is_correct": false}}
    ],
    "difficulty": "{difficulty}",
    "time_limit_seconds": 30,
    "points": 100
  }}
]
"""

        try:
            response = self.model.generate_content(prompt)
            text = response.text.strip()

            # Remove markdown code blocks if present
            if text.startswith("```json"):
                text = text[7:]
            if text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]

            text = text.strip()

            # Parse JSON
            questions = json.loads(text)

            # Validate structure
            for q in questions:
                if not all(k in q for k in ["question_text", "answers", "difficulty"]):
                    raise ValueError("Invalid question structure")

                if len(q["answers"]) != 4:
                    raise ValueError("Each question must have exactly 4 answers")

                correct_count = sum(1 for a in q["answers"] if a.get("is_correct", False))
                if correct_count != 1:
                    raise ValueError("Each question must have exactly 1 correct answer")

            logger.info(f"Successfully generated {len(questions)} questions for {category}")
            return questions

        except Exception as e:
            logger.error(f"Error generating trivia questions: {e}", exc_info=True)
            return []

    async def generate_category_suggestions(
        self,
        existing_categories: List[str],
        count: int = 10
    ) -> List[Dict[str, str]]:
        """
        Generate new category suggestions

        Args:
            existing_categories: List of existing category names
            count: Number of suggestions to generate

        Returns:
            List of category dictionaries:
            [
                {"name": "Category Name", "description": "Description", "difficulty": "medium"}
            ]
        """
        existing_str = ", ".join(existing_categories) if existing_categories else "None"

        prompt = f"""
Generate {count} new trivia category suggestions.

Existing categories (avoid duplicates): {existing_str}

Requirements:
- Categories should be broad enough for many questions
- Suggest a mix of popular and niche topics
- Include difficulty level (easy, medium, hard, expert)
- Provide a brief description

Return ONLY a valid JSON array:
[
  {{
    "name": "Category Name",
    "description": "Brief description of the category",
    "difficulty_level": "medium"
  }}
]
"""

        try:
            response = self.model.generate_content(prompt)
            text = response.text.strip()

            # Clean markdown
            if text.startswith("```json"):
                text = text[7:]
            if text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]

            text = text.strip()
            categories = json.loads(text)

            logger.info(f"Successfully generated {len(categories)} category suggestions")
            return categories

        except Exception as e:
            logger.error(f"Error generating categories: {e}", exc_info=True)
            return []

    async def generate_sports_questions(
        self,
        sport: str,
        event_context: Optional[str] = None,
        count: int = 5
    ) -> List[Dict]:
        """
        Generate sports prediction questions

        Args:
            sport: Sport type (e.g., "NFL", "NBA", "Soccer")
            event_context: Optional context about specific events
            count: Number of questions to generate

        Returns:
            List of sports question dictionaries
        """
        context = f" Context: {event_context}" if event_context else ""

        prompt = f"""
Generate {count} sports trivia/prediction questions about {sport}.{context}

Types of questions to include:
- Over/under predictions
- Winner predictions
- Statistical comparisons
- Historical facts

Return ONLY a valid JSON array:
[
  {{
    "question_text": "Question text",
    "question_type": "over_under",
    "answers": [
      {{"answer_text": "Option", "is_correct": false}}
    ],
    "difficulty": "medium"
  }}
]
"""

        try:
            response = self.model.generate_content(prompt)
            text = response.text.strip()

            # Clean markdown
            if text.startswith("```json"):
                text = text[7:]
            if text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]

            text = text.strip()
            questions = json.loads(text)

            logger.info(f"Successfully generated {len(questions)} sports questions for {sport}")
            return questions

        except Exception as e:
            logger.error(f"Error generating sports questions: {e}", exc_info=True)
            return []

    async def review_question_quality(self, question_text: str, answers: List[str]) -> Dict:
        """
        Use AI to review question quality

        Args:
            question_text: The question
            answers: List of answer texts

        Returns:
            {
                "is_quality": bool,
                "feedback": "Feedback text",
                "score": 0-10
            }
        """
        prompt = f"""
Review this trivia question for quality:

Question: {question_text}

Answers: {", ".join(answers)}

Evaluate:
1. Is the question clear and unambiguous?
2. Are the answer options distinct and plausible?
3. Is there exactly one correct answer?
4. Is the difficulty appropriate?

Return ONLY valid JSON:
{{
  "is_quality": true/false,
  "feedback": "Brief feedback",
  "score": 0-10
}}
"""

        try:
            response = self.model.generate_content(prompt)
            text = response.text.strip()

            # Clean markdown
            if text.startswith("```json"):
                text = text[7:]
            if text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]

            text = text.strip()
            review = json.loads(text)

            return review

        except Exception as e:
            logger.error(f"Error reviewing question: {e}", exc_info=True)
            return {"is_quality": False, "feedback": "Error during review", "score": 0}


# Global AI service instance
ai_service = AIService()
