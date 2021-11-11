import os
import sys
import pathlib
import numpy as np
from numpy.core.fromnumeric import std


def report():
    working = pathlib.Path("working")

    page_dirs = [x for x in working.iterdir() if x.is_dir()]
    
    fails = set()
    
    failed_crops = [x for x in page_dirs if not (x / "page-crop.png").exists()]
    fails.update(failed_crops)
    if failed_crops:
        print("failed to auto-crop ({} pages): {}".format(len(failed_crops),", ".join(x.name for x in failed_crops)))
        print("\t consider manually cropping these pages and saving as 'page-handcrop.png'")

    failed_to_split = [x for x in page_dirs if x not in fails and not (x / "column-1.png").exists()]
    failed_to_split.sort()
    fails.update(failed_to_split)
    if failed_to_split:
        print("failed to split into columns ({} pages): {}".format(len(failed_to_split),", ".join(x.name for x in failed_to_split)))
        print("\t consider manually cropping or cleaning up these pages and saving as 'page-handcrop.png'")
    
    failed_to_ocr = [x for x in page_dirs if x not in fails and not (x / "page.csv").exists()]
    failed_to_ocr.sort()
    fails.update(failed_to_ocr)
    if failed_to_ocr:
        print("failed to OCR ({} pages): {}".format(len(failed_to_ocr),", ".join(x.name for x in failed_to_ocr)))
        print("\t usually this is because the OCR was unable to identify a street name, consider manually splitting into columns")
    

    if False:
        # we should figure out how to detect OCR 
        # that could be improved
        # a quick pass of bytes of csv per byte of input png
        # seems not particularly interesting
        good_pages = [x for x in page_dirs if x not in fails]

        ratios = []
        for page in good_pages:
            pimg = page / "page.png"
            csvout = page / "page.csv"
            ratios.append(csvout.stat().st_size / pimg.stat().st_size)

        ratios = np.array(ratios)
        
        low_ratio = ratios.mean() - 2*ratios.std()
        for ratio, page in zip(ratios, good_pages):
            if ratio <  low_ratio:
                print("short page:", page)
    # print(np.mean(ratios), ratios.std())

if __name__ == '__main__':
    report()