import sys
import os
from dotenv import load_dotenv

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from game.ai_player import AIPlayer

# Load env
load_dotenv()

def test_ai():
    print("Testing AI Integration...")
    player = AIPlayer()
    
    if player.model is None:
        print("Skipping actual API call (No API Key). Testing Fallback.")
    
    dice = [1, 2, 3, 4, 5] # Large Straight
    rolls_left = 1
    scores = {"Ones": None, "Large Straight": None}
    potential_scores = {"Ones": 1, "Large Straight": 30}
    
    decision = player.decide_turn(dice, rolls_left, scores, potential_scores)
    print(f"Decision: {decision}")

if __name__ == "__main__":
    test_ai()
