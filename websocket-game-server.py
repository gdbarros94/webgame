import asyncio
import json
import uuid
import websockets
import random
import logging
from dataclasses import dataclass, asdict
from typing import Dict, List

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class Player:
    id: str
    name: str
    x: float
    y: float
    radius: float
    score: int = 0
    color: str = ''
    respawn_time: int = 0  # Tempo de respawn

class GameServer:
    def __init__(self, map_width: int = 1000, map_height: int = 1000):
        self.players: Dict[str, Player] = {}
        self.map_width = map_width
        self.map_height = map_height
        self.ranking: List[Dict] = []
        self.websockets = set()
        self.lock = asyncio.Lock()

    def generate_color(self):
        return f'rgb({random.randint(50, 200)},{random.randint(50, 200)},{random.randint(50, 200)})'

    def spawn_player(self) -> Player:
        player_id = str(uuid.uuid4())
        initial_radius = 15
        margin = initial_radius * 2
        player = Player(
            id=player_id,
            name="",
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
        if random.random() < 0.5:
            winner, loser = player1, player2
        else:
            winner, loser = player2, player1

        winner.score += 10
        if winner.score % 10 == 0:
            winner.radius *= 1.02  # Aumenta o tamanho do círculo em 2%

        loser.respawn_time = 15  # Inicializa o tempo de respawn com 15 segundos
        loser.x, loser.y = -100, -100  # Mover o jogador para fora da tela
        logger.info(f"Colisão: {winner.name} engoliu {loser.name}")

        asyncio.create_task(self.notify_death(loser.id))
        
        return winner, loser

    async def notify_death(self, loser_id):
        death_message = json.dumps({
            'type': 'death',
            'player_id': loser_id
        })
        
        async with self.lock:
            for ws in self.websockets:
                try:
                    player_data = await ws.recv()
                    player = json.loads(player_data)
                    if player.get('player_id') == loser_id:
                        await ws.send(death_message)
                        break
                except:
                    continue

    def update_ranking(self):
        self.ranking = sorted(
            [{'id': p.id, 'name': p.name, 'score': p.score, 'radius': p.radius} 
             for p in self.players.values()], 
            key=lambda x: x['score'], 
            reverse=True
        )[:10]

    async def game_loop(self, websocket, player):
        try:
            async for message in websocket:
                async with self.lock:
                    data = json.loads(message)
                    if data['type'] == 'move':
                        if player.respawn_time > 0:  # Se o jogador está em respawn, não permite movimento
                            continue
                        
                        # Lógica de movimentação
                        speed_factor = 1 / (player.radius * 0.05)
                        dx = (data['x'] - player.x) * speed_factor
                        dy = (data['y'] - player.y) * speed_factor
                        
                        player.x = max(player.radius, min(self.map_width - player.radius, player.x + dx))
                        player.y = max(player.radius, min(self.map_height - player.radius, player.y + dy))
                        
                        for other_player_id, other_player in list(self.players.items()):
                            if other_player_id != player.id and self.check_collision(player, other_player):
                                winner, loser = self.handle_player_collision(player, other_player)
                                if loser.id in self.players:
                                    loser.radius = 0  # Fazer o jogador "invisível"
                    
                        self.update_ranking()
                        await self.broadcast_game_state()
                
                # Atualiza o tempo de respawn
                if player.respawn_time > 0:
                    player.respawn_time -= 1  # Decrementa o tempo de respawn
                elif player.respawn_time == 0:
                    player.respawn_time = -1  # Marca como pronto para respawn
                    player.x = random.uniform(player.radius * 2, self.map_width - player.radius * 2)
                    player.y = random.uniform(player.radius * 2, self.map_height - player.radius * 2)
                    logger.info(f"Jogador {player.name} renasceu")

        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Jogador {player.name} (ID: {player.id}) desconectou")
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
        data = await websocket.recv()
        player_data = json.loads(data)
        
        player = self.spawn_player()
        player.name = player_data.get('name', 'Anônimo')
        
        self.players[player.id] = player
        self.websockets.add(websocket)
        
        logger.info(f"Novo jogador conectado: {player.name} (ID: {player.id})")
        
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