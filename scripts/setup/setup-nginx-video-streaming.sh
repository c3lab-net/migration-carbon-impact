#!/bin/zsh

cd "$(dirname "$0")"

# Source: https://www.digitalocean.com/community/tutorials/how-to-set-up-a-video-streaming-server-using-nginx-rtmp-on-ubuntu-20-04

sudo apt-get update
sudo apt-get install -y nginx libnginx-mod-rtmp

cat ./video-streaming/nginx.conf | sudo tee -a /etc/nginx/nginx.conf > /dev/null
sudo systemctl reload nginx.service

sudo apt-get install ffmpeg
