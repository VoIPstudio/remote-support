const { chromium } = require('playwright');
const fs = require('fs');
const B = '/opt/claude-devops/tmp/rustdesk-branding';
const svg = n => fs.readFileSync(`${B}/assets/${n}.svg`, 'utf8');
const page = (w, h, body, bg = 'transparent') =>
  `<html><head><style>html,body{margin:0;padding:0;background:${bg};width:${w}px;height:${h}px;overflow:hidden}
   svg{display:block}</style></head><body>${body}</body></html>`;
const plain = (name, s) => page(s, s, svg(name).replace('<svg ', `<svg width="${s}" height="${s}" `));
// macOS: Apple grid - 824px rounded square (r=185) centred on 1024, drop shadow, mark inside
const mac = s => { const k = s / 1024;
  return page(s, s, `<div style="position:absolute;left:${100*k}px;top:${92*k}px;width:${824*k}px;height:${824*k}px;
    border-radius:${185*k}px;background:#fff;box-shadow:0 ${10*k}px ${24*k}px rgba(0,0,0,.28)">
    ${svg('icon-square').replace('<svg ', `<svg width="${824*k}" height="${824*k}" `)}</div>`); };
// in-app banner: mark + name, 2x of the 300x60 maximum
const banner = (color) => page(600, 120, `<div style="display:flex;align-items:center;height:120px;gap:18px;
    font-family:'Inter','Helvetica Neue','Segoe UI','DejaVu Sans',Arial,sans-serif;color:${color}">
    ${svg('icon-tight').replace('<svg ', '<svg width="104" height="104" ').replace(/#18181b/g, color === '#fff' ? '#ffffff' : '#18181b')}
    <div style="line-height:1.05"><div style="font-size:44px;font-weight:700;letter-spacing:-.5px">VoIPstudio</div>
    <div style="font-size:30px;font-weight:500;opacity:.85">Remote Support</div></div></div>`);
const jobs = [
  ['icon-1024.png', 1024, 1024, plain('icon-tile', 1024)],
  ...[16, 20, 24, 32, 40, 48, 64, 128, 256, 512].map(s => [`icon-${s}.png`, s, s, plain(s <= 48 ? 'icon-tile-small' : 'icon-tile', s)]),
  ['mac-1024.png', 1024, 1024, mac(1024)],
  ['mac-tray-dark-x2.png', 60, 60, plain('icon-black', 60)],
  ['mac-tray-light-x2.png', 48, 48, plain('icon-white', 48)],
  ['logo.png', 600, 120, banner('#18181b')],
  ['logo_light.png', 600, 120, banner('#18181b')],
  ['logo_dark.png', 600, 120, banner('#fff')],
];
(async () => {
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ deviceScaleFactor: 1 });
  const p = await ctx.newPage();
  for (const [out, w, h, html] of jobs) {
    await p.setViewportSize({ width: w, height: h });
    await p.setContent(html);
    await p.screenshot({ path: `${B}/assets/${out}`, omitBackground: true, clip: { x: 0, y: 0, width: w, height: h } });
  }
  await browser.close();
  console.log(`rendered ${jobs.length}`);
})();
