import asyncio
import json
import uuid
import websockets
import random
import logging
from dataclasses import dataclass, asdict
from typing import Dict, List, Tuple

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class Player:
    id: str
    x: float
    y: float
    radius: float
    score: int = 0
    color: str = ''

class GameServer:
    def __init__(self, map_width: int = 1000, map_height: int = 1000):
        self.players: Dict[str, Player] = {}
        self.map_width = map_width
        self.map_height = map_height
        self.ranking: List[Dict] = []
        self.websockets = set()

    def generate_color(self):
        return f'rgb({random.randint(50, 200)},{random.randint(50, 200)},{random.randint(50, 200)})'

    def spawn_player(self) -> Player:
        player_id = str(uuid.uuid4())
        initial_radius = 15
        margin = initial_radius * 2
        player = Player(
            id=player_id, 
            x=random.uniform(margin, self.map_width - margin),
            y=random.uniform(margin, self.map_height - margin),
            radius=initial_radius,
            color=self.generate_color()
        )
        return player

    def check_collision(self, player1: Player, player2: Player) -> bool:
        distance = ((player1.x - player2.x)**2 + (player1.y - player2.y)**2)**0.5
        return distance < player1.radius + player2.radius

    def handle_player_collision(self, player1: Player, player2: Player):
        if player1.radius > player2.radius:
            player1.radius += player2.radius * 0.3
            player1.score += int(player2.radius)
            return player1, None
        elif player2.radius > player1.radius:
            player2.radius += player1.radius * 0.3
            player2.score += int(player1.radius)
            return None, player2
        return player1, player2

    def update_ranking(self):
        self.ranking = sorted(
            [{'id': p.id, 'score': p.score, 'radius': p.radius} 
             for p in self.players.values()], 
            key=lambda x: x['score'], 
            reverse=True
        )[:10]

    async def game_loop(self, websocket, player):
        try:
            async for message in websocket:
                data = json.loads(message)
                if data['type'] == 'move':
                    speed_factor = 1 / (player.radius * 0.05)
                    dx = (data['x'] - player.x) * speed_factor
                    dy = (data['y'] - player.y) * speed_factor
                    
                    player.x = max(player.radius, min(self.map_width - player.radius, 
                                                    player.x + dx))
                    player.y = max(player.radius, min(self.map_height - player.radius, 
                                                    player.y + dy))
                    
                    for other_player_id, other_player in list(self.players.items()):
                        if other_player_id != player.id and self.check_collision(player, other_player):
                            winner, loser = self.handle_player_collision(player, other_player)
                            if winner is player and loser is None:
                                if other_player_id in self.players:
                                    del self.players[other_player_id]
                            elif winner is other_player and loser is None:
                                if player.id in self.players:
                                    del self.players[player.id]
                                    return
                    
                    self.update_ranking()
                    await self.broadcast_game_state()
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Player {player.id} disconnected")
        finally:
            if player.id in self.players:
                del self.players[player.id]
            await self.broadcast_game_state()

    async def broadcast_game_state(self):
        if not self.players:
            return
        
        game_state = {
            'players': {pid: asdict(player) for pid, player in self.players.items()},
            'ranking': self.ranking
        }
        
        await asyncio.gather(
            *[websocket.send(json.dumps(game_state)) 
              for websocket in self.websockets]
        )

    async def register(self, websocket):
        player = self.spawn_player()
        self.players[player.id] = player
        self.websockets.add(websocket)
        
        await websocket.send(json.dumps({
            'type': 'init',
            'player_id': player.id,
            'map_width': self.map_width,
            'map_height': self.map_height
        }))
        
        await self.broadcast_game_state()
        return player

    async def unregister(self, websocket):
        self.websockets.remove(websocket)

    async def handler(self, websocket, path):
        try:
            player = await self.register(websocket)
            await self.game_loop(websocket, player)
        finally:
            await self.unregister(websocket)

    def start_server(self, host='localhost', port=8765):
        server = websockets.serve(self.handler, host, port)
        asyncio.get_event_loop().run_until_complete(server)
        asyncio.get_event_loop().run_forever()

def main():
    game_server = GameServer()
    game_server.start_server()

if __name__ == "__main__":
    main()
