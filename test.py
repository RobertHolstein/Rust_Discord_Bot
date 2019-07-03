import json

with open('my_rust_data.json') as f:
     data = json.load(f)


stat_names = []
for stat in data["users"][0]['playerstats']['stats']:
    stat_names.append(stat['name'] )
print(stat_names)

with open('rust_attributes.json', 'w+') as f:
    f.write(json.dumps(stat_names))
