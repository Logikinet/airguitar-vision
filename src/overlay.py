"""中文版空气吉他工作台：独立视频区域、演奏状态和可点击的音乐播放器。"""
from __future__ import annotations
import os
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from . import config
from .fretboard import Fretboard, FretboardGeom
from .hand_tracker import HandResult
from .strum_detector import StrumState
from .song_player import SongPlayer

CANVAS_W, CANVAS_H = 1440, 900
VIDEO_RECT = (28, 120, 988, 556)
SIDEBAR_X = 1040

# All tuples are BGR when used in cv2, RGB when used with Pillow explicitly.
CONNECTIONS = (
    (0,1),(1,2),(2,3),(3,4),(0,5),(5,6),(6,7),(7,8),
    (5,9),(9,10),(10,11),(11,12),(9,13),(13,14),(14,15),(15,16),
    (13,17),(17,18),(18,19),(19,20),(0,17),
)
FINGERS_CN = ('握拳','食指','剪刀手','三指','四指','张开手掌')
FONT_CANDIDATES = (
    'C:/Windows/Fonts/msyh.ttc',
    'C:/Windows/Fonts/msyhbd.ttc',
    'C:/Windows/Fonts/simhei.ttf',
    'C:/Windows/Fonts/simsun.ttc',
    '/System/Library/Fonts/PingFang.ttc',
    '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
    '/usr/share/fonts/truetype/arphic-gbsn00lp/gbsn00lp.ttf',
)


def find_chinese_font() -> str:
    # System fonts first. windows-latest cannot write C:\Windows\Fonts, so CI
    # also supplies %LOCALAPPDATA%\Microsoft\Windows\Fonts\simhei.ttf.
    candidates = list(FONT_CANDIDATES)
    local = os.environ.get('LOCALAPPDATA')
    if local:
        user_fonts = Path(local) / 'Microsoft' / 'Windows' / 'Fonts'
        candidates.extend(
            str(user_fonts / name)
            for name in ('msyh.ttc', 'msyhbd.ttc', 'simhei.ttf', 'simsun.ttc')
        )
    for path in candidates:
        if Path(path).is_file():
            return path
    raise RuntimeError('未找到可显示中文的系统字体。请在 Windows 安装“微软雅黑”或“黑体”，再启动程序。')


def _rgba_hex(value: str) -> tuple[int,int,int]:
    return tuple(int(value[i:i+2],16) for i in (1,3,5))


class Overlay:
    def __init__(self) -> None:
        self.board=Fretboard()
        self.font_path=find_chinese_font()
        self.fonts={i:ImageFont.truetype(self.font_path,i) for i in (13,14,15,16,17,18,19,20,21,22,24,26,28,32,36,42,48,55)}
        # Mouse callbacks use stable image-space rectangles; no external UI framework.
        self.buttons={
            'mode':(1059,209,1393,284),
            'twinkle':(1058,614,1212,661),
            'ode':(1221,614,1394,661),
            'play_pause':(1058,740,1276,797),
            'stop':(1286,740,1394,797),
            'mute':(1200,27,1288,67),
            'fullscreen':(1300,27,1409,67),
        }

    def hit_test(self,x:int,y:int) -> str|None:
        for name,(x0,y0,x1,y1) in self.buttons.items():
            if x0<=x<=x1 and y0<=y<=y1:
                return name
        return None

    def draw(self, frame: np.ndarray, hands: list[HandResult], geom: FretboardGeom,
             chord: Optional[str], strum_state: StrumState, debug: bool,
             *, mode: str='chord', active_cell: tuple[int,int]|None=None,
             fps: float=0.,confidence: float=0.,last_event: str='',
             demo: bool=False,current_gesture: int|None=None,
             role_swap: bool=False,sound_muted: bool=False,
             song_player: SongPlayer|None=None) -> np.ndarray:
        h,w=frame.shape[:2]
        vx,vy,vw,vh=VIDEO_RECT
        video=frame.copy()
        # Show guides in the video plane; chord mode keeps the face unobstructed.
        x,y,rw,rh=config.FRETBOARD_ROI
        a=(int(x*w),int(y*h)); b=(int((x+rw)*w),int((y+rh)*h))
        tint=video.copy()
        cv2.rectangle(tint,a,b,(60,38,16),-1)
        cv2.addWeighted(tint,.13,video,.87,0,video)
        cv2.rectangle(video,a,b,(194,148,102),1,cv2.LINE_AA)
        if mode=='single':
            self.board.draw_guide(video,geom,active_cell)
        x,y,rw,rh=config.STRUM_ROI
        p1=(int(x*w),int(y*h));p2=(int((x+rw)*w),int((y+rh)*h))
        tint=video.copy()
        cv2.rectangle(tint,p1,p2,(36,72,62),-1)
        cv2.addWeighted(tint,.20,video,.80,0,video)
        cv2.rectangle(video,p1,p2,(108,201,181),2,cv2.LINE_AA)
        yy=(p1[1]+p2[1])//2
        cv2.line(video,(p1[0]+8,yy),(p2[0]-8,yy),
                 (104,237,160) if strum_state == StrumState.COOLDOWN else (73,207,241),3,cv2.LINE_AA)
        hand_tags=[]
        for hand in hands:
            normalized=hand.handedness
            if role_swap:normalized='Right' if normalized=='Left' else 'Left'
            hand_color=(91,228,250) if normalized=='Left' else (170,229,125)
            pts=[(int(p[0]),int(p[1])) for p in hand.landmarks]
            if len(pts)<21:continue
            for i,j in CONNECTIONS:
                cv2.line(video,pts[i],pts[j],hand_color,2,cv2.LINE_AA)
            for i,pt in enumerate(pts):
                cv2.circle(video,pt,4 if i in (4,8,12,16,20) else 2,(244,245,247) if i==8 else hand_color,-1,cv2.LINE_AA)
            wx,wy=pts[0]
            hand_tags.append((min(vx+vw-150,max(vx+8,vx+wx*vw/w)),
                              min(vy+vh-40,max(vy+24,vy+(wy-38)*vh/h)),normalized,hand.score))
        output=np.zeros((CANVAS_H,CANVAS_W,3),np.uint8)
        output[:]=(24,19,13)
        resized=cv2.resize(video,(vw,vh),interpolation=cv2.INTER_LINEAR)
        output[vy:vy+vh,vx:vx+vw]=resized
        # One Pillow composition to display actual Chinese glyphs, not cv2.putText tofu.
        image=Image.fromarray(cv2.cvtColor(output,cv2.COLOR_BGR2RGB))
        p=ImageDraw.Draw(image)
        navy='#0D1625';panel='#142237'; stroke='#29415B'
        pale='#E9F2FA';muted='#92A8BC';cyan='#65DCED';green='#79E4B8';gold='#F8CB7C'
        def rr(coords, fill, outline=None, r=20, width=1):
            p.rounded_rectangle(coords,radius=r,fill=fill,outline=outline,width=width)
        def t(txt,xy,size=18,fill=pale,anchor=None):
            p.text(xy,str(txt),font=self.fonts[size],fill=fill,anchor=anchor)
        def center(txt,rect,size=18,color=pale):
            x0,y0,x1,y1=rect
            t(txt,((x0+x1)/2,(y0+y1)/2),size,color,'mm')
        def chip(text,rect,fg=cyan,bg='#183347'):
            rr(rect,bg,r=13)
            center(text,rect,15,fg)
        # Header with studio branding and camera status.
        rr((28,23,76,72),'#1C3F50',r=15)
        t('♫',(51,48),32,cyan,'mm')
        t('空气吉他', (91,24),32)
        t('计算机视觉 · 实时交互演奏台', (93,65),15,muted)
        cam_state='模拟演示' if demo else '摄像头已连接'
        t(f'{cam_state}   ·   帧率 {fps:.0f}',(825,42),17,green)
        chip('静音' if sound_muted else '音频开启',self.buttons['mute'],gold if sound_muted else green)
        chip('全屏 F',self.buttons['fullscreen'])
        p.line((28,99,1411,99),fill=stroke,width=1)
        # Main camera header chips, drawn over video with dark contrast.
        rr((vx+13,vy+14,vx+210,vy+50),'#102238',r=11)
        t('左手  /  选择和弦',(vx+28,vy+22),16,cyan)
        rr((vx+vw-194,vy+14,vx+vw-13,vy+50),'#102238',r=11)
        t('右手  /  扫弦',(vx+vw-182,vy+22),16,green)
        for px,py,shown,score in hand_tags:
            rr((int(px),int(py),int(px+115),int(py+30)), '#132537',r=9)
            t('左手' if shown=='Left' else '右手',(px+10,py+4),15,cyan if shown=='Left' else green)
            if debug:t(f'{score:.2f}',(px+65,py+8),13,muted)
        rr((vx+15,vy+vh-44,vx+vw-15,vy+vh-13),'#102034',r=9)
        t('镜像预览  ·  左手识别 / 单音定位  ·  右手上下穿过绿色扫弦线',
          (vx+27,vy+vh-39),15,'#CFDCE9')
        # Under-video performance overview.
        r1=(28,699,339,869);r2=(350,699,665,869);r3=(676,699,1016,869)
        for r in (r1,r2,r3):rr(r,panel,stroke,17)
        t('演奏模式',(r1[0]+21,r1[1]+20),16,muted)
        t('和弦演奏' if mode=='chord' else '单音演奏',(r1[0]+21,r1[1]+55),28,cyan)
        t('按 M 切换和弦 / 单音',(r1[0]+21,r1[1]+124),15,muted)
        t('当前识别',(r2[0]+20,r2[1]+20),16,muted)
        result=chord if mode=='chord' else (f'第{active_cell[0]+1}弦 / 第{active_cell[1]}品' if active_cell else '尚未定位')
        t(result or '等待手势',(r2[0]+20,r2[1]+56),28,green)
        t(f'置信度：{confidence:.2f}',(r2[0]+20,r2[1]+125),15,muted)
        t('扫弦反馈',(r3[0]+20,r3[1]+20),16,muted)
        feedback='检测到扫弦' if last_event else ('冷却中' if strum_state==StrumState.COOLDOWN else '准备就绪')
        t(feedback,(r3[0]+20,r3[1]+56),28,gold if last_event else pale)
        t('按空格可手动拨弦  ·  按 H 校正左右手',(r3[0]+20,r3[1]+125),14,muted)
        # Right side: instrument control
        rr((SIDEBAR_X,120,1412,305),panel,stroke,18)
        t('演奏控制',(1061,137),21,pale)
        t('双手交互 · 六和弦 / 虚拟指板',(1061,169),14,muted)
        rr((1059,209,1393,284),'#21354B',r=14)
        t('当前模式',(1078,221),14,muted)
        t('和弦  ·  手势识别' if mode=='chord' else '单音  ·  指板定位',(1078,245),21,cyan)
        t('点击切换 ↗',(1282,226),14,green)
        # right side: gesture mapping, keeping camera region clear
        rr((SIDEBAR_X,320,1412,519),panel,stroke,18)
        t('手势与和弦',(1061,338),21,pale)
        t('伸出手指数 · 对应和弦',(1061,369),14,muted)
        names=config.CHORD_ORDER
        for i,name in enumerate(names):
            col=i%3;row=i//3
            rx=1059+col*113; ry=401+row*51
            chosen=(chord==name and mode=='chord')
            rr((rx,ry,rx+104,ry+43),'#21555A' if chosen else '#1E3347',
               '#66DFD5' if chosen else None,12)
            t(f'{i}指',(rx+10,ry+12),14,green if chosen else muted)
            t(name,(rx+66,ry+8),21,pale,'mt')
        t('说明：和弦手势为简化教学映射，不是真实按弦姿势',(1059,500),13,muted)
        # Song player: actionable controls, not a static image.
        rr((SIDEBAR_X,533,1412,870),panel,stroke,18)
        t('示范曲播放器',(1061,552),22,pale)
        t('旋律 + 分解和弦伴奏 · 非阻塞播放',(1061,584),14,muted)
        selected=song_player.selected if song_player else 0
        for i,bid in enumerate(('twinkle','ode')):
            active=i==selected
            rr(self.buttons[bid],'#24515A' if active else '#1B2C40',
               '#56C8C9' if active else '#30445C',12,1)
            center('小星星' if i==0 else '欢乐颂',self.buttons[bid],18,pale if active else muted)
        current_song=song_player.song if song_player else None
        title=current_song.title if current_song else '小星星'
        sub=current_song.subtitle if current_song else '经典旋律 · 吉他指弹改编'
        t(title,(1059,680),21,gold)
        t(sub,(1140,687),13,muted)
        progress=song_player.progress if song_player else 0
        rr((1059,718,1393,726),'#2A4055',r=4)
        if progress>.001:
            rr((1059,718,max(1067,1059+int(334*progress)),726),'#64DBBB',r=4)
        if song_player:
            stamp=f'{int(song_player.elapsed_seconds//60):02d}:{int(song_player.elapsed_seconds%60):02d}'
            total=f'{int(song_player.song.duration_seconds//60):02d}:{int(song_player.song.duration_seconds%60):02d}'
            state={'stopped':'待播放','playing':'正在弹奏','paused':'已暂停'}[song_player.state]
        else:
            stamp='00:00';total='00:26';state='待播放'
        t(state,(1059,812),17,green if state=='正在弹奏' else muted)
        t(f'{stamp} / {total}',(1282,812),15,muted)
        state0=song_player.state if song_player else 'stopped'
        rr(self.buttons['play_pause'],'#65DBB8',r=13)
        center('暂停播放' if state0=='playing' else ('继续播放' if state0=='paused' else '▶ 播放示范曲'),
               self.buttons['play_pause'],19,'#092635')
        rr(self.buttons['stop'],'#283C50',r=13)
        center('■ 停止',self.buttons['stop'],18,pale)
        t('鼠标点击按钮 · P 播放 / 暂停 · T 停止',(1059,840),13,muted)
        return cv2.cvtColor(np.asarray(image),cv2.COLOR_RGB2BGR)
