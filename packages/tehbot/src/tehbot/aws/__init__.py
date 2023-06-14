import boto3

CACHE = {}

def client(name):
    if name not in CACHE:
        CACHE[name] = boto3.client(name)
    return CACHE[name]

def build_dynamo_value(val):
    if isinstance(val, bool):
        return {"BOOL": val}
    elif isinstance(val, str):
        return {"S": val}
    elif isinstance(val, (int, float)):
        return {"N": str(val)}
    elif isinstance(val, list):
        return {"L": [build_dynamo_value(i) for i in val]}
    elif isinstance(val, dict):
        return {"M": {str(i) : build_dynamo_value(val[i]) for i in val}}
    elif isinstance(val, set):
        return {"SS": tuple(val)}

def extract_dynamo_value(val):
    if "S" in val:
        return str(val["S"])
    elif "N" in val:
        if "." in val["N"]:
            return float(val["N"])
        else:
            return int(val["N"])
    elif "BOOL" in val:
        return val["BOOL"]
    elif "M" in val:
        out = {}
        for k in val["M"]:
            out[k] = extract_dynamo_value(val["M"][k])
        return out
    elif "L" in val:
        out = []
        for i in val["L"]:
            out.append(extract_dynamo_value(i))
        return out
    elif "SS" in val:
        out = set()
        for i in val["SS"]:
            out.add(str(i))
        return out

def add_to_dynamo_item(item, **kwargs):
    for key in kwargs:
        val = kwargs[key]
        item[key] = build_dynamo_value(val)

def to_dynamo_item(data):
    item = {}
    for key in data:
        item[key] = build_dynamo_value(data[key])
    return item

def from_dynamo_item(item):
    data = {}
    for key in item:
        data[key] = extract_dynamo_value(item[key])
    return data