import test from 'node:test';
import assert from 'node:assert/strict';
import { IDLE, transition } from '../public/state.mjs';

function toChoice() {
  let state = transition({ ...IDLE }, 'start');
  for (let i = 0; i < 3; i++) state = transition(state, 'ended');
  assert.equal(state.phase, 'choice');
  return state;
}

test('stage edition: keyboard replies preserve branch, curtain plays before finished',()=>{
  const options={twoInteractions:true,acknowledgements:true,curtain:true};
  for(const method of ['hide','alone']){
    let state={phase:'choice',clip:null,interaction:'prediction'};
    state=transition(state,'tiger',options);assert.equal(state.clip,'prediction_reply');
    state=transition(state,'ended',options);assert.equal(state.clip,'question');
    state=transition(state,'ended',options);assert.equal(state.phase,'choice');
    state=transition(state,method,options);
    assert.equal(state.clip,method==='hide'?'method_reply':'method_reply_alone');
    state=transition(state,'ended',options);assert.equal(state.clip,method);
    state=transition(state,'ended',options);assert.equal(state.clip,'ending');
    state=transition(state,'ended',options);assert.equal(state.clip,'curtain');
    assert.equal(transition(state,'presence',options),state);
    state=transition(state,'ended',options);assert.equal(state.phase,'finished');
  }
});

test('stage edition: a spoken AI reply does not cause a second prerecorded reply',()=>{
  const options={twoInteractions:true,acknowledgements:true,skipAcknowledgement:true};
  assert.equal(transition({phase:'choice',interaction:'prediction'},'fox',options).clip,'question');
  assert.equal(transition({phase:'choice',interaction:'method'},'alone',options).clip,'alone');
});

for (const branch of ['hide', 'alone']) {
  test(`${branch}: pauses for input and reaches shared ending`, () => {
    let state = transition(toChoice(), branch);
    assert.equal(state.clip, branch);
    state = transition(state, 'ended');
    assert.equal(state.clip, 'ending');
    state = transition(state, 'ended');
    assert.equal(state.phase, 'finished');
  });
}
test('presence does not interrupt playback, choice or finished state', () => {
  for (const state of [transition(IDLE, 'start'), toChoice(), { phase: 'finished', clip: null }]) {
    assert.equal(transition(state, 'presence'), state);
  }
});
test('branch input cannot skip opening; reset works in any phase', () => {
  for (const state of [IDLE, transition(IDLE, 'start'), toChoice(), { phase: 'finished', clip: null }]) {
    if (state.phase !== 'choice') assert.equal(transition(state, 'hide'), state);
    assert.deepEqual(transition(state, 'reset'), IDLE);
  }
});
test('idle presence begins welcome; stray ended event is harmless', () => {
  const welcome = transition(IDLE, 'presence');
  assert.equal(welcome.clip, 'welcome');
  assert.deepEqual(transition(welcome, 'ended'), IDLE);
  assert.equal(transition(IDLE, 'ended'), IDLE);
  assert.equal(transition(toChoice(), 'ended').phase, 'choice');
});

for(const prediction of ['fox','tiger'])for(const method of ['hide','alone']){
  test(`two interactions: ${prediction} prediction then ${method} verification`,()=>{
    const options={twoInteractions:true};
    let state=transition(IDLE,'start',options);
    state=transition(state,'ended',options);assert.equal(state.clip,'opening');
    state=transition(state,'ended',options);assert.equal(state.clip,'prediction');
    state=transition(state,'ended',options);assert.equal(state.interaction,'prediction');
    assert.equal(transition(state,method,options),state);
    state=transition(state,prediction,options);assert.equal(state.clip,'question');
    state=transition(state,'ended',options);assert.equal(state.interaction,'method');
    assert.equal(transition(state,prediction,options),state);
    state=transition(state,method,options);assert.equal(state.clip,method);
    state=transition(state,'ended',options);assert.equal(state.clip,'ending');
    state=transition(state,'ended',options);assert.equal(state.phase,'finished');
  });
}
