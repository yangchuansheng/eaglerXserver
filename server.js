import express from 'express';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();
const PORT = 3000;

app.use(express.json({ limit: '64mb' }));
app.use(express.urlencoded({ extended: true }));

// Serve 1.8 web client & admin
app.use('/1.8', express.static(path.join(__dirname, 'web-1.8')));

// Serve 1.12 web client & admin
app.use('/1.12', express.static(path.join(__dirname, 'web-1.12')));

// Fallback direct static access to web-1.12 for root assets (admin.css, admin.js, etc.) without intercepting root index
app.use(express.static(path.join(__dirname, 'web-1.12'), { index: false }));

// Admin direct redirects
app.get('/admin', (req, res) => {
  res.redirect('/1.12/admin.html');
});
app.get('/admin.html', (req, res) => {
  res.redirect('/1.12/admin.html');
});
app.get('/index.html', (req, res) => {
  res.redirect('/1.12/index.html');
});

// Dynmap proxy placeholder
app.get('/dynmap*', (req, res) => {
  res.send(`
    <!DOCTYPE html>
    <html>
      <head>
        <title>Dynmap View</title>
        <style>
          body { margin: 0; background: #0e1011; color: #3ECF8E; font-family: monospace; display: flex; align-items: center; justify-content: center; height: 100vh; flex-direction: column; }
          .card { border: 1px solid rgba(62,207,142,0.3); padding: 24px; border-radius: 8px; background: #161718; text-align: center; }
        </style>
      </head>
      <body>
        <div class="card">
          <h2>Dynmap Bridge</h2>
          <p>Dynmap is configured to proxy internal Paper port :8123.</p>
          <p style="color:#9e9e9e;font-size:12px;">Active in standalone / container runtime with Dynmap plugin enabled.</p>
        </div>
      </body>
    </html>
  `);
});

// In-memory state for admin demonstration & telemetry
let simulatedState = {
  minecraft_version: process.env.MINECRAFT_VERSION || '1.12.2',
  rcon_port: 25575,
  bridge_port: 3000,
  native_seed_finder_ready: true,
  weather: 'clear',
  time: 'day',
  difficulty: 'normal',
  gamemode: 'survival',
  rules: {
    doDaylightCycle: true,
    doWeatherCycle: true,
    doFireTick: true,
    doMobSpawning: true,
    doMobLoot: true,
    keepInventory: false,
    mobGriefing: true,
    naturalRegeneration: true,
    pvp: true,
    commandBlockOutput: true,
    showDeathMessages: true,
    saveToolbarActivator: true
  },
  online_players: ['Steve', 'Alex'],
  whitelist_enabled: false,
  whitelist: ['Steve', 'Alex'],
  seed: '5829104928104829104',
  plugins: [
    { name: 'EaglercraftXBungee.jar', state: 'active', size: '2.4 MB' },
    { name: 'Dynmap-3.4.jar', state: 'active', size: '8.1 MB' },
    { name: 'WorldEdit-6.1.9.jar', state: 'active', size: '1.2 MB' }
  ]
};

// API: Status
app.get('/api/status', (req, res) => {
  res.json({
    status: 'online',
    minecraft_version: simulatedState.minecraft_version,
    rcon_port: simulatedState.rcon_port,
    bridge_port: simulatedState.bridge_port,
    native_seed_finder_ready: simulatedState.native_seed_finder_ready
  });
});

// API: Login
app.post('/api/login', (req, res) => {
  const token = 'token-' + Math.random().toString(36).substring(2, 15);
  res.json({
    success: true,
    token: token,
    expires_at: Math.floor(Date.now() / 1000) + 28800
  });
});

// API: RCON Command execution
app.post('/api/rcon', (req, res) => {
  const cmd = (req.body && req.body.command ? req.body.command.trim() : '').toLowerCase();

  if (cmd === 'list') {
    const listStr = simulatedState.online_players.join(', ');
    return res.json({
      success: true,
      response: `There are ${simulatedState.online_players.length} of a max 20 players online: ${listStr}`
    });
  }
  if (cmd === 'tps') {
    return res.json({
      success: true,
      response: 'TPS from last 1m, 5m, 15m: 20.0, 19.9, 20.0'
    });
  }
  if (cmd === 'seed') {
    return res.json({
      success: true,
      response: `Seed: [${simulatedState.seed}]`
    });
  }
  if (cmd === 'save-all') {
    return res.json({
      success: true,
      response: 'Saved the world'
    });
  }
  if (cmd.startsWith('weather')) {
    const w = cmd.split(' ')[1] || 'clear';
    simulatedState.weather = w;
    return res.json({
      success: true,
      response: `Set weather to ${w}`
    });
  }
  if (cmd.startsWith('time set')) {
    const t = cmd.split(' ')[2] || 'day';
    simulatedState.time = t;
    return res.json({
      success: true,
      response: `Set the time to ${t}`
    });
  }
  if (cmd.startsWith('gamerule')) {
    const parts = cmd.split(' ');
    const rule = parts[1];
    const val = parts[2];
    if (rule && val !== undefined) {
      simulatedState.rules[rule] = val === 'true';
    }
    return res.json({
      success: true,
      response: `Game rule ${rule} has been updated to ${val}`
    });
  }

  return res.json({
    success: true,
    response: `Executed: ${req.body.command}`
  });
});

// API: Plugins
app.post('/api/plugins', (req, res) => {
  const action = req.body && req.body.action;
  if (action === 'delete') {
    const name = req.body.name;
    simulatedState.plugins = simulatedState.plugins.filter(p => p.name !== name);
    return res.json({ success: true, plugins: simulatedState.plugins });
  }
  res.json({
    success: true,
    plugins: simulatedState.plugins
  });
});

// API: World & Runtime State
app.post('/api/world-state', (req, res) => {
  res.json({
    success: true,
    world: {
      isRaining: simulatedState.weather === 'rain',
      isThundering: simulatedState.weather === 'thunder',
      time: simulatedState.time === 'night' ? 14000 : 1000,
      difficulty: simulatedState.difficulty
    }
  });
});

app.post('/api/runtime-state', (req, res) => {
  res.json({
    success: true,
    rules: simulatedState.rules,
    players: simulatedState.online_players
  });
});

app.post('/api/seed', (req, res) => {
  res.json({
    success: true,
    seed: simulatedState.seed
  });
});

app.post('/api/structures', (req, res) => {
  res.json({
    success: true,
    results: [
      { name: 'Village', x: 120, z: -240, distance: 268 },
      { name: 'Desert Temple', x: -450, z: 310, distance: 546 },
      { name: 'Stronghold', x: 890, z: 1240, distance: 1526 }
    ]
  });
});

app.post('/api/config', (req, res) => {
  res.json({
    success: true,
    config: {
      'server-port': 25565,
      'view-distance': 10,
      'max-players': 20,
      'motd': 'A Supabase-themed Eaglercraft Server'
    }
  });
});

// Root landing page: High-end Supabase-themed Hub
app.get('/', (req, res) => {
  res.send(`
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
  <title>EaglercraftX Server Portal</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Geist:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg: #0e1011;
      --surface-1: #161718;
      --surface-2: #1e2022;
      --border: rgba(255, 255, 255, 0.08);
      --border-strong: rgba(255, 255, 255, 0.16);
      --primary: #3ECF8E;
      --primary-hover: #4ade80;
      --on-primary: #0b1510;
      --text: #ededed;
      --text-muted: #8b929a;
      --font: "Geist", -apple-system, BlinkMacSystemFont, sans-serif;
      --mono: "JetBrains Mono", monospace;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    html, body {
      width: 100%;
      max-width: 100%;
      overflow-x: hidden;
    }
    body {
      font-family: var(--font);
      background-color: var(--bg);
      background-image:
        radial-gradient(ellipse 70% 40% at 50% -10%, rgba(62, 207, 142, 0.08), transparent 70%),
        linear-gradient(180deg, #0e1011 0%, #121416 100%);
      color: var(--text);
      min-height: 100vh;
      min-height: 100dvh;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 32px 20px;
    }
    h1 {
      font-size: 24px;
      font-weight: 600;
      letter-spacing: -0.02em;
      margin-bottom: 20px;
      text-align: center;
      color: #fff;
    }
    .grid {
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 12px;
      width: min(100%, 640px);
    }
    @media (max-width: 540px) {
      body {
        padding: max(24px, env(safe-area-inset-top)) 16px max(24px, env(safe-area-inset-bottom));
        justify-content: flex-start;
      }
      h1 {
        font-size: 20px;
        margin-top: 12px;
        margin-bottom: 16px;
      }
      .grid {
        grid-template-columns: 1fr;
        gap: 10px;
      }
      .card {
        padding: 14px 16px;
        min-height: 52px;
      }
      .card h2 {
        font-size: 14px;
      }
      .card.featured .card-btn {
        height: 36px;
        padding: 0 14px;
      }
      .footer-badge {
        margin-top: 24px;
      }
    }
    .card {
      background: var(--surface-1);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 16px 20px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      text-decoration: none;
      color: inherit;
      transition: border-color 0.15s ease, background-color 0.15s ease;
    }
    .card:hover {
      border-color: rgba(62, 207, 142, 0.4);
      background-color: var(--surface-2);
    }
    .card.featured {
      grid-column: 1 / -1;
      border-color: rgba(62, 207, 142, 0.35);
      background: linear-gradient(180deg, #181c1a 0%, #151718 100%);
    }
    .card.featured:hover {
      border-color: var(--primary);
    }
    .card-left {
      display: flex;
      align-items: center;
      gap: 10px;
    }
    .card h2 {
      font-size: 15px;
      font-weight: 600;
      color: #fff;
      letter-spacing: -0.01em;
    }
    .version-tag {
      font-family: var(--mono);
      font-size: 11px;
      padding: 2px 7px;
      border-radius: 4px;
      background: rgba(255, 255, 255, 0.06);
      color: var(--text-muted);
      font-weight: 500;
      border: 1px solid rgba(255, 255, 255, 0.06);
    }
    .card-cta {
      display: inline-flex;
      align-items: center;
      gap: 4px;
      font-size: 13px;
      font-weight: 500;
      color: var(--primary);
      white-space: nowrap;
    }
    .card.featured .card-btn {
      height: 32px;
      padding: 0 14px;
      background: var(--primary);
      color: var(--on-primary);
      border-radius: 6px;
      font-weight: 600;
      font-size: 13px;
      display: inline-flex;
      align-items: center;
      gap: 6px;
      white-space: nowrap;
      transition: background-color 0.15s;
    }
    .card.featured:hover .card-btn {
      background: var(--primary-hover);
    }
  </style>
</head>
<body>
  <h1 id="portal-title">EaglercraftX Server Portal</h1>

  <main class="grid" id="portal-grid">
    <a href="/admin" class="card featured" id="card-admin-hub">
      <div class="card-left">
        <h2>Admin Console</h2>
      </div>
      <div class="card-btn">
        Open &rarr;
      </div>
    </a>

    <a href="/1.12/admin.html" class="card" id="card-admin-1-12">
      <div class="card-left">
        <h2>Admin Console</h2>
        <span class="version-tag">1.12</span>
      </div>
      <div class="card-cta">Manage &rarr;</div>
    </a>

    <a href="/1.8/admin.html" class="card" id="card-admin-1-8">
      <div class="card-left">
        <h2>Admin Console</h2>
        <span class="version-tag">1.8</span>
      </div>
      <div class="card-cta">Manage &rarr;</div>
    </a>

    <a href="/1.12/index.html" class="card" id="card-client-1-12">
      <div class="card-left">
        <h2>Web Client</h2>
        <span class="version-tag">1.12</span>
      </div>
      <div class="card-cta">Play &rarr;</div>
    </a>

    <a href="/1.8/index.html" class="card" id="card-client-1-8">
      <div class="card-left">
        <h2>Web Client</h2>
        <span class="version-tag">1.8</span>
      </div>
      <div class="card-cta">Play &rarr;</div>
    </a>
  </main>
</body>
</html>
  `);
});

app.listen(PORT, '0.0.0.0', () => {
  console.log(`Server running on port ${PORT}`);
});
