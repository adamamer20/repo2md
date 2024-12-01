#!/bin/bash

if [ ! -d "/etc/repo2md" ]; then
    echo "/etc/repo2md does not exist. Creating directory."
    sudo mkdir /etc/repo2md
    sudo cp config.yaml /etc/repo2md/config.yaml
    sudo chmod 0644 /etc/repo2md/config.yaml
fi

if [ -f dist/repo2md ]; then
    sudo cp dist/repo2md /usr/local/bin/repo2md
    sudo chmod 0755 /usr/local/bin/repo2md
    echo "Installation complete."
    exit 0
else
    echo "Error: dist/repo2md does not exist. Please build the project first."
    echo "Refer to the BUILD.md for instructions on how to build the project."
    exit 1
fi

