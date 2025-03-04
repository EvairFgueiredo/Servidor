#!/usr/bin/env python3
"""
fightcade_clone_server.py
Servidor de matchmaking para o Fightcade Clone.
Recebe o registro dos jogadores via WebSocket, emparelha-os e envia os dados do adversário.
"""

import asyncio
import json
import logging
import uuid
import os
import websockets

# Configuração do logging para exibir informações no console
logging.basicConfig(level=logging.INFO)

# Lista global de jogadores aguardando partida
waiting_players = []

async def register_player(websocket, player_id, game, port):
    # Obtém o IP real do cliente a partir do websocket
    ip = websocket.remote_address[0]
    player = {
        "player_id": player_id,
        "game": game,
        "ip": ip,
        "port": port,
        "websocket": websocket
    }
    waiting_players.append(player)
    logging.info(f"Jogador registrado: {player_id} para o jogo: {game} com IP {ip}")
    await try_matchmaking()

async def try_matchmaking():
    while len(waiting_players) >= 2:
        player1 = waiting_players.pop(0)
        player2 = waiting_players.pop(0)
        match_id = str(uuid.uuid4())
        
        for p1, p2, role in [(player1, player2, 1), (player2, player1, 2)]:
            match_info = {
                "action": "match_found",
                "match_id": match_id,
                "game": p1['game'],
                "ip": p2['ip'],
                "port": p2['port'],
                "player_num": role
            }
            try:
                await p1['websocket'].send(json.dumps(match_info))
                logging.info(f"Match encontrado! {p1['player_id']} ({role}) vs {p2['player_id']} ({3 - role})")
            except websockets.exceptions.ConnectionClosed:
                logging.info(f"Erro: Conexão fechada para {p1['player_id']}.")

async def handler(websocket, path):
    try:
        async for message in websocket:
            data = json.loads(message)
            action = data.get("action")
            
            if action == "register":
                player_id = data.get("player_id")
                game = data.get("game")
                port = data.get("port")
                
                if player_id and game and port:
                    # Usa o IP real do cliente, ignorando o que foi enviado
                    await register_player(websocket, player_id, game, port)
                else:
                    logging.error("Registro falhou: player_id, game ou port faltando.")
            else:
                logging.warning(f"Ação desconhecida recebida: {action}")
    except websockets.exceptions.ConnectionClosed:
        logging.info("Conexão encerrada com um cliente.")
    finally:
        global waiting_players
        waiting_players = [
            player for player in waiting_players
            if player['websocket'] != websocket
        ]

async def main():
    port = int(os.getenv("PORT", 10000))
    # Configura os parâmetros de ping para evitar timeouts:
    # Envia pings a cada 10 segundos e espera até 30 segundos por uma resposta
    async with websockets.serve(handler, "0.0.0.0", port, ping_interval=10, ping_timeout=30):
        logging.info(f"Servidor de matchmaking rodando em ws://0.0.0.0:{port}")
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())
