export function mountVoice({canTalk,choose,getInteraction=()=> 'method',onActivity=()=>{},getAuto=()=>false,getPrompts=()=>({})}) {
  const panel=document.querySelector('#voice-panel');
  const button=document.querySelector('#talk');
  const note=document.querySelector('#voice-note');
  const transcript=document.querySelector('#transcript');
  const feedback=document.querySelector('#audience-feedback');
  const message=document.querySelector('#audience-message');
  const retry=document.querySelector('#retry-listen');
  const mouseFirst=document.querySelector('#mouse-first');
  const mouseSecond=document.querySelector('#mouse-second');
  const audio=new Audio();
  let held=false,busy=false,generation=0,startPending=null,ready=false;
  let readyHint='';
  let audioCancel=null;
  let autoTimer=null,autoAttempts=0,choiceContext=null;
  const statusLabels={recognizing:'正在听懂你的主意…',thinking:'小班主正在想办法…',speaking:'正在准备小班主的回应…'};
  function showFeedback(text,canRetry=false){
    if(feedback)feedback.hidden=!canTalk();
    if(message)message.textContent=text;
    if(retry)retry.hidden=!canRetry;
  }
  async function request(action,automatic=false) {
    const response=await fetch(`/api/voice/${action}`,{
      method:action==='status'?'GET':'POST',
      headers:action==='status'?{}:{'X-Stage-Control':'1','Content-Type':'application/json'},
      body:action==='start'?JSON.stringify({interaction:getInteraction(),...(automatic?{automatic:true}:{})}):undefined,
      cache:'no-store',signal:AbortSignal.timeout(7000),
    });
    const value=await response.json();
    if(!response.ok)throw new Error(value.error||'语音暂不可用，可按1/2继续。');
    return value;
  }
  function refresh() {
    const context=canTalk()?getInteraction():null;
    if(context!==choiceContext){clearTimeout(autoTimer);autoTimer=null;autoAttempts=0;choiceContext=context;}
    panel.hidden=!canTalk();
    if(feedback)feedback.hidden=!context;
    if(mouseFirst)mouseFirst.textContent=context==='prediction'?'猜狐狸':'让老虎藏好';
    if(mouseSecond)mouseSecond.textContent=context==='prediction'?'猜老虎':'让老虎独自过去';
    button.disabled=!canTalk()||(busy&&!held);
    button.textContent=held?'正在录音 · 松开提交':'按住说话 · 空格';
    button.classList.toggle('recording',held);
    if(!busy)note.textContent=ready?(getAuto()?'提问后自动收音，请直接说出选择。':'按住空格说完再松开，或按1/2选择。'):readyHint||'语音准备中，也可以按1/2选择。';
    if(context&&!busy){
      if(!getAuto())showFeedback(context==='prediction'?'按 1：猜狐狸　　按 2：猜老虎':'按 1：让老虎藏好　　按 2：让老虎独自过去');
      else showFeedback(!ready?'话筒暂未就绪，请稍候。':autoAttempts>=3?'还没听清。靠近话筒后，点击下方按钮再说一次。':'请等“我在听”出现后，再说出你的想法。',ready&&autoAttempts>=3);
    }
    if(context&&getAuto()&&ready&&!busy&&autoAttempts<3&&!autoTimer){
      const token=generation;
      autoTimer=setTimeout(()=>{autoTimer=null;if(token===generation&&canTalk()&&!busy){autoAttempts++;void begin(true);}},650);
    }
  }
  function playAudio(source) {
    return new Promise((resolve,reject)=>{
      let settled=false;
      const timer=setTimeout(()=>finish(new Error('回应声音播放超时。')),20000);
      function finish(error){
        if(settled)return;settled=true;
        clearTimeout(timer);audio.onended=null;audio.onerror=null;audioCancel=null;
        if(error){audio.pause();reject(error);}else resolve();
      }
      audioCancel=()=>finish();audio.onended=()=>finish();
      audio.onerror=()=>finish(new Error('回应声音未能播放，可按1/2继续。'));
      audio.src=source;audio.play().catch(finish);
    });
  }
  async function handleFailure(error,token,automatic) {
    if(token!==generation)return;
    held=false;
    note.textContent=error.message;
    showFeedback('没有听清，先听小班主提示，再等“我在听”。');
    if(automatic){
      const prompts=getPrompts(),path=prompts[autoAttempts>=3?'unavailable':getInteraction()];
      if(typeof path==='string'&&/^media\/[a-zA-Z0-9_./-]+$/.test(path)&&!path.includes('..')){
        try{await playAudio(path);}catch(cause){note.textContent=cause.message;}
      }
    }
    if(token!==generation)return;
    busy=false;onActivity(false);refresh();note.textContent=error.message;
  }
  function cancel() {
    generation++;
    clearTimeout(autoTimer);autoTimer=null;
    held=false;busy=false;
    onActivity(false);
    audio.pause();audio.removeAttribute('src');
    if(audioCancel){audioCancel();audioCancel=null;}
    transcript.textContent='';
    request('cancel').catch(()=>{note.textContent='语音连接中断，可按1/2继续。';});
    refresh();
  }
  async function waitForReply(token) {
    const deadline=Date.now()+120000;
    while(token===generation && canTalk()) {
      if(Date.now()>deadline)throw new Error('等候较久，可再试一次或按1/2继续。');
      const value=await request('status');
      if(token!==generation)return;
      if(value.transcript)transcript.textContent=`你说：“${value.transcript}”`;
      note.textContent=statusLabels[value.phase]||note.textContent;
      if(value.phase==='recording')showFeedback(value.listening_ready?(value.speech_detected?'听到声音了，请说完再停一下。':'我在听，请说出你的想法。'):'话筒准备中，请稍等…');
      else if(value.phase!=='error')showFeedback((value.transcript?`听到的是：“${value.transcript.slice(0,40)}”\n`:'')+(statusLabels[value.phase]||'小班主正在回应…'));
      if(value.phase==='error')throw new Error(value.error);
      if(value.phase==='done') {
        const allowed=getInteraction()==='prediction'?['fox','tiger','clarify']:['hide','alone','clarify'];
        if(!allowed.includes(value.branch)||!/^media\/runtime-voice\/[a-f0-9]{32}\.wav$/.test(value.audio))throw new Error('回应暂时无法播放，可按1/2继续。');
        note.textContent=`小班主：${value.response}`;
        showFeedback((value.transcript?`听到的是：“${value.transcript.slice(0,40)}”\n`:'')+'小班主正在回应…');
        await playAudio(value.audio);
        if(token!==generation)return;
        held=false;busy=false;
        onActivity(false);
        if(value.branch==='clarify'){refresh();note.textContent=`小班主：${value.response}`;return;}
        choose(value.branch);
        return;
      }
      await new Promise(resolve=>setTimeout(resolve,250));
    }
  }
  async function begin(automatic=false) {
    if(!canTalk()||busy)return;
    clearTimeout(autoTimer);autoTimer=null;
    held=!automatic;busy=true;
    onActivity(true);
    const token=++generation;
    transcript.textContent='';
    note.textContent=automatic?'正在自动收音，请直接说出选择…':'正在录音，请说出你的主意…';
    showFeedback('话筒准备中，请稍等…');
    refresh();
    startPending=request('start',automatic);
    try {
      await startPending;
      if(token!==generation){void request('cancel').catch(()=>{});return;}
      if(automatic){await waitForReply(token);return;}
      // Handles releasing the key before the start response arrives.
      if(!held){await request('stop');await waitForReply(token);}
    } catch(error) {
      await handleFailure(error,token,automatic);
    } finally {startPending=null;}
  }
  async function end() {
    if(!held)return;
    held=false;refresh();
    if(startPending)return;
    const token=generation;
    try {await request('stop');await waitForReply(token);}
    catch(error){if(token===generation){busy=false;onActivity(false);refresh();note.textContent=error.message;}}
  }
  button.addEventListener('pointerdown',event=>{event.preventDefault();button.setPointerCapture(event.pointerId);void begin();});
  button.addEventListener('pointerup',()=>void end());
  button.addEventListener('pointercancel',()=>void end());
  function retryListen(){if(!canTalk()||busy)return;autoAttempts=0;refresh();}
  retry?.addEventListener('click',retryListen);
  mouseFirst?.addEventListener('click',()=>{if(canTalk())document.querySelector('#hide')?.click();});
  mouseSecond?.addEventListener('click',()=>{if(canTalk())document.querySelector('#alone')?.click();});
  document.addEventListener('keydown',event=>{if(event.key==='Enter'&&!event.repeat&&canTalk()&&getAuto()&&!busy&&autoAttempts>=3){event.preventDefault();retryListen();}});
  document.addEventListener('keydown',event=>{if(event.code==='Space'&&canTalk()){event.preventDefault();if(!event.repeat)void begin();}});
  document.addEventListener('keyup',event=>{if(event.code==='Space'){event.preventDefault();void end();}});
  window.addEventListener('blur',()=>{if(held)void end();});
  async function checkReady(){try{const status=await request('status');ready=status.ready;readyHint=status.reason||'';}catch{ready=false;}if(!busy)refresh();}
  void checkReady();
  setInterval(()=>{if(!busy)void checkReady();},5000);
  refresh();
  return {cancel,refresh};
}
