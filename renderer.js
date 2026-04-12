const { ipcRenderer } = require('electron');

const claude = document.getElementById('claude');
const speechBubble = document.getElementById('speech-bubble');
const speechText = document.getElementById('speech-text');
const statusText = document.getElementById('status-text');
const moodIcon = document.getElementById('mood-icon');
const contextMenu = document.getElementById('context-menu');
const gameOverlay = document.getElementById('game-overlay');
const gameContent = document.getElementById('game-content');
const petContainer = document.getElementById('pet-container');
const particles = document.getElementById('particles');

let currentState = 'idle';
let isDragging = false;
let dragStartPos = { x: 0, y: 0 };
let hasMoved = false;
let speechTimeout = null;
let isSleeping = false;

// ===== SPEECH =====
function say(text, duration = 3000) {
  if (speechTimeout) clearTimeout(speechTimeout);
  speechText.textContent = text;
  speechBubble.classList.remove('hidden');
  speechTimeout = setTimeout(() => {
    speechBubble.classList.add('hidden');
  }, duration);
}

// ===== ANIMATION STATE =====
function setState(state, duration = null) {
  claude.className = state;
  currentState = state;
  if (duration) {
    setTimeout(() => {
      if (currentState === state) {
        if (isSleeping) {
          setState('sleeping');
        } else {
          setState('idle');
        }
      }
    }, duration);
  }
}

// ===== DRAG =====
petContainer.addEventListener('mousedown', (e) => {
  if (e.button === 0) {
    isDragging = true;
    hasMoved = false;
    dragStartPos = { x: e.screenX, y: e.screenY };
  }
});

document.addEventListener('mousemove', (e) => {
  if (isDragging) {
    const dx = e.screenX - dragStartPos.x;
    const dy = e.screenY - dragStartPos.y;
    if (Math.abs(dx) > 2 || Math.abs(dy) > 2) {
      hasMoved = true;
      dragStartPos = { x: e.screenX, y: e.screenY };
      ipcRenderer.send('window-move', { dx, dy });
    }
  }
});

document.addEventListener('mouseup', () => {
  isDragging = false;
});

// ===== CLICK =====
claude.addEventListener('click', (e) => {
  if (e.button === 0 && !hasMoved) {
    spawnHearts();
    if (isSleeping) {
      isSleeping = false;
      setState('idle');
      say('嗯...我醒啦！☀️');
      updateStatus('😊', '陪你上班中~');
    } else {
      const reactions = [
        '嘿嘿~ 😊', '在呢在呢！', '戳我干嘛啦~', '❤️',
        '想我了？', '要一起玩吗？', '你今天真好看~', '加油鸭！🦆',
        '摸摸头~', '嘻嘻', '我超喜欢你的！', '要喝杯咖啡吗 ☕',
        '（横着走）🦀', '咔嚓咔嚓~',
      ];
      say(reactions[Math.floor(Math.random() * reactions.length)]);
      setState('excited', 1200);
    }
  }
});

// ===== PARTICLES =====
function spawnHearts() {
  for (let i = 0; i < 4; i++) {
    setTimeout(() => {
      const heart = document.createElement('div');
      heart.className = 'heart-particle';
      heart.textContent = ['❤️', '🧡', '💛'][Math.floor(Math.random() * 3)];
      heart.style.left = (30 + Math.random() * 80) + 'px';
      heart.style.top = (10 + Math.random() * 50) + 'px';
      particles.appendChild(heart);
      setTimeout(() => heart.remove(), 1200);
    }, i * 120);
  }
}

function spawnSparkles() {
  for (let i = 0; i < 6; i++) {
    setTimeout(() => {
      const sparkle = document.createElement('div');
      sparkle.className = 'sparkle';
      sparkle.textContent = ['✨', '⭐', '🌟'][Math.floor(Math.random() * 3)];
      sparkle.style.left = (Math.random() * 120 + 10) + 'px';
      sparkle.style.top = (Math.random() * 100 + 10) + 'px';
      particles.appendChild(sparkle);
      setTimeout(() => sparkle.remove(), 800);
    }, i * 100);
  }
}

// ===== CONTEXT MENU =====
petContainer.addEventListener('contextmenu', (e) => {
  e.preventDefault();
  contextMenu.style.left = Math.min(e.offsetX, 60) + 'px';
  contextMenu.style.top = Math.min(e.offsetY, 100) + 'px';
  contextMenu.classList.remove('hidden');
});

document.addEventListener('click', (e) => {
  if (!contextMenu.contains(e.target)) {
    contextMenu.classList.add('hidden');
  }
});

document.querySelectorAll('.menu-item').forEach(item => {
  item.addEventListener('click', () => {
    contextMenu.classList.add('hidden');
    handleAction(item.dataset.action);
  });
});

function handleAction(action) {
  switch (action) {
    case 'wave':
      setState('waving', 2500);
      say('你好呀！👋', 2500);
      break;
    case 'dance':
      setState('dancing', 4000);
      say('跳舞时间！🎶', 3000);
      spawnSparkles();
      updateStatus('🎵', '跳舞中~');
      setTimeout(() => updateStatus('😊', '陪你上班中~'), 4000);
      break;
    case 'spin':
      setState('spinning', 2500);
      say('转圈圈！🌀', 2000);
      spawnSparkles();
      setTimeout(() => say('好晕~😵‍💫', 2000), 2500);
      break;
    case 'rps':
      startRPS();
      break;
    case 'guess':
      startGuessNumber();
      break;
    case 'flip':
      flipCoin();
      break;
    case 'fortune':
      tellFortune();
      break;
    case 'sleep':
      isSleeping = true;
      setState('sleeping');
      say('晚安~ 💤', 2000);
      updateStatus('😴', '睡觉中... 点我唤醒');
      addZzz();
      break;
  }
}

function updateStatus(icon, text) {
  moodIcon.textContent = icon;
  statusText.textContent = text;
}

function addZzz() {
  if (!isSleeping) return;
  const zzz = document.createElement('div');
  zzz.className = 'zzz';
  zzz.textContent = 'Z';
  zzz.style.right = '15px';
  zzz.style.top = '10px';
  particles.appendChild(zzz);
  setTimeout(() => zzz.remove(), 2000);
  if (isSleeping) setTimeout(addZzz, 2200);
}

// ===== GAMES =====

function startRPS() {
  setState('jumping', 1200);
  say('猜拳！出吧！✊✌️🖐️');
  ipcRenderer.send('resize-window', { width: 200, height: 380 });

  gameContent.innerHTML = `
    <h3>✊ 猜拳游戏 ✌️</h3>
    <div>
      <button class="game-btn" data-choice="rock">✊</button>
      <button class="game-btn" data-choice="scissors">✌️</button>
      <button class="game-btn" data-choice="paper">🖐️</button>
    </div>
    <div class="game-result" id="rps-result"></div>
    <button class="game-close" id="game-close-btn">关闭</button>
  `;
  gameOverlay.classList.remove('hidden');

  const choices = ['rock', 'scissors', 'paper'];
  const emojis = { rock: '✊', scissors: '✌️', paper: '🖐️' };

  gameContent.querySelectorAll('.game-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const player = btn.dataset.choice;
      const ai = choices[Math.floor(Math.random() * 3)];
      let result;

      if (player === ai) {
        result = `${emojis[player]} vs ${emojis[ai]}<br>平局！再来！`;
        say('平局！再来一次！');
      } else if (
        (player === 'rock' && ai === 'scissors') ||
        (player === 'scissors' && ai === 'paper') ||
        (player === 'paper' && ai === 'rock')
      ) {
        result = `${emojis[player]} vs ${emojis[ai]}<br>你赢了！🎉`;
        say('啊！你赢了！厉害！🎉');
        setState('jumping', 1200);
        spawnSparkles();
      } else {
        result = `${emojis[player]} vs ${emojis[ai]}<br>我赢啦！😝`;
        say('嘿嘿，我赢了！😝');
        setState('dancing', 2000);
      }

      document.getElementById('rps-result').innerHTML = result;
    });
  });

  document.getElementById('game-close-btn').addEventListener('click', closeGame);
}

let secretNumber, guessAttempts;

function startGuessNumber() {
  secretNumber = Math.floor(Math.random() * 20) + 1;
  guessAttempts = 0;
  say('我想了一个 1~20 的数！🤔');
  setState('thinking', 2000);
  ipcRenderer.send('resize-window', { width: 200, height: 380 });

  gameContent.innerHTML = `
    <h3>🔢 猜数字 (1-20)</h3>
    <div style="margin:8px 0">
      <input type="number" id="guess-input" min="1" max="20"
        style="width:60px;padding:6px;border:2px solid #D97757;border-radius:8px;text-align:center;font-size:16px;outline:none">
      <button class="game-btn" id="guess-btn" style="font-size:14px;padding:6px 12px">猜！</button>
    </div>
    <div class="game-result" id="guess-result">你有 5 次机会</div>
    <button class="game-close" id="game-close-btn">关闭</button>
  `;
  gameOverlay.classList.remove('hidden');

  const input = document.getElementById('guess-input');
  const guessBtn = document.getElementById('guess-btn');
  const resultEl = document.getElementById('guess-result');

  function makeGuess() {
    const guess = parseInt(input.value);
    if (isNaN(guess) || guess < 1 || guess > 20) return;
    guessAttempts++;
    input.value = '';

    if (guess === secretNumber) {
      resultEl.innerHTML = `🎉 答对了！答案是 ${secretNumber}<br>用了 ${guessAttempts} 次`;
      say('天才！猜对了！🎉🎉');
      setState('dancing', 3000);
      spawnSparkles();
      guessBtn.disabled = true;
    } else if (guessAttempts >= 5) {
      resultEl.innerHTML = `❌ 机会用完了！<br>答案是 ${secretNumber}`;
      say(`哈哈答案是 ${secretNumber}！😜`);
      setState('jumping', 1200);
      guessBtn.disabled = true;
    } else {
      const hint = guess > secretNumber ? '大了 📉' : '小了 📈';
      resultEl.innerHTML = `${hint}（还有 ${5 - guessAttempts} 次机会）`;
      say(guess > secretNumber ? '太大了！往小猜~' : '太小了！往大猜~');
    }
  }

  guessBtn.addEventListener('click', makeGuess);
  input.addEventListener('keydown', (e) => { if (e.key === 'Enter') makeGuess(); });
  document.getElementById('game-close-btn').addEventListener('click', closeGame);
}

function flipCoin() {
  setState('spinning', 2400);
  say('抛硬币！🪙');
  setTimeout(() => {
    const result = Math.random() < 0.5 ? '正面 ☀️' : '反面 🌙';
    say(`结果是... ${result}！`, 3000);
    spawnSparkles();
  }, 1200);
}

function tellFortune() {
  setState('thinking', 2500);
  say('让我算算...🔮', 1500);

  const fortunes = [
    { icon: '🌟', text: '大吉！今天超级幸运！', mood: '🤩' },
    { icon: '✨', text: '中吉！好事要发生~', mood: '😊' },
    { icon: '🍀', text: '小吉！平平安安就是福', mood: '☺️' },
    { icon: '🌈', text: '今天适合搞创作！', mood: '🎨' },
    { icon: '☕', text: '今天适合摸鱼...不是！努力！', mood: '😏' },
    { icon: '🎵', text: '今天心情会很好~', mood: '🎶' },
    { icon: '💡', text: '会有灵感迸发！', mood: '💡' },
    { icon: '🍰', text: '该吃点好的犒劳自己！', mood: '🤤' },
  ];

  setTimeout(() => {
    const f = fortunes[Math.floor(Math.random() * fortunes.length)];
    say(`${f.icon} ${f.text}`, 4000);
    updateStatus(f.mood, f.text);
    setState('dancing', 2000);
    setTimeout(() => updateStatus('😊', '陪你上班中~'), 5000);
  }, 2500);
}

function closeGame() {
  gameOverlay.classList.add('hidden');
  ipcRenderer.send('resize-window', { width: 200, height: 280 });
  setState('idle');
}

// ===== RANDOM BEHAVIORS =====
const idleActions = [
  () => { setState('scuttling', 3000); say('横着走~🦀', 2000); updateStatus('🦀', '螃蟹步'); setTimeout(() => updateStatus('😊', '陪你上班中~'), 3000); },
  () => { setState('walking', 3000); say('散个步~', 2000); updateStatus('🚶', '散步中'); setTimeout(() => updateStatus('😊', '陪你上班中~'), 3000); },
  () => { setState('dancing', 3000); say('突然想跳舞！🎶', 2000); spawnSparkles(); },
  () => { setState('thinking', 3000); say('嗯...在想事情...🤔', 2000); updateStatus('🤔', '思考中...'); setTimeout(() => updateStatus('😊', '陪你上班中~'), 3000); },
  () => { setState('waving', 2000); say('你在忙吗？👀', 2000); },
  () => { say('加油！你可以的！💪'); },
  () => { say('要不要休息一下？☕'); },
  () => { say('今天也要元气满满哦！✨'); spawnSparkles(); },
  () => { say('我在看你工作...好厉害 👀'); },
  () => { say('咔嚓咔嚓~ 🦀'); setState('scuttling', 2000); },
  () => { setState('jumping', 1200); say('突然好开心！🎉'); },
  () => { setState('spinning', 2500); say('转一个！🌀'); },
];

function randomAction() {
  if (isSleeping || currentState !== 'idle') return;
  idleActions[Math.floor(Math.random() * idleActions.length)]();
}

function scheduleRandom() {
  const delay = 30000 + Math.random() * 60000;
  setTimeout(() => { randomAction(); scheduleRandom(); }, delay);
}
scheduleRandom();

// ===== TIME GREETINGS =====
function timeGreeting() {
  const hour = new Date().getHours();
  if (hour >= 6 && hour < 9) { say('早上好！新的一天开始啦 ☀️', 4000); updateStatus('🌅', '早安~'); }
  else if (hour >= 12 && hour < 13) { say('中午啦！记得吃饭哦 🍱', 4000); updateStatus('🍱', '午饭时间'); }
  else if (hour >= 18 && hour < 19) { say('下班时间到！辛苦啦 🌆', 4000); updateStatus('🌆', '下班啦~'); }
  else if (hour >= 22) { say('很晚了，早点休息哦 🌙', 4000); updateStatus('🌙', '该睡觉了'); }
  setTimeout(() => updateStatus('😊', '陪你上班中~'), 6000);
}

setTimeout(() => {
  const hour = new Date().getHours();
  if (hour >= 22 || hour < 6) say('这么晚还在？注意休息哦~ 🌙', 3000);
  else say('嗨！我是 Clawd~ 🦀 今天也一起加油！💪', 3000);
  spawnSparkles();
}, 500);

setInterval(timeGreeting, 3600000);
