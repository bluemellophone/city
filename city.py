#!/usr/bin/env python
from __future__ import absolute_import, division, print_function
# HTTP / HTML
import socket
import tornado.wsgi
import tornado.httpserver
import flask
from flask import request, redirect, url_for, make_response  # NOQA
# Web Internal
import cityfuncs as cf
import simplejson as json
import optparse
import logging
# Other
from detecttools.directory import Directory
from os.path import join, exists, isdir
import utool as ut


################################################################################
# SERVER PARAMETERS
################################################################################

# Flags
BROWSER = ut.get_argflag('--browser')

# Defaults
DEFAULT_PORT = 5000
DEFAULT_DATA_DIR = 'data'

# Application
app = flask.Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 256 * 1024 * 1024  # 256 Megabytes
# print('GET:  ', request.args)
# print('POST: ', request.form)
# print('FILES:', request.files)


################################################################################
# SIMPLE ROUTES
################################################################################


@app.route('/')
def index():
    return cf.template(None)


################################################################################
# COMPLEX / GET ROUTES
################################################################################


@app.route('/status')
def status():
    cars = {}
    # STEP 1 - GPS
    try:
        gps_path      = join(DEFAULT_DATA_DIR, 'gps')
        direct = Directory(gps_path, recursive=True, include_file_extensions=[])
        for direct_car in direct.directory_list:
            base_car = direct_car.base()
            car_path = join(gps_path, base_car)
            # Establish flags
            flags = {}
            flags['submitted_gpx']  = exists(join(car_path, 'track.gpx'))
            flags['submitted_generated_json'] = exists(join(car_path, 'track.json'))
            cars[base_car] = { 'gps': flags }
            cars[base_car]['persons'] = {}
    except:
        print("No GPS data submitted yet")

    # STEP 2 - IMAGES
    try:
        images_path   = join(DEFAULT_DATA_DIR, 'images')
        direct = Directory(images_path, recursive=True, include_file_extensions=[])
        for direct_car in direct.directory_list:
            base_car = direct_car.base()
            if base_car not in cars:
                cars[base_car] = {}
            cars[base_car]['persons'] = {}
            # Construct dict for person
            for direct_person in direct_car.directory_list:
                base_person = direct_person.base()
                person_path = join(images_path, base_car, base_person)
                # Establish flags, inherit GPS for person if car has GPS flags
                if 'gps' in cars[base_car]:
                    flags = dict(cars[base_car]['gps'])
                else:
                    flags = {}
                flags['submitted_images'] = True
                flags['submitted_first'] = exists(join(person_path, 'first.jpg'))
                flags['submitted_last']  = exists(join(person_path, 'last.jpg'))
                # Giraffe flags
                giraffe_path = join(person_path, 'giraffe')
                if isdir(giraffe_path):
                    flags['submitted_giraffe'] = True
                    temp = Directory(giraffe_path, include_file_extensions='images')
                    flags['submitted_giraffe_number'] = len(temp.files())
                # Zebra flags
                zebra_path = join(person_path, 'zebra')
                if isdir(zebra_path):
                    flags['submitted_zebra'] = True
                    temp = Directory(zebra_path, include_file_extensions='images')
                    flags['submitted_zebra_number'] = len(temp.files())
                # Generated offset
                offset_path = join(person_path, 'offset.json')
                if exists(offset_path):
                    flags['submitted_generated_offset'] = True
                    with open(offset_path, 'r') as off:
                        data = json.load(off)
                        offset = data.get('offset', 0.0)
                    flags['submitted_generated_offset_number'] = offset
                # Assign flags to person
                cars[base_car]['persons'][base_person] = flags
            cars[base_car]['persons_number'] = len(cars[base_car]['persons'].keys())
    except:
        print("No Image data submitted yet")

    # STEP 3 - ANALYSIS
    try:
        analysis_path = join(DEFAULT_DATA_DIR, 'analysis')
        direct = Directory(analysis_path, recursive=True, include_file_extensions=[])
        for direct_car in direct.directory_list:
            base_car = direct_car.base()
            if base_car not in cars:
                cars[base_car] = {}
            # Append to dict for person
            for direct_person in direct_car.directory_list:
                base_person = direct_person.base()
                person_path = join(analysis_path, base_car, base_person)
                # Establish flags
                if base_person in cars[base_car]['persons']:
                    flags = dict(cars[base_car]['persons'][base_person])
                else:
                    flags = {}
                flags['analyzed'] = True
                flags['analyzed_review'] = exists(join(person_path, 'review.flag'))
                # Giraffe flags
                giraffe_path = join(person_path, 'giraffe')
                if isdir(giraffe_path):
                    flags['analyzed_giraffe'] = True
                    flags['analyzed_generated_giraffe_confidences'] = exists(join(giraffe_path, 'confidences.json'))
                    temp = Directory(giraffe_path, include_file_extensions=['jpg', 'json'])
                    flags['analyzed_giraffe_number'] = (len(temp.files()) - 1) / 4.0  # 4 images per detection generated (minus 1 confidences)
                    if not flags['analyzed_generated_giraffe_confidences'] and flags['analyzed_giraffe_number'] == -0.25:
                        flags['analyzed_giraffe_number'] = 0.0

                # Zebra flags
                zebra_path = join(person_path, 'zebra')
                if isdir(zebra_path):
                    flags['analyzed_zebra'] = True
                    flags['analyzed_generated_zebra_confidences'] = exists(join(zebra_path, 'confidences.json'))
                    temp = Directory(zebra_path, include_file_extensions=['jpg', 'json'])
                    flags['analyzed_zebra_number'] = (len(temp.files()) - 1) / 4.0  # 4 images per detection generated (minus 1 confidences)
                    if not flags['analyzed_generated_zebra_confidences'] and flags['analyzed_zebra_number'] == -0.25:
                        flags['analyzed_zebra_number'] = 0.0
                # Assign flags to person
                cars[base_car]['persons'][base_person] = flags
            cars[base_car]['persons_number'] = len(cars[base_car]['persons'].keys())
    except:
        print("No images analyzed yet")

    # STEP 4 - PDFS
    try:
        pdfs_path     = join(DEFAULT_DATA_DIR, 'pdfs')
        direct = Directory(pdfs_path, recursive=True, include_file_extensions=[])
        for direct_car in direct.directory_list:
            base_car = direct_car.base()
            if base_car not in cars:
                cars[base_car] = {}
            # Append to dict for person
            for direct_person in direct_car.directory_list:
                base_person = direct_person.base()
                person_path = join(pdfs_path, base_car, base_person)
                # Establish flags
                if base_person in cars[base_car]['persons']:
                    flags = dict(cars[base_car]['persons'][base_person])
                else:
                    flags = {}
                flags['reviewed'] = True
                flags['reviewed_posted']   = exists(join(person_path, 'content.html'))
                flags['reviewed_rendered'] = exists(join(person_path, 'content.pdf'))
                flags['reviewed_printed']  = exists(join(person_path, 'printed.flag'))
                # Assign flags to person
                cars[base_car]['persons'][base_person] = flags
            cars[base_car]['persons_number'] = len(cars[base_car]['persons'].keys())
    except:
        print("No PDFs rendered yet")

    extra = {}
    extra['cars'] = cars
    extra['cars_number'] = len(cars.keys())
    return cf.response(**extra)


################################################################################
# POST ROUTES
################################################################################


################################################################################
# TORNADO / FLASK INITIALIZATION
################################################################################


def start_tornado(app, port=5000, browser=BROWSER, blocking=False, reset_db=True):
    def _start_tornado():
        http_server = tornado.httpserver.HTTPServer(
            tornado.wsgi.WSGIContainer(app))
        http_server.listen(port)
        tornado.ioloop.IOLoop.instance().start()
    # Initialize the web server
    logging.getLogger().setLevel(logging.INFO)
    try:
        app.server_ip_address = socket.gethostbyname(socket.gethostname())
        app.port = port
    except:
        app.server_ip_address = '127.0.0.1'
        app.port = port
    url = 'http://%s:%s' % (app.server_ip_address, app.port)
    print('[web] Tornado server starting at %s' % (url,))
    if browser:
        import webbrowser
        webbrowser.open(url)
    # Blocking
    _start_tornado()


def start_from_terminal():
    # Parse command line arduments
    parser = optparse.OptionParser()
    parser.add_option(
        '-p', '--port',
        help='which port to serve content on',
        type='int', default=DEFAULT_PORT)
    # Start tornado
    opts, args = parser.parse_args()
    start_tornado(app, opts.port)


if __name__ == '__main__':
    start_from_terminal()
