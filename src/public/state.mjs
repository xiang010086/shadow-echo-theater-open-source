export const IDLE = Object.freeze({ phase: 'idle', clip: null });

export function transition(state, event, options={}) {
  if (event === 'reset') return { ...IDLE };
  if ((event === 'start' || event === 'presence') && state.phase === 'idle') {
    return { phase: 'playing', clip: 'welcome', welcomeOnly: event === 'presence' };
  }
  if (event === 'ended' && state.phase === 'playing') {
    if(state.clip==='prediction_reply')return {phase:'playing',clip:'question'};
    if(['method_reply','method_reply_alone'].includes(state.clip)&&['hide','alone'].includes(state.nextClip))return {phase:'playing',clip:state.nextClip};
    if (state.clip === 'welcome' && state.welcomeOnly) return { ...IDLE };
    if(options.twoInteractions){
      if(state.clip==='opening')return {phase:'playing',clip:'prediction'};
      if(state.clip==='prediction')return {phase:'choice',clip:null,interaction:'prediction'};
      if(state.clip==='question')return {phase:'choice',clip:null,interaction:'method'};
    }
    const next = { welcome: 'opening', opening: 'question', hide: 'ending', alone: 'ending' };
    if (state.clip === 'question') return { phase: 'choice', clip: null };
    if (state.clip === 'ending') return options.curtain?{phase:'playing',clip:'curtain'}:{ phase: 'finished', clip: null };
    if (state.clip === 'curtain') return { phase: 'finished', clip: null };
    if (next[state.clip]) return { phase: 'playing', clip: next[state.clip] };
  }
  if(options.twoInteractions && state.phase==='choice' && state.interaction==='prediction'){
    if(['fox','tiger'].includes(event))return {phase:'playing',clip:options.acknowledgements&&!options.skipAcknowledgement?'prediction_reply':'question'};
    return state;
  }
  if (state.phase === 'choice' && ['hide', 'alone'].includes(event)) {
    if(options.acknowledgements&&!options.skipAcknowledgement)return {phase:'playing',clip:event==='hide'?'method_reply':'method_reply_alone',nextClip:event};
    return { phase: 'playing', clip: event };
  }
  return state;
}
