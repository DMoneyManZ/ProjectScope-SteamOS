"""Remember editing increments separately from portable preset values."""
import json
STEPS=(.1,.25,.5)
DIMENSIONS=frozenset(('scale','outline_width','lines.length','lines.thickness','lines.gap',
                       'dot.radius','circle.radius','circle.thickness'))
def options(default): return tuple(sorted(set((*STEPS,default))))
def step_for(cfg,key,default):
    try:
        values=json.loads(cfg.get_string('precision-steps'))
        value=values.get(key,default)
        return value if type(value) in (int,float) and value in options(default) else default
    except (ValueError,AttributeError): return default

def remember(cfg,key,value):
    try: values=json.loads(cfg.get_string('precision-steps'))
    except ValueError: values={}
    if not isinstance(values,dict): values={}
    values[key]=value
    cfg.set_string('precision-steps',json.dumps(values,sort_keys=True))
