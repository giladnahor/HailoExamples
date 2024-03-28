import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gst', '1.0')
from gi.repository import Gtk, Gst, GLib
import argparse
import re
import os

from face_tracking import *

# Run Examples
# python3 CameraTracker.py -i file:///home/giladn/HAILO_SUITE/2023-07-self-extract/hailo_sw_suite/artifacts/tappas/apps/h8/gstreamer/resources/mp4/detection0.mp4

def parse_arguments():
    parser = argparse.ArgumentParser(description="GStreamer App with GUI Controls")
    parser.add_argument("--framerate", type=int, default=15, help="Default framerate for the video.")
    parser.add_argument("--sync", action="store_true", help="Enable display sink sync.")
    parser.add_argument("--input", "-i", type=str, default="/dev/video0", help="URI of the input stream.")
    parser.add_argument("--dump-dot", action="store_true", help="Dump the pipeline graph to a dot file.")
    parser.add_argument("--debug", action="store_true", help="Enable debug prints.")
    return parser.parse_args()

def main():
    args = parse_arguments()
    win = AppWindow(default_framerate=args.framerate, default_sync=args.sync, 
                    input_uri=args.input, dump_dot=args.dump_dot, debug=args.debug)
    
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    Gtk.main()

class AppWindow(Gtk.Window):
    def __init__(self, default_framerate=15, default_sync=False, 
                 input_uri=None, dump_dot=False, debug=False):
        
        self.input_uri = input_uri
        self.dump_dot = dump_dot
        self.debug = debug
        
        Gtk.Window.__init__(self, title="GStreamer App")
        self.set_border_width(10)
        self.set_default_size(400, 200)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.add(vbox)
        # Slider to control framerate
        self.slider = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 1, 30, 1)
        self.slider.set_value(default_framerate)
        self.slider.connect("value-changed", self.on_slider_value_changed)
        vbox.pack_start(self.slider, False, False, 0)

        # Checkbox to control displaysink sync parameter
        self.sync_checkbox = Gtk.CheckButton(label="Enable Display Sink Sync")
        self.sync_checkbox.set_active(default_sync)
        self.sync_checkbox.connect("toggled", self.on_sync_toggled)
        vbox.pack_start(self.sync_checkbox, False, False, 0)

        # Quit Button
        quit_button = Gtk.Button(label="Quit")
        quit_button.connect("clicked", Gtk.main_quit)
        vbox.pack_start(quit_button, False, False, 0)

        # get current path
        self.current_path = os.getcwd()
        print("Current path is: ", self.current_path)
        if (self.dump_dot):
            os.environ["GST_DEBUG_DUMP_DOT_DIR"] = self.current_path
    
        # GStreamer Initialization
        Gst.init(None)
        self.pipeline = self.create_pipeline()
        bus = self.pipeline.get_bus()
        bus.add_signal_watch()
        bus.connect("message", self.on_message)

        self.pipeline.set_state(Gst.State.PLAYING)
        if (self.dump_dot):
            GLib.timeout_add_seconds(5, self.dump_dot_file)
    
    def dump_dot_file(self):
        print("Dumping dot file...")
        Gst.debug_bin_to_dot_file(self.pipeline, Gst.DebugGraphDetails.ALL, "pipeline")
        return False

    def on_message(self, bus, message):
        t = message.type
        if t == Gst.MessageType.EOS:
            self.pipeline.set_state(Gst.State.NULL)
            Gtk.main_quit()
        elif t == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            print("Error: %s" % err, debug)
            self.pipeline.set_state(Gst.State.NULL)
            Gtk.main_quit()
        return True

    def on_slider_value_changed(self, widget):
        value = int(widget.get_value())
        print(f"Setting framerate to: {value} fps")
        
    def on_sync_toggled(self, widget):
        sync = widget.get_active()
        # Adjust displaysink sync parameter. For this example, we just print the value.
        print(f"Display sink sync is set to: {sync}")

    
    def create_pipeline(self):
        # Check if the input seems like a v4l2 device path (e.g., /dev/video0)
        if re.match(r'/dev/video\d+', self.input_uri):
            pipeline_str = f"v4l2src device={self.input_uri} !  image/jpeg ! decodebin ! videoflip video-direction=horiz ! "
        else:
            pipeline_str = f"uridecodebin uri={self.input_uri} ! "
        pipeline_str += get_pipeline(self.current_path)
        print(pipeline_str)
        pipeline = Gst.parse_launch(pipeline_str)
        return pipeline
    
if __name__ == '__main__':
    main()
