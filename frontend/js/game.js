class Game {
    constructor() {
        this.canvas = document.getElementById('gameCanvas');
        this.ctx = this.canvas.getContext('2d');
        this.players = {};
        this.food = [];
        this.camera = { x: 0, y: 0 };
        this.localPlayer = null;
        this.eliminated = false;
        this.controlType = 'mouse';
        this.keyState = {
            up: false,
            down: false,
            left: false,
            right: false
        };
        
        this.resizeCanvas();
        window.addEventListener('resize', () => this.resizeCanvas());
    }

    resizeCanvas() {
        this.canvas.width = window.innerWidth;
        this.canvas.height = window.innerHeight;
    }

    updateCamera() {
        if (this.localPlayer) {
            this.camera.x = this.localPlayer.x - this.canvas.width / 2;
            this.camera.y = this.localPlayer.y - this.canvas.height / 2;
        }
    }

    draw() {
        if (this.eliminated) {
            this.drawGameOver();
            return;
        }

        this.ctx.fillStyle = '#111';
        this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);

        // Desenha grade
        this.ctx.strokeStyle = '#222';
        this.ctx.beginPath();
        for (let x = 0; x < 2000; x += 50) {
            this.ctx.moveTo(x - this.camera.x, 0 - this.camera.y);
            this.ctx.lineTo(x - this.camera.x, 2000 - this.camera.y);
        }
        for (let y = 0; y < 2000; y += 50) {
            this.ctx.moveTo(0 - this.camera.x, y - this.camera.y);
            this.ctx.lineTo(2000 - this.camera.x, y - this.camera.y);
        }
        this.ctx.stroke();

        // Desenha comida
        this.food.forEach(food => {
            this.ctx.beginPath();
            this.ctx.fillStyle = food.color;
            this.ctx.arc(
                food.x - this.camera.x,
                food.y - this.camera.y,
                food.mass,
                0,
                Math.PI * 2
            );
            this.ctx.fill();
        });

        // Desenha jogadores
        Object.values(this.players).forEach(player => {
            this.ctx.beginPath();
            this.ctx.fillStyle = player.color;
            this.ctx.arc(
                player.x - this.camera.x,
                player.y - this.camera.y,
                Math.sqrt(player.mass) * 4,
                0,
                Math.PI * 2
            );
            this.ctx.fill();

            // Nome do jogador
            this.ctx.fillStyle = 'white';
            this.ctx.textAlign = 'center';
            this.ctx.font = '16px Arial';
            this.ctx.fillText(
                `${player.name} (${player.score})`,
                player.x - this.camera.x,
                player.y - this.camera.y - Math.sqrt(player.mass) * 4 - 5
            );
        });
    }

    drawGameOver() {
        this.ctx.fillStyle = 'rgba(0, 0, 0, 0.8)';
        this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
        
        this.ctx.fillStyle = 'white';
        this.ctx.textAlign = 'center';
        this.ctx.font = '48px Arial';
        this.ctx.fillText(
            'Game Over!',
            this.canvas.width / 2,
            this.canvas.height / 2 - 50
        );
        
        this.ctx.font = '24px Arial';
        this.ctx.fillText(
            `Pontuação final: ${this.finalScore || 0}`,
            this.canvas.width / 2,
            this.canvas.height / 2 + 50
        );
        
        // Desenha o botão de reiniciar
        const buttonWidth = 200;
        const buttonHeight = 50;
        const buttonX = this.canvas.width / 2 - buttonWidth / 2;
        const buttonY = this.canvas.height / 2 + 100;
        
        this.ctx.fillStyle = '#4A5568';
        this.ctx.fillRect(buttonX, buttonY, buttonWidth, buttonHeight);
        
        this.ctx.fillStyle = 'white';
        this.ctx.font = '20px Arial';
        this.ctx.fillText(
            'Jogar Novamente',
            this.canvas.width / 2,
            buttonY + buttonHeight/2 + 7
        );

        // Adiciona área clicável do botão se ainda não existe
        if (!this.restartButtonArea) {
            this.restartButtonArea = {
                x: buttonX,
                y: buttonY,
                width: buttonWidth,
                height: buttonHeight
            };
            
            // Adiciona listener de clique para o canvas
            this.canvas.addEventListener('click', (event) => {
                if (this.eliminated) {
                    const rect = this.canvas.getBoundingClientRect();
                    const x = event.clientX - rect.left;
                    const y = event.clientY - rect.top;
                    
                    if (x >= this.restartButtonArea.x && 
                        x <= this.restartButtonArea.x + this.restartButtonArea.width &&
                        y >= this.restartButtonArea.y && 
                        y <= this.restartButtonArea.y + this.restartButtonArea.height) {
                        location.reload();
                    }
                }
            });
        }
    }

    updateRanking() {
        const ranking = document.getElementById('ranking');
        const sortedPlayers = Object.values(this.players)
            .sort((a, b) => b.score - a.score)
            .slice(0, 10);

        ranking.innerHTML = sortedPlayers
            .map((player, index) => `
                <div class="flex justify-between">
                    <span>${index + 1}. ${player.name}</span>
                    <span>${player.score}</span>
                </div>
            `)
            .join('');
    }

    setupKeyboardControls() {
        document.addEventListener('keydown', (event) => {
            switch(event.key.toLowerCase()) {
                case 'w':
                case 'arrowup':
                    this.keyState.up = true;
                    break;
                case 's':
                case 'arrowdown':
                    this.keyState.down = true;
                    break;
                case 'a':
                case 'arrowleft':
                    this.keyState.left = true;
                    break;
                case 'd':
                case 'arrowright':
                    this.keyState.right = true;
                    break;
            }
        });

        document.addEventListener('keyup', (event) => {
            switch(event.key.toLowerCase()) {
                case 'w':
                case 'arrowup':
                    this.keyState.up = false;
                    break;
                case 's':
                case 'arrowdown':
                    this.keyState.down = false;
                    break;
                case 'a':
                case 'arrowleft':
                    this.keyState.left = false;
                    break;
                case 'd':
                case 'arrowright':
                    this.keyState.right = false;
                    break;
            }
        });
    }

    updatePlayerPosition() {
        if (!this.localPlayer) return;

        if (this.controlType === 'keyboard') {
            const speed = 5;
            let dx = 0;
            let dy = 0;

            if (this.keyState.up) dy -= speed;
            if (this.keyState.down) dy += speed;
            if (this.keyState.left) dx -= speed;
            if (this.keyState.right) dx += speed;

            // Normaliza o movimento diagonal
            if (dx !== 0 && dy !== 0) {
                const factor = 1 / Math.sqrt(2);
                dx *= factor;
                dy *= factor;
            }

            if (dx !== 0 || dy !== 0) {
                this.localPlayer.x += dx;
                this.localPlayer.y += dy;

                if (ws.readyState === WebSocket.OPEN) {
                    ws.send(JSON.stringify({
                        x: this.localPlayer.x,
                        y: this.localPlayer.y
                    }));
                }
            }
        }
    }
}

let game;
let ws;

function startGame() {
    const playerName = document.getElementById('playerName').value;
    const playerColor = document.getElementById('playerColor').value;
    const controlType = document.querySelector('input[name="control"]:checked').value;

    if (!playerName) {
        alert('Por favor, insira seu nome!');
        return;
    }

    document.getElementById('login').classList.add('hidden');
    document.getElementById('game').classList.remove('hidden');

    game = new Game();
    game.controlType = controlType;

    if (controlType === 'keyboard') {
        game.setupKeyboardControls();
    } else {
        document.addEventListener('mousemove', handleMouseMove);
    }
    
    ws = new WebSocket('ws://localhost:8765');
    
    ws.onopen = () => {
        ws.send(JSON.stringify({
            name: playerName,
            color: playerColor
        }));
    };

    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        
        if (data.eliminated) {
            game.eliminated = true;
            game.finalScore = data.finalScore;  // Guarda a pontuação final
            return;
        }

        game.players = data.players;
        game.food = data.food;
        
        const localPlayerObj = Object.values(game.players).find(
            p => p.name === playerName && p.color === playerColor
        );
        
        if (localPlayerObj && !game.localPlayer) {
            game.localPlayer = localPlayerObj;
            console.log("Jogador local definido:", game.localPlayer);
        }
        
        game.updateRanking();
    };

    gameLoop();
}

// Função separada para lidar com o movimento do mouse
function handleMouseMove(event) {
    if (game && game.localPlayer) {
        const mouseX = event.clientX;
        const mouseY = event.clientY;
        
        // Calcula direção do movimento
        const dx = mouseX - window.innerWidth / 2;
        const dy = mouseY - window.innerHeight / 2;
        const length = Math.sqrt(dx * dx + dy * dy);
        
        if (length > 0) {
            const speed = 5;
            game.localPlayer.x += (dx / length) * speed;
            game.localPlayer.y += (dy / length) * speed;
            
            // Envia a nova posição para o servidor
            if (ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({
                    x: game.localPlayer.x,
                    y: game.localPlayer.y
                }));
            }
        }
    }
}

function gameLoop() {
    if (game) {
        game.updatePlayerPosition();
        game.updateCamera();
        game.draw();
    }
    requestAnimationFrame(gameLoop);
} 