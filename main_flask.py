#!/usr/bin/python3

from rest.api.routes import app

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080)
