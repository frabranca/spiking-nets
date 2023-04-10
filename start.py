import samna, samnagui
import time
from threading import Thread
import sys
import os

def open_speck2e_dev_kit():
    return samna.device.open_device("Speck2eDevKit")

def build_samna_event_route(dk, dvs_graph):
    # build a graph in samna to show dvs
    _, _, streamer = dvs_graph.sequential([dk.get_model_source_node(), "Speck2eDvsToVizConverter", "VizEventStreamer"])

    streamer.set_streamer_endpoint("tcp://0.0.0.0:40000")

def build_samnagui_event_route(visualizer, plot_id):
    # set the viz events route in samnagui
    visualizer.receiver.set_receiver_endpoint("tcp://0.0.0.0:40000")
    visualizer.receiver.add_destination(visualizer.splitter.get_input_channel())
    visualizer.splitter.add_destination("passthrough", visualizer.plots.get_plot_input(plot_id))

def open_visualizer(window_width, window_height, receiver_endpoint, sender_endpoint, visualizer_id):
    # start visualizer in a isolated process which is required on mac, intead of a sub process.
    # it will not return until the remote node is opened. Return the opened visualizer.
    gui_cmd = '''%s -c "import samna, samnagui; samnagui.runVisualizer(%f, %f, '%s', '%s', %d)"''' % \
        (sys.executable, window_width, window_height, receiver_endpoint, sender_endpoint, visualizer_id)
    print("Visualizer start command: ", gui_cmd)
    gui_thread = Thread(target=os.system, args=(gui_cmd,))
    gui_thread.start()

    # wait for open visualizer and connect to it.
    timeout = 10
    begin = time.time()
    name = "visualizer" + str(visualizer_id)
    while time.time() - begin < timeout:
        try:
            time.sleep(0.05)
            samna.open_remote_node(visualizer_id, name)
        except:
            continue
        else:
            return getattr(samna, name), gui_thread

    raise Exception("open_remote_node failed:  visualizer id %d can't be opened in %d seconds!!" % (visualizer_id, timeout))

# init samna, endpoints should correspond to visualizer, if some port is already bound, please change it.
samna_node = samna.init_samna()
time.sleep(1)   # wait tcp connection build up, this is necessary to open remote node.

visualizer_id = 3
visualizer, gui_thread = open_visualizer(0.75, 0.75, samna_node.get_receiver_endpoint(), samna_node.get_sender_endpoint(), visualizer_id)

dk = open_speck2e_dev_kit()

# route events
dvs_graph = samna.graph.EventFilterGraph()
build_samna_event_route(dk, dvs_graph)

activity_plot_id = visualizer.plots.add_activity_plot(128, 128, "DVS Layer")
plot_name = "plot_" + str(activity_plot_id)
plot = getattr(visualizer, plot_name)
plot.set_layout(0, 0, 0.6, 1)   # set the position: top left x, top left y, bottom right x, bottom right y

build_samnagui_event_route(visualizer, activity_plot_id)

dvs_graph.start()

# modify configuration
config = samna.speck2e.configuration.SpeckConfiguration()
# enable dvs event monitoring
config.dvs_layer.monitor_enable = True
dk.get_model().apply_configuration(config)

# wait until visualizer window destroys.
gui_thread.join()

dvs_graph.stop()