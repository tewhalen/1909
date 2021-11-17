#!/usr/bin/python
import bisect
import glob
import os
import subprocess
import sys
from itertools import accumulate, groupby

import matplotlib.pyplot as plt
import numpy as np
import peakutils
from loguru import logger
from PIL import Image
from shapely.geometry import Polygon

from image_utils import deskew, get_histogram, new_crop

DEBUG = False


def debug(*args):
    if DEBUG:
        print(*args)


def split_on_center_line(img):
    a, b = divide_slip(img)
    img_a = img.crop(a)
    if b:
        img_b = img.crop(b)
    else:
        img_b = None
    return img_a, img_b


def v_any(subimg):
    "What percentage of the vertical rows has a black pixel?"
    wd, ht = subimg.size
    pix = np.array(subimg.convert("1").getdata(), np.uint8)
    bin_img = 1 - (pix.reshape((ht, wd)) / 255.0)
    # print(np.any(bin_img, axis=1))
    return np.sum(np.any(bin_img, axis=1)) / ht


def divide_slip(img, thresh=5):
    wd, ht = img.size
    full_img = (0, 0, wd, ht)

    hist = get_histogram(img)
    x = hist > thresh  # detect whitespace

    # we're looking for a narrow, nearly-full height line
    # near the middle of the cell

    groups = [(len(list(j)), i) for i, j in groupby(x)]
    group_info = []

    # within 5% of the center of the cell
    center = wd / 2
    window = wd / 20

    i = 0
    for group, v in groups:
        if v and (abs(i - center) < window):
            # not whitespace and near the center
            s = sum(hist[i : i + group])
            # start, width, end, average value, % of a totally filled column
            group_info.append((i, group, i + group, s / group, s / (group * ht)))
        i += group

    debug("group_info", group_info)

    # middle_columns = [x for x in group_info if (abs(x[0]-center) < window)]
    # debug('middle_columns',middle_columns)
    middle_columns = group_info
    if debug and middle_columns:
        mc = middle_columns[0]
        debug(hist[mc[0] : mc[0] + mc[1]])

    if not middle_columns:
        # nothing in the middle, abort
        return full_img, None
    slip_any = hist.max() / ht

    filled_columns = []
    for form in middle_columns:
        subimg = img.crop((form[0], 0, form[2], ht))
        # return v_any(subimg)
        if v_any(subimg) / slip_any > 0.78 and form[1] <= 12:
            # at least 78% of a filled line, relative to the slip content
            # and 12 pixels wide
            filled_columns.append(form)

    # filled_columns = [x for x in middle_columns if (x[4] >= .5 and x[1] <= 12)]
    debug(center - wd / 40, center + wd / 40, wd, ht)
    debug("filled_columns", filled_columns)
    if not filled_columns:
        # print("no line!", group_info)
        # we found no line
        return full_img, None
    elif len(filled_columns) > 1:
        sys.stderr.write(
            "warning, more than one possible center line detected, choosing thiccest\n"
        )
        m = max((x[4] for x in filled_columns))
        filled_columns = [x for x in filled_columns if x[4] == m]
        # print(group_info)
        # print(center-wd/20, center+wd/20)
        # return full_img, None

    center_line = filled_columns[0]
    left, right = center_line[0], center_line[2]
    if center_line[1] > 15:  # too wide?!?
        # print("line too wide!")
        return full_img, None
    # split it
    a = (0, 0, left - 1, ht)
    b = (right + 1, 0, wd, ht)
    return a, b


def find_five_columns(img):
    """
    We're trying to find five columns of numbers

    """
    image_width, image_height = img.size

    # top_line = find_top_line(img)

    # find the thick vertical lines
    hist = get_histogram(img, axis=0)
    if DEBUG and False:
        plt.plot(hist)
        plt.show()
    indexes = peakutils.indexes(
        hist, thres=0.75, min_dist=image_width / 7
    )  # , min_dist=5)
    debug([(i, hist[i]) for i in indexes])

    x = indexes - np.roll(indexes, 1)
    x[0] = 0
    x = np.append(x, 0)

    median_column_width = np.median(x[1:-1])  # find median width of a column
    q = abs(1 - x / median_column_width) < 0.02  # within 2% of median width is good

    proper_indexes = [indexes[i] for i in range(len(indexes)) if q[i] or q[i + 1]]

    # let's say that a line is a 66% filled column within 5% of the center
    # of the cell
    debug("right distance apart:", proper_indexes)

    if len(proper_indexes) != 4:
        # if not four bars, we have a problem
        logger.error("found {}, not 5 columns", proper_indexes)
        raise RuntimeError("can't split into 5 columns")

    prev_i = 0
    bar_limits = []  # [0] + proper_indexes + [image_width]
    for i in proper_indexes:
        bar_limits.append((prev_i, i))
        prev_i = i
    bar_limits.append((prev_i, image_width))
    debug(bar_limits)
    return bar_limits


def x_find_five_columns(img):
    """
    We're trying to find five columns of numbers

    """
    image_width, image_height = img.size

    # top_line = find_top_line(img)

    # find the thick vertical lines
    hist = get_histogram(img, axis=0)
    if DEBUG:
        plt.plot(hist)
        plt.show()
    indexes = peakutils.indexes(
        hist, thres=0.75, min_dist=image_width / 7
    )  # , min_dist=5)
    debug([(i, hist[i]) for i in indexes])

    thresh = (
        image_height * 0.50
    )  # if it's not at least 50% full, it's whitespace for our purposes
    x = hist > thresh  # detect whitespace
    debug(image_height, max(hist))
    # we're looking for a nearly-full height line

    groups = [(len(list(j)), i) for i, j in groupby(x)]
    debug(groups)
    group_info = []
    i = 0
    for group, v in groups:
        if v:  # we decided this wasn't whitespace
            s = sum(hist[i : i + group])
            # start, width, end, average value, % of a totally filled column
            if group < 10:
                # too small
                i += group
                continue
            group_info.append(
                (i, group, i + group, s / group, s / (group * image_height))
            )
        i += group
    debug("orig groups", group_info)

    # some will be the wrong distance from each other, those are edges

    indexes = np.array([x[0] + (x[1] / 2) for x in group_info])
    x = indexes - np.roll(indexes, 1)
    x[0] = 0
    x = np.append(x, 0)

    median_column_width = np.median(x[1:-1])  # find median width of a column
    q = abs(1 - x / median_column_width) < 0.02  # within 2% of median width is good
    group_info = [group_info[i] for i in range(len(indexes)) if q[i] or q[i + 1]]

    # let's say that a line is a 66% filled column within 5% of the center
    # of the cell
    debug("right distance apart:", group_info)
    if len(group_info) == 4:
        # we found five columns
        bars = group_info
    else:
        bars = [x for x in group_info if (x[4] >= 0.66 and x[1] >= 10)]
        debug("thick enough:", bars)
    assert len(bars) == 4  # if not four bars, we have a problem
    indexes = np.array([x[0] + (x[1] / 2) for x in bars])
    x = (indexes - np.roll(indexes, 1))[1:]
    m = np.mean(x)
    debug(x, m)
    bar_limits = []
    for fc in bars:
        min_x_position, width, max_x_position, = (
            fc[0],
            fc[1],
            fc[2],
        )
        # creep left and right from the center of the bars to crop out the space
        b0 = min_x_position
        b1 = min_x_position
        while hist[b0] <= hist[b1] or hist[b1] > 1000:
            b1 = b0
            b0 -= 1
        left = b1
        b0 = max_x_position
        b1 = max_x_position
        while hist[b0] <= hist[b1] or hist[b1] > 1000:
            b1 = b0
            b0 += 1
        right = b1
        bar_limits.append((left, right))  # pad a little

    # add a notional left and right bar
    bar_limits.insert(
        0, (max(0, int(bars[0][0] - (m + 2))), max(0, int(bars[0][0] - m)))
    )
    bar_limits.append(
        (
            min(image_width, int(bars[-1][2] + m)),
            min(image_width, int(bars[-1][2] + (m + 2))),
        )
    )

    # print(bar_limits)

    return bar_limits


def find_top_line(img):
    # find the top lines
    hist = get_histogram(img, axis=1)
    indexes = peakutils.indexes(hist, thres=0.9)  # , min_dist=5)
    top_line = indexes[-1]
    b0 = top_line + 1
    while hist[b0] <= hist[top_line]:
        top_line = b0
        b0 += 1
    return top_line


def get_columns(bar_limits, top_bar, im_size):
    width, height = im_size

    cols = []
    for right, left in zip(bar_limits, bar_limits[1:]):
        r = right[1]
        l = left[0]
        p = Polygon([(r, top_bar), (l, top_bar), (l, height), (r, height)])
        cols.append(p)
    return cols


def split_into_rows(img, threshold=10):
    """generator that spits out images for each row"""
    for dims in divide_into_rows(img, threshold):
        yield img.crop(dims)


def divide_into_rows(img, threshold=10):
    """generator that yields the bounding box of each row"""
    image_width, ht = img.size

    hist = get_histogram(img, axis=1)

    x = hist > threshold  # threshold is around 10

    groups = [[len(list(j)), i] for i, j in groupby(x)]

    debug(groups)

    save_whitespace = False

    # we can split the whitespace between two adjacent rows, or just discard it
    if save_whitespace:
        g = [groups[0][:]]

        i = 1
        while i < len(groups):
            # given x[i-1], x[i], x[i+1], split whitespace x[i] between the two
            group, group_has_black = groups[i]

            if not group_has_black:  # whitespace
                if i + 2 < len(groups):  # not close to end
                    g[-1][0] += group / 2
                    g[-1][0] += group - (group / 2)
                    i += 1
                    continue

            g.append([group, group_has_black])
            i += 1

        groups = g
    # else:
    #    groups = [g for g in groups if g[1]] # just the stuff with content

    # the median width of a detected row ought to be the average width of an address row
    median = np.median(np.array([g for g, x in groups]))

    def multiple_rows(group):
        # is this likely a run of multiple rows?
        slips = group / median
        remainder = group % median
        slop = min(median - remainder, remainder)  # how close are we
        # print(group, median, remainder, slop)
        if slop < median * 0.05:
            return True
        else:
            return False

    j = 0
    row = 0
    for group, v in groups:
        # address slips are about 40-50 pixels
        # print (group, median)
        if not v:  # whitespace
            debug("ws", group)
            pass
        elif group < 17:  # skip rows that are short
            debug("short", group)
            pass
        elif group > median * 1.1 and multiple_rows(
            group
        ):  # this is too long to be a single row
            step = group / round(group / median)
            debug(
                "splitting",
                j,
                group,
                "into",
                int(round(group / median)),
                "slips of ",
                step,
            )
            for i in range(int(round(group / median))):
                # print("split", i,step*i)
                yield (0, row + step * i, image_width, row + step * (i + 1))
                j += 1
        else:
            debug(j, "whole", row, group)
            slip = (0, row, image_width, row + group)
            # slip = remove_center_line(slip)

            yield slip
            j += 1

        row += group


def split_and_save_column(im, i, column, fbase):
    """Save OCRed text from this column"""

    ftif = "%s-%d" % (fbase, i)

    # cmd = "tesseract -psm 4 %s %s" % (ftif, fbase) # assume vertical alignment, no columns

    width, height = im.size

    trimmed = im.crop(column.bounds)
    trimmed.save(ftif + ".png", "PNG")

    row_slice = "%s-%02d-%d.png"

    for row, row_img in enumerate(split_into_rows(trimmed)):
        # print(row, row_img.size)
        if row_img.size[1] <= 10:
            # too narrow to be a real rows
            continue
        l, r = split_on_center_line(row_img)
        if l:
            auto_crop(l).save(row_slice % (ftif, row, 0), "PNG")
        if r:
            auto_crop(r).save(row_slice % (ftif, row, 1), "PNG")


def load_image(filename):
    """Extract columns from spreadsheet-like image file"""
    im = Image.open(filename)
    # pix = im.load()
    width, height = im.size
    sys.stderr.write("%s: %dx%d\n" % (filename, width, height))
    sys.stderr.write("%s: cropping\n" % (filename,))
    im = new_crop(im)
    sys.stderr.write("%s: deskewing\n" % (filename,))
    im = deskew(im)
    width, height = im.size

    sys.stderr.write("%s: revised to %dx%d\n" % (filename, width, height))
    # im.save("adjusted.png")
    return im


def split_page(filename):
    """Extract columns from spreadsheet-like image file"""
    im = load_image(filename)

    cols, top_line = find_five_columns(im)
    clips = get_columns(cols, top_line, im.size)
    # sys.stderr.write("%s: %d columns detected\n" % (filename, len(vlines)))

    # clips = get_columns(vlines, top_bar, im.size)
    sys.stderr.write("%s: cols: %d\n" % (filename, len(clips)))

    data = []
    for i, col in enumerate(clips):
        split_and_save_column(im, i, col, os.path.splitext(filename)[0])


def split_pdf(filename):
    """Split PDF into PNG pages, return filenames"""
    prefix = filename[:-4]
    cmd = (
        "convert +dither -colors 2 -colorspace gray -normalize -density 600x600 %s working/%s-%%d.png"
        % (filename, prefix)
    )
    subprocess.call([cmd], shell=True)
    return [f for f in glob.glob(os.path.join("working", "%s*.png" % prefix))]
