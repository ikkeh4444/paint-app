const canvas = document.getElementById('board');
const ctx = canvas.getContext('2d');
const colorInput = document.getElementById('color');
const sizeInput = document.getElementById('size');
const sizeValue = document.getElementById('sizeValue');
const swatchesEl = document.getElementById('swatches');
const eraserBtn = document.getElementById('eraser');
const undoBtn = document.getElementById('undo');
const clearBtn = document.getElementById('clear');
const saveBtn = document.getElementById('save');

const PALETTE = [
  '#000000', '#ffffff', '#e53935', '#fb8c00', '#fdd835',
  '#43a047', '#1e88e5', '#8e24aa', '#6d4c41', '#90a4ae'
];
const CANVAS_BG = '#ffffff';
const MAX_UNDO = 50;

let drawing = false;
let erasing = false;
let last = null;
let hasContent = false;
const undoStack = [];

function dpr() {
  return window.devicePixelRatio || 1;
}

function fillBackground() {
  ctx.save();
  ctx.globalCompositeOperation = 'source-over';
  ctx.fillStyle = CANVAS_BG;
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  ctx.restore();
}

function resizeCanvas() {
  const rect = canvas.parentElement.getBoundingClientRect();
  const snapshot = document.createElement('canvas');
  snapshot.width = canvas.width;
  snapshot.height = canvas.height;
  if (canvas.width > 0 && canvas.height > 0) {
    snapshot.getContext('2d').drawImage(canvas, 0, 0);
  }
  canvas.width = Math.max(1, Math.floor(rect.width * dpr()));
  canvas.height = Math.max(1, Math.floor(rect.height * dpr()));
  ctx.lineCap = 'round';
  ctx.lineJoin = 'round';
  if (hasContent && snapshot.width > 0) {
    ctx.drawImage(snapshot, 0, 0, canvas.width, canvas.height);
  } else {
    fillBackground();
  }
  hasContent = true;
}

function pos(e) {
  const rect = canvas.getBoundingClientRect();
  return {
    x: (e.clientX - rect.left) * (canvas.width / rect.width),
    y: (e.clientY - rect.top) * (canvas.height / rect.height)
  };
}

function strokeColor() {
  return erasing ? CANVAS_BG : colorInput.value;
}

function applyStrokeStyle() {
  ctx.strokeStyle = strokeColor();
  ctx.lineWidth = Number(sizeInput.value) * dpr();
}

function begin(e) {
  if (e.button !== undefined && e.button !== 0) return;
  e.preventDefault();
  pushUndo();
  drawing = true;
  last = pos(e);
  applyStrokeStyle();
  ctx.beginPath();
  ctx.moveTo(last.x, last.y);
  ctx.lineTo(last.x + 0.01, last.y + 0.01);
  ctx.stroke();
  canvas.setPointerCapture(e.pointerId);
}

function move(e) {
  if (!drawing) return;
  e.preventDefault();
  const p = pos(e);
  applyStrokeStyle();
  ctx.beginPath();
  ctx.moveTo(last.x, last.y);
  ctx.lineTo(p.x, p.y);
  ctx.stroke();
  last = p;
}

function end() {
  drawing = false;
}

function pushUndo() {
  undoStack.push(canvas.toDataURL('image/png'));
  if (undoStack.length > MAX_UNDO) undoStack.shift();
  undoBtn.disabled = false;
}

function undo() {
  const data = undoStack.pop();
  if (!data) {
    undoBtn.disabled = true;
    return;
  }
  const img = new Image();
  img.onload = () => {
    ctx.save();
    ctx.globalCompositeOperation = 'source-over';
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
    ctx.restore();
  };
  img.src = data;
  undoBtn.disabled = undoStack.length === 0;
}

function clearCanvas() {
  pushUndo();
  fillBackground();
}

function save() {
  const link = document.createElement('a');
  const stamp = new Date().toISOString().replace(/[:.]/g, '-');
  link.download = `paint-${stamp}.png`;
  link.href = canvas.toDataURL('image/png');
  link.click();
}

function setErasing(value) {
  erasing = value;
  eraserBtn.classList.toggle('active', erasing);
}

PALETTE.forEach((c) => {
  const b = document.createElement('button');
  b.type = 'button';
  b.className = 'swatch';
  b.style.background = c;
  b.title = c;
  b.addEventListener('click', () => {
    colorInput.value = c;
    setErasing(false);
  });
  swatchesEl.appendChild(b);
});

colorInput.addEventListener('input', () => setErasing(false));
sizeInput.addEventListener('input', () => {
  sizeValue.textContent = sizeInput.value;
});
eraserBtn.addEventListener('click', () => setErasing(!erasing));
undoBtn.addEventListener('click', undo);
clearBtn.addEventListener('click', clearCanvas);
saveBtn.addEventListener('click', save);

canvas.addEventListener('pointerdown', begin);
canvas.addEventListener('pointermove', move);
canvas.addEventListener('pointerup', end);
canvas.addEventListener('pointercancel', end);

window.addEventListener('keydown', (e) => {
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'z') {
    e.preventDefault();
    undo();
  }
});

window.addEventListener('resize', resizeCanvas);

resizeCanvas();
