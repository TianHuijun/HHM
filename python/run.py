import numpy as np
from PIL import Image
from scipy.signal import savgol_filter
import time


def Th(na, pixel_num):
    B = np.zeros((3, 256))
    Sa = np.zeros((3, 256))
    threshold = np.zeros(3)
    for c in range(3):
        index = np.argsort(na[c, :])
        B[c, :] = np.sort(na[c, :])
        Sa[c, 0] = B[c, 0]
        for n in range(1, 256):
            Sa[c, n] = Sa[c, n-1] + B[c, n]
        number = 0
        while (Sa[c, number] < pixel_num/20):
            number += 1
        threshold[c] = na[c, index[number]]
    return threshold


def HHM(im_tgt, im_src):    # read image with pillow
    W, H = im_src.size
    pixel_num = H*W
    im_tgt = im_tgt.resize([W, H])
    x = np.arange(256)

    # get pixel number
    na = np.zeros((3, 256))
    Sa = np.zeros((3, 256))
    nb = np.zeros((3, 256))
    Sb = np.zeros((3, 256))

    for c in range(3):
        na[c, :] = im_tgt.split()[c].histogram()   # faster than np.histogram() aprox 0.02 s
        nb[c, :] = im_src.split()[c].histogram()

    Sa[:, 0] = na[:, 0]
    Sb[:, 0] = nb[:, 0]
    for n in range(1, 256):
        Sa[:, n] = Sa[:, n-1] + na[:, n]
        Sb[:, n] = Sb[:, n-1] + nb[:, n]

    # build map
    mapp = np.array([x, x, x]).astype(float)
    index = np.ones((3, 256))
    threshold_a = Th(na, pixel_num)
    threshold_b = Th(nb, pixel_num)
    for c in range(3):
        gradient = np.zeros((c+1, 257))
        srcMax = np.max(np.array(im_src)[:, :, c])+1
        srcMin = np.min(np.array(im_src)[:, :, c])+1

        for a in range(256):
            b = 0
            while Sa[c, a] > Sb[c, b]:
                b += 1
                if b > srcMax:
                    b = srcMax
                    break
            if b < srcMin:
                b = srcMin
            mapp[c, a] = b+1
            if na[c, a] < threshold_a[c]:
                mapp[c, a] = np.nan
                index[c, a] = 0
            if nb[c, b] < threshold_b[c]:
                mapp[c, a] = np.nan
                index[c, a] = 0
        mapp[c, 0] = srcMin
        mapp[c, 255] = srcMax
        index[c, 0] = 1
        index[c, 255] = 1
    gradient[:, 1:256] = index[:, 1:256]-index[:, 0:255]
    gradient[:, 0] = 0

    # print(mapp)
    region = np.zeros((3, 256, 2)).astype(int)
    XX = np.zeros((3, 256, 2)).astype(int)
    YY = np.zeros((3, 256, 2)).astype(int)

    for c in range(3):
        n_re = -1
        for a in range(256):
            if gradient[c, a] == -1:
                n_re += 1
                region[c, n_re, 0] = a
            elif gradient[c, a] == 1:
                region[c, n_re, 1] = a-1
        for num in range(n_re+1):
            XX[c, num, 0] = region[c, num, 0]-1
            YY[c, num, 0] = mapp[c, XX[c, num, 0]]
            XX[c, num, 1] = region[c, num, 1]+1
            YY[c, num, 1] = mapp[c, XX[c, num, 1]]

            p = np.polyfit(XX[c, num, :], YY[c, num, :], 1)
            for a in range(region[c, num, 0], region[c, num, 1]+1):
                mapp[c, a] = np.polyval(p, a)

    x = np.arange(256)
    # smooth with savgol_filter
    mapp[0, :] = savgol_filter(mapp[0, x], 15, 1)
    mapp[1, :] = savgol_filter(mapp[1, x], 15, 1)
    mapp[2, :] = savgol_filter(mapp[2, x], 15, 1)
    return mapp


def PA(mapp, input):
    w, h = input.size
    im = np.array(input)
    for c in range(3):
        im[0:h, 0:w, c] = mapp[c, im[0:h, 0:w, c]]-1

    return Image.fromarray(im)

if __name__ == '__main__':
    imsrc = Image.open('../6to7/6to7.png')
    imtgt = Image.open('../6to7/7to6.png')
    im = Image.open('../6to7/7.png')

    start = time.time()
    mapp = HHM(imtgt, imsrc)
    print('Map time: ', time.time()-start)

    start = time.time()
    correct = PA(mapp, im)
    print('Color adjustment time: ', time.time()-start)
    correct.save('../6to7/output7.png')
