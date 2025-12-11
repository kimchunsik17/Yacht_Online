import random
import copy
import json

class AIPlayer:
    def __init__(self):
        pass

    def simulate_full_game(self):
        """
        Simulates a full 12-round game of Yacht and returns the action log.
        """
        from .engine import YachtGameEngine 
        
        engine = YachtGameEngine()
        game_log = []

        for r in range(1, 13):
            round_actions = []
            
            sim_engine = YachtGameEngine.from_dict(engine.to_dict()) 
            
            while True:
                # Decide move with strategy info
                decision = self._decide_turn_heuristic(sim_engine.dice, sim_engine.rolls_left, sim_engine.scores, sim_engine.calculate_potential_scores())
                
                # Generate rule-based commentary immediately
                commentary = self.get_commentary(
                    sim_engine.dice,
                    sim_engine.rolls_left,
                    sim_engine.scores,
                    sim_engine.calculate_potential_scores(),
                    decision
                )

                if decision['action'] == 'roll':
                    keep_indices = decision['keep_indices']
                    
                    action_entry = {
                        "type": "roll",
                        "dice_before": sim_engine.dice.copy(),
                        "keep_indices": keep_indices,
                        "commentary": commentary
                    }
                    
                    sim_engine.roll_dice(keep_indices) 
                    action_entry["dice_after"] = sim_engine.dice.copy()
                    
                    round_actions.append(action_entry)
                    
                elif decision['action'] == 'select_score':
                    category = decision['score_category']
                    
                    score = sim_engine.select_score(category) 
                    
                    action_entry = {
                        "type": "select",
                        "category": category,
                        "score": score,
                        "engine_state": sim_engine.to_dict(),
                        "commentary": commentary
                    }
                    round_actions.append(action_entry)
                    
                    engine.dice = sim_engine.dice
                    engine.rolls_left = sim_engine.rolls_left
                    engine.scores = sim_engine.scores
                    engine.bonus_score = sim_engine.bonus_score
                    engine.total_score = sim_engine.total_score
                    engine.round = sim_engine.round
                    engine.game_over = sim_engine.game_over
                    
                    break 
            
            game_log.append({
                "round": r,
                "actions": round_actions
            })
            
            if engine.game_over:
                break
                
        return game_log

    def _decide_turn_heuristic(self, dice, rolls_left, scores, potential_scores):
        counts = [0] * 7
        for d in dice:
            counts[d] += 1
        
        # 1. Yacht
        for i in range(1, 7):
            if counts[i] == 5 and scores['Yacht'] is None:
                return {"action": "select_score", "score_category": "Yacht", "strategy": "Yacht"}

        # 2. Rolls left > 0 -> Try to improve
        if rolls_left > 0:
            keep, strategy = self._get_keep_indices(dice, scores, counts)
            return {"action": "roll", "keep_indices": keep, "strategy": strategy}
        
        # 3. Select Best
        best = self._pick_best_category(scores, potential_scores)
        return {"action": "select_score", "score_category": best, "strategy": "Maximize Score"}

    def _get_keep_indices(self, dice, scores, counts):
        # Strategy: Keep duplicates
        max_count = 0
        target = 0
        for i in range(1, 7):
            if counts[i] > max_count:
                max_count = counts[i]
                target = i
            elif counts[i] == max_count:
                if i > target: target = i 
        
        if max_count >= 2:
            indices = [i for i, d in enumerate(dice) if d == target]
            return indices, f"Keep {target}s"
        
        # Keep high numbers (4,5,6)
        indices = [i for i, d in enumerate(dice) if d >= 4]
        if indices:
            return indices, "Keep High Numbers"
        
        return [], "Re-roll All"

    def _pick_best_category(self, scores, potential_scores):
        available = {k: v for k, v in potential_scores.items() if scores[k] is None}
        if not available: return None
        
        if available.get('Yacht') == 50: return 'Yacht'
        if available.get('Large Straight') == 30: return 'Large Straight'
        if available.get('Small Straight') == 15: return 'Small Straight'
        if available.get('Full House', 0) > 0: return 'Full House'
        if available.get('4 of a Kind', 0) > 18: return '4 of a Kind'
        
        for cat in ['Sixes', 'Fives', 'Fours']:
            if cat in available and available[cat] >= 8: return cat
            
        return max(available, key=available.get)

    def get_commentary(self, dice, rolls_left, scores, potential_scores, ai_decision):
        """
        Generates rule-based commentary.
        """
        action = ai_decision['action']
        strategy = ai_decision.get('strategy', '')
        
        if action == 'roll':
            keep_indices = ai_decision.get('keep_indices', [])
            kept_values = [dice[i] for i in keep_indices]
            
            if not keep_indices:
                return "AI: 마음에 드는 게 없어서 전부 다시 굴릴게요."
            
            if "Keep" in strategy:
                return f"AI: {strategy} 전략으로 {kept_values}를 유지하고 나머지를 굴립니다."
            
            return f"AI: {kept_values}는 남겨두고 나머지를 다시 굴려볼게요."
            
        elif action == 'select_score':
            category = ai_decision.get('score_category')
            score = potential_scores.get(category, 0)
            
            if category == 'Yacht' and score == 50:
                return "AI: 야추(Yacht)! 50점 획득합니다!"
            if category == 'Large Straight' and score == 30:
                return "AI: 라지 스트레이트 성공! 30점 가져갑니다."
            
            if score == 0:
                return f"AI: 아쉽지만 {category}에 0점을 기록합니다."
            
            return f"AI: {category}에 {score}점을 기록할게요."
            
        return ""
