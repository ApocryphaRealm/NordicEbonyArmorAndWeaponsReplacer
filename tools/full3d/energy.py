import numpy as np, sys
from PIL import Image
from scipy.ndimage import gaussian_filter as G
def L(p,c=None):
    a=np.asarray(Image.open(p).convert('RGBA'),np.float32)/255
    return a
for n,s in (('helm',1.0),('torso',1.0),('bgpb',1.0)):
    N=L('src_png/%s_n.png'%n); M=L('src_png/orig/%sebony_m.png'%n)[...,0]
    W=N.shape[0]; k=W/1024
    nx=N[...,0]*2-1; ny=N[...,1]*2-1
    e=0
    for ch in (nx,ny):
        bp=G(ch,0.8*k)-G(ch,3*k); e=e+bp*bp
    E=np.sqrt(G(e,8*k))
    bm=G(M,0.8*k)-G(M,3*k); EM=np.sqrt(G(bm*bm,8*k))
    print(n,np.percentile(E,[50,75,90,99]),np.percentile(EM,[50,75,90,99]))
    def nz(x): return np.clip(x/np.percentile(x,99.5),0,1)
    out=np.concatenate([nz(E),nz(EM)],1)
    Image.fromarray((out*255).astype(np.uint8)).resize((1400,700)).save('energy_%s.png'%n)
    np.save('E_%s.npy'%n,np.stack([E,EM]))
