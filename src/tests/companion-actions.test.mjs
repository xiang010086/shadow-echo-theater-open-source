import test from 'node:test';
import assert from 'node:assert/strict';
import { companionReaction } from '../public/stage/companion-actions.mjs';

test('fox alone: companions look but stay, including after dialogue', () => {
  const data={lines:[{role:'fox',start:2,end:6}]};
  for (const t of [0,2,3,5,10,30]) {
    const state=companionReaction('hide',t,data);
    assert.equal(state.rabbit,0);
    assert.equal(state.deer,0);
  }
  assert.ok(companionReaction('hide',3,data).watch>0);
});

test('first procession: attention precedes flight and rabbit leaves first', () => {
  const data={lines:[{role:'host',start:0,end:10}]};
  const waiting=companionReaction('prediction',6.8,data);
  assert.ok(waiting.watch>0);
  assert.equal(waiting.rabbit,0);
  const early=companionReaction('prediction',7.8,data);
  assert.ok(early.rabbit>0);
  assert.equal(early.deer,0);
  const late=companionReaction('prediction',10,data);
  assert.equal(late.rabbit,1);
  assert.equal(late.deer,1);
});

test('tiger alone: flight follows narrator cue and remains bounded', () => {
  const data={lines:[{role:'tiger',start:0,end:4},{role:'host',start:5,end:10}]};
  assert.equal(companionReaction('alone',5,data).rabbit,0);
  assert.ok(companionReaction('alone',6,data).rabbit>0);
  assert.equal(companionReaction('alone',20,data).deer,1);
  assert.equal(companionReaction('question',0,data).rabbit,1);
});
