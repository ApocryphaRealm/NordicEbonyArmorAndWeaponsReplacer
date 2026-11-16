# periodicity score: share of a tile's band-passed spectral energy in the ring-frequency annulus, max over a peak
import numpy as np
from PIL import Image
from numpy.lib.stride_tricks import sliding_window_view as swv
from scipy.ndimage import zoom, gaussian_filter as G
for n in ('helm','torso','bgpb'):
    M=np.asarray(Image.open('src_png/orig/%sebony_m.png'%n).convert('L'),np.float32)/255
    W=M.shape[0]; k=W//1024
    m=M[::k,::k] if k>1 else M   # work at 1024
    T=32; S=8
    t=swv(m,(T,T))[::S,::S]               # (h,w,T,T)
    t=t-t.mean((-1,-2),keepdims=True)
    win=np.hanning(T)[:,None]*np.hanning(T)[None]
    F=np.abs(np.fft.fft2(t*win))**2
    fy=np.fft.fftfreq(T)[:,None]; fx=np.fft.fftfreq(T)[None]; r=np.sqrt(fx**2+fy**2)
    band=(r>1/16)&(r<1/5)          # ring period 5..16 px at 1024
    tot=F[...,r>1/T*1.5].sum(-1)+1e-6
    ratio=F[...,band].sum(-1)/tot
    peak=F[...,band].max(-1)/ (F[...,band].mean(-1)+1e-9)
    amp=np.sqrt(t.var((-1,-2)))
    for nm,x in (('ratio',ratio),('peak',peak),('amp',amp)): print(n,nm,np.percentile(x,[10,50,90]).round(3))
    np.save('P_%s.npy'%n,np.stack([ratio,peak,amp]))
    def nz(x): return np.clip((x-np.percentile(x,2))/(np.percentile(x,99)-np.percentile(x,2)),0,1)
    out=np.concatenate([nz(ratio),nz(peak),nz(amp)],1)
    Image.fromarray((out*255).astype(np.uint8)).resize((out.shape[1]*4,out.shape[0]*4),Image.NEAREST).save('period_%s.png'%n)
