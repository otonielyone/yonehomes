bind = '0.0.0.0:5000'
workers = 1
worker_class = 'uvicorn.workers.UvicornWorker'
accesslog = '/home/oyone/fastapi_project/logs/access.log'
errorlog = '/home/oyone/fastapi_project/logs/error.log'
loglevel = 'info'
