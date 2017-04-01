#!/usr/bin/python
#
# examples/shapewin.py -- demonstrate shape extension
#
#    Copyright (C) 2002 Peter Liljenberg <petli@ctrl-c.liu.se>
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public License
# as published by the Free Software Foundation; either version 2.1
# of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the
#    Free Software Foundation, Inc.,
#    59 Temple Place,
#    Suite 330,
#    Boston, MA 02111-1307 USA


# Python 2/3 compatibility.
from __future__ import print_function

import sys
import os

# Change path so we find Xlib
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from Xlib import X, display, Xutil
from Xlib.ext import shape

from PIL import Image

# Application window (only one)
class Window(object):
    def __init__(self, display):
        self.d = display

        # Check for extension
        if not self.d.has_extension('SHAPE'):
            sys.stderr.write('%s: server does not have SHAPE extension\n'
                             % sys.argv[1])
            sys.exit(1)

        # print(version)
        r = self.d.shape_query_version()
        print('SHAPE version %d.%d' % (r.major_version, r.minor_version))


        # Find which screen to open the window on
        self.screen = self.d.screen()

        # background pattern
        im = Image.open('xeyes.png')
        im_width, im_height = im.size

        bgpm = self.screen.root.create_pixmap(im_width, im_height, self.screen.root_depth)


        bggc = self.screen.root.create_gc(foreground = self.screen.black_pixel,
                                          background = self.screen.black_pixel)
        bgpm.put_pil_image(bggc, 0, 0, im)

        # Actual window
        self.window = self.screen.root.create_window(
            100, 100, im_width, im_height, 0,
            self.screen.root_depth,
            X.InputOutput,
            X.CopyFromParent,

            # special attribute values
            background_pixmap = bgpm,
            event_mask = (X.StructureNotifyMask |
                          X.ButtonPressMask | X.ButtonReleaseMask),
            colormap = X.CopyFromParent,
            )

        # Set some WM info

        self.WM_DELETE_WINDOW = self.d.intern_atom('WM_DELETE_WINDOW')
        self.WM_PROTOCOLS = self.d.intern_atom('WM_PROTOCOLS')

        self.window.set_wm_name('Xlib example: shapewin.py')
        self.window.set_wm_icon_name('shapewin.py')
        self.window.set_wm_class('shapewin', 'XlibExample')

        self.window.set_wm_protocols([self.WM_DELETE_WINDOW])
        self.window.set_wm_hints(flags = Xutil.StateHint,
                                 initial_state = Xutil.NormalState)

        self.window.set_wm_normal_hints(flags = (Xutil.PPosition | Xutil.PSize
                                                 | Xutil.PMinSize),
                                        min_width = im_width,
                                        min_height = im_height)

        mask_im = im.convert('1')
        self.add_pm = self.window.create_pixmap(im_width, im_height, 1)
        gc = self.add_pm.create_gc(foreground = self.screen.white_pixel, background = 0)
        self.add_pm.put_pil_image(gc, 0, 0, mask_im)
        gc.free()

        # Set initial mask
        self.window.shape_mask(shape.SO.Set, shape.SK.Input,
                               0, 0, self.add_pm)

        # Tell X server to send us mask events
        self.window.shape_select_input(1)

        # Map the window, making it visible
        self.window.map()


    # Main loop, handling events
    def loop(self):
        current = None
        while 1:
            e = self.d.next_event()

            # Window has been destroyed, quit
            if e.type == X.DestroyNotify:
                sys.exit(0)

            # Shape has changed
            elif e.type == self.d.extension_event.ShapeNotify:
                print('Shape change')

            # Somebody wants to tell us something
            elif e.type == X.ClientMessage:
                if e.client_type == self.WM_PROTOCOLS:
                    fmt, data = e.data
                    if fmt == 32 and data[0] == self.WM_DELETE_WINDOW:
                        sys.exit(0)


if __name__ == '__main__':
    Window(display.Display()).loop()
