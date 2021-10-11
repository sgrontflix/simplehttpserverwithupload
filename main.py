"""Simple HTTP server with upload functionality and optional SSL/TLS support."""

__version__ = '0.3'
__author__ = 'sgrontflix'

import contextlib
import html
import http.server
import io
import os
import re
import socket  # For gethostbyaddr()
import ssl
import sys
import urllib.parse
import uuid
from functools import partial
from http import HTTPStatus


def sanitize_filename(filename: str) -> str:
    """
    Replaces all forbidden chars with '' and removes unnecessary whitespaces
    If, after sanitization, the given filename is empty, the function will return 'file_[UUID].[ext]'

    :param filename: filename to be sanitized
    :return: sanitized filename
    """
    chars = ['\\', '/', ':', '*', '?', '"', '<', '>', '|']

    filename = filename.translate({ord(x): '' for x in chars}).strip()
    name = re.sub(r'\.[^.]+$', '', filename)
    extension = re.search(r'(\.[^.]+$)', filename)
    extension = extension.group(1) if extension else ''

    return filename if name else f'file_{uuid.uuid4().hex}{extension}'


class SimpleHTTPRequestHandlerWithUpload(http.server.SimpleHTTPRequestHandler):
    """
    Simple HTTP request handler with upload functionality.
    This class is derived from SimpleHTTPRequestHandler with small tweaks
    to add the upload functionality.
    """

    server_version = 'SimpleHTTPWithUpload/' + __version__

    def do_POST(self):
        """Serve a POST request."""
        # upload file
        result, message = self.handle_upload()

        r = []
        enc = sys.getfilesystemencoding()

        # html code of upload result page
        r.append('<!DOCTYPE HTML>')
        r.append('<html>\n<title>Upload result</title>')
        r.append('<body>\n<h1>Upload result</h1>')
        if result:
            r.append('<b><font color="green">File(s) successfully uploaded</font></b>: ')
            r.append(f'{", ".join(message)}.')
        else:
            r.append('<b><font color="red">Failed to upload file(s)</font></b>: ')
            r.append(message)
        r.append(f'<br /><br />\n<a href=\"{self.headers["referer"]}\">Go back</a>')
        r.append('</body>\n</html>')

        encoded = '\n'.join(r).encode(enc, 'surrogateescape')
        f = io.BytesIO()
        f.write(encoded)
        f.seek(0)

        self.send_response(HTTPStatus.OK)
        self.send_header('Content-type', 'text/html')
        self.send_header('Content-Length', str(len(encoded)))
        self.end_headers()

        if f:
            self.copyfile(f, self.wfile)
            f.close()

    def handle_upload(self):
        """Handle the file upload."""

        # extract boundary from headers
        boundary = re.search(f'boundary=([^;]+)', self.headers['content-type']).group(1)

        # read all bytes (headers included)
        # 'readlines()' hangs the script because it needs the EOF character to stop,
        # even if you specify how many bytes to read
        # 'file.read(nbytes).splitlines(True)' does the trick because 'read()' reads 'nbytes' bytes
        # and 'splitlines(True)' splits the file into lines and retains the newline character
        data = self.rfile.read(int(self.headers['content-length'])).splitlines(True)

        # find all filenames
        filenames = re.findall(f'{boundary}.+?filename="(.+?)"', str(data))

        if not filenames:
            return False, 'couldn\'t find file name(s).'

        filenames = [sanitize_filename(filename) for filename in filenames]

        # find all boundary occurrences in data
        boundary_indices = list((i for i, line in enumerate(data) if re.search(boundary, str(line))))

        # save file(s)
        for i in range(len(filenames)):
            # remove file headers
            file_data = data[(boundary_indices[i] + 4):boundary_indices[i+1]]

            # join list of bytes into bytestring
            file_data = b''.join(file_data)

            # write to file
            try:
                with open(f'{args.directory}/{filenames[i]}', 'wb') as file:
                    file.write(file_data)
            except IOError:
                return False, f'couldn\'t save {filenames[i]}.'

        return True, filenames

    def list_directory(self, path):
        """Helper to produce a directory listing (absent index.html).
        Return value is either a file object, or None (indicating an
        error).  In either case, the headers are sent, making the
        interface the same as for send_head().
        """
        try:
            list = os.listdir(path)
        except OSError:
            self.send_error(
                HTTPStatus.NOT_FOUND,
                'No permission to list directory')
            return None
        list.sort(key=lambda a: a.lower())
        r = []
        try:
            displaypath = urllib.parse.unquote(self.path,
                                               errors='surrogatepass')
        except UnicodeDecodeError:
            displaypath = urllib.parse.unquote(path)
        displaypath = html.escape(displaypath, quote=False)
        enc = sys.getfilesystemencoding()
        title = 'Directory listing for %s' % displaypath
        r.append('<!DOCTYPE HTML>')
        r.append('<html>\n<head>')
        r.append('<meta http-equiv="Content-Type" '
                 'content="text/html; charset=%s">' % enc)
        r.append('<title>%s</title>\n</head>' % title)
        r.append('<body>\n<h1>%s</h1>' % title)
        r.append('<hr>\n<ul>')
        for name in list:
            fullname = os.path.join(path, name)
            displayname = linkname = name
            # Append / for directories or @ for symbolic links
            if os.path.isdir(fullname):
                displayname = name + '/'
                linkname = name + '/'
            if os.path.islink(fullname):
                displayname = name + '@'
                # Note: a link to a directory displays with @ and links with /
            r.append('<li><a href="%s">%s</a></li>' % (urllib.parse.quote(linkname, errors='surrogatepass'),
                                                       html.escape(displayname, quote=False)))
        r.append('</ul>\n<hr>')
        # file upload form
        r.append('<h1>File upload</h1>\n<hr>')
        r.append('<form id="upload" enctype="multipart/form-data" method="post" action="#">')
        r.append('<input id="fileupload" name="file" type="file" multiple />')
        r.append('<input type="submit" value="Submit" id="submit" />')
        r.append('</form>')
        r.append('<hr>\n</body>\n</html>')
        encoded = '\n'.join(r).encode(enc, 'surrogateescape')
        f = io.BytesIO()
        f.write(encoded)
        f.seek(0)
        self.send_response(HTTPStatus.OK)
        self.send_header('Content-type', 'text/html; charset=%s' % enc)
        self.send_header('Content-Length', str(len(encoded)))
        self.end_headers()
        return f


def test(HandlerClass=http.server.BaseHTTPRequestHandler,
         ServerClass=http.server.ThreadingHTTPServer,
         protocol='HTTP/1.0', port=8000, bind=None):
    """Test the HTTP request handler class.
    This runs an HTTP server on port 8000 (or the port argument).
    """
    ServerClass.address_family, addr = http.server._get_best_family(bind, port)

    HandlerClass.protocol_version = protocol
    with ServerClass(addr, HandlerClass) as httpd:
        host, port = httpd.socket.getsockname()[:2]
        url_host = f'[{host}]' if ':' in host else host
        print(
            'Serving HTTP' + ('S' if args.certificate else '') + f' on {host} port {port} '
            '(http' + ('s' if args.certificate else '') + f'://{url_host}:{port}/) ...'
        )
        # add ssl to http connection if certificate was specified
        if args.certificate:
            httpd.socket = ssl.wrap_socket(httpd.socket, certfile='cert.pem', server_side=True)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print('\nKeyboard interrupt received, exiting.')
            sys.exit(0)


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('--cgi', action='store_true',
                        help='Run as CGI Server')
    parser.add_argument('--bind', '-b', metavar='ADDRESS',
                        help='Specify alternate bind address '
                             '[default: all interfaces]')
    parser.add_argument('--directory', '-d', default=os.getcwd(),
                        help='Specify alternative directory '
                             '[default: current directory]')
    parser.add_argument('--certificate', '-c', metavar='PATH_TO_CERTIFICATE',
                        help='Your SSL certificate in the .pem file format '
                             '[default: none]')
    parser.add_argument('port', action='store',
                        default=8000, type=int,
                        nargs='?',
                        help='Specify alternate port [default: 8000]')
    args = parser.parse_args()
    if args.cgi:
        handler_class = http.server.CGIHTTPRequestHandler
    else:
        handler_class = partial(SimpleHTTPRequestHandlerWithUpload,
                                directory=args.directory)

    # ensure dual-stack is not disabled; ref #38907
    class DualStackServer(http.server.ThreadingHTTPServer):
        def server_bind(self):
            # suppress exception when protocol is IPv4
            with contextlib.suppress(Exception):
                self.socket.setsockopt(
                    socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
            return super().server_bind()

    test(
        HandlerClass=handler_class,
        ServerClass=DualStackServer,
        port=args.port,
        bind=args.bind
    )
