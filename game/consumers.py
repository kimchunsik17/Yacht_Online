import json
import asyncio
import traceback
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from .models import GameSession, Match
from .engine import YachtGameEngine
from .ai_player import AIPlayer

User = get_user_model()

# Setup simple logger
logging.basicConfig(
    filename='server_error.log', 
    level=logging.ERROR, 
    format='%(asctime)s %(levelname)s: %(message)s'
)

class GameConsumer(AsyncWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ai_player = AIPlayer()
        self.ai_user = None

    async def connect(self):
        try:
            self.room_name = self.scope['url_route']['kwargs']['room_name']
            self.room_group_name = f'game_{self.room_name}'
            
            logging.info(f"DEBUG LOG: Connecting to room {self.room_name}")
            print(f"DEBUG: Connecting to room {self.room_name}")

            self.game_session, self.match = await self.get_game_data(self.room_name)
            if not self.game_session or not self.match:
                logging.error(f"DEBUG LOG: Game session or Match not found for room {self.room_name}")
                print(f"DEBUG: Game session or Match not found for room {self.room_name}")
                await self.close()
                return

            self.ai_user = await self.get_or_create_ai_user()

            print(f"DEBUG: Game session and Match found. Joining group.")
            await self.channel_layer.group_add(
                self.room_group_name,
                self.channel_name
            )

            await self.accept() 
            
            player_id = self.match.current_turn_player.id if self.match.current_turn_player else None
            
            # Send initial state with both players data
            await self.send_game_state_to_channel(self.game_session.game_state, player_id)

            # If AI's turn immediately, trigger AI move
            if self.match.current_turn_player == self.ai_user:
                asyncio.create_task(self.trigger_ai_turn())

        except Exception as e:
            error_msg = f"Error in connect: {str(e)}\n"
            error_msg += traceback.format_exc()
            print(error_msg)
            logging.error(error_msg)
            await self.close()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    def get_user_id_from_scope(self):
        if self.scope['user'].is_authenticated:
            return self.scope['user'].id
        
        # Check session for guest user ID
        session = self.scope.get('session')
        if session:
            guest_id = session.get('guest_user_id')
            if guest_id:
                return int(guest_id)
        return None

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            action = data.get('action')
            
            self.game_session, self.match = await self.get_game_data(self.room_name)
            
            if not self.game_session or not self.match:
                 await self.send_error("Game session not found.")
                 return

            current_player_id = self.get_user_id_from_scope()
            match_turn_id = self.match.current_turn_player.id if self.match.current_turn_player else None
            
            # Check turn logic (Skip for next_game action as it might be sent by non-turn player)
            if action != 'next_game' and match_turn_id != current_player_id:
                await self.send_error("It's not your turn.")
                return

            if action == 'roll':
                await self.handle_roll(data)
            elif action == 'select_score':
                await self.handle_select_score(data)
            elif action == 'next_game':
                await self.handle_next_game()
            elif 'message' in data:
                message = data.get('message')
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'chat_message',
                        'message': message
                    }
                )
        except Exception as e:
            error_msg = f"Error in receive: {str(e)}\n"
            error_msg += traceback.format_exc()
            print(error_msg)
            logging.error(error_msg)
            await self.send_error("Server error processing request.")

    def get_current_player_key(self):
        if self.match.current_turn_player == self.match.player1:
            return 'player1'
        return 'player2'

    async def handle_roll(self, data):
        keep_indices = data.get('keep_indices', [])
        
        player_key = self.get_current_player_key()
        player_state = self.game_session.game_state.get(player_key)
        
        if not player_state:
             await self.send_error(f"Game state corrupted for {player_key}")
             return

        engine = YachtGameEngine.from_dict(player_state)
        
        try:
            if engine.rolls_left <= 0:
                await self.send_error("No rolls left for this turn.")
                return

            engine.roll_dice(keep_indices)
            
            self.game_session.game_state[player_key] = engine.to_dict()
            await self.save_game_state(self.game_session.game_state)
            
            player_id = self.match.current_turn_player.id if self.match.current_turn_player else None
            await self.send_game_state_to_group(self.game_session.game_state, player_id)
            
        except ValueError as e:
            await self.send_error(str(e))

    async def handle_select_score(self, data):
        category = data.get('category')
        
        player_key = self.get_current_player_key()
        player_state = self.game_session.game_state.get(player_key)
        
        engine = YachtGameEngine.from_dict(player_state)
        
        try:
            if category not in YachtGameEngine.SCORE_CATEGORIES or engine.scores[category] is not None:
                await self.send_error(f"Invalid or already scored category: {category}")
                return

            engine.select_score(category)
            
            self.game_session.game_state[player_key] = engine.to_dict()
            await self.save_game_state(self.game_session.game_state)
            
            await self.set_next_turn()
            
            game_ended = await self.check_and_process_game_end()
            
            player_id = self.match.current_turn_player.id if self.match.current_turn_player else None
            await self.send_game_state_to_group(self.game_session.game_state, player_id)

            if not game_ended and self.match.current_turn_player == self.ai_user:
                asyncio.create_task(self.trigger_ai_turn())

        except ValueError as e:
            await self.send_error(str(e))

    async def handle_next_game(self):
        if self.match.status == 'FINISHED':
            return

        if not self.game_session.result:
            return

        current_round = self.game_session.round_number
        next_round = current_round + 1
        
        ai_log = self.ai_player.simulate_full_game()
        
        engine1 = YachtGameEngine()
        engine2 = YachtGameEngine()
        initial_state = {
            'player1': engine1.to_dict(),
            'player2': engine2.to_dict(),
        }
        
        new_session, created = await database_sync_to_async(GameSession.objects.get_or_create)(
            match=self.match,
            round_number=next_round,
            defaults={
                'game_state': initial_state,
                'ai_actions_log': ai_log
            }
        )
        
        self.game_session = new_session
        
        if next_round % 2 == 1:
            self.match.current_turn_player = self.match.player1
        else:
            self.match.current_turn_player = self.match.player2 if self.match.player2 else self.ai_user
            
        await database_sync_to_async(self.match.save)()
        
        player_id = self.match.current_turn_player.id if self.match.current_turn_player else None
        await self.send_game_state_to_group(self.game_session.game_state, player_id)
        
        if self.match.current_turn_player == self.ai_user:
            asyncio.create_task(self.trigger_ai_turn())

    async def game_update(self, event):
        await self.send_game_state_to_channel(event['state'], event['current_turn_player_id'])

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'type': 'chat',
            'message': event['message']
        }))
        
    async def send_error(self, message):
        await self.send(text_data=json.dumps({
            'type': 'error',
            'message': message
        }))

    async def send_game_state_to_channel(self, game_state_dict, current_turn_player_id):
        engine1 = YachtGameEngine.from_dict(game_state_dict['player1'])
        pot1 = engine1.calculate_potential_scores()
        
        engine2 = YachtGameEngine.from_dict(game_state_dict['player2'])
        pot2 = engine2.calculate_potential_scores()
        
        match_info = {
            'player1_wins': self.match.player1_wins,
            'player2_wins': self.match.player2_wins,
            'status': self.match.status,
            'winner_id': self.match.winner.id if self.match.winner else None,
            'session_result': self.game_session.result,
            'round_number': self.game_session.round_number
        }

        message = {
            'type': 'game_state',
            'state': game_state_dict,
            'potential_scores': {
                'player1': pot1,
                'player2': pot2
            },
            'current_turn_player_id': current_turn_player_id,
            'match_info': match_info
        }
        await self.send(text_data=json.dumps(message))
    
    async def send_game_state_to_group(self, game_state_dict, current_turn_player_id):
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'game_update',
                'state': game_state_dict,
                'current_turn_player_id': current_turn_player_id
            }
        )
    
    async def trigger_ai_turn(self):
        self.game_session, self.match = await self.get_game_data(self.room_name)
        
        current_p2_round = self.game_session.game_state['player2']['round']
        
        if not self.game_session.ai_actions_log or current_p2_round > len(self.game_session.ai_actions_log):
            logging.error("AI Log missing or round out of bounds")
            return

        round_log = self.game_session.ai_actions_log[current_p2_round - 1]
        actions = round_log['actions']
        
        player_key = 'player2'
        
        engine = YachtGameEngine.from_dict(self.game_session.game_state[player_key])
        
        for action in actions:
            await asyncio.sleep(0.7) 
            
            # Send commentary if exists (pre-calculated)
            if action.get('commentary'):
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'chat_message',
                        'message': action['commentary']
                    }
                )
            
            if action['type'] == 'roll':
                engine.dice = action['dice_after']
                engine.rolls_left -= 1
                
                self.game_session.game_state[player_key] = engine.to_dict()
                await self.save_game_state(self.game_session.game_state)
                
                player_id = self.match.current_turn_player.id if self.match.current_turn_player else None
                await self.send_game_state_to_group(self.game_session.game_state, player_id)
                
            elif action['type'] == 'select':
                self.game_session.game_state[player_key] = action['engine_state']
                await self.save_game_state(self.game_session.game_state)
                
                await self.set_next_turn()
                await self.check_and_process_game_end()
                
                player_id = self.match.current_turn_player.id if self.match.current_turn_player else None
                await self.send_game_state_to_group(self.game_session.game_state, player_id)

    @database_sync_to_async
    def get_game_data(self, room_name):
        try:
            match_obj = Match.objects.select_related('player1', 'player2', 'current_turn_player', 'winner').get(id=room_name)
            game_session_obj = GameSession.objects.filter(match=match_obj).order_by('-round_number').first()
            return game_session_obj, match_obj
        except Exception as e:
            logging.error(f"Error getting game data: {e}")
            return None, None
    
    @database_sync_to_async
    def get_or_create_ai_user(self):
        ai_user, created = User.objects.get_or_create(username='AIPlayer', defaults={'email': 'ai@example.com'})
        if created:
            ai_user.set_unusable_password()
            ai_user.save()
        return ai_user

    @database_sync_to_async
    def set_next_turn(self):
        self.match = Match.objects.get(id=self.match.id)
        if self.match.current_turn_player == self.match.player1:
            self.match.current_turn_player = self.ai_user
        else:
            self.match.current_turn_player = self.match.player1
        self.match.save()

    @database_sync_to_async
    def save_game_state(self, state):
        self.game_session.game_state = state
        self.game_session.save()

    async def check_and_process_game_end(self):
        state = self.game_session.game_state
        engine1 = YachtGameEngine.from_dict(state['player1'])
        engine2 = YachtGameEngine.from_dict(state['player2'])
        
        if engine1.game_over and engine2.game_over:
            score1 = engine1.total_score
            score2 = engine2.total_score
            
            print(f"DEBUG: Game End. P1: {score1}, P2: {score2}") # DEBUG LOG
            
            if not self.game_session.result:
                if score1 > score2:
                    self.match.player1_wins += 1
                    self.game_session.result = 'P1_WIN'
                    print("DEBUG: P1 Wins Round")
                elif score2 > score1:
                    self.match.player2_wins += 1
                    self.game_session.result = 'P2_WIN'
                    print("DEBUG: P2 Wins Round")
                else:
                    self.game_session.result = 'DRAW'
                    print("DEBUG: Draw Round")
                
                await database_sync_to_async(self.match.save)()
                await database_sync_to_async(self.game_session.save)()
                
                if self.match.player1_wins >= 2:
                    self.match.status = 'FINISHED'
                    self.match.winner = self.match.player1
                elif self.match.player2_wins >= 2:
                    self.match.status = 'FINISHED'
                    self.match.winner = self.match.player2
                
                await database_sync_to_async(self.match.save)()
            
            return True
            
        return False
