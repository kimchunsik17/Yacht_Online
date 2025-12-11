from django.db import models
from django.conf import settings
import uuid

class Match(models.Model):
    STATUS_CHOICES = (
        ('WAITING', 'Waiting'),
        ('IN_PROGRESS', 'In Progress'),
        ('FINISHED', 'Finished'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    player1 = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='matches_as_p1', null=True, blank=True)
    player2 = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='matches_as_p2')
    player1_wins = models.IntegerField(default=0)
    player2_wins = models.IntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='WAITING')
    winner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='won_matches')
    current_turn_player = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='current_turn_matches')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Match {self.id} ({self.player1} vs {self.player2})"

class GameSession(models.Model):
    match = models.ForeignKey(Match, on_delete=models.CASCADE, related_name='games')
    round_number = models.IntegerField(default=1) # 1, 2, 3 (within match)
    # Store engine state: dice, scores, turn, etc.
    game_state = models.JSONField(default=dict) 
    result = models.CharField(max_length=20, null=True, blank=True) # P1_WIN, P2_WIN, DRAW
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Game {self.round_number} of {self.match}"