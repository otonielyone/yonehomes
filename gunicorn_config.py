bind = '192.168.0.19:5000'
workers = 1
worker_class = 'uvicorn.workers.UvicornWorker'
accesslog = '/home/oyone/fastapi_project/logs/access.log'
errorlog = '/home/oyone/fastapi_project/logs/error.log'
loglevel = 'info'
