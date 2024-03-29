from __future__ import absolute_import, division, print_function
# HTTP / HTML
import flask
from flask import request
# Web Internal
import simplejson as json
import cStringIO as StringIO
# Image
from PIL import Image
import numpy as np
# Other
from os import mkdir
from os.path import join, exists
from datetime import date


class NavbarClass(object):
    def __init__(nav):
        nav.item_list = [
            ('',            'Home'),
            ('overview',    'Overview'),
            ('images/form', 'Images'),
            ('gps/form',    'GPS'),
            ('map/form',    'Map'),
            ('cards',       'Cards'),
        ]

    def __iter__(nav):
        _link = request.path.strip('/').split('/')
        for link, nice in nav.item_list:
            yield link == _link[0], link, nice


ORIENTATIONS = {   # used in apply_orientation
    2: (Image.FLIP_LEFT_RIGHT,),
    3: (Image.ROTATE_180,),
    4: (Image.FLIP_TOP_BOTTOM,),
    5: (Image.FLIP_LEFT_RIGHT, Image.ROTATE_90),
    6: (Image.ROTATE_270,),
    7: (Image.FLIP_LEFT_RIGHT, Image.ROTATE_270),
    8: (Image.ROTATE_90,)
}


global_args = {
    'NAVBAR': NavbarClass(),
    'YEAR':   date.today().year,
}


def open_oriented_image(im_path):
    im = Image.open(im_path)
    if hasattr(im, '_getexif'):
        exif = im._getexif()
        if exif is not None and 274 in exif:
            orientation = exif[274]
            im = apply_orientation(im, orientation)
    img = np.asarray(im).astype(np.float32) / 255.
    if img.ndim == 2:
        img = img[:, :, np.newaxis]
        img = np.tile(img, (1, 1, 3))
    elif img.shape[2] == 4:
        img = img[:, :, :3]
    return img


def apply_orientation(im, orientation):
    '''
    This script handles the skimage exif problem.
    '''
    if orientation in ORIENTATIONS:
        for method in ORIENTATIONS[orientation]:
            im = im.transpose(method)
    return im


def embed_image_html(image, filter_width=True):
    '''Creates an image embedded in HTML base64 format.'''
    image_pil = Image.fromarray((255 * image).astype('uint8'))
    width, height = image_pil.size
    if filter_width:
        _height = 350
        _width = int((float(_height) / height) * width)
    else:
        _width = 700
        _height = int((float(_width) / width) * height)
    image_pil = image_pil.resize((_width, _height))
    string_buf = StringIO.StringIO()
    image_pil.save(string_buf, format='jpeg')
    data = string_buf.getvalue().encode('base64').replace('\n', '')
    return 'data:image/jpeg;base64,' + data


def template(template_name=None, **kwargs):
    if template_name is None :
        template_name = 'index'
    template_ = template_name + '.html'
    # Update global args with the template's args
    _global_args = dict(global_args)
    _global_args.update(kwargs)
    print(template_)
    return flask.render_template(template_, **_global_args)


def response(code=0, message='', **kwargs):
    '''
        CODES:
            0XX - SYSTEM
                0 - Sucess / Nominal

            1XX - IMAGE IMPORT
                100 - File I/O error
                101 - Car color invalid
                102 - Car number invalid
                103 - Person letter invalid
                104 - Time (hour) invalid
                105 - Time (minute) invalid
                106 - Image archive malformatted

            2XX - GPS IMPORT
                200 - File I/O error
                201 - Car color invalid
                202 - Car number invalid
                203 - NOT USED
                204 - Time (hour) invalid
                205 - Time (minute) invalid
                206 - GPS file malformatted
                207 - GPX file failed to parse

            3XX - REVIEW
                300 - File I/O error
                301 - wkhtmltopdf failure

            4XX - PRINT
                400 - No content.pdf
                401 - Failed to print
    '''
    resp = {
        'status': {
            'code': code,
            'message': message,
        }
    }
    if kwargs:
        resp['data'] = kwargs
    return json.dumps(resp)


def ensure_structure(data, kind, car_number, car_color, person=None):
    data       = data.lower()
    kind       = kind.lower()
    car_number = car_number.lower()
    car_color  = car_color.lower()
    # Create data dir
    if not exists(data):
        mkdir(data)
    # Create kind dir
    kind_dir = join(data, kind)
    if not exists(kind_dir):
        mkdir(kind_dir)
    # Create car dir
    car_dir = join(kind_dir, car_number + car_color)
    if not exists(car_dir):
        mkdir(car_dir)
    # If no person, return car dir
    if person is None:
        return car_dir
    # Create person dir
    person     = person.lower()
    person_dir = join(car_dir, person)
    if not exists(person_dir):
        mkdir(person_dir)
    # Return peron dir
    return person_dir
