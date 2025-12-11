from django.test import TestCase
from .engine import YachtGameEngine

class YachtGameEngineTest(TestCase):
    def setUp(self):
        self.engine = YachtGameEngine()

    def test_roll_dice(self):
        initial_dice = self.engine.dice
        new_dice = self.engine.roll_dice()
        self.assertNotEqual(initial_dice, new_dice) # Very small chance to fail if rolled same
        self.assertEqual(self.engine.rolls_left, 2)
        
        # Test keep
        kept_dice = [new_dice[0], new_dice[1]]
        next_dice = self.engine.roll_dice(keep_indices=[0, 1])
        self.assertEqual(next_dice[0], kept_dice[0])
        self.assertEqual(next_dice[1], kept_dice[1])
        self.assertEqual(self.engine.rolls_left, 1)

    def test_score_ones(self):
        # Force dice to be [1, 1, 2, 3, 4]
        score = self.engine._calculate_score("Ones", [1, 1, 2, 3, 4])
        self.assertEqual(score, 2)

    def test_score_yacht(self):
        score = self.engine._calculate_score("Yacht", [5, 5, 5, 5, 5])
        self.assertEqual(score, 50)
        
        score = self.engine._calculate_score("Yacht", [5, 5, 5, 5, 6])
        self.assertEqual(score, 0)

    def test_score_full_house(self):
        score = self.engine._calculate_score("Full House", [3, 3, 3, 5, 5])
        self.assertEqual(score, 19) # 3+3+3+5+5
        
        # Yacht is also Full House in some rules, checking logic
        # My implementation: counts[i] == 5 -> has_three=True, has_two=True logic fix needed?
        # Current logic: counts[i] == 5 -> sets has_three and has_two to True. 
        score = self.engine._calculate_score("Full House", [5, 5, 5, 5, 5]) 
        self.assertEqual(score, 25)

    def test_score_small_straight(self):
        score = self.engine._calculate_score("Small Straight", [1, 2, 3, 4, 6])
        self.assertEqual(score, 15)
        
        score = self.engine._calculate_score("Small Straight", [1, 3, 4, 5, 6])
        self.assertEqual(score, 15)

    def test_score_large_straight(self):
        score = self.engine._calculate_score("Large Straight", [1, 2, 3, 4, 5])
        self.assertEqual(score, 30)

        score = self.engine._calculate_score("Large Straight", [1, 2, 3, 5, 6]) # Not straight
        self.assertEqual(score, 0)
    
    def test_bonus_calculation(self):
        # Simulate getting 63+ in upper section
        self.engine.scores["Ones"] = 3 # 3 ones
        self.engine.scores["Twos"] = 6 # 3 twos
        self.engine.scores["Threes"] = 9 # 3 threes
        self.engine.scores["Fours"] = 12 # 3 fours
        self.engine.scores["Fives"] = 15 # 3 fives
        self.engine.scores["Sixes"] = 18 # 3 sixes
        # Total = 63
        self.engine._update_total_score()
        self.assertEqual(self.engine.bonus_score, 35)
