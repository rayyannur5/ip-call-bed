#!/bin/sh
cd
sudo apt -y update
sudo apt -y install gparted
sudo gparted
sudo apt -y upgrade
wget https://download.teamviewer.com/download/linux/teamviewer_arm64.deb
sudo apt -y install ./teamviewer_arm64.deb
sudo apt -y install linphone
sudo apt -y install linphone-cli
sudo apt-get -y install vorbis-tools
pip3 install paho-mqtt
pip3 install flask
pip3 install wifimangement-linux
git clone https://github.com/orangepi-xunlong/wiringOP.git -b next
cd wiringOP
sudo ./build clean
sudo ./build
cd
sudo raspi-config
