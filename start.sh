#!/bin/bash

nohup nginx &
/scripts/main_flask.py
#uwsgi /scripts/flaskconfig.ini