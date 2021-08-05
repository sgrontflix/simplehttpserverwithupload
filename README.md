# Simple HTTP server with upload functionality

This script allows the user to create an HTTP server on the fly for file sharing inside a home network.

## Installation

```
git clone https://github.com/sgrontflix/simplehttpserverwithupload
cd simplehttpserverwithupload
```

## Usage

`python main.py [-h] [--cgi] [--bind ADDRESS] [--directory DIRECTORY] [--certificate PATH_TO_CERTIFICATE] [port]`

or

`python3 main.py [-h] [--cgi] [--bind ADDRESS] [--directory DIRECTORY] [--certificate PATH_TO_CERTIFICATE] [port]`

After the server finishes starting, open a web browser on another machine and type `http://<IP_ADDRESS>:<PORT>` on the address bar, where `<IP_ADDRESS>` is your server's IP address and `<PORT>` is the port the server is running on (default: 8000). 
You should now see all of the files contained in the directory you ran the code from (you can optionally specify a different one) and an upload section.

## HTTPS

You can optionally enable HTTPS by providing a CA or self-signed certificate in the `.pem` file format.

To generate a self-signed certificate with [OpenSSL](https://www.openssl.org/), run the following command and follow the instructions:

`openssl req -new -x509 -days 365 -nodes -out cert.pem -keyout cert.pem`

Make sure to use HTTPS when connecting to the server, otherwise you'll get an error message. If your browser tells you the connection is not secure, it's because you're using a self-signed certificate; however, since you generated it, you don't have to worry.
