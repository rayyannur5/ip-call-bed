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
sudo apt-get -y install git swig python3-dev python3-setuptools
git clone --recursive https://github.com/orangepi-xunlong/wiringOP-Python -b next
cd wiringOP-Python
git submodule update --init --remote
python3 generate-bindings.py > bindings.i
sudo python3 setup.py install
sudo raspi-config
