class Request:
    def __init__(self, event):
        self.headers = event.get("multiValueHeaders", {})
        self.method = event["httpMethod"]
        self.body = event.get("body", "")
        self.path = event["path"]
        self.queryparams = event.get("queryStringParameters", {})
