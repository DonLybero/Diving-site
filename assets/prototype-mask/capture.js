// Render every frame of scene.html to a PNG via headless Chromium.
const { chromium } = require('/opt/node22/lib/node_modules/playwright');
const path = require('path');

(async () => {
  const only = process.argv[2] ? parseInt(process.argv[2],10) : null; // single-frame test
  const browser = await chromium.launch({
    executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome',
    args: ['--no-sandbox','--use-gl=swiftshader','--enable-unsafe-swdecoder']
  });
  const page = await browser.newPage({ viewport:{ width:1080, height:1350 }, deviceScaleFactor:1 });
  const url = 'file://' + path.resolve(__dirname, 'scene.html');
  await page.goto(url);
  await page.waitForFunction('window.__ready === true');
  const TOTAL = await page.evaluate('window.TOTAL');
  const canvas = await page.$('#stage');

  if (only !== null) {
    await page.evaluate(i => window.renderFrame(i), only);
    await page.waitForTimeout(60);
    await canvas.screenshot({ path: path.join(__dirname, 'test.png') });
    console.log('wrote test.png for frame', only);
    await browser.close();
    return;
  }

  for (let i=0;i<TOTAL;i++){
    await page.evaluate(idx => window.renderFrame(idx), i);
    const f = String(i).padStart(4,'0');
    await canvas.screenshot({ path: path.join(__dirname, 'frames', `f${f}.jpg`), type:'jpeg', quality:96 });
    if (i%30===0) console.log('frame', i, '/', TOTAL);
  }
  console.log('done', TOTAL, 'frames');
  await browser.close();
})();
