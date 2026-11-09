(() => {
  const themes = [
    {id:"dark",name:"Dark Cinema",group:"original",bg:"#20201e",fg:"#e8e2d8",accent:"#c16b56"},
    {id:"light",name:"Paper Journal",group:"original",bg:"#f5f1e8",fg:"#24221f",accent:"#8b3d2e"},
    {id:"forest",name:"Forest Study",group:"original",bg:"#1c2820",fg:"#e1e8d8",accent:"#a9bf86"},
    {id:"velvet",name:"Velvet Curtain",group:"original",bg:"#291b27",fg:"#f1dce5",accent:"#e4a1b5"},
    {id:"blue",name:"Bad Signal Blue",group:"analog",bg:"#050814",fg:"#d9e6ff",accent:"#7196ff"},
    {id:"grey",name:"Cathode Static Grey",group:"analog",bg:"#0b0d10",fg:"#edf2f7",accent:"#d8e0e8"},
    {id:"nixie",name:"Nixie Clock Red",group:"analog",bg:"#120806",fg:"#ffe4d6",accent:"#ff934f"},
    {id:"dos",name:"DOS Screen Green",group:"secret",bg:"#07110b",fg:"#9ff7bf",accent:"#66ff99"}
  ];
  const root=document.documentElement;
  const dialog=document.getElementById("appearance-dialog");
  const backdrop=document.getElementById("appearance-layer");
  const openButton=document.getElementById("appearance-open");
  const closeButton=document.getElementById("appearance-close");
  const notice=document.getElementById("appearance-notice");
  const logo=document.querySelector(".brand");
  if(!dialog||!backdrop||!openButton||!closeButton)return;
  let unlocked=false;
  try{unlocked=localStorage.getItem("atc-secret-dos")==="true"}catch(_){}
  const stored=root.dataset.theme||"dark";
  if(stored==="dos"&&!unlocked)root.dataset.theme="dark";
  let lastFocused=null;
  const grids={
    original:document.getElementById("appearance-original"),
    analog:document.getElementById("appearance-analog"),
    secret:document.getElementById("appearance-secret")
  };
  function makeTile(theme){
    const btn=document.createElement("button");
    btn.type="button";btn.className="appearance-choice";btn.dataset.palette=theme.id;
    btn.setAttribute("aria-pressed",String((root.dataset.theme||"dark")===theme.id));
    const sw=document.createElement("span");
    sw.className="appearance-swatch";
    sw.style.setProperty("--sw-bg",theme.bg);
    sw.style.setProperty("--sw-text",theme.fg);
    sw.style.setProperty("--sw-accent",theme.accent);
    const name=document.createElement("span");name.className="appearance-swatch-name";name.textContent="Aa · 0123";
    const line=document.createElement("span");line.className="appearance-swatch-line";sw.append(name,line);
    const label=document.createElement("span");label.className="appearance-choice-caption";
    const title=document.createElement("span");title.textContent=theme.name;
    const check=document.createElement("span");check.className="appearance-check";check.textContent=btn.getAttribute("aria-pressed")==="true"?"✓":"";
    label.append(title,check);btn.append(sw,label);
    btn.addEventListener("click",()=>choose(theme.id));
    return btn;
  }
  function render(){
    for(const key of ["original","analog"]){
      grids[key]?.replaceChildren(...themes.filter(t=>t.group===key).map(makeTile));
    }
    if(grids.secret){
      if(unlocked)grids.secret.replaceChildren(makeTile(themes.find(t=>t.id==="dos")));
      else {const message=document.createElement("div");message.className="appearance-locked";message.textContent="Locked · A hidden frequency awaits.";grids.secret.replaceChildren(message)}
    }
  }
  function choose(id){
    if(id==="dos"&&!unlocked)return;
    root.dataset.theme=id;
    try{localStorage.setItem("atc-theme",id)}catch(_){}
    render();
    const theme=themes.find(t=>t.id===id);
    if(notice)notice.textContent=theme?theme.name+" selected.":"";
  }
  function setOpen(open){
    dialog.hidden=!open;backdrop.hidden=!open;
    openButton.setAttribute("aria-expanded",String(open));
    document.body.style.overflow=open?"hidden":"";
    if(open){lastFocused=document.activeElement;render();closeButton.focus()}
    else if(lastFocused instanceof HTMLElement)lastFocused.focus();
  }
  openButton.addEventListener("click",()=>setOpen(dialog.hidden));
  closeButton.addEventListener("click",()=>setOpen(false));
  backdrop.addEventListener("click",()=>setOpen(false));
  document.addEventListener("keydown",event=>{
    if(dialog.hidden)return;
    if(event.key==="Escape"){event.preventDefault();setOpen(false);return}
    if(event.key==="Tab"){
      const focusable=Array.from(dialog.querySelectorAll("button:not([disabled])"));
      const first=focusable[0],last=focusable[focusable.length-1];
      if(event.shiftKey&&document.activeElement===first){event.preventDefault();last.focus()}
      else if(!event.shiftKey&&document.activeElement===last){event.preventDefault();first.focus()}
    }
  });
  let taps=0,lastTap=0;
  logo?.addEventListener("click",event=>{
    // Keep the logo as a normal Home link on other pages.
    if(unlocked||window.location.pathname!=="/")return;
    event.preventDefault();
    const now=Date.now();
    taps=now-lastTap>3000?1:taps+1;lastTap=now;
    if(taps>=5){
      unlocked=true;
      try{localStorage.setItem("atc-secret-dos","true")}catch(_){}
      setOpen(true);
      if(notice)notice.textContent="✦ Hidden frequency discovered: DOS Screen Green.";
      taps=0;
    }
  });
  render();
})();