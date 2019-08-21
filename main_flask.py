#!/usr/bin/python3
from about import properties
from rest.api.routes import app

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=properties["port"])
