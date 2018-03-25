#!/usr/bin/env python3
import os
from functools import partial
from bokeh.server.server import Server
from bokeh.embed import server_document
from bokeh.layouts import widgetbox, column, row
from bokeh.models import ColumnDataSource, Div, Range1d
from bokeh.plotting import figure
from bokeh.themes import Theme
from bokeh.models.widgets import Select
from bokeh.io import curdoc
from jinja2 import Environment, FileSystemLoader
from tornado.web import RequestHandler
from acumos_proto_viewer import data, get_module_logger
from acumos_proto_viewer.run_handlers import MODEL_SELECTION, MESSAGE_SELECTION, GRAPH_SELECTION, GRAPH_OPTIONS, AFTER_MODEL_SELECTION, FIGURE_MODEL, FIELD_SELECTION, IMAGE_MIME_SELECTION, IMAGE_SELECTION, MIME_SELECTION, DEFAULT_UNSELECTED, X_AXIS_SELECTION, Y_AXIS_SELECTION
from acumos_proto_viewer import run_handlers


# read params from env variables
CBF = int(os.environ["UPDATE_CALLBACK_FREQUENCY"]) if "UPDATE_CALLBACK_FREQUENCY" in os.environ else 1000  # default to 1s
SUPPORTED_MIME_TYPES = ["png", "jpeg"]
_host = None  # magic that will be used to return the correct image url even when in Docker; will be set to the request uri to /. If they can hit whatever:/, then they can hit whatever/data etc
_last_callback = None

_logger = get_module_logger(__name__)


class IndexHandler(RequestHandler):
    """handler for /"""
    def get(self):
        """handler for GET /"""
        # this trick allows us to return the correct image url, even in docker
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
    """handler for /data"""
    def post(self):
        """handler for POST /data"""
        code, status = run_handlers.handle_data_post(self.request.headers, self.request.body)
        self.set_status(code)
        self.write(status)
        self.finish()


class ONAPMRTopicHandler(RequestHandler):
    """handler for /onap_mr_topic"""
    def put(self, topic_name):
        """handler for PUT  on /onap_mr_topic"""
        code, status = run_handlers.handle_onap_mr_put(self.request.headers, topic_name)
        self.set_status(code)
        self.write(status)
        self.finish()

    def delete(self, topic_name):
        """handler for delete on /onap_mr_topic"""
        code, status = run_handlers.handle_onap_mr_delete(topic_name)
        self.set_status(code)
        self.write(status)
        self.finish()


class ImageHandler(RequestHandler):
    """handler for /image"""
    def get(self, slug):
        """handler for GET /image"""
        (model_id, message_name, field, mime, sind, index) = slug.split("---")
        self.set_header('Content-Type', 'image/' + mime)
        raw_data_size = data.get_raw_data_source_size(model_id, message_name)
        if raw_data_size > 0:
            i = min(int(index), raw_data_size - 1)  # if session was logged in before midnight, raw data set might have reset and the session index is now greater; check for this edge case so we don't blow up
            source = data.get_raw_data(model_id, message_name, i, i + 1)
            self.set_status(200)
            self.write(source[0][field])
        else:
            self.set_status(404)
        self.finish()

#######
# Helpers


def _remove_fig(curdoc):
    if curdoc.get_model_by_name(FIGURE_MODEL) is not None:
        curdoc.remove_root(curdoc.get_model_by_name(FIGURE_MODEL))


def _remove_selection(curdoc):
    if curdoc.get_model_by_name(FIELD_SELECTION) is not None:
        curdoc.remove_root(curdoc.get_model_by_name(FIELD_SELECTION))
    if curdoc.get_model_by_name(IMAGE_MIME_SELECTION) is not None:
        curdoc.remove_root(curdoc.get_model_by_name(IMAGE_MIME_SELECTION))


def _remove_callback(curdoc):
    if _last_callback is not None:
        try:
            curdoc.remove_periodic_callback(_last_callback)
            _logger.info("Callback removed")
        except Exception as exc:
            _logger.debug(exc)


def _install_callback_and_cds(sind, model_id, message_name, field_transforms={}, stream_limit=None):
    """
    Set up a new column_data_source, install a callback to update it
    If it already exists do nothing
    """
    d = curdoc()
    _remove_callback(d)
    model_id, message_name, model_type = run_handlers.get_modelid_messagename_type(d)
    emptyd = {k: [] for k in run_handlers.get_model_properties(model_id, message_name, model_type)}
    if d.get_model_by_name(sind) is None:
        d.add_root(ColumnDataSource(emptyd,
                                    name=sind,
                                    tags=[0]))
    func = partial(_bokeh_periodic_update, sind, model_id, message_name, field_transforms, stream_limit)
    global _last_callback
    _last_callback = func
    d.add_periodic_callback(func, CBF)
    _logger.info("Callback {0} added for sind {1}".format(func, sind))


########
# UPDATE CALLBACKS
def _bokeh_periodic_update(sind, model_id, message_name, field_transforms={}, stream_limit=None):
    """
    Callback that gets called periodically *for each session*. That is, each session (user connecting via browser) will register a callback of this for their session
    Here we will update the data source with new points
    https://bokeh.pydata.org/en/latest/docs/reference/models/sources.html

    field_transoforms is a dict {k : [func, kwargs]} where func(k, **kwargs) will be applied for all k in the raw data before going into the column_data_source

    PLEASE READ ABOUT DATA REDUNDANCY:
        https://groups.google.com/a/continuum.io/forum/#!topic/bokeh/m91Y2La6fS0

    """
    d = curdoc()
    column_data_source = d.get_model_by_name(sind)
    index = column_data_source.tags[0]
    model_id, message_name, model_type = run_handlers.get_modelid_messagename_type(d)
    source = data.get_raw_data(model_id, message_name, index, -1)
    if source != []:  # might be no data, exit callback immediately if so
        sinit = {k: [] for k in run_handlers.get_model_properties(model_id, message_name, model_type)}
        newdata = sinit
        num_data = 0
        for m in source:  # from where we left off to the end
            for mk in sinit.keys():
                val = m[mk]
                if mk in field_transforms:
                    val = field_transforms[mk][0](val, **field_transforms[mk][1])
                if isinstance(val, bytes):
                    # this can happen in rare cases, like RAW being used to try to display an image
                    # bokeh internally does a JSON serialization so we can't let bytes slip through
                    # this does not affect image rendering is that is not put into the bokeh CDS, only the URL is
                    val = "<RAW BYTES>"
                newdata[mk].append(val)
            num_data += 1

        # Warning, don't check newdata = sinit because it's not a deep copy!!!!!11!
        d.get_model_by_name(sind).stream(newdata, stream_limit)  # after the data source is updated, some magic happens such that the new data is streamed via web socket to the browser
        column_data_source.tags = [index + num_data]


def modelselec_change():
    d = curdoc()
    _remove_fig(d)
    _remove_selection(d)
    d.remove_root(d.get_model_by_name(AFTER_MODEL_SELECTION))
    modelselec = d.get_model_by_name(MODEL_SELECTION)
    msv = modelselec.value
    if msv != DEFAULT_UNSELECTED:
        model_id, message_name, model_type = run_handlers.get_modelid_messagename_type(d)
        if model_type == "protobuf":
            message = Select(title="Message Selection", value=DEFAULT_UNSELECTED, options=list(data.proto_data_structure[model_id]["messages"].keys()) + [DEFAULT_UNSELECTED], name=MESSAGE_SELECTION)
            graphs = Select(title="Graph Selection", value=DEFAULT_UNSELECTED, options=[], name=GRAPH_SELECTION)
            message.on_change('value', lambda attr, old, new: message_change())
            graphs.on_change('value', lambda attr, old, new: graphs_change())
            selec = row(widgetbox([message]), widgetbox([graphs]), name=AFTER_MODEL_SELECTION)
        else:  # there is no message selection here
            graphs = Select(title="Graph Selection", value=DEFAULT_UNSELECTED, options=GRAPH_OPTIONS, name=GRAPH_SELECTION)
            graphs.on_change('value', lambda attr, old, new: graphs_change())
            selec = row(widgetbox([graphs]), name=AFTER_MODEL_SELECTION)
        d.add_root(selec)
        d.add_root(selec)


def message_change():
    d = curdoc()
    _remove_fig(d)
    _remove_selection(d)
    message_name = d.get_model_by_name(MESSAGE_SELECTION).value
    d.get_model_by_name(GRAPH_SELECTION).options = GRAPH_OPTIONS if message_name != DEFAULT_UNSELECTED else [DEFAULT_UNSELECTED]
    d.get_model_by_name(GRAPH_SELECTION).value = DEFAULT_UNSELECTED


def graphs_change():
    d = curdoc()
    _remove_fig(d)
    _remove_selection(d)

    graph_val = d.get_model_by_name(GRAPH_SELECTION).value
    model_id, message_name, model_type = run_handlers.get_modelid_messagename_type(d)
    props = run_handlers.get_model_properties(model_id, message_name, model_type)

    if graph_val in ["line", "scatter", "step"]:
        field_options = ["{0} : {1}".format(k, props[k]) for k in props if k not in "apv_model_as_string"]  # never want to plot this special string field
        xselect = Select(title="X axis", value=DEFAULT_UNSELECTED, options=field_options + [DEFAULT_UNSELECTED], name=X_AXIS_SELECTION)
        yselect = Select(title="Y axis", value=DEFAULT_UNSELECTED, options=field_options + [DEFAULT_UNSELECTED], name=Y_AXIS_SELECTION)
        xselect.on_change('value', lambda attr, old, new: make_2axis_graph())
        yselect.on_change('value', lambda attr, old, new: make_2axis_graph())
        d.add_root(column(Div(text=""), row(widgetbox([xselect]), widgetbox([yselect])), name=FIELD_SELECTION))

    if graph_val in ["image"]:
        # alter the field options for known non-image fields
        field_options = ["{0} : {1}".format(k, props[k]) for k in props if k not in ["apv_recieved_at", "apv_sequence_number", "apv_model_as_string"]]
        imageselect = Select(title="Image Field", value=DEFAULT_UNSELECTED, options=[DEFAULT_UNSELECTED] + field_options, name=IMAGE_SELECTION)
        mimeselect = Select(title="MIME Type", value=DEFAULT_UNSELECTED, options=[DEFAULT_UNSELECTED] + SUPPORTED_MIME_TYPES, name=MIME_SELECTION)
        imageselect.on_change('value', lambda attr, old, new: image_selection_change())
        mimeselect.on_change('value', lambda attr, old, new: image_selection_change())
        d.add_root(column(Div(text=""), widgetbox([imageselect, mimeselect]), name=IMAGE_MIME_SELECTION))

    if graph_val in ["raw"]:
        p = figure(plot_width=500, plot_height=500,
                   background_fill_color="white",
                   y_range=(-40, 0), title="", name=FIGURE_MODEL)

        p.xaxis.visible = False
        p.yaxis.visible = False
        sind = run_handlers.get_source_index(d.session_context.id, model_id, message_name)
        _install_callback_and_cds(sind, model_id, message_name, stream_limit=1)
        p.text(x='apv_sequence_number',
               y=0,
               text='apv_model_as_string',
               source=d.get_model_by_name(sind),
               text_font_size="10pt",
               text_line_height=0.7,
               text_baseline="top",
               text_align="left")
        p.x_range.follow = "end"  # don't jam all the data into the graph; "window" it
        p.x_range.follow_interval = 1  # don't jam all the data into the graph; "window" it
        p.x_range.range_padding = 0

        d.add_root(p)


def image_selection_change():
    """Callback for changing the image field or mime field"""

    def return_image(val, model_id, message_name, field, mime, sind):
        """Returns a URL resolvable by the probe"""
        column_data_source = curdoc().get_model_by_name(sind)
        index = column_data_source.tags[0]
        url = "http://{0}/image/".format(_host) + "---".join([model_id, message_name, field, mime, sind, str(index)])
        return url

    d = curdoc()
    _remove_fig(d)
    model_id, message_name, _ = run_handlers.get_modelid_messagename_type(d)
    image_field = d.get_model_by_name(IMAGE_SELECTION).value.split(" :")[0]
    mime = d.get_model_by_name(MIME_SELECTION).value

    if image_field != DEFAULT_UNSELECTED and mime != DEFAULT_UNSELECTED:
        plot = figure(plot_width=500, plot_height=500, title="", x_range=Range1d(start=0, end=1), y_range=Range1d(start=0, end=1), name=FIGURE_MODEL)
        sind = run_handlers.get_source_index(d.session_context.id, model_id, message_name, image_field + mime)

        _install_callback_and_cds(sind, model_id, message_name,
                                  {image_field: [return_image, {"model_id": model_id,
                                                                "message_name": message_name,
                                                                "field": image_field,
                                                                "mime": mime,
                                                                "sind": sind}]},
                                  stream_limit=1)
        plot.image_url(url=image_field, x=0, y=1, h=1, w=1, source=d.get_model_by_name(sind))
        d.add_root(plot)


def make_2axis_graph():
    """Makes a 2 axis graph"""
    d = curdoc()
    _remove_fig(d)
    graph_val = d.get_model_by_name(GRAPH_SELECTION).value
    model_id, message_name, _ = run_handlers.get_modelid_messagename_type(d)

    xval = d.get_model_by_name(X_AXIS_SELECTION).value
    yval = d.get_model_by_name(Y_AXIS_SELECTION).value

    if xval != DEFAULT_UNSELECTED and yval != DEFAULT_UNSELECTED:
        plot = figure(plot_width=400, plot_height=400, name=FIGURE_MODEL)
        sind = run_handlers.get_source_index(d.session_context.id, model_id, message_name)
        _install_callback_and_cds(sind, model_id, message_name, stream_limit=100000)

        # get the field name back from the pretty field : meta string formed above
        x = xval.split(" :")[0]
        y = yval.split(" :")[0]

        if graph_val == "line":
            plot.line(x=x, y=y, color="firebrick", line_width=2, source=d.get_model_by_name(sind))
            plot.x_range.follow = "end"  # don't jam all the data into the graph; "window" it
            plot.x_range.follow_interval = 100
            plot.x_range.range_padding = 0
        if graph_val == "scatter":
            plot.cross(x=x, y=y, size=20, color="firebrick", line_width=2, source=d.get_model_by_name(sind))
        if graph_val == "step":
            plot.step(x=x, y=y, color="#FB8072", source=d.get_model_by_name(sind))

        d.add_root(plot)


def modify_doc(doc):
    """Render the initial webpage"""
    # Create Input controls
    topic_options = ["topic_{0}".format(x) for x in data.list_known_jsonschemas()]
    proto_options = ["protobuf_{0}".format(x) for x in data.list_known_protobufs()]
    modelselec = Select(title="Model Selection", value=DEFAULT_UNSELECTED, options=topic_options + proto_options + [DEFAULT_UNSELECTED], name=MODEL_SELECTION)

    # Add a handler for input changes
    modelselec.on_change('value', lambda attr, old, new: modelselec_change())

    # construct what the user will see
    selec = widgetbox([modelselec])

    doc.add_root(selec)

    doc.theme = Theme(filename="theme.yaml")

# Setting num_procs here means we can't touch the IOLoop before now, we must
# let Server handle that. If you need to explicitly handle IOLoops then you
# will need to use the lower level BaseServer class.

# warning!!! VERY HORRIBLE THINGS happen if you change num_procs > 1
# including:
#    source index being greater than the amount of available data
#   _host not being available in the image handler, despite the fact it should have been called waaaaay before when index handler is first called
#   I think tornado is doing weird things with the state of the other threads and it doesn't share the state with this current document
#    dont change this, at least not without understanding all this.


server = Server({'/bkapp': modify_doc},
                num_procs=1,  # see above!
                port = 5006,
                extra_patterns=[(
                    '/', IndexHandler),
                    ('/data', DataHandler),
                    ('/image/([^/]+)', ImageHandler),
                    ('/onap_topic_subscription/([^/]+)', ONAPMRTopicHandler)],
                address="0.0.0.0",
                allow_websocket_origin=["*:5006"])
server.start()

if __name__ == '__main__':
    server.io_loop.start()
