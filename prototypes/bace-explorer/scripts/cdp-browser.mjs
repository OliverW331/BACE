import fs from 'node:fs/promises';

export async function openBrowser(url='http://127.0.0.1:4173/') {
  const tab=await (await fetch('http://127.0.0.1:9334/json/new?about:blank',{method:'PUT'})).json();
  const ws=new WebSocket(tab.webSocketDebuggerUrl);
  await new Promise((resolve,reject)=>{ws.addEventListener('open',resolve,{once:true});ws.addEventListener('error',reject,{once:true})});
  let seq=0;const pending=new Map(),errors=[];
  ws.addEventListener('message',event=>{
    const msg=JSON.parse(event.data);
    if(msg.id){const entry=pending.get(msg.id);if(entry){clearTimeout(entry.timeout);pending.delete(msg.id);msg.error?entry.reject(msg.error):entry.resolve(msg.result)}}
    if(msg.method==='Runtime.exceptionThrown')errors.push(msg.params.exceptionDetails);
    if(msg.method==='Log.entryAdded'&&msg.params.entry.level==='error')errors.push(msg.params.entry);
  });
  const cdp=(method,params={})=>new Promise((resolve,reject)=>{
    const id=++seq,timeout=setTimeout(()=>{pending.delete(id);reject(Error(`CDP timeout: ${method}`))},15000);
    pending.set(id,{resolve,reject,timeout});ws.send(JSON.stringify({id,method,params}));
  });
  const run=async expression=>{const r=await cdp('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(r.exceptionDetails)throw Error(JSON.stringify(r.exceptionDetails));return r.result.value};
  const sleep=ms=>new Promise(resolve=>setTimeout(resolve,ms));
  const moveAway=()=>cdp('Input.dispatchMouseEvent',{type:'mouseMoved',x:5,y:5});
  const click=async selector=>{
    const point=await run(`(()=>{const e=document.querySelector(${JSON.stringify(selector)});if(!e)throw Error('Missing target: '+${JSON.stringify(selector)});e.scrollIntoView({block:'nearest',inline:'nearest'});const r=e.getClientRects()[0];return{x:r.x+r.width/2,y:r.y+r.height/2}})()`);
    await cdp('Input.dispatchMouseEvent',{type:'mouseMoved',...point});
    await cdp('Input.dispatchMouseEvent',{type:'mousePressed',button:'left',clickCount:1,...point});
    await cdp('Input.dispatchMouseEvent',{type:'mouseReleased',button:'left',clickCount:1,...point});
    await sleep(100);
  };
  const key=async (key,code=key,keyCode=key==='Escape'?27:13)=>{
    await cdp('Input.dispatchKeyEvent',{type:'keyDown',key,code,windowsVirtualKeyCode:keyCode,...(key==='Enter'?{text:'\r',unmodifiedText:'\r'}:{})});
    await cdp('Input.dispatchKeyEvent',{type:'keyUp',key,code,windowsVirtualKeyCode:keyCode});await sleep(100);
  };
  const waitFor=async expression=>{for(let i=0;i<100;i++){if(await run(`Boolean(${expression})`))return;await sleep(100)}throw Error(`Timeout: ${expression}`)};
  const viewport=async (width,height)=>{await cdp('Emulation.setDeviceMetricsOverride',{width,height,deviceScaleFactor:1,mobile:false});await sleep(150)};
  const capture=async path=>{await moveAway();await sleep(150);const shot=await cdp('Page.captureScreenshot',{format:'png',captureBeyondViewport:false});await fs.writeFile(path,Buffer.from(shot.data,'base64'))};
  await cdp('Runtime.enable');await cdp('Log.enable');await cdp('Page.enable');await viewport(1710,803);await cdp('Page.navigate',{url});
  return {cdp,run,sleep,click,key,waitFor,viewport,capture,moveAway,errors,close:()=>ws.close()};
}
