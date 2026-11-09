import { IDLE, transition } from './state.mjs';
import {mountVoice} from './voice.mjs';

const video = document.querySelector('#stage');
const status = document.querySelector('#status');
const error = document.querySelector('#error');
const start = document.querySelector('#start');
const choices = document.querySelector('#choices');
const resume = document.querySelector('#resume');
let state = { ...IDLE };
let config;
let generation = 0;
let failed = false;
let voice;
let returnTimer;

async function playAmbient() {
  const path=state.phase==='idle'?config.ambient?.idle:
    state.phase==='choice'?config.ambient?.[state.interaction||'method']:null;
  if(!path)return;
  const token=++generation;
  video.pause();video.loop=true;video.muted=false;video.volume=1;
  video.src=path;video.load();
  try {await video.play();}
  catch(cause){
    if(token!==generation||cause.name==='AbortError')return;
    if(cause.name==='NotAllowedError'){
      video.muted=true;
      try{await video.play();}catch(error){if(token===generation)showError(`候场视频未能播放：${error.name}`);}
    } else showError(`候场视频未能播放：${cause.name}`);
  }
}

function showError(message) {
  error.textContent = message;
  error.hidden = false;
}

function refresh() {
  const prediction=state.interaction==='prediction';
  document.querySelector('#hide').textContent=prediction?'1 · 猜狐狸':'1 · 藏好观察';
  document.querySelector('#alone').textContent=prediction?'2 · 猜老虎':'2 · 独自验证';
  start.disabled = !config || state.phase !== 'idle';
  choices.hidden = state.phase !== 'choice';
  status.textContent = {
    idle: config?.testMedia ? '就绪：点击“开始测试”或按回车开始。' : '小班主候场 · 按回车入戏',
    playing: config?.testMedia ? `正在播放测试片段：${state.clip}` : '好戏正在上演 · 0 重新开始',
    choice: prediction?'猜猜动物怕谁：1 狐狸　2 老虎':'帮老虎拿个主意：1 藏好观察　2 独自验证',
    finished: '本轮完成 · 按0再来一场',
  }[state.phase];
  voice?.refresh();
}

async function playCurrent() {
  const token = ++generation;
  video.pause();
  video.loop=false;video.muted=false;video.volume=1;
  resume.hidden = true;
  failed = false;
  error.hidden = true;
  video.src = config.clips[state.clip];
  video.load();
  try {
    await video.play();
  } catch (cause) {
    if (token !== generation) return;
    if (cause.name === 'NotAllowedError') {
      resume.hidden = false;
      showError('浏览器尚未允许有声播放，请点击“继续播放”。');
    } else if (cause.name !== 'AbortError') {
      failed = true;
      showError(`片段未能播放：${state.clip}。请检查文件、编码和设备解码支持。`);
    }
  }
}

function dispatch(event,{spoken=false}={}) {
  if (!config) return;
  const next = transition(state, event, {...config,skipAcknowledgement:spoken});
  if (next === state) return;
  clearTimeout(returnTimer);
  if (['reset','hide','alone','fox','tiger'].includes(event)) voice?.cancel();
  state = next;
  if (event === 'reset') {
    generation++;
    failed = false;
    video.pause();
    video.removeAttribute('src');
    video.load();
    error.hidden = true;
    resume.hidden = true;
  }
  refresh();
  if (state.phase === 'playing') void playCurrent();
  else if(state.phase==='idle'||state.phase==='choice')void playAmbient();
  else if(state.phase==='finished'&&config.autoReturnToIdle){
    const token=generation;
    returnTimer=setTimeout(()=>{if(token===generation&&state.phase==='finished')dispatch('reset');},700);
  }
}

video.addEventListener('timeupdate', () => {
  const after=config?.autoStartAfterIdleSeconds;
  if(state.phase==='idle'&&Number.isFinite(after)&&after>0&&video.currentTime>=after)dispatch('start');
});

video.addEventListener('ended', () => {
  if (!failed && state.phase === 'playing') dispatch('ended');
});
video.addEventListener('error', () => {
  if (state.phase !== 'playing') return;
  failed = true;
  showError(`无法解码或读取片段：${state.clip}。按0复位；请保留该信息用于设备检查。`);
});
start.addEventListener('click', () => dispatch('start'));
video.addEventListener('click', () => {
  if (!resume.hidden) resume.click();
  else if (state.phase === 'idle') dispatch('start');
});
document.addEventListener('contextmenu', event => {
  event.preventDefault();
  if(state.phase!=='idle')dispatch('reset');
});
document.querySelector('#reset').addEventListener('click', () => dispatch('reset'));
document.querySelector('#hide').addEventListener('click', () => dispatch(state.interaction==='prediction'?'fox':'hide'));
document.querySelector('#alone').addEventListener('click', () => dispatch(state.interaction==='prediction'?'tiger':'alone'));
resume.addEventListener('click', async () => {
  const token = generation;
  try {
    await video.play();
    if (token !== generation) return;
    resume.hidden = true;
    error.hidden = true;
  } catch (cause) {
    if (token === generation) showError(`仍未开始播放：${cause.name}。请检查音视频支持。`);
  }
});
document.addEventListener('keydown', (event) => {
  if (event.repeat) return;
  if (event.key.toLowerCase() === 'f') {
    event.preventDefault();
    const action=document.fullscreenElement ? document.exitFullscreen() : document.documentElement.requestFullscreen();
    void action.catch(cause=>console.warn('Fullscreen unavailable',cause.name));
    return;
  }
  if (event.key === 'Enter' && event.target.tagName !== 'BUTTON') {
    if (!resume.hidden) {
      event.preventDefault();
      resume.click();
    } else if (state.phase === 'idle') {
      event.preventDefault();
      dispatch('start');
    }
    return;
  }
  const action = { '1': state.interaction==='prediction'?'fox':'hide', '2': state.interaction==='prediction'?'tiger':'alone', '0': 'reset', g: 'presence', G: 'presence' }[event.key];
  if (action) { event.preventDefault(); dispatch(action); }
});

voice=mountVoice({canTalk:()=>state.phase==='choice',getInteraction:()=>state.interaction||'method',choose:branch=>dispatch(branch,{spoken:true}),
  getAuto:()=>Boolean(config?.autoListen),getPrompts:()=>config?.voicePrompts||{},
  onActivity:active=>{if(state.phase==='choice')video.muted=active;}});

try {
  const response = await fetch('config.json', { cache: 'no-store' });
  if (!response.ok) throw new Error(`清单读取失败：HTTP ${response.status}`);
  const candidate = await response.json();
  for (const key of ['welcome', 'opening', 'question', 'hide', 'alone', 'ending', ...(candidate.twoInteractions?['prediction']:[])]) {
    const path = candidate.clips?.[key];
    if (typeof path !== 'string' || !/^media\/[a-zA-Z0-9_./-]+$/.test(path) || path.includes('..')) {
      throw new Error(`清单中的本地素材路径无效：${key}`);
    }
  }
  for(const path of [...Object.values(candidate.ambient||{}),...Object.values(candidate.voicePrompts||{}),...(candidate.curtain?[candidate.clips?.curtain]:[]),
    ...(candidate.acknowledgements?['prediction_reply','method_reply','method_reply_alone'].map(key=>candidate.clips?.[key]):[])]){
    if(typeof path!=='string'||!/^media\/[a-zA-Z0-9_./-]+$/.test(path)||path.includes('..'))throw new Error('候场或谢幕素材路径无效');
  }
  config = candidate;
  if(!config.testMedia){
    document.body.classList.add('show-mode');
    if(new URLSearchParams(location.search).get('controls')==='1')document.body.classList.add('operator-mode');
    start.textContent='请开戏 · 回车';
    document.querySelector('#mode-note').hidden=true;
    video.poster='stage/idle.png';
    if(config.mirror)video.style.transform='scaleX(-1)';
  }
  refresh();
  void playAmbient();
} catch (cause) {
  status.textContent = '启动失败';
  showError(cause.message);
}
