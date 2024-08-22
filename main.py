from start_files.app import create_app

app = create_app()

#if __name__ == "__main__":
#    import uvicorn
<<<<<<< HEAD
#    uvicorn.run(app, host="127.0.0.1", port=5000)


#gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app --bind 0.0.0.0:5000
#kill blocking ports
#netstat -tuln | grep LISTEN
#lsof -i :5000
#kill -9 282229
=======
#    uvicorn.run(app, host="127.0.0.1", port=50000)
>>>>>>> 5531c79 (cleaning files)
