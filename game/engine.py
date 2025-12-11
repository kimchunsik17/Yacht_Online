import random

class YachtGameEngine:
    SCORE_CATEGORIES = [
        "Ones", "Twos", "Threes", "Fours", "Fives", "Sixes",
        "Choice", "4 of a Kind", "Full House", "Small Straight", "Large Straight", "Yacht"
    ]

    def __init__(self):
        self.dice = [1, 1, 1, 1, 1]
        self.rolls_left = 3
        self.scores = {category: None for category in self.SCORE_CATEGORIES} # None means not scored yet
        self.bonus_score = 0
        self.total_score = 0
        self.round = 1
        self.game_over = False

    def roll_dice(self, keep_indices=None):
        """
        Rolls the dice.
        :param keep_indices: List of indices (0-4) of dice to keep.
        """
        if self.rolls_left <= 0:
            raise ValueError("No rolls left")

        if keep_indices is None:
            keep_indices = []

        new_dice = []
        for i in range(5):
            if i in keep_indices:
                new_dice.append(self.dice[i])
            else:
                new_dice.append(random.randint(1, 6))
        
        self.dice = new_dice
        self.rolls_left -= 1
        return self.dice

    def calculate_potential_scores(self):
        """
        Calculates potential scores for all categories based on current dice.
        :return: Dictionary {category: score}
        """
        potential_scores = {}
        for category in self.SCORE_CATEGORIES:
            if self.scores[category] is None:
                potential_scores[category] = self._calculate_score(category, self.dice)
        return potential_scores

    def select_score(self, category):
        """
        Selects a score category and records the score.
        Advances the turn/round.
        """
        if category not in self.SCORE_CATEGORIES:
            raise ValueError(f"Invalid category: {category}")
        
        if self.scores[category] is not None:
             raise ValueError(f"Category already scored: {category}")

        score = self._calculate_score(category, self.dice)
        self.scores[category] = score
        self._update_total_score()
        
        # Reset for next turn
        self.round += 1
        self.rolls_left = 3
        self.dice = [1, 1, 1, 1, 1] # Or random? Usually reset.
        
        # Check game over (12 rounds for 12 categories)
        # Actually standard Yacht has 12 categories.
        if all(score is not None for score in self.scores.values()):
            self.game_over = True

        return score

    def _calculate_score(self, category, dice):
        counts = [0] * 7
        for d in dice:
            counts[d] += 1
        
        if category == "Ones":
            return counts[1] * 1
        elif category == "Twos":
            return counts[2] * 2
        elif category == "Threes":
            return counts[3] * 3
        elif category == "Fours":
            return counts[4] * 4
        elif category == "Fives":
            return counts[5] * 5
        elif category == "Sixes":
            return counts[6] * 6
        
        elif category == "Choice":
            return sum(dice)
        
        elif category == "4 of a Kind":
            for i in range(1, 7):
                if counts[i] >= 4:
                    return sum(dice)
            return 0
        
        elif category == "Full House":
            has_three = False
            has_two = False
            for i in range(1, 7):
                if counts[i] == 3:
                    has_three = True
                elif counts[i] == 2:
                    has_two = True
                elif counts[i] == 5: # Yacht is also a Full House
                    has_three = True
                    has_two = True
            
            if has_three and has_two:
                return sum(dice)
            return 0

        elif category == "Small Straight":
            # 1-2-3-4, 2-3-4-5, 3-4-5-6
            # Check unique sorted dice
            unique_dice = sorted(list(set(dice)))
            consecutive = 0
            for i in range(len(unique_dice) - 1):
                if unique_dice[i+1] == unique_dice[i] + 1:
                    consecutive += 1
                else:
                    consecutive = 0
                if consecutive >= 3:
                    return 15
            return 0

        elif category == "Large Straight":
            unique_dice = sorted(list(set(dice)))
            if unique_dice == [1, 2, 3, 4, 5] or unique_dice == [2, 3, 4, 5, 6]:
                return 30
            return 0

        elif category == "Yacht":
            for i in range(1, 7):
                if counts[i] == 5:
                    return 50
            return 0
        
        return 0

    def _update_total_score(self):
        subtotal = 0
        for cat in ["Ones", "Twos", "Threes", "Fours", "Fives", "Sixes"]:
            if self.scores[cat] is not None:
                subtotal += self.scores[cat]
        
        if subtotal >= 63:
            self.bonus_score = 35
        else:
            self.bonus_score = 0
        
        total = 0
        for score in self.scores.values():
            if score is not None:
                total += score
        self.total_score = total + self.bonus_score

    def to_dict(self):
        return {
            "dice": self.dice,
            "rolls_left": self.rolls_left,
            "scores": self.scores,
            "bonus_score": self.bonus_score,
            "total_score": self.total_score,
            "round": self.round,
            "game_over": self.game_over
        }

    @classmethod
    def from_dict(cls, data):
        engine = cls()
        engine.dice = data.get("dice", [1, 1, 1, 1, 1])
        engine.rolls_left = data.get("rolls_left", 3)
        engine.scores = data.get("scores", {category: None for category in cls.SCORE_CATEGORIES})
        engine.bonus_score = data.get("bonus_score", 0)
        engine.total_score = data.get("total_score", 0)
        engine.round = data.get("round", 1)
        engine.game_over = data.get("game_over", False)
        return engine
