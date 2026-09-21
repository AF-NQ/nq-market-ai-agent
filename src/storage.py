import json
from pathlib import Path

class Store:
    def __init__(self,path):
        self.path=Path(path)
        self.path.parent.mkdir(parents=True,exist_ok=True)
        if self.path.exists():
            try: self.data=json.loads(self.path.read_text(encoding='utf-8'))
            except Exception: self.data={"seen":{},"state":{}}
        else: self.data={"seen":{},"state":{}}
    def new_events(self,items):
        out=[]
        for x in items:
            if x['id'] not in self.data['seen']:
                self.data['seen'][x['id']]={"ts":x['published'],"title":x['title']}
                out.append(x)
        # Keep a bounded state file.
        if len(self.data['seen'])>3000:
            keys=sorted(self.data['seen'],key=lambda k:self.data['seen'][k].get('ts',''))[-2500:]
            self.data['seen']={k:self.data['seen'][k] for k in keys}
        self.save(); return out
    def recent(self,limit=20): return []
    def get(self,k): return self.data['state'].get(k)
    def set(self,k,v): self.data['state'][k]=str(v); self.save()
    def save(self): self.path.write_text(json.dumps(self.data,ensure_ascii=False,indent=2),encoding='utf-8')
