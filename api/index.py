"""极简 Python function — 零 import 测试。"""
import json

def handler(request):
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"alive": True})
    }
