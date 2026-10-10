import os

def handler(event, context):
    return {"message": f"hello from {os.environ['ENVIRONMENT']}", "version": os.environ["APP_VERSION"]}
