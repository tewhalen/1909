import csv
import json

streets = {row['street'] for row in csv.DictReader(open("page.csv"))}

smap = {s:s for s in streets}
json.dump(smap, open("known_streets.json",'w'), indent=4)

