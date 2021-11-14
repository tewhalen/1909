import os
import sys
import pathlib
import numpy as np
from numpy.core.fromnumeric import std
import pandas

def get_csv_confidence_std(page):
    try:
        d = pandas.read_csv(page)
    except pandas.errors.ParserError:
        print("error in", page)
        return 0
    try:
        return min(d['new_conf'].mean(), d['old_conf'].mean()), max(d['new_conf'].std(), d['old_conf'].std())
    except KeyError:
        print("error in", page)
        return 0

def report():
    working = pathlib.Path("working")

    page_dirs = [x for x in working.iterdir() if x.is_dir()]
    page_dirs.sort()
    
    fails = {x for x in page_dirs if  (x / "page.csv").exists()}
    conf_std_page = [(get_csv_confidence_std(x/"page.csv"),x) for x in fails]
    confidences = [(n[0], x) for n,x in conf_std_page]
    confidences.sort()
    print("Least confident pages:")
    for conf, pagedir in confidences[:10]:
        print("\t{:.02f} {}".format(conf, pagedir))
        
    deviances = [(n[1], x) for n,x in conf_std_page]
    deviances.sort(reverse=True)
    print("Most deviant pages:")
    for conf, pagedir in deviances[:10]:
        print("\t{:.02f} {}".format(conf, pagedir))
    
    for conf, pagedir in confidences:
        if conf == 0:
            print(pagedir/"*.csv",end="  ")
    


    failed_crops = [x for x in page_dirs if x not in fails and not (x / "page-crop.png").exists()]
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