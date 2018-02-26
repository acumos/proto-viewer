#!/usr/bin/env python3
import os
from functools import partial
import hashlib

from bokeh.server.server import Server
from bokeh.embed import server_document
from bokeh.layouts import widgetbox, column, row
from bokeh.models import ColumnDataSource, Div, Range1d
from bokeh.plotting import figure
from bokeh.themes import Theme
from bokeh.models.widgets import Select
from bokeh.io import curdoc
from jinja2 import Environment, FileSystemLoader

from acumos_proto_viewer import data, get_module_logger
from acumos_proto_viewer.utils import list_compiled_proto_names
from acumos_proto_viewer.exceptions import ProtoNotReachable

from tornado.web import RequestHandler

#magic that will be used to return the correct image url even when in Docker; will be set to the request uri to /. If they can hit whatever:/, then they can hit whatever/data etc

#read params from env variables
CBF = int(os.environ["UPDATE_CALLBACK_FREQUENCY"]) if "UPDATE_CALLBACK_FREQUENCY" in os.environ else 1000 #default to 1s
SUPPORTED_MIME_TYPES = ["png", "jpeg"]

_host = None
_last_callback = None

_logger = get_module_logger(__name__)

def return_image(val, model_id, message_name, field, mime, sind):
    CDS = curdoc().get_model_by_name(sind)
    index = CDS.tags[0]
    url = "http://{0}/image/".format(_host) + "---".join([model_id, message_name, field, mime, sind, str(index)])
    #_logger.debug("generated image URL: {0}".format(url))
    return url

class IndexHandler(RequestHandler):
    def get(self):
        #this trick allows us to return the correct image url, even in docker
        global _host
        _host = self.request.host
        _logger.debug("setting hostname to {0}".format(_host))

        env = Environment(loader=FileSystemLoader('templates'))
        template = env.get_template('embed.html')
        script = server_document('http://{0}/bkapp'.format(_host))
        self.set_status(200)
        self.write(template.render(script=script, template="Tornado"))
        self.finish()

class DataHandler(RequestHandler):
    def post(self):
        proto_url = self.request.headers["PROTO-URL"] #the weird casing on these were told to me by the model connector team
        message_name = self.request.headers["Message-Name"]
        if (proto_url is None or message_name is None):
            self.set_status(400)
            self.write("Error: model_id or message_name header missing.")
        else:
            try:
                data.inject_data(self.request.body, proto_url, message_name)
                self.set_status(200)
                self.write(self.request.body) #Kazi has asked that due to the way the Acmos "model conector" aka "blueprint orchestrator" works, that I should return the request body that I recieved. OK..
            except ProtoNotReachable:
                self.set_status(400)
                self.write("Error: {0} was not downloadable!".format(proto_url))
        self.finish()

class ImageHandler(RequestHandler):
    def get(self, slug):
        (model_id, message_name, field, mime, sind, index) = slug.split("---")
        self.set_header('Content-Type', 'image/' + mime)
        raw_data_size = data.get_raw_data_source_size(model_id, message_name)
        if raw_data_size > 0:
            i = min(int(index), raw_data_size - 1) #if session was logged in before midnight, raw data set might have reset and the session index is now greater; check for this edge case so we don't blow up
            source = data.get_raw_data(model_id, message_name, i, i + 1)
            self.set_status(200)
            self.write(source[0][field])
        else:
            self.set_status(404)
        self.finish()

#######
# Helpers
def _remove_fig(curdoc):
    try:
        curdoc.remove_root(curdoc.get_model_by_name("thefig"))
    except:
        pass

def _remove_selection(curdoc):
    try:
        curdoc.remove_root(curdoc.get_model_by_name("fieldsselection"))
        curdoc.remove_root(curdoc.get_model_by_name("imageselection"))
    except:
        pass

def _remove_callback(curdoc):
    if _last_callback is not None:
        try:
            curdoc.remove_periodic_callback(_last_callback)
            _logger.info("Callback removed")
        except:
            pass


def _get_source_index(session_id, model_id, message_name, field_name=None):
    if field_name is None:
        h = "{0}{1}{2}".format(session_id, model_id, message_name)
    else:
        h = "{0}{1}{2}{3}".format(session_id, model_id, message_name, field_name)
    return hashlib.sha224(h.encode('utf-8')).hexdigest()


def _install_callback_and_cds(sind, model_id, message_name, field_transforms={}, stream_limit=None):
    """
    Set up a new CDS, install a callback to update it
    If it already exists do nothing
    """
    d = curdoc()
    _remove_callback(d)

    if d.get_model_by_name(sind) is None:
        d.add_root(ColumnDataSource({k: [] for k in data.proto_data_structure[model_id]["messages"][message_name]["properties"].keys()},
                                    name=sind,
                                    tags=[0]))
    f = partial(_bokeh_periodic_update, sind, model_id, message_name, field_transforms, stream_limit)
    global _last_callback
    _last_callback = f
    d.add_periodic_callback(f, CBF)
    _logger.info("Callback {0} added for sind {1}".format(f, sind))


########
# UPDATE CALLBACKS
def _bokeh_periodic_update(sind, model_id, message_name, field_transforms={}, stream_limit=None):
    """
    Callback that gets called periodically *for each session*. That is, each session (user connecting via browser) will register a callback of this for their session
    Here we will update the data source with new points
    https://bokeh.pydata.org/en/latest/docs/reference/models/sources.html

    field_transoforms is a dict {k : [func, kwargs]} where func(k, **kwargs) will be applied for all k in the raw data before going into the CDS

    PLEASE READ ABOUT DATA REDUNDANCY:
        https://groups.google.com/a/continuum.io/forum/#!topic/bokeh/m91Y2La6fS0

    """
    d = curdoc()
    CDS = d.get_model_by_name(sind)
    index = CDS.tags[0]
    source = data.get_raw_data(model_id, message_name, index, -1)
    if source != []: #might be no data, exit callback immediately if so
        sinit = {k: [] for k in data.proto_data_structure[model_id]["messages"][message_name]["properties"].keys()}
        newdata = sinit
        num_data = 0
        for m in source: #from where we left off to the end
            for mk in sinit.keys():
                val = m[mk]
                if mk in field_transforms:
                    val = field_transforms[mk][0](val, **field_transforms[mk][1])
                newdata[mk].append(val)
            num_data += 1

        #Warning, don't check newdata = sinit because it's not a deep copy!!!!!11!
        d.get_model_by_name(sind).stream(newdata, stream_limit) #after the data source is updated, some magic happens such that the new data is streamed via web socket to the browser
        CDS.tags = [index + num_data]


def proto_change():
    d = curdoc()
    _remove_fig(d)
    _remove_selection(d)
    pv = d.get_model_by_name("proto").value
    message = d.get_model_by_name("message")
    if pv != "Please Select":
        message.options = list(data.proto_data_structure[pv]["messages"].keys()) + ["Please Select"]
        message.value = "Please Select"
    else:
        message.options = []
        d.get_model_by_name("graphs").options = []


def message_change():
    d = curdoc()
    _remove_fig(d)
    _remove_selection(d)
    message_name = d.get_model_by_name("message").value

    if message_name != "Please Select":
        #for the genius use of partial here see https://stackoverflow.com/questions/41926478/python-bokeh-send-additional-parameters-to-widget-event-handler
        d.get_model_by_name("graphs").options = ["Please Select", "line", "scatter", "step", "image", "raw"]
        d.get_model_by_name("graphs").value = "Please Select"
    else:
        d.get_model_by_name("graphs").options = []


def graphs_change():
    d = curdoc()
    _remove_fig(d)
    _remove_selection(d)

    gv = d.get_model_by_name("graphs").value
    model_id = d.get_model_by_name("proto").value
    message_name = d.get_model_by_name("message").value
    props = data.proto_data_structure[model_id]["messages"][message_name]["properties"]
    if gv in ["line", "scatter", "step"]:
        field_options = ["{0} : {1}".format(k, props[k]) for k in props if k not in "apv_model_as_string"] #never want to plot this special string field
        xselect = Select(title="X axis", value="Please Select", options=field_options + ["Please Select"], name="xaxisselect")
        yselect = Select(title="Y axis", value="Please Select", options=field_options + ["Please Select"], name="yaxisselect")
        xselect.on_change('value', lambda attr, old, new: make_2axis_graph())
        yselect.on_change('value', lambda attr, old, new: make_2axis_graph())
        d.add_root(column(Div(text=""), row(widgetbox([xselect]), widgetbox([yselect])), name="fieldsselection"))

    if gv in ["image"]:
        #alter the field options for known non-image fields
        field_options = ["{0} : {1}".format(k, props[k]) for k in props if k not in ["apv_recieved_at", "apv_sequence_number", "apv_model_as_string"]]
        imageselect = Select(title="Image Field", value="Please Select", options=["Please Select"] + field_options, name="imageselect")
        mimeselect = Select(title="MIME Type", value="Please Select", options=["Please Select"] + SUPPORTED_MIME_TYPES, name="mimeselect")
        imageselect.on_change('value', lambda attr, old, new: image_selection_change())
        mimeselect.on_change('value', lambda attr, old, new: image_selection_change())
        d.add_root(column(Div(text=""), widgetbox([imageselect, mimeselect]), name="imageselection"))

    if gv in ["raw"]:
        p = figure(plot_width=500, plot_height=500, title="", name="thefig")
        sind = _get_source_index(d.session_context.id, d.get_model_by_name("proto").value, d.get_model_by_name("message").value)
        _install_callback_and_cds(sind, model_id, message_name, stream_limit=1)
        p.text(x='apv_sequence_number', y=0, text='apv_model_as_string', source=d.get_model_by_name(sind), text_font_size="30pt")
        p.x_range.follow = "end" # don't jam all the data into the graph; "window" it
        p.x_range.follow_interval = 1 # don't jam all the data into the graph; "window" it
        p.x_range.range_padding = 0

        d.add_root(p)


def image_selection_change():
    d = curdoc()
    _remove_fig(d)
    model_id = d.get_model_by_name("proto").value
    message_name = d.get_model_by_name("message").value
    image_field = d.get_model_by_name("imageselect").value.split(" :")[0]
    mime = d.get_model_by_name("mimeselect").value

    if image_field != "Please Select" and mime != "Please Select":
        p = figure(plot_width=500, plot_height=500, title="", x_range=Range1d(start=0, end=1), y_range=Range1d(start=0, end=1), name="thefig")
        sind = _get_source_index(d.session_context.id, model_id, message_name, image_field + mime)

        _install_callback_and_cds(sind, model_id, message_name,
                                  {image_field: [return_image, {"model_id": model_id,
                                                                "message_name": message_name,
                                                                "field": image_field,
                                                                "mime": mime,
                                                                "sind": sind}]},
                                  stream_limit=1)
        p.image_url(url=image_field, x=0, y=1, h=1, w=1, source=d.get_model_by_name(sind))
        d.add_root(p)


def make_2axis_graph():
    d = curdoc()
    _remove_fig(d)
    gv = d.get_model_by_name("graphs").value
    model_id = d.get_model_by_name("proto").value
    message_name = d.get_model_by_name("message").value

    xval = d.get_model_by_name("xaxisselect").value
    yval = d.get_model_by_name("yaxisselect").value

    if xval == "Please Select" or yval == "Please Select":
        pass
    else:
        p = figure(plot_width=400, plot_height=400, name="thefig")
        sind = _get_source_index(d.session_context.id, d.get_model_by_name("proto").value, d.get_model_by_name("message").value)
        _install_callback_and_cds(sind, model_id, message_name, stream_limit = 100000)

        #get the field name back from the pretty field : meta string formed above
        x = xval.split(" :")[0]
        y = yval.split(" :")[0]

        if gv == "line":
            p.line(x=x, y=y, color="firebrick", line_width=2, source=d.get_model_by_name(sind))
            p.x_range.follow = "end" # don't jam all the data into the graph; "window" it
            p.x_range.follow_interval = 100
            p.x_range.range_padding = 0
        if gv == "scatter":
            p.cross(x=x, y=y, size=20, color="firebrick", line_width=2, source=d.get_model_by_name(sind))
        if gv == "step":
            p.step(x=x, y=y, color="#FB8072", source=d.get_model_by_name(sind))

        d.add_root(p)


def modify_doc(doc):
    # Create Input controls
    proto = Select(title="Proto Selection", value="Please Select", options=list_compiled_proto_names() + ["Please Select"], name="proto")
    message = Select(title="Message Selection", value="Please Select", options=["Please Select"], name="message")
    graphs = Select(title="Graph Selection", value="Please Select", options=[], name="graphs")

    # Add a handler for input changes
    proto.on_change('value', lambda attr, old, new: proto_change())
    message.on_change('value', lambda attr, old, new: message_change())
    graphs.on_change('value', lambda attr, old, new: graphs_change())

    #construct what the user will see
    selec = row(widgetbox([proto]), widgetbox([message]), widgetbox([graphs]))

    doc.add_root(selec)

    doc.theme = Theme(filename="theme.yaml")

# Setting num_procs here means we can't touch the IOLoop before now, we must
# let Server handle that. If you need to explicitly handle IOLoops then you
# will need to use the lower level BaseServer class.

#warning!!! VERY HORRIBLE THINGS happen if you change num_procs > 1
#including:
    #source index being greater than the amount of available data
    # _host not being available in the image handler, despite the fact it should have been called waaaaay before when index handler is first called
    #I think tornado is doing weird things with the state of the other threads and it doesn't share the state with this current document
    #dont change this, at least not without understanding all this.
server = Server({'/bkapp': modify_doc},
                num_procs=1, #see above!
                extra_patterns=[('/', IndexHandler), ('/data', DataHandler), ('/image/([^/]+)', ImageHandler)],
                address="0.0.0.0",
                #80 is when running in docker behind nginx, 5006 when local
                allow_websocket_origin=["*:80", "*:5006"])
server.start()

if __name__ == '__main__':
    server.io_loop.start()
