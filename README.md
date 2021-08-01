# Simple HTTP server with upload functionality

Simple HTTP server with upload functionality written in Python.

This script allows the user to create an HTTP server on the go for file sharing inside an home network.

It does NOT provide any encryption. Only use it inside trusted networks.

## Installation

```
git clone https://github.com/sgrontflix/simplehttpserverwithupload
cd simplehttpserverwithupload
```

## Usage

`python main.py [-h] [port]`

or

`python3 main.py [-h] [port]`

After the server finishes starting, open a web browser on another machine and type `<IP_ADDRESS>:<PORT>` on the address bar, where `<IP_ADDRESS>` is your server's IP address and `<PORT>` is the port the server is running on (default: 8000). 
You should now see all of the files contained in the directory you ran the code from and an upload section.
