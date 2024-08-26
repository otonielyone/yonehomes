bind = '192.168.0.100:5000'
workers = 4
worker_class = 'uvicorn.workers.UvicornWorker'
accesslog = '/home/oyone/fastapi_project/logs/access.log'
errorlog = '/home/oyone/fastapi_project/logs/error.log'
loglevel = 'debug'  # Set log level to debug to capture detailed logs
capture_output = True  # Ensure Gunicorn captures stdout and stderr
