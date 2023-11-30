import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib

def on_message(bus, message, loop):
    if message.type == Gst.MessageType.ELEMENT:
        s = message.get_structure()
        if s.get_name() == 'barcode':
            print(f"QR Code Detected: {s.get_string('symbol')}, Type: {s.get_string('type')}")
    elif message.type == Gst.MessageType.EOS:
        loop.quit()
    return True

def main():
    Gst.init(None)

    # Create GStreamer pipeline
    pipeline = Gst.parse_launch("v4l2src device=/dev/video2 ! videoconvert ! zbar ! videoconvert ! autovideosink")

    # Create a GLib Main Loop
    loop = GLib.MainLoop()

    # Get the bus from the pipeline and connect the message handler
    bus = pipeline.get_bus()
    bus.add_signal_watch()
    bus.connect("message", on_message, loop)

    # Start the pipeline
    pipeline.set_state(Gst.State.PLAYING)

    try:
        loop.run()
    except:
        pass

    # Clean up
    pipeline.set_state(Gst.State.NULL)

if __name__ == "__main__":
    main()
