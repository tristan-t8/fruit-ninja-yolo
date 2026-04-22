"""
Fruit Ninja YOLO - Browser Game Page
Separate module with the full HTML game
"""

GAME_PAGE_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>🍉 Fruit Ninja - Hand Detection</title>
    <meta charset="UTF-8">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; user-select: none; }
        body {
            font-family: 'Arial Black', sans-serif;
            background: linear-gradient(180deg, #1a0033 0%, #000814 100%);
            color: white;
            overflow: hidden;
            height: 100vh;
        }
        #game-container {
            position: relative;
            width: 100vw;
            height: 100vh;
            overflow: hidden;
        }
        #video {
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            object-fit: cover;
            transform: scaleX(-1);
            opacity: 0.3;
            z-index: 1;
        }
        #game-canvas {
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            z-index: 2;
        }
        #ui-overlay {
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            z-index: 3;
            pointer-events: none;
        }
        #hud {
            position: absolute;
            top: 20px;
            left: 20px;
            right: 20px;
            display: flex;
            justify-content: space-between;
            font-size: 32px;
            text-shadow: 2px 2px 4px black, -1px -1px 0 black;
        }
        #score { color: #ffd700; }
        #lives { color: #ff4444; }
        #combo {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            font-size: 80px;
            color: #ff6b35;
            text-shadow: 4px 4px 0 black, -2px -2px 0 black;
            opacity: 0;
            transition: opacity 0.3s;
            pointer-events: none;
        }
        #combo.show { opacity: 1; }
        #start-screen, #game-over {
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.85);
            z-index: 4;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            pointer-events: auto;
            padding: 20px;
            text-align: center;
        }
        #game-over { display: none; }
        h1 {
            font-size: 72px;
            background: linear-gradient(90deg, #ff6b35, #ffd700);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 20px;
            text-shadow: none;
        }
        h2 { font-size: 48px; margin-bottom: 20px; color: #ffd700; }
        p { font-size: 20px; margin-bottom: 15px; max-width: 600px; line-height: 1.5; }
        button {
            background: linear-gradient(135deg, #ff6b35, #f7931e);
            color: white;
            border: none;
            padding: 20px 60px;
            border-radius: 50px;
            font-size: 28px;
            font-weight: bold;
            cursor: pointer;
            margin-top: 30px;
            box-shadow: 0 8px 16px rgba(0,0,0,0.4);
            transition: transform 0.2s;
            font-family: inherit;
        }
        button:hover { transform: scale(1.05); }
        button:disabled { background: #666; cursor: not-allowed; }
        #status {
            font-size: 14px;
            color: #888;
            margin-top: 20px;
        }
        .connected { color: #4caf50 !important; }
        .disconnected { color: #f44336 !important; }
        #hand-indicator {
            position: absolute;
            width: 40px;
            height: 40px;
            border-radius: 50%;
            border: 4px solid #00ff00;
            pointer-events: none;
            z-index: 3;
            transform: translate(-50%, -50%);
            box-shadow: 0 0 20px #00ff00;
            display: none;
        }
        .instruction {
            background: rgba(255, 107, 53, 0.2);
            border: 2px solid #ff6b35;
            padding: 15px 25px;
            border-radius: 10px;
            margin: 10px 0;
        }
        #final-score { font-size: 64px; color: #ffd700; margin: 20px 0; }
    </style>
</head>
<body>
    <div id="game-container">
        <video id="video" autoplay muted playsinline></video>
        <canvas id="game-canvas"></canvas>

        <div id="ui-overlay">
            <div id="hud">
                <div>Score: <span id="score">0</span></div>
                <div>Lives: <span id="lives">❤️❤️❤️</span></div>
            </div>
            <div id="combo"></div>
            <div id="hand-indicator"></div>
        </div>

        <!-- Start Screen -->
        <div id="start-screen">
            <h1>🍉 FRUIT NINJA 🍉</h1>
            <h2>Hand Detection Edition</h2>
            <div class="instruction">
                <p>✋ Move your hand in front of the webcam to slice fruits!</p>
                <p>💣 AVOID bombs or lose a life!</p>
                <p>🔥 Chain slices for combo bonuses!</p>
            </div>
            <p>Powered by YOLO + Your GPU</p>
            <button id="start-btn">START GAME</button>
            <p id="status">Connecting to backend...</p>
        </div>

        <!-- Game Over Screen -->
        <div id="game-over">
            <h1>GAME OVER</h1>
            <div id="final-score">0</div>
            <p id="high-score-msg"></p>
            <button id="restart-btn">PLAY AGAIN</button>
        </div>
    </div>

    <script>
        // ============================================================
        // CONFIGURATION
        // ============================================================
        const SERVER_URL = window.location.origin;
        const DETECT_INTERVAL = 150; // ms between detections
        const FRUIT_SPAWN_INTERVAL = 1200; // ms between fruit spawns
        const BOMB_CHANCE = 0.15;

        // ============================================================
        // GAME STATE
        // ============================================================
        const game = {
            score: 0,
            lives: 3,
            highScore: parseInt(localStorage.getItem('fruitNinjaHighScore') || '0'),
            running: false,
            fruits: [],
            particles: [],
            handPos: null,
            prevHandPos: null,
            handTrail: [],
            combo: 0,
            comboTimer: 0,
            lastSpawn: 0,
            lastDetect: 0,
            detecting: false
        };

        // ============================================================
        // CANVAS SETUP
        // ============================================================
        const canvas = document.getElementById('game-canvas');
        const ctx = canvas.getContext('2d');
        const video = document.getElementById('video');
        const handIndicator = document.getElementById('hand-indicator');

        function resizeCanvas() {
            canvas.width = window.innerWidth;
            canvas.height = window.innerHeight;
        }
        resizeCanvas();
        window.addEventListener('resize', resizeCanvas);

        // ============================================================
        // FRUIT TYPES
        // ============================================================
        const FRUIT_TYPES = [
            { emoji: '🍎', name: 'apple', points: 10, color: '#ff3333' },
            { emoji: '🍊', name: 'orange', points: 10, color: '#ff9933' },
            { emoji: '🍋', name: 'lemon', points: 15, color: '#ffeb3b' },
            { emoji: '🍉', name: 'watermelon', points: 20, color: '#4caf50' },
            { emoji: '🍌', name: 'banana', points: 10, color: '#ffeb3b' },
            { emoji: '🍓', name: 'strawberry', points: 15, color: '#e91e63' },
            { emoji: '🍇', name: 'grapes', points: 15, color: '#9c27b0' },
            { emoji: '🥝', name: 'kiwi', points: 15, color: '#8bc34a' },
            { emoji: '🍑', name: 'peach', points: 20, color: '#ffab40' },
            { emoji: '🍍', name: 'pineapple', points: 25, color: '#fdd835' }
        ];
        const BOMB = { emoji: '💣', name: 'bomb', points: -50, color: '#333' };

        // ============================================================
        // FRUIT CLASS
        // ============================================================
        class Fruit {
            constructor(isBomb = false) {
                this.isBomb = isBomb;
                this.type = isBomb ? BOMB : FRUIT_TYPES[Math.floor(Math.random() * FRUIT_TYPES.length)];
                this.x = Math.random() * (canvas.width - 100) + 50;
                this.y = canvas.height + 50;
                this.vx = (Math.random() - 0.5) * 6;
                this.vy = -(15 + Math.random() * 8);
                this.size = 70 + Math.random() * 20;
                this.rotation = 0;
                this.rotationSpeed = (Math.random() - 0.5) * 0.15;
                this.sliced = false;
                this.gravity = 0.4;
            }

            update() {
                this.x += this.vx;
                this.y += this.vy;
                this.vy += this.gravity;
                this.rotation += this.rotationSpeed;
            }

            draw() {
                ctx.save();
                ctx.translate(this.x, this.y);
                ctx.rotate(this.rotation);
                ctx.font = `${this.size}px Arial`;
                ctx.textAlign = 'center';
                ctx.textBaseline = 'middle';
                if (this.isBomb) {
                    ctx.shadowColor = '#ff0000';
                    ctx.shadowBlur = 20;
                }
                ctx.fillText(this.type.emoji, 0, 0);
                ctx.restore();
            }

            isOffScreen() {
                return this.y > canvas.height + 100;
            }

            checkCollision(x, y, radius = 60) {
                const dx = this.x - x;
                const dy = this.y - y;
                return Math.sqrt(dx * dx + dy * dy) < radius + this.size / 2;
            }
        }

        // ============================================================
        // PARTICLE EFFECTS
        // ============================================================
        class Particle {
            constructor(x, y, color, emoji = null) {
                this.x = x;
                this.y = y;
                this.vx = (Math.random() - 0.5) * 12;
                this.vy = (Math.random() - 0.5) * 12 - 3;
                this.life = 1.0;
                this.color = color;
                this.emoji = emoji;
                this.size = emoji ? 30 + Math.random() * 20 : 5 + Math.random() * 8;
                this.gravity = 0.3;
            }

            update() {
                this.x += this.vx;
                this.y += this.vy;
                this.vy += this.gravity;
                this.life -= 0.02;
            }

            draw() {
                ctx.save();
                ctx.globalAlpha = this.life;
                if (this.emoji) {
                    ctx.font = `${this.size}px Arial`;
                    ctx.textAlign = 'center';
                    ctx.fillText(this.emoji, this.x, this.y);
                } else {
                    ctx.fillStyle = this.color;
                    ctx.beginPath();
                    ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2);
                    ctx.fill();
                }
                ctx.restore();
            }
        }

        // ============================================================
        // BACKEND COMMUNICATION
        // ============================================================
        async function checkBackend() {
            try {
                const res = await fetch(SERVER_URL + '/health');
                const data = await res.json();
                const statusEl = document.getElementById('status');
                if (data.status === 'healthy' && data.models_loaded) {
                    statusEl.textContent = `✓ Backend ready (${data.device})`;
                    statusEl.className = 'connected';
                    document.getElementById('start-btn').disabled = false;
                    return true;
                } else {
                    statusEl.textContent = '⚠ Backend loading...';
                    return false;
                }
            } catch (e) {
                document.getElementById('status').textContent = '✗ Backend offline';
                document.getElementById('status').className = 'disconnected';
                return false;
            }
        }

        async function detectHand() {
            if (game.detecting || !video.videoWidth) return;
            game.detecting = true;

            try {
                // Capture current frame
                const tmpCanvas = document.createElement('canvas');
                tmpCanvas.width = 320; // smaller for speed
                tmpCanvas.height = 240;
                const tmpCtx = tmpCanvas.getContext('2d');
                tmpCtx.drawImage(video, 0, 0, 320, 240);
                const imageData = tmpCanvas.toDataURL('image/jpeg', 0.6).split(',')[1];

                const res = await fetch(SERVER_URL + '/detect', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({image: imageData})
                });
                const data = await res.json();

                if (data.detections && data.detections.length > 0) {
                    // Get the most confident detection
                    const best = data.detections.reduce((a, b) =>
                        a.confidence > b.confidence ? a : b
                    );

                    // Map from 320x240 detection to canvas coordinates
                    // Mirror X because video is mirrored
                    const scaleX = canvas.width / 320;
                    const scaleY = canvas.height / 240;
                    const x = canvas.width - (best.center[0] * scaleX);
                    const y = best.center[1] * scaleY;

                    game.prevHandPos = game.handPos;
                    game.handPos = { x, y };

                    // Update hand trail
                    game.handTrail.push({ x, y, time: Date.now() });
                    if (game.handTrail.length > 10) game.handTrail.shift();

                    // Show hand indicator
                    handIndicator.style.display = 'block';
                    handIndicator.style.left = x + 'px';
                    handIndicator.style.top = y + 'px';
                } else {
                    game.handPos = null;
                    handIndicator.style.display = 'none';
                }
            } catch (e) {
                console.error('Detection error:', e);
            } finally {
                game.detecting = false;
            }
        }

        // ============================================================
        // GAME LOGIC
        // ============================================================
        function spawnFruit() {
            const isBomb = Math.random() < BOMB_CHANCE;
            game.fruits.push(new Fruit(isBomb));
        }

        function sliceFruit(fruit) {
            if (fruit.sliced) return;
            fruit.sliced = true;

            // Create particles
            for (let i = 0; i < 8; i++) {
                game.particles.push(new Particle(fruit.x, fruit.y, fruit.type.color));
            }
            // Fruit chunks
            for (let i = 0; i < 3; i++) {
                game.particles.push(new Particle(fruit.x, fruit.y, fruit.type.color, fruit.type.emoji));
            }

            if (fruit.isBomb) {
                // Bomb hit!
                game.lives--;
                updateLives();
                game.combo = 0;
                screenShake();
                if (game.lives <= 0) endGame();
            } else {
                // Fruit sliced!
                game.combo++;
                game.comboTimer = 60;
                const points = fruit.type.points * (1 + game.combo * 0.1);
                game.score += Math.floor(points);
                updateScore();

                if (game.combo >= 3) {
                    showCombo(game.combo);
                }
            }
        }

        function checkSlicing() {
            if (!game.handPos || !game.prevHandPos) return;

            // Calculate hand velocity
            const dx = game.handPos.x - game.prevHandPos.x;
            const dy = game.handPos.y - game.prevHandPos.y;
            const velocity = Math.sqrt(dx * dx + dy * dy);

            // Only slice if hand is moving fast enough
            if (velocity < 15) return;

            // Check all fruits along the hand's path
            for (const fruit of game.fruits) {
                if (fruit.sliced) continue;
                // Check multiple points along the hand's path
                for (let t = 0; t <= 1; t += 0.2) {
                    const x = game.prevHandPos.x + dx * t;
                    const y = game.prevHandPos.y + dy * t;
                    if (fruit.checkCollision(x, y)) {
                        sliceFruit(fruit);
                        break;
                    }
                }
            }
        }

        function updateScore() {
            document.getElementById('score').textContent = game.score;
        }

        function updateLives() {
            document.getElementById('lives').textContent = '❤️'.repeat(Math.max(0, game.lives));
        }

        function showCombo(count) {
            const el = document.getElementById('combo');
            el.textContent = `${count}x COMBO!`;
            el.classList.add('show');
            setTimeout(() => el.classList.remove('show'), 800);
        }

        function screenShake() {
            canvas.style.transition = 'transform 0.1s';
            canvas.style.transform = 'translate(10px, 5px)';
            setTimeout(() => canvas.style.transform = 'translate(-8px, -3px)', 50);
            setTimeout(() => canvas.style.transform = 'translate(0, 0)', 150);
        }

        // ============================================================
        // RENDER LOOP
        // ============================================================
        function drawHandTrail() {
            if (game.handTrail.length < 2) return;
            const now = Date.now();

            ctx.save();
            ctx.lineCap = 'round';
            ctx.lineJoin = 'round';

            for (let i = 1; i < game.handTrail.length; i++) {
                const age = (now - game.handTrail[i].time) / 500;
                const alpha = Math.max(0, 1 - age);
                const width = Math.max(2, 20 * alpha);

                ctx.strokeStyle = `rgba(255, 255, 255, ${alpha * 0.8})`;
                ctx.lineWidth = width;
                ctx.beginPath();
                ctx.moveTo(game.handTrail[i - 1].x, game.handTrail[i - 1].y);
                ctx.lineTo(game.handTrail[i].x, game.handTrail[i].y);
                ctx.stroke();

                // Glow
                ctx.strokeStyle = `rgba(100, 200, 255, ${alpha * 0.5})`;
                ctx.lineWidth = width * 2;
                ctx.beginPath();
                ctx.moveTo(game.handTrail[i - 1].x, game.handTrail[i - 1].y);
                ctx.lineTo(game.handTrail[i].x, game.handTrail[i].y);
                ctx.stroke();
            }
            ctx.restore();

            // Clean up old trail points
            const cutoff = now - 500;
            game.handTrail = game.handTrail.filter(p => p.time > cutoff);
        }

        function gameLoop() {
            if (!game.running) return;

            ctx.clearRect(0, 0, canvas.width, canvas.height);

            // Spawn fruits
            const now = Date.now();
            if (now - game.lastSpawn > FRUIT_SPAWN_INTERVAL) {
                // Spawn 1-3 fruits at once for variety
                const count = Math.random() < 0.3 ? 2 : 1;
                for (let i = 0; i < count; i++) {
                    setTimeout(() => spawnFruit(), i * 150);
                }
                game.lastSpawn = now;
            }

            // Detect hand
            if (now - game.lastDetect > DETECT_INTERVAL) {
                detectHand();
                game.lastDetect = now;
            }

            // Check slicing
            checkSlicing();

            // Update and draw fruits
            game.fruits = game.fruits.filter(f => {
                f.update();
                if (!f.sliced) f.draw();

                // Missed fruit (not bomb) = lose life
                if (f.isOffScreen()) {
                    if (!f.sliced && !f.isBomb) {
                        game.lives--;
                        updateLives();
                        if (game.lives <= 0) endGame();
                    }
                    return false;
                }
                return !f.sliced;
            });

            // Update and draw particles
            game.particles = game.particles.filter(p => {
                p.update();
                p.draw();
                return p.life > 0;
            });

            // Draw hand trail
            drawHandTrail();

            // Decay combo
            if (game.comboTimer > 0) {
                game.comboTimer--;
                if (game.comboTimer === 0) game.combo = 0;
            }

            requestAnimationFrame(gameLoop);
        }

        // ============================================================
        // GAME CONTROL
        // ============================================================
        async function startGame() {
            try {
                // Start camera
                const stream = await navigator.mediaDevices.getUserMedia({
                    video: { width: 640, height: 480, facingMode: 'user' }
                });
                video.srcObject = stream;

                // Wait for video to be ready
                await new Promise(resolve => {
                    video.onloadedmetadata = () => resolve();
                });

                // Reset game state
                game.score = 0;
                game.lives = 3;
                game.fruits = [];
                game.particles = [];
                game.handTrail = [];
                game.combo = 0;
                game.running = true;
                game.lastSpawn = Date.now();
                game.lastDetect = Date.now();

                updateScore();
                updateLives();

                // Hide start screen
                document.getElementById('start-screen').style.display = 'none';
                document.getElementById('game-over').style.display = 'none';

                // Start game loop
                gameLoop();
            } catch (e) {
                alert('Camera access required: ' + e.message);
            }
        }

        function endGame() {
            game.running = false;
            document.getElementById('final-score').textContent = game.score;

            if (game.score > game.highScore) {
                game.highScore = game.score;
                localStorage.setItem('fruitNinjaHighScore', game.score);
                document.getElementById('high-score-msg').textContent =
                    '🏆 NEW HIGH SCORE! 🏆';
            } else {
                document.getElementById('high-score-msg').textContent =
                    `High Score: ${game.highScore}`;
            }

            document.getElementById('game-over').style.display = 'flex';
        }

        // ============================================================
        // EVENT LISTENERS
        // ============================================================
        document.getElementById('start-btn').onclick = startGame;
        document.getElementById('restart-btn').onclick = startGame;

        // Initial backend check
        checkBackend();
        setInterval(checkBackend, 5000);
    </script>
</body>
</html>
"""
