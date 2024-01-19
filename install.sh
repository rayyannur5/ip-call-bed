#!/bin/sh
cd
sudo apt -y install gparted
sudo gparted
sudo apt -y update
sudo apt -y upgrade
wget https://download.teamviewer.com/download/linux/teamviewer_arm64.deb
sudo apt install ./teamviewer_arm64.deb
sudo apt -y install linphone
sudo apt -y install linphone-cli
pip install paho-mqtt
git clone https://github.com/orangepi-xunlong/wiringOP.git -b next
cd wiringOP
sudo ./build clean
sudo ./build
sudo raspi-config
