const { chromium } = require('playwright');
const API='http://127.0.0.1:8003/api';
const j=async(path,body,tok)=>{const r=await fetch(API+path,{method:'POST',headers:{'Content-Type':'application/json',...(tok?{Authorization:'Token '+tok}:{})},body:JSON.stringify(body||{})});return {s:r.status,d:await r.json().catch(()=>({}))}};
async function run(mode){
  const b=await chromium.launch(); const p=await b.newPage({viewport:{width:1366,height:768}});
  const errs=[]; p.on('console',m=>{if(m.type()==='error')errs.push(m.text())}); p.on('pageerror',e=>errs.push('PAGEERR '+e.message));
  const cps=[]; p.on('response',r=>{ if(/\/checkpoint\/|\/auth\/refresh\//.test(r.url())) cps.push(r.url().split('/api')[1]+' '+r.status()) });
  await p.goto('http://localhost:5175/'); await p.waitForTimeout(500); if(await p.locator('input[name=username]').count()===0){await p.getByRole('button',{name:'Login'}).first().click();await p.waitForTimeout(400)}
  await p.fill('input[name=username]','e2e_player'); await p.fill('input[name=password]','safe-password-123');
  await p.locator('button.primary.full').click(); await p.waitForTimeout(1200);
  if(await p.locator('button',{hasText:/^01/}).count()) await p.locator('button',{hasText:/^01/}).first().click(); await p.waitForTimeout(1000); await p.getByRole('button',{name:/Restart/}).first().click().catch(()=>{}); await p.waitForTimeout(800);
  const play=async(ks)=>{for(const k of ks){await p.keyboard.press(k);await p.waitForTimeout(400)}};
  await play(['ArrowRight','ArrowRight','ArrowRight','ArrowRight']); await p.waitForTimeout(600);
  const before=cps.length;
  // another device logs in then logs out
  const dev=await j('/auth/login/',{username:'e2e_player',password:'safe-password-123'});
  await j('/auth/logout/', mode==='per-device'?{refresh_token:dev.d.refresh_token}:{}, dev.d.token);
  await play(['ArrowDown','ArrowDown','ArrowDown','ArrowDown']); await p.waitForTimeout(2000);
  const body=await p.innerText('body');
  const out={mode, hud:(await p.innerText('body')).match(/Apples \d+ · Moves \d+ · Score \d+/)?.[0], allCheckpointCalls:cps, requestsAfterLogoutEvent:cps.slice(before), invalidTokenBannerShown:/Invalid token/i.test(body), sessionExpiredShown:/session has expired/i.test(body), onLoginScreen:(await p.locator('input[name=username]').count())>0, consoleErrors:errs.filter(e=>!/401/.test(e))};
  await p.screenshot({path:`after_${mode}.png`}); await b.close(); return out;
}
(async()=>{ console.log(JSON.stringify(await run(process.argv[2]),null,1)); })();
