bind = '127.0.0.1:5000'
workers = 4
worker_class = 'uvicorn.workers.UvicornWorker'
accesslog = '/home/oyone/fastapi_project/logs/access.log'
errorlog = '/home/oyone/fastapi_project/logs/error.log'
loglevel = 'info'