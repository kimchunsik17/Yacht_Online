from django.shortcuts import render, redirect
from .models import Match, GameSession
from .engine import YachtGameEngine

def home(request):
    return render(request, 'game/home.html')

def create_match(request):
    # If authenticated, use user, else None
    user = request.user if request.user.is_authenticated else None
    
    match = Match.objects.create(player1=user, current_turn_player=user)
    
    # Initialize engine state
    engine = YachtGameEngine()
    
    GameSession.objects.create(
        match=match,
        game_state=engine.to_dict()
    )
    
    return redirect('room', room_name=str(match.id))

def room(request, room_name):
    user_id = request.user.id if request.user.is_authenticated else None

    return render(request, 'game/room.html', {
        'room_name': room_name,
        'score_categories': YachtGameEngine.SCORE_CATEGORIES,
        'user_id': user_id,
    })
