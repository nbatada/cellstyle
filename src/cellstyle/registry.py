from dataclasses import dataclass,field
import pandas as pd
@dataclass
class ColorRegistry:
    entries:dict=field(default_factory=dict)
    def register(self,entity,color,parent=None,level=None,role="identity"): self.entries[entity]=dict(entity=entity,parent=parent,level=level,role=role,color=color)
    def color(self,entity): return self.entries[entity]["color"]
    def palette(self,entities): return [self.color(x) for x in entities]
    def to_tsv(self,path): pd.DataFrame(self.entries.values()).to_csv(path,sep="\t",index=False)
    @classmethod
    def from_tsv(cls,path):
        o=cls()
        for r in pd.read_csv(path,sep="\t").fillna("").to_dict("records"): o.register(r["entity"],r["color"],r.get("parent") or None,r.get("level") or None,r.get("role") or "identity")
        return o
