"""Read controller buttons without grabbing devices or observing keyboards."""
import os
import fcntl
from pathlib import Path
import struct
import time

LEFT_BUMPER=310
RIGHT_BUMPER=311
Y_BUTTON=308
MENU_BUTTONS=frozenset((LEFT_BUMPER,RIGHT_BUMPER,Y_BUTTON))
EVENT=struct.Struct('@llHHi')

class AxisDirection:
    """Normalize signed/unsigned sticks with a dead zone and release hysteresis."""
    def __init__(self,minimum,maximum):
        self.center=(minimum+maximum)/2;self.radius=(maximum-minimum)/2;self.direction=0
    def event(self,value):
        if self.radius<=0: return 0
        position=(value-self.center)/self.radius
        direction=(-1 if position<0 else 1) if abs(position)>.55 else 0
        if abs(position)<.30: self.direction=0
        if direction and direction!=self.direction:
            self.direction=direction;return direction
        return 0


def axes_for(fd):
    result={}
    for code in (0,1):
        values=bytearray(24)
        try:
            # EVIOCGABS: _IOR('E', 0x40 + axis, struct input_absinfo), Linux.
            fcntl.ioctl(fd,0x80184540+code,values,True)
            _,minimum,maximum,_,_,_=struct.unpack('6i',values)
            result[code]=AxisDirection(minimum,maximum)
        except OSError: pass
    return result

class MenuChord:
    """One activation after a 600 ms hold; all three buttons must release to rearm."""
    def __init__(self): self.reset()
    def reset(self): self.pressed=set();self.since=None;self.fired=False
    def button(self,code,value,now):
        if code not in MENU_BUTTONS or value==2: return
        if value: self.pressed.add(code)
        else: self.pressed.discard(code)
        if self.pressed==MENU_BUTTONS:
            if self.since is None: self.since=now
        else: self.since=None
        if not self.pressed: self.fired=False
    def ready(self,now):
        if not self.fired and self.since is not None and now-self.since>=.6:
            self.fired=True;return True
        return False


class ChordGroup:
    """Treat physical/Steam Input mirrors as one hold; use one menu input source."""
    def __init__(self): self.latched=False;self.source=None
    def observe_release(self,chords):
        if not any(chord.pressed for chord in chords.values()): self.latched=False
    def poll(self,chords,now):
        self.observe_release(chords)
        ready=[source for source,chord in chords.items() if chord.ready(now)]
        if ready and not self.latched:
            self.latched=True;self.source=ready[0];return self.source
        return None


def controller_paths():
    """Only devices advertising gamepad and the menu chord buttons; never keyboard nodes."""
    for path in Path('/sys/class/input').glob('event*'):
        try:
            words=(path/'device/capabilities/key').read_text().split()
            bits=0
            for word in words: bits=(bits<<struct.calcsize('L')*8)|int(word,16)
            if all(bits&(1<<code) for code in (304,*MENU_BUTTONS)):
                yield Path('/dev/input')/path.name
        except (OSError,ValueError): continue

class ControllerMonitor:
    def __init__(self,open_menu,navigate=lambda *_:None):
        from gi.repository import GLib
        self.glib=GLib;self.open_menu=open_menu;self.navigate=navigate
        self.devices={};self.group=ChordGroup();self.timer=None;self.scan()
        self.scan_timer=GLib.timeout_add_seconds(2,self.scan)

    def scan(self):
        available=set(controller_paths())
        for path in list(self.devices):
            if path not in available: self.remove(path)
        for path in available-self.devices.keys():
            try: fd=os.open(path,os.O_RDONLY|os.O_NONBLOCK|os.O_CLOEXEC)
            except OSError: continue
            item={'fd':fd,'chord':MenuChord(),'buffer':b'','dropping':False,'axes':axes_for(fd),'hats':{}}
            self.devices[path]=item
            item['watch']=self.glib.io_add_watch(fd,self.glib.IO_IN|self.glib.IO_HUP|self.glib.IO_ERR,
                lambda _fd,condition,p=path:self.read(p,condition))
        return True

    def remove(self,path):
        item=self.devices.pop(path,None)
        if item:
            self.glib.source_remove(item['watch']);os.close(item['fd'])
            if self.group.source==path: self.group.source=None
            if not any(d['chord'].pressed for d in self.devices.values()): self.group.latched=False

    def read(self,path,condition):
        item=self.devices.get(path)
        if item is None: return False
        if condition&(self.glib.IO_HUP|self.glib.IO_ERR): self.remove(path);return False
        try: data=os.read(item['fd'],EVENT.size*64)
        except BlockingIOError: return True
        except OSError: self.remove(path);return False
        if not data: self.remove(path);return False
        item['buffer']+=data
        while len(item['buffer'])>=EVENT.size:
            _,_,kind,code,value=EVENT.unpack(item['buffer'][:EVENT.size])
            item['buffer']=item['buffer'][EVENT.size:]
            if kind==0 and code==3:
                item['chord'].reset();item['axes']=axes_for(item['fd']);item['hats'].clear();item['dropping']=True;continue
            if item['dropping']:
                if kind==0 and code==0: item['dropping']=False
                continue
            if kind==1:
                item['chord'].button(code,value,time.monotonic())
                self.group.observe_release({p:d['chord'] for p,d in self.devices.items()})
                if value==1 and code in (304,305,544,545,546,547): self.navigation(path,code,value)
            elif kind==3:
                if code in (16,17):
                    previous=item['hats'].get(code,0);item['hats'][code]=value
                    if value and value!=previous: self.navigation(path,code,value)
                elif code in item['axes']:
                    direction=item['axes'][code].event(value)
                    if direction: self.navigation(path,16+code,direction)
        self.dispatch_chords()
        if self.timer is None and any(d['chord'].since is not None for d in self.devices.values()):
            self.timer=self.glib.timeout_add(50,self.tick)
        return True

    def navigation(self,path,code,value):
        if self.group.source is None: self.group.source=path
        if self.group.source==path: self.navigate(code,value)

    def dispatch_chords(self):
        chords={path:item['chord'] for path,item in self.devices.items()}
        if self.group.poll(chords,time.monotonic()) is not None: self.open_menu()

    def tick(self):
        self.dispatch_chords()
        keep=any(d['chord'].since is not None and not d['chord'].fired for d in self.devices.values())
        if not keep: self.timer=None
        return keep

    def close(self):
        self.glib.source_remove(self.scan_timer)
        if self.timer is not None: self.glib.source_remove(self.timer);self.timer=None
        for path in list(self.devices): self.remove(path)
