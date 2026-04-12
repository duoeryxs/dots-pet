// Clawd - Pixel Crab / Claude Code mascot
// Minimal pixel art: wide rounded rect body, 2 ears, 2 eyes, 2 legs. That's it.

const canvas = document.getElementById('clawd-canvas');
const ctx = canvas.getContext('2d');

const PX = 8; // pixel block size

// Colors
const BODY = '#D2654A';     // brick-red / terracotta
const BODY_LIGHT = '#DA7A62'; // slightly lighter for ears
const BODY_DARK = '#B8533C';  // slightly darker for legs
const EYE = '#1a1a1a';       // near black

// Grid: 18 wide x 16 tall
// 0=empty, 1=body, 2=body_light(ears), 3=body_dark(legs), 4=eye
const GRID = [
  //0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7
  [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0], // 0
  [0,0,0,2,2,0,0,0,0,0,0,0,0,2,2,0,0,0], // 1  ears
  [0,0,0,2,2,0,0,0,0,0,0,0,0,2,2,0,0,0], // 2  ears
  [0,0,0,1,1,1,1,1,1,1,1,1,1,1,1,0,0,0], // 3  body top (rounded)
  [0,0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0,0], // 4
  [0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0], // 5
  [0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0], // 6
  [0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0], // 7
  [0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0], // 8
  [0,1,1,1,4,4,1,1,1,1,1,1,4,4,1,1,1,0], // 9  eyes
  [0,1,1,1,4,4,1,1,1,1,1,1,4,4,1,1,1,0], // 10 eyes
  [0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0], // 11
  [0,0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0,0], // 12
  [0,0,0,1,1,1,1,1,1,1,1,1,1,1,1,0,0,0], // 13 body bottom (rounded)
  [0,0,0,0,3,3,3,0,0,0,0,3,3,3,0,0,0,0], // 14 legs
  [0,0,0,0,3,3,3,0,0,0,0,3,3,3,0,0,0,0], // 15 legs
];

const colorMap = {
  1: BODY,
  2: BODY_LIGHT,
  3: BODY_DARK,
  4: EYE,
};

function drawClawd() {
  ctx.clearRect(0, 0, canvas.width, canvas.height);

  for (let row = 0; row < GRID.length; row++) {
    for (let col = 0; col < GRID[row].length; col++) {
      const val = GRID[row][col];
      if (val === 0) continue;
      ctx.fillStyle = colorMap[val];
      ctx.fillRect(col * PX, row * PX, PX, PX);
    }
  }
}

drawClawd();
window.drawClawd = drawClawd;
window.PX = PX;
window.GRID = GRID;
