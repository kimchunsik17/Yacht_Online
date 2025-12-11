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
            await self.send_game_state_to_channel(self.game_session.game_state, player_id)

            # If AI's turn immediately, trigger AI move
            if self.match.current_turn_player == self.ai_user:
                await self.trigger_ai_turn()

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

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            action = data.get('action')
            
            # Reload game data to check turn validity
            self.game_session, self.match = await self.get_game_data(self.room_name)
            
            current_player_id = self.scope['user'].id if self.scope['user'].is_authenticated else None
            match_turn_id = self.match.current_turn_player.id if self.match.current_turn_player else None
            
            # Check turn logic
            if match_turn_id != current_player_id:
                await self.send_error("It's not your turn.")
                return

            if action == 'roll':
                await self.handle_roll(data)
            elif action == 'select_score':
                await self.handle_select_score(data)
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

    async def handle_roll(self, data):
        keep_indices = data.get('keep_indices', [])
        
        # Reload state ensures we are working with latest data
        self.game_session, self.match = await self.get_game_data(self.room_name)
        engine = YachtGameEngine.from_dict(self.game_session.game_state)
        
        try:
            if engine.rolls_left <= 0:
                await self.send_error("No rolls left for this turn.")
                return

            engine.roll_dice(keep_indices)
            await self.save_game_state(engine.to_dict())
            
            player_id = self.match.current_turn_player.id if self.match.current_turn_player else None
            await self.send_game_state_to_group(engine.to_dict(), player_id)
            
        except ValueError as e:
            await self.send_error(str(e))

    async def handle_select_score(self, data):
        category = data.get('category')
        
        self.game_session, self.match = await self.get_game_data(self.room_name)
        engine = YachtGameEngine.from_dict(self.game_session.game_state)
        
        try:
            if category not in YachtGameEngine.SCORE_CATEGORIES or engine.scores[category] is not None:
                await self.send_error(f"Invalid or already scored category: {category}")
                return

            engine.select_score(category)
            await self.save_game_state(engine.to_dict())
            
            # Change turn
            await self.set_next_turn()
            
            player_id = self.match.current_turn_player.id if self.match.current_turn_player else None
            await self.send_game_state_to_group(engine.to_dict(), player_id)

            # If AI's turn, trigger AI move
            if self.match.current_turn_player == self.ai_user:
                await self.trigger_ai_turn()

        except ValueError as e:
            await self.send_error(str(e))

    async def game_update(self, event):
        await self.send_game_state_to_channel(event['state'], event['current_turn_player_id'], event.get('potential_scores', {}))

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

    async def send_game_state_to_channel(self, game_state_dict, current_turn_player_id, potential_scores_dict=None):
        if potential_scores_dict is None:
            engine = YachtGameEngine.from_dict(game_state_dict)
            potential_scores_dict = engine.calculate_potential_scores()

        message = {
            'type': 'game_state',
            'state': game_state_dict,
            'potential_scores': potential_scores_dict,
            'current_turn_player_id': current_turn_player_id
        }
        await self.send(text_data=json.dumps(message))
    
    async def send_game_state_to_group(self, game_state_dict, current_turn_player_id):
        engine = YachtGameEngine.from_dict(game_state_dict)
        potential_scores_dict = engine.calculate_potential_scores()

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'game_update',
                'state': game_state_dict,
                'potential_scores': potential_scores_dict,
                'current_turn_player_id': current_turn_player_id
            }
        )
    
    async def trigger_ai_turn(self):
        await asyncio.sleep(2) # Simulate AI thinking time
        
        self.game_session, self.match = await self.get_game_data(self.room_name)
        engine = YachtGameEngine.from_dict(self.game_session.game_state)

        potential_scores = engine.calculate_potential_scores()
        ai_decision = self.ai_player.decide_turn(
            engine.dice,
            engine.rolls_left,
            engine.scores,
            potential_scores
        )
        print(f"AI Decision: {ai_decision}")
        
        player_id = self.match.current_turn_player.id if self.match.current_turn_player else None

        if ai_decision['action'] == 'roll':
            engine.roll_dice(ai_decision.get('keep_indices', []))
            await self.save_game_state(engine.to_dict())
            await self.send_game_state_to_group(engine.to_dict(), player_id)
            
            if engine.rolls_left > 0:
                await self.trigger_ai_turn()
            else:
                self.game_session, self.match = await self.get_game_data(self.room_name)
                engine = YachtGameEngine.from_dict(self.game_session.game_state)
                potential_scores_after_rolls = engine.calculate_potential_scores()
                
                ai_forced_decision = self.ai_player.decide_turn(
                    engine.dice,
                    engine.rolls_left,
                    engine.scores,
                    potential_scores_after_rolls
                )
                if ai_forced_decision['action'] == 'select_score':
                    engine.select_score(ai_forced_decision['score_category'])
                    await self.save_game_state(engine.to_dict())
                    await self.set_next_turn()
                    
                    player_id = self.match.current_turn_player.id if self.match.current_turn_player else None
                    await self.send_game_state_to_group(engine.to_dict(), player_id)
                else:
                    logging.error("AI failed to select score after max rolls.")
        
        elif ai_decision['action'] == 'select_score':
            engine.select_score(ai_decision['score_category'])
            await self.save_game_state(engine.to_dict())
            await self.set_next_turn()
            
            player_id = self.match.current_turn_player.id if self.match.current_turn_player else None
            await self.send_game_state_to_group(engine.to_dict(), player_id)

    @database_sync_to_async
    def get_game_data(self, room_name):
        try:
            match_obj = Match.objects.select_related('player1', 'player2', 'current_turn_player').get(id=room_name)
            game_session_obj = GameSession.objects.get(match=match_obj)
            return game_session_obj, match_obj
        except (GameSession.DoesNotExist, Match.DoesNotExist):
            return None, None
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