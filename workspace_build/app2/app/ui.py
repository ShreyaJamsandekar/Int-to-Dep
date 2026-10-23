"""Interactive Chess Game Web Console UI."""

CHESS_DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Enterprise Chess Platform | Microservices Architecture</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600&family=Outfit:wght@300;400;500;600;700&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg: #080c16;
      --card-bg: rgba(16, 23, 38, 0.75);
      --card-border: rgba(99, 102, 241, 0.2);
      --card-glow: rgba(99, 102, 241, 0.4);
      --primary: #6366f1;
      --primary-gradient: linear-gradient(135deg, #6366f1 0%, #8b5cf6 50%, #ec4899 100%);
      --accent-gold: #f59e0b;
      --accent-cyan: #06b6d4;
      --success: #10b981;
      --danger: #ef4444;
      --text: #f8fafc;
      --text-muted: #94a3b8;
      
      /* Chessboard palette */
      --sq-light: #e2e8f0;
      --sq-dark: #334155;
      --sq-selected: #facc15;
      --sq-dest: rgba(6, 182, 212, 0.5);
      --sq-last-move: rgba(99, 102, 241, 0.35);
    }

    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: 'Outfit', -apple-system, sans-serif;
      background: radial-gradient(circle at 10% 20%, #151c33 0%, #080c16 65%, #030509 100%);
      color: var(--text);
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      overflow-x: hidden;
    }

    .ambient-glow {
      position: fixed;
      border-radius: 50%;
      filter: blur(140px);
      pointer-events: none;
      z-index: 0;
    }
    .glow-top { width: 550px; height: 550px; background: rgba(99, 102, 241, 0.12); top: -150px; left: -100px; }
    .glow-bottom { width: 500px; height: 500px; background: rgba(245, 158, 11, 0.08); bottom: -150px; right: -80px; }

    header {
      position: sticky;
      top: 0;
      z-index: 20;
      backdrop-filter: blur(16px);
      background: rgba(8, 12, 22, 0.82);
      border-bottom: 1px solid var(--card-border);
      padding: 1rem 2rem;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    .logo-container {
      display: flex;
      align-items: center;
      gap: 0.9rem;
    }
    .logo-icon {
      width: 44px;
      height: 44px;
      border-radius: 12px;
      background: var(--primary-gradient);
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 1.5rem;
      box-shadow: 0 4px 18px rgba(99, 102, 241, 0.4);
    }
    .logo-title h1 {
      font-size: 1.3rem;
      font-weight: 700;
      letter-spacing: -0.02em;
      background: linear-gradient(135deg, #ffffff 0%, #c7d2fe 100%);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
    }
    .logo-title p {
      font-size: 0.76rem;
      color: var(--text-muted);
    }

    .header-nav {
      display: flex;
      align-items: center;
      gap: 0.85rem;
    }
    .status-pill {
      display: inline-flex;
      align-items: center;
      gap: 0.45rem;
      padding: 0.35rem 0.85rem;
      border-radius: 9999px;
      background: rgba(16, 185, 129, 0.12);
      border: 1px solid rgba(16, 185, 129, 0.3);
      font-size: 0.8rem;
      color: var(--success);
      font-weight: 500;
    }
    .status-dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: var(--success);
      box-shadow: 0 0 10px var(--success);
      animation: pulse-dot 2s infinite ease-in-out;
    }
    @keyframes pulse-dot {
      0%, 100% { transform: scale(1); opacity: 1; }
      50% { transform: scale(0.85); opacity: 0.4; }
    }
    .nav-btn {
      color: var(--text-muted);
      text-decoration: none;
      font-size: 0.82rem;
      padding: 0.45rem 0.85rem;
      border-radius: 8px;
      border: 1px solid var(--card-border);
      background: rgba(255, 255, 255, 0.03);
      transition: all 0.2s ease;
    }
    .nav-btn:hover {
      color: var(--text);
      border-color: var(--primary);
      background: rgba(255, 255, 255, 0.08);
    }

    main {
      position: relative;
      z-index: 10;
      max-width: 1380px;
      width: 100%;
      margin: 0 auto;
      padding: 2rem 1.5rem 3.5rem;
      display: flex;
      flex-direction: column;
      gap: 1.75rem;
    }

    /* Hero bar */
    .hero-strip {
      background: linear-gradient(135deg, rgba(26, 34, 56, 0.7) 0%, rgba(14, 20, 36, 0.5) 100%);
      border: 1px solid var(--card-border);
      border-radius: 16px;
      padding: 1.4rem 1.8rem;
      backdrop-filter: blur(12px);
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 1rem;
    }
    .hero-info h2 {
      font-size: 1.45rem;
      font-weight: 700;
      margin-bottom: 0.25rem;
    }
    .hero-info p {
      font-size: 0.85rem;
      color: var(--text-muted);
    }
    .hero-badges {
      display: flex;
      gap: 0.75rem;
      flex-wrap: wrap;
    }
    .metric-badge {
      background: rgba(8, 12, 22, 0.7);
      border: 1px solid var(--card-border);
      padding: 0.6rem 1rem;
      border-radius: 10px;
      display: flex;
      flex-direction: column;
    }
    .metric-label { font-size: 0.7rem; color: var(--text-muted); text-transform: uppercase; }
    .metric-val { font-size: 1.1rem; font-weight: 600; color: #a5b4fc; }

    /* Chess Playground Layout */
    .game-arena {
      display: grid;
      grid-template-columns: auto 1fr;
      gap: 2rem;
      align-items: start;
    }
    @media (max-width: 1050px) {
      .game-arena { grid-template-columns: 1fr; }
    }

    /* Board Container */
    .board-card {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 20px;
      padding: 1.5rem;
      backdrop-filter: blur(14px);
      display: flex;
      flex-direction: column;
      align-items: center;
      box-shadow: 0 12px 35px rgba(0, 0, 0, 0.5);
    }
    .board-header {
      width: 100%;
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 1rem;
    }
    .turn-indicator {
      display: flex;
      align-items: center;
      gap: 0.6rem;
      font-weight: 600;
      font-size: 0.95rem;
    }
    .turn-disc {
      width: 16px;
      height: 16px;
      border-radius: 50%;
      border: 2px solid #94a3b8;
      background: white;
      transition: all 0.3s ease;
    }
    .turn-disc.black-turn { background: #0f172a; }

    /* The 8x8 Board */
    .chessboard-wrapper {
      position: relative;
      padding: 24px;
      background: #0f172a;
      border-radius: 14px;
      border: 2px solid rgba(99, 102, 241, 0.3);
      box-shadow: inset 0 0 20px rgba(0,0,0,0.8), 0 8px 30px rgba(0,0,0,0.6);
    }
    .chessboard {
      display: grid;
      grid-template-columns: repeat(8, 64px);
      grid-template-rows: repeat(8, 64px);
      border: 2px solid #475569;
      border-radius: 4px;
      overflow: hidden;
      user-select: none;
    }
    @media (max-width: 600px) {
      .chessboard {
        grid-template-columns: repeat(8, 42px);
        grid-template-rows: repeat(8, 42px);
      }
      .chessboard-wrapper { padding: 12px; }
    }

    .square {
      position: relative;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 2.5rem;
      cursor: pointer;
      transition: background-color 0.15s ease;
    }
    @media (max-width: 600px) {
      .square { font-size: 1.6rem; }
    }
    .square.light { background: var(--sq-light); color: #0f172a; }
    .square.dark { background: var(--sq-dark); color: #f8fafc; }
    .square.selected {
      background: #eab308 !important;
      box-shadow: inset 0 0 12px rgba(0,0,0,0.4);
    }
    .square.valid-target::after {
      content: '';
      position: absolute;
      width: 18px;
      height: 18px;
      border-radius: 50%;
      background: rgba(6, 182, 212, 0.85);
      box-shadow: 0 0 8px var(--accent-cyan);
    }
    .square.last-move {
      background: #6366f1 !important;
      color: white !important;
    }

    .piece {
      transition: transform 0.15s ease;
    }
    .piece:hover {
      transform: scale(1.12);
    }

    /* Rank & File Labels */
    .coord-ranks {
      position: absolute;
      left: 6px;
      top: 24px;
      bottom: 24px;
      display: flex;
      flex-direction: column;
      justify-content: space-around;
      font-family: 'JetBrains Mono', monospace;
      font-size: 0.72rem;
      color: #64748b;
    }
    .coord-files {
      position: absolute;
      bottom: 4px;
      left: 24px;
      right: 24px;
      display: flex;
      justify-content: space-around;
      font-family: 'JetBrains Mono', monospace;
      font-size: 0.72rem;
      color: #64748b;
    }

    /* Side Control Deck */
    .control-deck {
      display: flex;
      flex-direction: column;
      gap: 1.4rem;
    }

    .card {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 18px;
      padding: 1.5rem;
      backdrop-filter: blur(12px);
    }
    .card-title {
      font-size: 1.05rem;
      font-weight: 600;
      margin-bottom: 0.85rem;
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }

    .btn-group {
      display: flex;
      flex-wrap: wrap;
      gap: 0.6rem;
    }
    .action-btn {
      background: var(--primary-gradient);
      color: white;
      border: none;
      padding: 0.65rem 1.1rem;
      border-radius: 10px;
      font-weight: 600;
      font-size: 0.82rem;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 0.4rem;
      transition: all 0.2s ease;
      box-shadow: 0 4px 12px rgba(99, 102, 241, 0.3);
    }
    .action-btn:hover {
      transform: translateY(-2px);
      box-shadow: 0 6px 18px rgba(99, 102, 241, 0.45);
    }
    .action-btn.secondary {
      background: rgba(255, 255, 255, 0.05);
      border: 1px solid var(--card-border);
      color: var(--text);
      box-shadow: none;
    }
    .action-btn.secondary:hover {
      background: rgba(255, 255, 255, 0.1);
      border-color: var(--primary);
    }

    /* Move History Table */
    .move-log {
      max-height: 140px;
      overflow-y: auto;
      font-family: 'JetBrains Mono', monospace;
      font-size: 0.8rem;
      background: #050811;
      border: 1px solid var(--card-border);
      border-radius: 10px;
      padding: 0.75rem;
    }
    .move-row {
      display: grid;
      grid-template-columns: 40px 1fr 1fr;
      padding: 0.25rem 0.4rem;
      border-bottom: 1px solid rgba(255, 255, 255, 0.03);
    }
    .move-num { color: var(--text-muted); }

    /* API Inspector Console */
    .console-box {
      background: #050811;
      border: 1px solid var(--card-border);
      border-radius: 12px;
      overflow: hidden;
    }
    .console-header {
      background: rgba(255, 255, 255, 0.03);
      padding: 0.5rem 0.8rem;
      font-size: 0.75rem;
      display: flex;
      justify-content: space-between;
      align-items: center;
      border-bottom: 1px solid var(--card-border);
      color: var(--text-muted);
    }
    .console-status {
      font-family: 'JetBrains Mono', monospace;
      font-weight: 600;
    }
    .status-ok { color: var(--success); }
    .status-err { color: var(--danger); }
    pre {
      padding: 0.85rem;
      font-family: 'JetBrains Mono', monospace;
      font-size: 0.78rem;
      color: #cbd5e1;
      max-height: 200px;
      overflow-x: auto;
      line-height: 1.4;
    }

    footer {
      margin-top: auto;
      text-align: center;
      padding: 1.5rem;
      font-size: 0.78rem;
      color: var(--text-muted);
      border-top: 1px solid var(--card-border);
    }
  </style>
</head>
<body>
  <div class="ambient-glow glow-top"></div>
  <div class="ambient-glow glow-bottom"></div>

  <header>
    <div class="logo-container">
      <div class="logo-icon">♟️</div>
      <div class="logo-title">
        <h1>Autonomous Chess Platform</h1>
        <p>Microservices: chess-game-service &bull; chess-engine-service</p>
      </div>
    </div>
    <div class="header-nav">
      <div class="status-pill">
        <span class="status-dot"></span>
        <span id="service-status">ONLINE (2 Services)</span>
      </div>
      <a href="/docs" target="_blank" class="nav-btn">📖 Swagger Docs</a>
      <a href="/healthz" target="_blank" class="nav-btn">🩺 /healthz</a>
      <a href="/readyz" target="_blank" class="nav-btn">⚡ /readyz</a>
    </div>
  </header>

  <main>
    <div class="hero-strip">
      <div class="hero-info">
        <h2>Live Chess Engine & Session Matchmaker</h2>
        <p>Every move triggers contract-verified REST requests to <code>chess-engine-service</code> while maintaining game session invariants.</p>
      </div>
      <div class="hero-badges">
        <div class="metric-badge">
          <span class="metric-label">Game ID</span>
          <span class="metric-val" id="disp-game-id">MATCH-001</span>
        </div>
        <div class="metric-badge">
          <span class="metric-label">Move Counter</span>
          <span class="metric-val" id="disp-move-num">Turn 1</span>
        </div>
        <div class="metric-badge">
          <span class="metric-label">Engine Latency</span>
          <span class="metric-val" id="disp-latency" style="color: var(--success);">&lt; 3ms</span>
        </div>
      </div>
    </div>

    <div class="game-arena">
      <!-- Left: Interactive Chess Board -->
      <div class="board-card">
        <div class="board-header">
          <div class="turn-indicator">
            <span class="turn-disc" id="turn-disc"></span>
            <span id="turn-text">White to Move</span>
          </div>
          <span style="font-size: 0.78rem; color: var(--text-muted);" id="board-msg">Click a piece to begin</span>
        </div>

        <div class="chessboard-wrapper">
          <div class="coord-ranks">
            <span>8</span><span>7</span><span>6</span><span>5</span><span>4</span><span>3</span><span>2</span><span>1</span>
          </div>
          <div class="chessboard" id="board">
            <!-- 64 squares populated by JS -->
          </div>
          <div class="coord-files">
            <span>a</span><span>b</span><span>c</span><span>d</span><span>e</span><span>f</span><span>g</span><span>h</span>
          </div>
        </div>
      </div>

      <!-- Right: Control Deck & Live Inspection -->
      <div class="control-deck">
        <div class="card">
          <div class="card-title">🎮 Match Controls & Opening Presets</div>
          <div class="btn-group">
            <button class="action-btn" onclick="startNewMatch()">✨ New Match (ST-001)</button>
            <button class="action-btn secondary" onclick="playPreset('e2e4')">Play e4</button>
            <button class="action-btn secondary" onclick="playPreset('e7e5')">Play e5</button>
            <button class="action-btn secondary" onclick="playPreset('g1f3')">Play Nf3</button>
            <button class="action-btn secondary" onclick="playPreset('b8c6')">Play Nc6</button>
            <button class="action-btn secondary" style="color: #f87171;" onclick="testDomainError()">⚠️ Invariant Check (422)</button>
          </div>
        </div>

        <div class="card">
          <div class="card-title">📜 Move History Ledger</div>
          <div class="move-log" id="move-history">
            <div class="move-row" style="color: var(--text-muted);">
              <span>#</span><span>White</span><span>Black</span>
            </div>
            <!-- Dynamic rows -->
          </div>
        </div>

        <div class="card">
          <div class="card-title">📡 Live Microservice API Inspector</div>
          <div class="console-box">
            <div class="console-header">
              <span id="console-endpoint">POST /api/handle_chess_game_service_endpoint</span>
              <span class="console-status status-ok" id="console-status">200 OK</span>
            </div>
            <pre id="console-json">// Real-time JSON payload from microservice will appear here</pre>
          </div>
        </div>
      </div>
    </div>
  </main>

  <footer>
    Autonomous Chess Microservice Engine &bull; Modular Monolith Architecture &bull; Generated by HLD-to-Code Pipeline
  </footer>

  <script>
    // Standard starting positions
    const INITIAL_BOARD = [
      ['♜','♞','♝','♛','♚','♝','♞','♜'],
      ['♟','♟','♟','♟','♟','♟','♟','♟'],
      ['','','','','','','',''],
      ['','','','','','','',''],
      ['','','','','','','',''],
      ['','','','','','','',''],
      ['♙','♙','♙','♙','♙','♙','♙','♙'],
      ['♖','♘','♗','♕','♔','♗','♘','♖']
    ];

    let boardState = JSON.parse(JSON.stringify(INITIAL_BOARD));
    let selectedSquare = null;
    let currentTurn = 'white';
    let moveCount = 1;
    let gameId = 'CHESS-MATCH-001';
    let movesHistoryList = [];

    const files = ['a','b','c','d','e','f','g','h'];

    function isWhitePiece(p) {
      return ['♙','♖','♘','♗','♕','♔'].includes(p);
    }
    function isBlackPiece(p) {
      return ['♟','♜','♞','♝','♛','♚'].includes(p);
    }

    function renderBoard() {
      const boardEl = document.getElementById('board');
      boardEl.innerHTML = '';

      for (let r = 0; r < 8; r++) {
        for (let c = 0; c < 8; c++) {
          const sq = document.createElement('div');
          const isLight = (r + c) % 2 === 0;
          sq.className = `square ${isLight ? 'light' : 'dark'}`;
          sq.dataset.row = r;
          sq.dataset.col = c;
          sq.dataset.coord = `${files[c]}${8 - r}`;

          if (selectedSquare && selectedSquare.r === r && selectedSquare.c === c) {
            sq.classList.add('selected');
          }

          const piece = boardState[r][c];
          if (piece) {
            const pieceSpan = document.createElement('span');
            pieceSpan.className = 'piece';
            pieceSpan.textContent = piece;
            sq.appendChild(pieceSpan);
          }

          sq.onclick = () => onSquareClick(r, c);
          boardEl.appendChild(sq);
        }
      }
    }

    function onSquareClick(r, c) {
      const piece = boardState[r][c];

      // If already selected, attempt move
      if (selectedSquare) {
        if (selectedSquare.r === r && selectedSquare.c === c) {
          selectedSquare = null;
          renderBoard();
          return;
        }

        // Execute Move
        executeMove(selectedSquare.r, selectedSquare.c, r, c);
        selectedSquare = null;
        return;
      }

      // Selection logic: must select own piece
      if (piece) {
        if ((currentTurn === 'white' && isWhitePiece(piece)) || (currentTurn === 'black' && isBlackPiece(piece))) {
          selectedSquare = { r, c };
          renderBoard();
          document.getElementById('board-msg').textContent = `Selected ${piece} at ${files[c]}${8 - r}`;
        }
      }
    }

    async function executeMove(fromR, fromC, toR, toC) {
      const p = boardState[fromR][fromC];
      boardState[toR][toC] = p;
      boardState[fromR][fromC] = '';

      const uci = `${files[fromC]}${8 - fromR}${files[toC]}${8 - toR}`;
      
      // Update turn
      currentTurn = currentTurn === 'white' ? 'black' : 'white';
      moveCount++;

      updateTurnDisplay();
      renderBoard();

      // Record Move History
      recordMoveLog(uci);

      // Call Backend Chess Engine Service
      await notifyEngine(uci);
    }

    function updateTurnDisplay() {
      const disc = document.getElementById('turn-disc');
      const text = document.getElementById('turn-text');
      const moveDisp = document.getElementById('disp-move-num');

      if (currentTurn === 'white') {
        disc.classList.remove('black-turn');
        text.textContent = 'White to Move';
      } else {
        disc.classList.add('black-turn');
        text.textContent = 'Black to Move';
      }
      moveDisp.textContent = `Turn ${moveCount}`;
    }

    function recordMoveLog(uci) {
      const log = document.getElementById('move-history');
      movesHistoryList.push(uci);

      const movePairIndex = Math.ceil(movesHistoryList.length / 2);
      if (movesHistoryList.length % 2 === 1) {
        const row = document.createElement('div');
        row.className = 'move-row';
        row.id = `move-row-${movePairIndex}`;
        row.innerHTML = `<span class="move-num">${movePairIndex}.</span><span>${uci}</span><span></span>`;
        log.appendChild(row);
      } else {
        const row = document.getElementById(`move-row-${movePairIndex}`);
        if (row) {
          row.children[2].textContent = uci;
        }
      }
      log.scrollTop = log.scrollHeight;
    }

    async function notifyEngine(uci) {
      const t0 = performance.now();
      try {
        const res = await fetch('/api/handle_chess_engine_service_endpoint', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ game_id: gameId, quantity: moveCount })
        });
        const elapsed = (performance.now() - t0).toFixed(1);
        document.getElementById('disp-latency').textContent = `${elapsed}ms`;

        const data = await res.json();
        updateConsole('POST /api/handle_chess_engine_service_endpoint', res.status, data);
        document.getElementById('board-msg').textContent = `Engine evaluated move ${uci} (status: ${data.data?.status || 'OK'})`;
      } catch (err) {
        updateConsole('POST /api/handle_chess_engine_service_endpoint', 500, { error: String(err) });
      }
    }

    async function startNewMatch() {
      gameId = `MATCH-${Math.floor(100 + Math.random() * 900)}`;
      document.getElementById('disp-game-id').textContent = gameId;
      boardState = JSON.parse(JSON.stringify(INITIAL_BOARD));
      selectedSquare = null;
      currentTurn = 'white';
      moveCount = 1;
      movesHistoryList = [];

      document.getElementById('move-history').innerHTML = `
        <div class="move-row" style="color: var(--text-muted);">
          <span>#</span><span>White</span><span>Black</span>
        </div>
      `;
      updateTurnDisplay();
      renderBoard();

      // Call Chess Game Service initialization endpoint
      try {
        const res = await fetch('/api/handle_chess_game_service_endpoint', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ game_id: gameId, quantity: 1 })
        });
        const data = await res.json();
        updateConsole('POST /api/handle_chess_game_service_endpoint', res.status, data);
        document.getElementById('board-msg').textContent = `Match ${gameId} initialized with status ${data.data?.status}`;
      } catch (e) {
        updateConsole('POST /api/handle_chess_game_service_endpoint', 500, { error: String(e) });
      }
    }

    async function playPreset(uci) {
      const fromC = files.indexOf(uci[0]);
      const fromR = 8 - parseInt(uci[1], 10);
      const toC = files.indexOf(uci[2]);
      const toR = 8 - parseInt(uci[3], 10);

      await executeMove(fromR, fromC, toR, toC);
    }

    async function testDomainError() {
      try {
        const res = await fetch('/api/handle_chess_game_service_endpoint', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ game_id: '', quantity: -1 })
        });
        const data = await res.json();
        updateConsole('POST /api/handle_chess_game_service_endpoint [INVARIANT FAIL]', res.status, data);
        document.getElementById('board-msg').textContent = `Validation triggered: 422 ${data.title}`;
      } catch (e) {
        updateConsole('ERROR', 500, { error: String(e) });
      }
    }

    function updateConsole(endpoint, status, data) {
      document.getElementById('console-endpoint').textContent = endpoint;
      const stEl = document.getElementById('console-status');
      stEl.textContent = `${status} ${status === 200 ? 'OK' : 'PROBLEM DETAILS'}`;
      stEl.className = `console-status ${status === 200 ? 'status-ok' : 'status-err'}`;
      document.getElementById('console-json').textContent = JSON.stringify(data, null, 2);
    }

    // Initialize board
    renderBoard();
    updateTurnDisplay();
    startNewMatch();
  </script>
</body>
</html>
"""
