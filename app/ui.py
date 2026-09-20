"""Dependency-free browser chat interface for the development demonstration."""
from fastapi.responses import HTMLResponse


CHAT_PAGE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Banksy | Banking support</title>
  <style>
    :root { color-scheme: light; --navy:#17253d; --blue:#1677ef; --blue-dark:#0e61c7; --ink:#172033; --muted:#667085; --line:#e5eaf1; --canvas:#f3f6fa; --card:#fff; }
    * { box-sizing:border-box; }
    body { min-height:100vh; margin:0; background:linear-gradient(140deg,#edf4ff 0%,var(--canvas) 42%,#f8fafc 100%); color:var(--ink); font-family:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; }
    .shell { width:min(100%,880px); min-height:100vh; margin:0 auto; padding:28px 20px; display:flex; align-items:center; }
    .chat-window { width:100%; height:min(780px,calc(100vh - 56px)); min-height:610px; display:flex; flex-direction:column; overflow:hidden; background:var(--card); border:1px solid rgba(211,220,232,.9); border-radius:22px; box-shadow:0 20px 55px rgba(29,48,81,.14); }
    .topbar { display:flex; align-items:center; gap:13px; padding:18px 22px; color:#fff; background:var(--navy); }
    .brand-mark,.avatar { display:grid; place-items:center; flex:0 0 auto; border-radius:50%; font-weight:750; }
    .brand-mark { width:40px; height:40px; color:var(--navy); background:#a8d7ff; box-shadow:inset 0 0 0 5px rgba(255,255,255,.35); }
    .brand-copy { min-width:0; } .brand-copy strong { display:block; font-size:17px; letter-spacing:-.01em; } .brand-copy span { display:block; margin-top:2px; color:#b9cbe2; font-size:13px; }
    .status { display:flex; align-items:center; gap:6px; margin-left:auto; color:#dcecff; font-size:12px; white-space:nowrap; } .status::before { width:8px; height:8px; content:""; border-radius:50%; background:#42d392; box-shadow:0 0 0 3px rgba(66,211,146,.15); }
    #chat { flex:1; overflow-y:auto; padding:26px clamp(16px,4vw,34px); background:radial-gradient(circle at 88% 5%,#edf7ff 0,transparent 24%),#f8fafc; }
    .intro { margin:0 0 24px 54px; max-width:580px; } .intro h1 { margin:0 0 7px; font-size:22px; letter-spacing:-.03em; } .intro p { margin:0; color:var(--muted); font-size:14px; line-height:1.55; }
    .message-row { display:flex; gap:10px; align-items:flex-end; margin:14px 0; } .message-row.user { justify-content:flex-end; }
    .avatar { width:34px; height:34px; color:#fff; background:linear-gradient(135deg,#1677ef,#63b3ff); font-size:14px; box-shadow:0 5px 12px rgba(22,119,239,.2); }
    .bubble { max-width:min(78%,580px); padding:12px 15px; border:1px solid var(--line); border-radius:15px 15px 15px 4px; background:#fff; box-shadow:0 2px 5px rgba(27,48,84,.04); font-size:14px; line-height:1.48; white-space:pre-wrap; }
    .user .bubble { color:#fff; border-color:transparent; border-radius:15px 15px 4px 15px; background:linear-gradient(135deg,var(--blue),#2c8df5); box-shadow:0 7px 16px rgba(22,119,239,.2); }
    .error .bubble { color:#9d2631; border-color:#f6c8ce; background:#fff5f5; } .typing .bubble { color:var(--muted); font-style:italic; }
    .suggestions { margin:22px 0 6px 44px; } .suggestions p { margin:0 0 10px; color:var(--muted); font-size:13px; font-weight:650; } .suggestion-list { display:flex; flex-wrap:wrap; gap:8px; }
    .suggestion { padding:9px 11px; color:#245485; border:1px solid #cfe2f8; border-radius:10px; background:#fff; font:600 13px inherit; text-align:left; cursor:pointer; transition:.15s ease; } .suggestion:hover,.suggestion:focus-visible { border-color:var(--blue); background:#edf6ff; outline:none; }
    .composer { padding:15px clamp(16px,4vw,28px) 18px; border-top:1px solid var(--line); background:#fff; } .composer-form { display:flex; align-items:flex-end; gap:10px; padding:7px 7px 7px 15px; border:1px solid #ccd6e4; border-radius:15px; background:#fff; transition:border-color .15s,box-shadow .15s; } .composer-form:focus-within { border-color:var(--blue); box-shadow:0 0 0 3px rgba(22,119,239,.12); }
    textarea { min-height:27px; max-height:120px; flex:1; resize:none; padding:4px 0; border:0; outline:0; color:var(--ink); background:transparent; font:14px/1.4 inherit; } textarea::placeholder { color:#8a97a9; }
    #send { display:grid; width:40px; height:40px; place-items:center; flex:0 0 auto; border:0; border-radius:11px; color:#fff; background:var(--blue); cursor:pointer; transition:.15s ease; } #send:hover { background:var(--blue-dark); } #send:disabled { cursor:wait; opacity:.6; } #send svg { width:19px; height:19px; }
    .composer-note { margin:9px 4px 0; color:#7a8798; font-size:11px; text-align:center; } kbd { padding:1px 4px; border:1px solid #d6dde7; border-radius:3px; background:#f6f8fb; font:inherit; }
    @media (max-width:620px) { .shell { padding:0; } .chat-window { min-height:100vh; height:100vh; border:0; border-radius:0; } .status { display:none; } #chat { padding-top:22px; } .intro,.suggestions { margin-left:0; } .bubble { max-width:84%; } }
  </style>
</head>
<body>
  <main class="shell">
    <section class="chat-window" aria-label="Banksy banking support chat">
      <header class="topbar"><div class="brand-mark" aria-hidden="true">B</div><div class="brand-copy"><strong>Banksy</strong><span>Your banking support assistant</span></div><div class="status">Online</div></header>
      <div id="chat" aria-live="polite" aria-relevant="additions">
        <div class="intro"><h1>Welcome to Banksy</h1><p>Get help with everyday banking in one secure conversation.</p></div>
        <div class="message-row assistant"><div class="avatar" aria-hidden="true">B</div><div class="bubble">Hi! I’m Banksy. I can help with balances, recent transactions, statements, address updates, cheque books, and KYC. What would you like to do today?</div></div>
        <div class="suggestions" id="suggestions"><p>Try one of these</p><div class="suggestion-list"><button class="suggestion" type="button">What is my available balance?</button><button class="suggestion" type="button">Show my recent transactions</button><button class="suggestion" type="button">How do I update my address?</button><button class="suggestion" type="button">Request a cheque book</button></div></div>
      </div>
      <div class="composer"><form class="composer-form" id="composer"><textarea id="message" rows="1" maxlength="4000" placeholder="Message Banksy..." aria-label="Message Banksy"></textarea><button id="send" type="submit" aria-label="Send message"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m22 2-7 20-4-9-9-4Z"/><path d="M22 2 11 13"/></svg></button></form><p class="composer-note">Press <kbd>Enter</kbd> to send · Please do not share passwords or one-time codes.</p></div>
    </section>
  </main>
  <script>
    const chat = document.querySelector('#chat');
    const form = document.querySelector('#composer');
    const input = document.querySelector('#message');
    const send = document.querySelector('#send');
    const sessionId = `banksy-${crypto.randomUUID ? crypto.randomUUID() : Date.now()}`;
    const scrollToLatest = () => { chat.scrollTop = chat.scrollHeight; };
    const addMessage = (text, kind = 'assistant') => {
      const row = document.createElement('div'); row.className = `message-row ${kind}`;
      if (kind !== 'user') { const avatar = document.createElement('div'); avatar.className = 'avatar'; avatar.setAttribute('aria-hidden', 'true'); avatar.textContent = 'B'; row.append(avatar); }
      const bubble = document.createElement('div'); bubble.className = 'bubble'; bubble.textContent = text; row.append(bubble); chat.append(row); scrollToLatest(); return row;
    };
    const resize = () => { input.style.height = 'auto'; input.style.height = `${Math.min(input.scrollHeight, 120)}px`; };
    async function submitMessage(message) {
      const text = message.trim(); if (!text || send.disabled) return;
      document.querySelector('#suggestions')?.remove(); addMessage(text, 'user'); input.value = ''; resize(); send.disabled = true;
      const typing = addMessage('Banksy is thinking…', 'typing');
      try {
        const response = await fetch('/v1/chat', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({session_id:sessionId, message:text}) });
        const data = await response.json(); typing.remove();
        if (!response.ok) throw new Error(data.detail || 'I could not complete that request. Please try again.');
        addMessage(data.response);
      } catch (error) { typing.remove(); addMessage(error.message || 'I could not complete that request. Please try again.', 'error'); }
      finally { send.disabled = false; input.focus(); }
    }
    form.addEventListener('submit', event => { event.preventDefault(); submitMessage(input.value); });
    input.addEventListener('input', resize);
    input.addEventListener('keydown', event => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); form.requestSubmit(); } });
    document.querySelectorAll('.suggestion').forEach(button => button.addEventListener('click', () => submitMessage(button.textContent)));
    scrollToLatest(); input.focus();
  </script>
</body>
</html>"""


def chat_page() -> HTMLResponse:
    """Return the same-origin development chat interface."""
    return HTMLResponse(CHAT_PAGE)
