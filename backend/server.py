import asyncio
import json
import websockets
import random
from dataclasses import dataclass, asdict
from typing import Dict, Set
import math

@dataclass
class Player:
    id: str
    name: str
    color: str
    x: float
    y: float
    mass: float
    score: int

class GameState:
    def __init__(self):
        self.players: Dict[str, Player] = {}
        self.food = []
        self.generate_food()
        self.players_to_remove = set()  # Novo conjunto para controlar remoções

    def generate_food(self):
        for _ in range(50):
            self.food.append({
                'x': random.randint(0, 2000),
                'y': random.randint(0, 2000),
                'mass': 5,
                'color': f'rgb({random.randint(0,255)},{random.randint(0,255)},{random.randint(0,255)})'
            })

    def check_collisions(self, player_id: str) -> bool:
        if player_id not in self.players:
            return None
            
        player = self.players[player_id]
        player_radius = math.sqrt(player.mass) * 4

        # Verifica colisão com comida
        for food in self.food[:]:
            food_distance = math.sqrt(
                (player.x - food['x'])**2 + 
                (player.y - food['y'])**2
            )
            if food_distance < player_radius + food['mass']:
                self.food.remove(food)
                player.mass += food['mass']
                player.score += 10
                if len(self.food) < 50:
                    self.generate_food()

        # Verifica colisão com outros jogadores
        for other_id, other in list(self.players.items()):  # Usa list() para evitar modificação durante iteração
            if other_id != player_id and other_id not in self.players_to_remove:
                other_radius = math.sqrt(other.mass) * 4
                distance = math.sqrt(
                    (player.x - other.x)**2 + 
                    (player.y - other.y)**2
                )
                
                if distance < player_radius + other_radius:
                    # O maior jogador absorve o menor
                    if player.mass > other.mass:
                        player.mass += other.mass * 0.8
                        player.score += other.score
                        self.players_to_remove.add(other_id)
                        return other_id  # Retorna o ID do jogador que deve ser eliminado
                    elif player.mass < other.mass:
                        other.mass += player.mass * 0.8
                        other.score += player.score
                        self.players_to_remove.add(player_id)
                        return player_id  # Retorna o ID do jogador atual que deve ser eliminado
        
        return None

    def to_json(self):
        return json.dumps({
            'players': {id: asdict(player) for id, player in self.players.items()},
            'food': self.food
        })

game_state = GameState()
CLIENTS = set()

async def handle_connection(websocket):
    try:
        CLIENTS.add(websocket)
        player_id = str(random.randint(1000, 9999))
        
        init_data = await websocket.recv()
        player_info = json.loads(init_data)
        
        new_player = Player(
            id=player_id,
            name=player_info['name'],
            color=player_info['color'],
            x=random.randint(0, 2000),
            y=random.randint(0, 2000),
            mass=20,
            score=0
        )
        
        game_state.players[player_id] = new_player
        state_json = game_state.to_json()
        await websocket.send(state_json)

        try:
            while True:
                data = await websocket.recv()
                movement = json.loads(data)
                
                if player_id in game_state.players and player_id not in game_state.players_to_remove:
                    player = game_state.players[player_id]
                    player.x = movement['x']
                    player.y = movement['y']
                    
                    # Verifica colisões e atualiza estado
                    eliminated_player_id = game_state.check_collisions(player_id)
                    
                    # Remove jogadores marcados para remoção
                    for pid in game_state.players_to_remove:
                        if pid in game_state.players:
                            # Notifica o jogador eliminado
                            for client in CLIENTS:
                                try:
                                    client_data = await client.recv()
                                    client_info = json.loads(client_data)
                                    if 'id' in client_info and client_info['id'] == pid:
                                        await client.send(json.dumps({"eliminated": True}))
                                except:
                                    continue
                            del game_state.players[pid]
                    
                    game_state.players_to_remove.clear()
                    
                    if player_id not in game_state.players:
                        await websocket.send(json.dumps({"eliminated": True}))
                        break
                    
                    # Envia estado atualizado para todos
                    state_json = game_state.to_json()
                    websockets.broadcast(CLIENTS, state_json)
                
                await asyncio.sleep(0.016)

        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            if player_id in game_state.players:
                del game_state.players[player_id]
            CLIENTS.remove(websocket)
            
    except Exception as e:
        print(f"Erro: {e}")

async def main():
    async with websockets.serve(handle_connection, "localhost", 8765):
        print("Servidor iniciado em ws://localhost:8765")
        await asyncio.Future()  # roda indefinidamente

if __name__ == "__main__":
    asyncio.run(main()) 