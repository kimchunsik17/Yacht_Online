import google.generativeai as genai
import os
import json

class AIPlayer:
    def __init__(self, api_key=None):
        if api_key is None:
            api_key = os.getenv("GEMINI_API_KEY")
        
        if not api_key or api_key == "YOUR_GEMINI_API_KEY_HERE":
            self.model = None
            print("Warning: GEMINI_API_KEY is not set. AI functionality will be disabled.")
        else:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel('gemini-pro')

    def decide_turn(self, dice, rolls_left, scores, potential_scores):
        """
        Decides the AI's move using Gemini.
        :param dice: Current dice values [d1, d2, d3, d4, d5]
        :param rolls_left: Number of rolls left (0-2)
        :param scores: Current scoreboard state (dict)
        :param potential_scores: Potential scores for current dice (dict)
        :return: JSON object with action.
        """
        if not self.model:
             # Fallback logic if API is not available
            return self._fallback_logic(dice, rolls_left, potential_scores)

        prompt = self._construct_prompt(dice, rolls_left, scores, potential_scores)
        
        try:
            response = self.model.generate_content(prompt)
            # Basic cleanup for JSON parsing
            text = response.text.strip()
            if text.startswith("```json"):
                text = text[7:-3]
            elif text.startswith("```"):
                text = text[3:-3]
            
            return json.loads(text)
        except Exception as e:
            print(f"Gemini API Error: {e}")
            return self._fallback_logic(dice, rolls_left, potential_scores)

    def _construct_prompt(self, dice, rolls_left, scores, potential_scores):
        return f"""
        You are playing a game of Yacht (Yahtzee).
        Current Dice: {dice}
        Rolls Left: {rolls_left}
        
        Current Scoreboard (None means open):
        {json.dumps(scores, indent=2)}
        
        Potential Scores if you stop now:
        {json.dumps(potential_scores, indent=2)}
        
        Decide your move.
        If rolls_left > 0, you can choose to "roll" again, selecting which dice to keep.
        Or you can "select_score" to end your turn and take points.
        
        Goal: Maximize total score. Be strategic.
        
        Output strictly in JSON format:
        {{
            "action": "roll" or "select_score",
            "keep_indices": [0, 1] (only if action is roll, indices of dice to keep 0-4),
            "score_category": "Name" (only if action is select_score, must be one of the open categories)
        }}
        """

    def _fallback_logic(self, dice, rolls_left, potential_scores):
        # Very dumb fallback
        if rolls_left > 0:
            return {"action": "roll", "keep_indices": []}
        else:
            # Pick first available
            for cat, score in potential_scores.items():
                return {"action": "select_score", "score_category": cat}
        return {"action": "error"}
