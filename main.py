"""Simple HTTP server with upload functionality."""

__version__ = '0.1'
__author__ = 'sgrontflix'

import http.server
import html
import io
import os
import re
import socket  # For gethostbyaddr()
import sys
import urllib.parse
import contextlib

from http import HTTPStatus


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
        r.append('<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN" '
                 '"http://www.w3.org/TR/html4/strict.dtd">')
        r.append('<html>\n<title>Upload result</title>\n')
        r.append('<body>\n<h1>Upload result</h1>\n')
        if result:
            r.append('<b><font color="green">File successfully uploaded</font></b>: ')
            r.append(message)
        else:
            r.append('<b><font color="red">Failed to upload file</font></b>: ')
            r.append(message)
        r.append(f'\n<br /><br />\n<a href=\"{self.headers["referer"]}\">Go back</a>')
        r.append('\n</body>\n</html>')

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
        """Handles the file upload."""

        # read all bytes (headers included)
        # 'readlines()' hangs the script because it needs the EOF character to stop,
        # even if you specify how many bytes to read
        # "file.read(nbytes).splitlines(True)" does the trick because 'read()' reads 'nbytes' bytes
        # and 'splitlines(True)' splits the file into lines and retains the newline character
        data = self.rfile.read(int(self.headers['content-length'])).splitlines(True)

        # find filename inside the headers
        filename = re.findall(r'Content-Disposition.*name="file"; filename="(.*)"', str(data[1]))

        # name is found if 'filename' contains only one element
        if len(filename) == 1:
            filename = filename[0]
        else:
            return False, 'Couldn\'t find file name.'

        # delete lines 0, 1, 2, 3, n-2, n-1 (headers)
        data = data[4:-2]

        # join list of bytes into bytestring
        data = b''.join(data)

        # write to file
        try:
            with open(filename, 'wb') as file:
                file.write(data)
        except IOError:
            return False, 'Couldn\'t save file.'

        return True, filename

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
        r.append('<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN" '
                 '"http://www.w3.org/TR/html4/strict.dtd">')
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
        r.append('</ul>\n<hr>\n')
        # file upload form
        r.append('<form id="upload" enctype="multipart/form-data" method="post" action="#">\n'
                 '<input id="fileupload" name="file" type="file" />\n'
                 '<input type="submit" value="Submit" id="submit" />\n'
                 '</form>')
        r.append('\n<hr>\n</body>\n</html>\n')
        encoded = '\n'.join(r).encode(enc, 'surrogateescape')
        f = io.BytesIO()
        f.write(encoded)
        f.seek(0)
        self.send_response(HTTPStatus.OK)
        self.send_header('Content-type', 'text/html; charset=%s' % enc)
        self.send_header('Content-Length', str(len(encoded)))
        self.end_headers()
        return f


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('port', action='store',
                        default=8000, type=int,
                        nargs='?',
                        help='Specify alternate port [default: 8000]')
    args = parser.parse_args()

    # ensure dual-stack is not disabled; ref #38907
    class DualStackServer(http.server.ThreadingHTTPServer):
        def server_bind(self):
            # suppress exception when protocol is IPv4
            with contextlib.suppress(Exception):
                self.socket.setsockopt(
                    socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
            return super().server_bind()

    http.server.test(
        HandlerClass=SimpleHTTPRequestHandlerWithUpload,
        ServerClass=DualStackServer,
        port=args.port
    )
