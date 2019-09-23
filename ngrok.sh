#!/bin/bash

wget -O ngrok.zip https://bin.equinox.io/c/4VmDzA7iaHb/ngrok-stable-linux-amd64.zip
unzip ngrok.zip
{
    nc -l -v -p 8888
    killall -SIGINT ngrok && echo "ngrok terminated"
} &
{
    ./ngrok http 8080 --authtoken=$NGROK_TOKEN
} &