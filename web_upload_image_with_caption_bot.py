# web_upload.py  (Railway version - NOW STREAMING poster)
#
# Env in Railway > Variables:
#   API_ID, API_HASH, BOT_TOKEN
#   CHANNEL_ID = single channel (e.g. -1001234567890 or @cinepopx)
#   CHANNELS   = multiple channels comma separated (e.g. -1001111,-1002222,@cinepopx)
#   CHANNEL_NAMES = optional labels comma separated (e.g. CinePopX,Hub)
#   KEY, PORT (auto)
#
# Open: https://<your-railway-domain>/?key=<KEY>
import asyncio, html, os, re, secrets, sys
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from telethon import TelegramClient, events
from telethon.errors import FloodWaitError
from telethon.sessions import StringSession

PORT = int(os.environ.get("PORT", "8000"))
WAIT_FOR_POST = 300
TMP_DIR = Path("/tmp/web_tmp")

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
STATE = {"client": None, "target": None, "targets": [], "target_map": {}, "token": ""}

PAGE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>NOW STREAMING - Telegram Poster</title>
<style>
  :root{--bg:#1a1d23;--card:#1e222c;--text:#e8e8ea;--muted:#8a8f9c;--accent:#4c8dff;--shadow-dark:#0f1115;--shadow-light:#252a38;--inset-dark:#15181f;--inset-light:#222734}
  *{box-sizing:border-box}
  body{font-family:system-ui,sans-serif;background:var(--bg);color:var(--text);margin:0;padding:20px}
  .wrap{max-width:760px;margin:0 auto}
  h1{font-size:22px;text-align:center;margin:0 0 6px;letter-spacing:1px}
  .sub{color:var(--muted);text-align:center;font-size:13px;margin-bottom:20px}
  .card{background:var(--card);border-radius:20px;padding:22px;box-shadow: 10px 10px 20px var(--shadow-dark), -10px -10px 20px var(--shadow-light);margin-bottom:20px}
  label{font-size:12px;color:var(--muted);letter-spacing:.5px;margin:14px 0 6px;display:block}
  label:first-child{margin-top:0}
  input,textarea,select{width:100%;background:var(--card);border:none;outline:none;color:var(--text);padding:12px 14px;border-radius:12px;box-shadow: inset 5px 5px 10px var(--inset-dark), inset -5px -5px 10px var(--inset-light);font-size:14px;font-family:inherit}
  textarea{resize:vertical;min-height:80px}
  select{cursor:pointer}
  .grid2{display:grid;grid-template-columns:1fr 1fr;gap:12px}
  @media(max-width:600px){.grid2{grid-template-columns:1fr}}
  .filebox{border-radius:12px;padding:20px;text-align:center;cursor:pointer;box-shadow: inset 5px 5px 10px var(--inset-dark), inset -5px -5px 10px var(--inset-light);border:2px dashed #2e3444}
  .filebox.over{border-color:var(--accent)}
  .filebox small{color:var(--muted)}
  #previewImg{max-width:100%;border-radius:12px;margin-top:12px;display:none;box-shadow: 6px 6px 12px var(--shadow-dark)}
  .btn{width:100%;margin-top:18px;padding:14px;border:none;border-radius:14px;background:var(--card);color:var(--text);font-weight:700;letter-spacing:.5px;cursor:pointer;box-shadow: 6px 6px 12px var(--shadow-dark), -6px -6px 12px var(--shadow-light);transition:.15s}
  .btn:active{box-shadow: inset 5px 5px 10px var(--inset-dark), inset -5px -5px 10px var(--inset-light)}
  .btn:disabled{opacity:.6;cursor:not-allowed}
  #preview{white-space:pre-wrap;background:var(--card);border-radius:14px;padding:14px;font-size:13px;line-height:1.5;box-shadow: inset 5px 5px 10px var(--inset-dark), inset -5px -5px 10px var(--inset-light);max-height:420px;overflow:auto}
  .status{margin-top:12px;font-size:13px;text-align:center;min-height:18px}
  .status.ok{color:#2ecc71}.status.err{color:#ff6b6b}
</style></head><body><div class="wrap">
<h1>🎬 NOW STREAMING 🎬</h1>
<p class="sub">Neumorphism Poster • Image + Exact Caption Format</p>

<div class="card">
  <label>Post to Channel *</label>
  <select id="channel">__CHANNEL_OPTIONS__</select>

  <label>Poster Image (required)</label>
  <div id="drop" class="filebox">Tap or drop image here<br><small>JPG, PNG, WEBP - sent as-is for best clarity</small><input id="file" type="file" accept="image/*" hidden></div>
  <img id="previewImg">

  <label>Movie Title *</label>
  <input id="title" placeholder="e.g. Salamat Daks">

  <div class="grid2">
    <div><label>Year</label><input id="year" placeholder="2023"></div>
    <div><label>Studio</label><input id="studio" placeholder="Vivamax"></div>
  </div>

  <label>Tagline (line 3)</label>
  <input id="tagline" placeholder="Turning back time has never been this tempting. ⏰🔥">

  <label>Description</label>
  <textarea id="desc" placeholder="A woman turns to technology to be younger again..."></textarea>

  <label>Quality / Type Line</label>
  <input id="quality" value="HD | FULL MOVIE | EP 1/1">

  <div class="grid2">
    <div><label>Rating</label><input id="rating" placeholder="4.7/10"></div>
    <div><label>Votes</label><input id="votes" placeholder="496"></div>
  </div>

  <label>Stars (separate with , or · )</label>
  <input id="stars" placeholder="Ayanna Misola, Nikko Natividad, Alma Moreno">

  <label>Director</label>
  <input id="director" placeholder="Bobby Bonifacio Jr.">

  <label>Writers (separate with ,)</label>
  <input id="writers" placeholder="Bobby Bonifacio Jr., Corrine Cornejo">

  <label>WATCH HERE Channels (one per line)</label>
  <textarea id="channels" style="min-height:60px">@cinepopx
@philippines_adult_movies_hub</textarea>

  <label>Links (one per line)</label>
  <textarea id="links" placeholder="https://streamtape.com/v/...
https://www.diskwala.com/app/...
https://t.me/payment_vmx_bot"></textarea>

  <label>Hashtags (space separated, # will be added if missing)</label>
  <input id="tags" placeholder="#SalamatDaks #VivamaxOriginal #2023">

  <label>Bottom Line</label>
  <input id="bottom" placeholder="⏰ Second chances never looked so good. Watch now">

  <button id="send" class="btn">📤 POST TO TELEGRAM</button>
  <div id="status" class="status"></div>
</div>

<div class="card">
  <label>Live Preview (exact caption)</label>
  <div id="preview"></div>
</div>

</div>
<script>
const KEY="__KEY__";
const $=id=>document.getElementById(id);
const els=['title','year','studio','tagline','desc','quality','rating','votes','stars','director','writers','channels','links','tags','bottom'].map($);
const drop=$('drop'), fileIn=$('file'), img=$('previewImg'), preview=$('preview'), status=$('status'), btn=$('send');
let chosenFile=null;

drop.onclick=()=>fileIn.click();
drop.ondragover=e=>{e.preventDefault();drop.classList.add('over')};
drop.ondragleave=()=>drop.classList.remove('over');
drop.ondrop=e=>{e.preventDefault();drop.classList.remove('over'); if(e.dataTransfer.files[0]) handleFile(e.dataTransfer.files[0])};
fileIn.onchange=()=>{if(fileIn.files[0]) handleFile(fileIn.files[0])};
function handleFile(f){
  chosenFile=f;
  img.src=URL.createObjectURL(f);
  img.style.display='block';
  drop.innerHTML=`Selected: <b>${f.name}</b><br><small>Tap to change</small>`;
  update();
}
function buildCaption(){
  const v=id=>$(id).value.trim();
  const title=v('title')||'Movie Title';
  const year=v('year'), studio=v('studio');
  const head = `🎬 NOW STREAMING 🎬\n${title}${year?` (${year})`:''}${studio?` | ${studio} Original`:''}`;
  const tagline=v('tagline');
  const desc=v('desc');
  const quality=v('quality')?`🎥 ${v('quality')}`:'';
  const rating=v('rating'), votes=v('votes');
  const ratingLine = rating?`⭐️ Rating: ${rating}${votes?` (${votes} votes)`:''}`:'';
  const stars=v('stars')?`👥 Stars: ${v('stars').split(/[,·]+/).map(s=>s.trim()).filter(Boolean).join(' · ')}`:'';
  const director=v('director')?`🎬 Director: ${v('director')}`:'';
  const writers=v('writers')?`✍️ Writers: ${v('writers').split(',').map(s=>s.trim()).filter(Boolean).join(' · ')}`:'';
  const channels=v('channels').split('\n').map(s=>s.trim()).filter(Boolean);
  const links=v('links').split('\n').map(s=>s.trim()).filter(Boolean);
  let tags=v('tags').split(/\s+/).filter(Boolean).map(t=>t.startsWith('#')?t:'#'+t.replace(/^#+/,'')).join(' ');
  const bottom=v('bottom');
  let out=[head];
  if(tagline) out.push(tagline);
  if(desc) out.push(desc);
  if(quality) out.push(quality);
  if(ratingLine) out.push(ratingLine);
  if(stars) out.push(stars);
  if(director) out.push(director);
  if(writers) out.push(writers);
  if(channels.length){
    out.push(`📥 WATCH HERE:`);
    channels.forEach(c=>out.push(c));
  }
  if(links.length){
    out.push(`🔗 Link:`);
    links.forEach((l,i)=>out.push(`${i+1}. ${l}`));
  }
  if(tags) out.push(`\n${tags}`);
  if(bottom) out.push(bottom);
  return out.join('\n');
}
function update(){ preview.textContent=buildCaption(); }
els.forEach(e=>e.addEventListener('input',update));
update();

btn.onclick=async()=>{
  if(!chosenFile){ status.textContent='Please select an image'; status.className='status err'; return; }
  if(!$('title').value.trim()){ status.textContent='Title is required'; status.className='status err'; return; }
  btn.disabled=true; status.textContent='Posting...'; status.className='status';
  const fd=new FormData();
  fd.append('image', chosenFile);
  fd.append('channel', $('channel').value);
  ['title','year','studio','tagline','desc','quality','rating','votes','stars','director','writers','channels','links','tags','bottom'].forEach(id=>fd.append(id, $(id).value));
  try{
    const r=await fetch('/?key='+encodeURIComponent(KEY),{method:'POST',body:fd});
    const text = await r.text();
    let j={}; try{ j=JSON.parse(text); } catch{ throw new Error(text.slice(0,400) || 'Server error'); }
    if(!r.ok) throw new Error(j.detail||text.slice(0,400));
    status.textContent='✅ Posted to channel!'; status.className='status ok';
  }catch(e){ status.textContent='❌ '+e.message; status.className='status err'; }
  btn.disabled=false;
}
</script></body></html>
"""

def check(key: str):
    if not key or not secrets.compare_digest(key, STATE["token"]):
        raise HTTPException(status_code=403, detail="bad key")

def build_caption_from_form(data: dict) -> str:
    e = html.escape
    title = data.get("title","").strip() or "Movie Title"
    year = data.get("year","").strip()
    studio = data.get("studio","").strip()
    tagline = data.get("tagline","").strip()
    desc = data.get("desc","").strip()
    quality = data.get("quality","").strip()
    rating = data.get("rating","").strip()
    votes = data.get("votes","").strip()
    stars_raw = data.get("stars","").strip()
    director = data.get("director","").strip()
    writers_raw = data.get("writers","").strip()
    channels_raw = data.get("channels","").strip()
    links_raw = data.get("links","").strip()
    tags_raw = data.get("tags","").strip()
    bottom = data.get("bottom","").strip()

    # FIX 1: Bold exactly like screenshot
    title_line = f'<b>{e(title.upper())}</b>' + (f' <b>({e(year)})</b>' if year else '') + (f' | <b>{e(studio)} Original</b>' if studio else '')
    lines = [f'🎬 <b>NOW STREAMING</b> 🎬', title_line]

    if tagline: lines.append(f'<b>{e(tagline)}</b>')
    if desc: lines.append(e(desc))
    if quality: lines.append(f'🎥 <b>{e(quality)}</b>')
    if rating: lines.append(f'⭐️ <b>Rating:</b> {e(rating)}' + (f' ({e(votes)} votes)' if votes else ''))
    if stars_raw:
        stars = " · ".join([s.strip() for s in re.split(r"[,·]+", stars_raw) if s.strip()])
        if stars: lines.append(f'👥 <b>Stars:</b> {e(stars)}')
    if director: lines.append(f'🎬 <b>Director:</b> {e(director)}')
    if writers_raw:
        writers = " · ".join([s.strip() for s in writers_raw.split(",") if s.strip()])
        if writers: lines.append(f'✍️ <b>Writers:</b> {e(writers)}')
    
    channels = [c.strip() for c in channels_raw.splitlines() if c.strip()]
    if channels:
        lines.append('📥 <b>WATCH HERE:</b>')
        lines.extend(e(c) for c in channels)
    
    links = [l.strip() for l in links_raw.splitlines() if l.strip()]
    if links:
        lines.append('🔗 <b>Link:</b>')
        for i,l in enumerate(links,1):
            lines.append(f'{i}. {e(l)}')
    
    if tags_raw:
        tags = []
        for t in tags_raw.split():
            t=t.strip()
            if not t: continue
            if not t.startswith("#"): t="#"+t.lstrip("#")
            tags.append(e(t))
        if tags: lines.append('\n' + " ".join(tags))
    
    if bottom: lines.append(f'<i>{e(bottom)}</i>')

    caption = "\n".join(lines)
    # Telegram caption limit 1024 chars - truncate HTML safely before sending
    # plain text length check
    plain = re.sub(r"<[^>]+>", "", html.unescape(caption))
    if len(plain) > 1024:
        caption = caption[:1021] + "…"
    return caption

@app.get("/", response_class=HTMLResponse)
async def index(key: str = ""):
    check(key)
    # build channel options for UI
    opts = ""
    for idx, label in enumerate(STATE["target_map"].keys()):
        opts += f'<option value="{idx}">{html.escape(label)}</option>'
    if not opts:
        opts = '<option value="0">Default Channel</option>'
    return PAGE.replace("__KEY__", key).replace("__CHANNEL_OPTIONS__", opts)

@app.post("/")
async def post_image(request: Request, key: str = ""):
    try:
        check(key)
        form = await request.form()
        image: UploadFile = form.get("image")
        if not image or not image.filename:
            raise HTTPException(status_code=400, detail="image required")
        data = {k: str(form.get(k) or "") for k in ["title","year","studio","tagline","desc","quality","rating","votes","stars","director","writers","channels","links","tags","bottom"]}
        if not data["title"].strip():
            raise HTTPException(status_code=400, detail="title required")

        # FIX 3: pick channel without restarting bot
        ch_idx = 0
        try:
            ch_idx = int(str(form.get("channel") or "0"))
        except: pass
        if STATE["targets"] and 0 <= ch_idx < len(STATE["targets"]):
            target = STATE["targets"][ch_idx]
        else:
            target = STATE["target"]

        caption = build_caption_from_form(data)
        tmp = TMP_DIR / f"poster_{secrets.token_hex(4)}{Path(image.filename).suffix or '.jpg'}"
        TMP_DIR.mkdir(parents=True, exist_ok=True)
        content = await image.read()
        if len(content) > 10*1024*1024:
            raise HTTPException(status_code=400, detail="image too large (max 10MB)")
        if len(content) < 10*1024:
            raise HTTPException(status_code=400, detail="image file is corrupted or too small")
        tmp.write_bytes(content)

        client = STATE["client"]
        try:
            for attempt in range(5):
                try:
                    # FIX 2: send original bytes as photo, high quality (no recompression)
                    await client.send_file(target, str(tmp), caption=caption, parse_mode="html", force_document=False)
                    break
                except FloodWaitError as e:
                    await asyncio.sleep(e.seconds + 1)
                except (ConnectionError, OSError, asyncio.TimeoutError):
                    await asyncio.sleep(5*(attempt+1))
            else:
                raise HTTPException(status_code=500, detail="failed after 5 retries")
        finally:
            tmp.unlink(missing_ok=True)
        return {"ok": True}
    except HTTPException:
        raise
    except Exception as ex:
        import traceback; traceback.print_exc()
        return JSONResponse(status_code=500, content={"detail": str(ex)[:400]})

# --- Telegram startup ---
async def resolve_channel(client, channel):
    try: return await client.get_input_entity(channel)
    except Exception: pass
    if not isinstance(channel, int): return None
    loop = asyncio.get_running_loop()
    fut = loop.create_future()
    async def on_msg(event):
        if event.chat_id == channel and not fut.done():
            fut.set_result(await event.get_input_chat())
    client.add_event_handler(on_msg, events.NewMessage())
    print("Now post any short message in your channel (e.g. 'start')...", flush=True)
    try: return await asyncio.wait_for(fut, timeout=WAIT_FOR_POST)
    except asyncio.TimeoutError: return None
    finally: client.remove_event_handler(on_msg)

def need(name: str) -> str:
    v = os.environ.get(name,"").strip()
    if not v: sys.exit(f"Missing environment variable: {name}")
    return v

def parse_channels():
    # CHANNELS takes priority, fallback to CHANNEL_ID
    raw = os.environ.get("CHANNELS","").strip() or os.environ.get("CHANNEL_ID","").strip()
    if not raw:
        sys.exit("Missing CHANNEL_ID or CHANNELS")
    names_raw = os.environ.get("CHANNEL_NAMES","").strip()
    labels = [n.strip() for n in names_raw.split(",")] if names_raw else []
    ch_map = {}
    for i, ch in enumerate([c.strip() for c in raw.split(",") if c.strip()]):
        cid = int(ch) if re.fullmatch(r"-?\d+", ch) else ch
        label = labels[i] if i < len(labels) and labels[i] else ch
        ch_map[label] = cid
    return ch_map

async def main():
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    api_id = int(need("API_ID")); api_hash = need("API_HASH")
    bot_tok = need("BOT_TOKEN")
    ch_map = parse_channels()
    key = os.environ.get("KEY","").strip() or secrets.token_urlsafe(16)
    client = TelegramClient(StringSession(), api_id, api_hash)
    await client.start(bot_token=bot_tok)

    targets = []
    for label, cid in ch_map.items():
        t = await resolve_channel(client, cid)
        if t is None:
            print(f"Channel not found: {label} ({cid}) - make bot admin.", flush=True)
            await client.disconnect(); sys.exit(1)
        targets.append(t)
        print(f"Channel OK: {label}", flush=True)

    STATE.update(client=client, target=targets[0], targets=targets, target_map=ch_map, token=key)
    domain = os.environ.get("RAILWAY_PUBLIC_DOMAIN","")
    print("="*60, flush=True)
    print(f"Open: https://{domain}/?key={key}" if domain else f"Open: https://<your-domain>/?key={key}", flush=True)
    print(f"Channels: {', '.join(ch_map.keys())}", flush=True)
    print("="*60, flush=True)
    server = uvicorn.Server(uvicorn.Config(app, host="0.0.0.0", port=PORT, log_level="warning"))
    try: await server.serve()
    finally: await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
