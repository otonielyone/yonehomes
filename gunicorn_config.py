bind = '192.168.0.200:5000'
workers = 4
worker_class = 'uvicorn.workers.UvicornWorker'
accesslog = '/var/www/html/fastapi_project/logs/access.log'
errorlog = '/var/www/html/fastapi_project/logs/error.log'
loglevel = 'debug'  # Set log level to debug to capture detailed logs
capture_output = True  # Ensure Gunicorn captures stdout and stderrs
