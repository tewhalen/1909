#!/usr/bin/python

import cv2 as cv
import numpy as np
from PIL import Image, ImageOps
from scipy.ndimage import interpolation as inter
from scipy.ndimage import label, morphology
from loguru import logger
DEBUG = False


def debug(*args):
    if DEBUG:
        print(*args)


def get_histogram(img, axis=0):
    wd, ht = img.size
    pix = np.array(img.convert("1").getdata(), np.uint8)
    bin_img = 1 - (pix.reshape((ht, wd)) / 255.0)

    return np.sum(bin_img, axis)


def rrr(b):
    v = np.array(b)
    n = v == 0
    # a = ~n
    c = np.cumsum(v)
    d = np.diff(np.concatenate(([0.0], c[n])))
    v[n] = -d
    q = np.cumsum(v)

    return q


def run_length(x, axis=0, flipped=True):
    if flipped:
        intermed = np.apply_along_axis(rrr, axis, np.flip(x, axis))
        return np.flip(intermed, axis)
    else:
        return np.apply_along_axis(rrr, axis, x)


def find_max_square(a, margin=0.1):
    pts = []
    min_sq = a.shape[0] * a.shape[1] * 0.80
    for flip in (True, False):

        col_wise, row_wise = run_length(a, 1, flip), run_length(a, 0, flip)

        sc = col_wise * row_wise

        # fill everything inside the margins with zeroes, so we don't
        # pick a best crop that's too narrow
        ht, wd = sc.shape
        # print(sc)
        # print(flip)
        if flip:
            sc[int(ht * margin) :] = 0
            sc[:, int(wd * margin) :] = 0
            # ,int(wd*margin):] = 0
        else:
            sc[: ht - int(ht * margin)] = 0
            sc[:, : wd - int(wd * margin)] = 0

        # print(sc)
        argm = sc.argmax()
        if argm <= min_sq:
            # the crop we found is too small, fall back on the longest runs
            # print("ERROR:", argm, min_sq)
            # only zero-out parts of the matrix, as we need the longest run
            if flip:
                col_wise[int(ht * margin) :] = 0
                # col_wise[:,int(wd*margin):] =0
                # row_wise[int(ht*margin):] = 0
                row_wise[:, int(wd * margin) :] = 0
            else:
                # col_wise[:ht-int(ht*margin)] = 0
                col_wise[:, : wd - int(wd * margin)] = 0
                row_wise[: ht - int(ht * margin)] = 0
                # row_wise[:,:wd-int(wd*margin)] = 0
            max_col = np.unravel_index(col_wise.argmax(), col_wise.shape)
            max_row = np.unravel_index(row_wise.argmax(), row_wise.shape)
            pt = (max_col[0], max_row[1])
        else:
            pt = np.unravel_index(argm, sc.shape)
        pts.append((pt[1], pt[0]))

    return pts[0], pts[1]


def max_square_crop(img):
    wd, ht = img.size

    im = np.array(img.convert("1").getdata(), np.uint8).reshape((ht, wd)) / 255.0

    # im = morphology.grey_closing(im, (1, 101))
    # t, im = cv.threshold(im, 0, 1, cv.THRESH_OTSU)

    # "Clean noise".
    im = morphology.grey_opening(im, (51, 51))

    a, b = find_max_square(im)
    # print(a+b)
    return img.crop(a + b)


def new_crop(img):
    return max_square_crop(img)  # 10% margins
    # return new_crop_y(new_crop_x(img))


def new_crop(img):
    # wd, ht = img.size
    return max_square_crop(img)  # , int(wd*.1), int(ht*.1)) # 10% margins
    # return new_crop_y(new_crop_x(img))


def new_crop_x(img):
    # make histograms
    wd, ht = img.size

    im = np.array(img, dtype=np.uint8)
    im = morphology.grey_closing(im, (1, 101))
    t, im = cv.threshold(im, 0, 1, cv.THRESH_OTSU)

    # "Clean noise".
    im = morphology.grey_opening(im, (51, 51))

    col_sum = np.sum(im, axis=0)

    window = 0.05
    # find the maximally white stretch of the outside 10%

    left_max = max(col_sum[: int(wd * window)])
    right_max = max(col_sum[int(wd * (1 - window)) :])

    # col_mean, col_std = col_sum.mean(), col_sum.std() + 0.000001
    # row_mean, row_std = row_sum.mean(), row_sum.std() + 0.000001

    # row_standard = (row_sum - row_mean) / row_std
    # col_standard = (col_sum - col_mean) / col_std

    def end_points(s, lr_max, rl_max):
        i, j = 0, len(s) - 1
        for i, rs in enumerate(s):
            if rs == lr_max:
                break
        for j in range(len(s) - 1, i, -1):
            if s[j] == rl_max:
                break
        return (i, j)

    # Bounding rectangle.
    x1, x2 = end_points(col_sum, left_max, right_max)

    return img.crop((x1, 0, x2, ht))


def new_crop_y(img):
    # make histograms
    wd, ht = img.size

    im = np.array(img, dtype=np.uint8)
    im = morphology.grey_closing(im, (1, 101))
    t, im = cv.threshold(im, 0, 1, cv.THRESH_OTSU)

    # "Clean noise".
    im = morphology.grey_opening(im, (51, 51))

    row_sum = np.sum(im, axis=1)

    window = 0.05
    # find the maximally white stretch of the outside 10%
    top_max = max(row_sum[: int(ht * window)])
    bot_max = max(row_sum[int(ht * (1 - window)) :])

    # col_mean, col_std = col_sum.mean(), col_sum.std() + 0.000001
    # row_mean, row_std = row_sum.mean(), row_sum.std() + 0.000001

    # row_standard = (row_sum - row_mean) / row_std
    # col_standard = (col_sum - col_mean) / col_std

    def end_points(s, lr_max, rl_max):
        i, j = 0, len(s) - 1
        for i, rs in enumerate(s):
            if rs == lr_max:
                break
        for j in range(len(s) - 1, i, -1):
            if s[j] == rl_max:
                break
        return (i, j)

    # Bounding rectangle.
    y1, y2 = end_points(row_sum, top_max, bot_max)
    return img.crop((0, y1, wd, y2))


def newish_crop(img):
    # make histograms
    wd, ht = img.size

    im = np.array(img, dtype=np.uint8)
    im = morphology.grey_closing(im, (1, 101))
    t, im = cv.threshold(im, 0, 1, cv.THRESH_OTSU)

    # "Clean noise".
    im = morphology.grey_opening(im, (51, 51))

    col_sum = np.sum(im, axis=0)
    row_sum = np.sum(im, axis=1)

    window = 0.05
    # find the maximally white stretch of the outside 10%
    top_max = max(row_sum[: int(ht * window)])
    bot_max = max(row_sum[int(ht * (1 - window)) :])
    left_max = max(col_sum[: int(wd * window)])
    right_max = max(col_sum[int(wd * (1 - window)) :])

    # col_mean, col_std = col_sum.mean(), col_sum.std() + 0.000001
    # row_mean, row_std = row_sum.mean(), row_sum.std() + 0.000001

    # row_standard = (row_sum - row_mean) / row_std
    # col_standard = (col_sum - col_mean) / col_std

    def end_points(s, lr_max, rl_max):
        i, j = 0, len(s) - 1
        for i, rs in enumerate(s):
            if rs == lr_max:
                break
        for j in range(len(s) - 1, i, -1):
            if s[j] == rl_max:
                break
        return (i, j)

    # Bounding rectangle.
    x1, x2 = end_points(col_sum, left_max, right_max)
    y1, y2 = end_points(row_sum, top_max, bot_max)
    return img.crop((x1, y1, x2, y2))


def auto_crop(img):
    # print(img.size)
    im = np.array(img, dtype=np.uint8)

    im = morphology.grey_closing(im, (1, 101))
    t, im = cv.threshold(im, 0, 1, cv.THRESH_OTSU)

    # "Clean noise".
    im = morphology.grey_opening(im, (51, 51))

    # Keep only largest component.
    lbl, ncc = label(im)
    largest = 0, 0
    # find largest
    for i in range(1, ncc + 1):
        size = len(np.where(lbl == i)[0])
        if size > largest[1]:
            largest = i, size
    # clear out others
    for i in range(1, ncc + 1):
        if i == largest[0]:
            continue
        im[lbl == i] = 0

    # make histograms
    col_sum = np.sum(im, axis=0)
    row_sum = np.sum(im, axis=1)

    col_mean, col_std = col_sum.mean(), col_sum.std() + 0.000001
    row_mean, row_std = row_sum.mean(), row_sum.std() + 0.000001

    row_standard = (row_sum - row_mean) / row_std
    col_standard = (col_sum - col_mean) / col_std

    def end_points(s, std_below_mean=-1.5):
        i, j = 0, len(s) - 1
        for i, rs in enumerate(s):
            if rs > std_below_mean:
                break
        for j in range(len(s) - 1, i, -1):
            if s[j] > std_below_mean:
                break
        return (i, j)

    # Bounding rectangle.
    x1, x2 = end_points(col_standard)
    y1, y2 = end_points(row_standard)

    return img.crop((x1, y1, x2, y2))


def silly_crop(img):
    """Attempt to remove the rows/columns from the edges that are 98-100% black or white"""
    wd, ht = img.size

    pix = np.array(img.convert("1").getdata(), np.uint8)
    bin_img = 1 - (pix.reshape((ht, wd)) / 255.0)

    hist = np.sum(bin_img, axis=0)
    t = 0.03
    min_t_y = ht * t
    max_t_y = ht * (1 - t)
    min_t_x = wd * t
    max_t_x = wd * (1 - t)

    x_min = 0
    x_max = wd - 1
    while hist[x_min] <= min_t_y or hist[x_min] >= max_t_y:
        x_min += 1
    while hist[x_max] <= min_t_y or hist[x_max] >= max_t_y:
        x_max -= 1

    hist = np.sum(bin_img, axis=1)

    y_min = 0
    y_max = ht - 1
    while hist[y_min] <= min_t_y or hist[y_min] >= max_t_y:
        y_min += 1
    while hist[y_max] <= min_t_y or hist[y_max] >= max_t_y:
        y_max -= 1
    return img.crop((x_min, y_min, x_max, y_max))


def find_deskew_score(arr, angle, axis, simple=False):
    data = inter.rotate(arr, angle, reshape=False, order=0)
    hist = np.sum(data, axis=axis)
    if simple:
        # attempt to maximize highest peak
        score = max(hist)  # simpler score?
    else:
        score = np.sum((hist[1:] - hist[:-1]) ** 2)

        return hist, score


def find_deskew_score(arr, angle, axis, simple=False):
    data = inter.rotate(arr, angle, reshape=False, order=0)
    hist = np.sum(data, axis=axis)
    if simple:
        # attempt to maximize highest peak
        score = max(hist)  # simpler score?
    else:
        # seems like maximizing variance means
        # longest lines and longest runs of whitespace
        score = np.var(hist, axis=0)

        # but maybe just sum of squares gets lines
        # score = np.sum(hist ** 2)

    return hist, score


def deskew(img, delta=0.1, limit=1, axis=0, simple=False):
    # convert to binary
    wd, ht = img.size

    pix = np.array(img.convert("1").getdata(), np.uint8)
    bin_img = 1 - (pix.reshape((ht, wd)) / 255.0)

    # hist = np.sum(bin_img, axis=0) # along y axis

    delta = 0.025
    limit = 0.5
    angles = np.arange(-limit, limit + delta, delta)
    scores = {}
    last_score = 0
    for angle in np.arange(0, limit + delta, delta):
        hist, score = find_deskew_score(bin_img, angle, axis, simple)
        debug("angle", angle, "score", score)
        if score < last_score:
            break
        last_score = score
        scores[score] = (angle, hist)
    last_score = 0
    for angle in np.arange(0, -limit, -delta):
        hist, score = find_deskew_score(bin_img, angle, axis, simple)
        debug("angle", angle, "score", score)
        if score < last_score:
            break
        last_score = score
        scores[score] = (angle, hist)

    best_score = max(scores)
    best_angle, best_hist = scores[best_score]
    logger.info("Best angle: {}",best_angle)

    # correct skew
    data = inter.rotate(bin_img, best_angle, reshape=False, order=0)
    img = ImageOps.invert(Image.fromarray((255 * data).astype("uint8")).convert("L"))
    return img
