from django.shortcuts import render, redirect
from .models import Match, GameSession
from .engine import YachtGameEngine
from .ai_player import AIPlayer
from django.contrib.auth import get_user_model
import uuid

User = get_user_model()

def home(request):
    return render(request, 'game/home.html')

def create_match(request):
    if request.user.is_authenticated:
        user_obj = request.user
    else:
        # Create a guest user
        guest_username = f"Guest_{uuid.uuid4().hex[:8]}"
        user_obj = User.objects.create(username=guest_username, email=f"{guest_username}@example.com")
        user_obj.set_unusable_password()
        user_obj.save()
        # Store guest user ID in session for client-side identification
        request.session['guest_user_id'] = str(user_obj.id)
    
    match = Match.objects.create(player1=user_obj, current_turn_player=user_obj)
    
    # Initialize engine state for both players
    engine1 = YachtGameEngine()
    engine2 = YachtGameEngine()
    
    # Pre-calculate AI moves
    ai_player = AIPlayer()
    ai_log = ai_player.simulate_full_game()
    
    initial_state = {
        'player1': engine1.to_dict(),
        'player2': engine2.to_dict(),
    }
    
    GameSession.objects.create(
        match=match,
        game_state=initial_state,
        ai_actions_log=ai_log
    )
    
    return redirect('room', room_name=str(match.id))

def room(request, room_name):
    user_id = request.session.get('guest_user_id', None)
    if request.user.is_authenticated:
        user_id = str(request.user.id)
    
    try:
        match = Match.objects.get(id=room_name)
        player1_id = str(match.player1.id) if match.player1 else None
    except Match.DoesNotExist:
        player1_id = None

    return render(request, 'game/room.html', {
        'room_name': room_name,
        'score_categories': YachtGameEngine.SCORE_CATEGORIES,
        'user_id': user_id,
        'player1_id': player1_id
    })