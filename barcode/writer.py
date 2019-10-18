import gzip
import os
import xml.dom

from barcode.version import version

try:
    import Image
    import ImageDraw
    import ImageFont

except ImportError:
    try:
        from PIL import Image, ImageDraw, ImageFont  # lint:ok

    except ImportError:
        import logging

        log = logging.getLogger("pyBarcode")
        log.info("Pillow not found. Image output disabled")
        Image = ImageDraw = ImageFont = None  # lint:ok


def mm2px(mm, dpi=300):
    return (mm * dpi) / 25.4


def pt2mm(pt):
    return pt * 0.352777778


def _set_attributes(element, **attributes):
    for key, value in attributes.items():
        element.setAttribute(key, value)


def create_svg_object():
    imp = xml.dom.getDOMImplementation()
    doctype = imp.createDocumentType(
        "svg",
        "-//W3C//DTD SVG 1.1//EN",
        "http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd",
    )
    document = imp.createDocument(None, "svg", doctype)
    _set_attributes(
        document.documentElement, version="1.1", xmlns="http://www.w3.org/2000/svg"
    )
    return document


SIZE = "{0:.3f}mm"
COMMENT = "Autogenerated with python-barcode {0}".format(version)
PATH = os.path.dirname(os.path.abspath(__file__))
FONT = os.path.join(PATH, "DejaVuSansMono.ttf")


class BaseWriter(object):
    """Baseclass for all writers.

    Initializes the basic writer options. Childclasses can add more
    attributes and can set them directly or using
    `self.set_options(option=value)`.

    :parameters:
        initialize : Function
            Callback for initializing the inheriting writer.
            Is called: `callback_initialize(raw_code)`
        paint_module : Function
            Callback for painting one barcode module.
            Is called: `callback_paint_module(xpos, ypos, width, color)`
        paint_text : Function
            Callback for painting the text under the barcode.
            Is called: `callback_paint_text(xpos, ypos)` using `self.text`
            as text.
        finish : Function
            Callback for doing something with the completely rendered
            output.
            Is called: `return callback_finish()` and must return the
            rendered output.
    """

    def __init__(
        self, initialize=None, paint_module=None, paint_text=None, finish=None
    ):
        self._callbacks = {
            "initialize": initialize,
            "paint_module": paint_module,
            "paint_text": paint_text,
            "finish": finish,
        }
        self.module_width = 10
        self.module_height = 10
        self.font_size = 10
        self.quiet_zone = 6.5
        self.background = "white"
        self.foreground = "black"
        self.write_text = True
        self.text = ""
        self.human = ""  # human readable text
        self.text_distance = 5
        self.text_line_distance = 1
        self.center_text = True
        self.supported_file_types = []
        self._file_type = None

    @property
    def file_type(self):
        return self._file_type

    @file_type.setter
    def file_type(self, file_type):
        if file_type in self.supported_file_types:
            self._file_type = file_type
        else:
            raise ValueError(
                f"file_type '{file_type}' not supported by {self.__class__.__name__}"
            )

    def calculate_size(self, modules_per_line, number_of_lines, dpi=300):
        """Calculates the size of the barcode in pixel.

        :parameters:
            modules_per_line : Integer
                Number of modules in one line.
            number_of_lines : Integer
                Number of lines of the barcode.
            dpi : Integer
                DPI to calculate.

        :returns: Width and height of the barcode in pixel.
        :rtype: Tuple
        """
        width = 2 * self.quiet_zone + modules_per_line * self.module_width
        height = 2.0 + self.module_height * number_of_lines
        number_of_text_lines = len(self.text.splitlines())
        if self.font_size and self.text:
            height += (
                pt2mm(self.font_size) / (2 * dpi / 200) * number_of_text_lines
                + self.text_distance
            )
            height += self.text_line_distance * (number_of_text_lines - 1)
        return int(mm2px(width, dpi)), int(mm2px(height, dpi))

    def save(self, filename, output):
        """Saves the rendered output to `filename`.

        :parameters:
            filename : String
                Filename without extension.
            output : String
                The rendered output.

        :returns: The full filename with extension.
        :rtype: String
        """
        raise NotImplementedError

    def register_callback(self, action, callback):
        """Register one of the three callbacks if not given at instance
        creation.

        :parameters:
            action : String
                One of 'initialize', 'paint_module', 'paint_text', 'finish'.
            callback : Function
                The callback function for the given action.
        """
        self._callbacks[action] = callback

    def set_options(self, options):
        """Sets the given options as instance attributes (only
        if they are known).

        :parameters:
            options : Dict
                All known instance attributes and more if the childclass
                has defined them before this call.

        :rtype: None
        """
        for key, val in options.items():
            key = key.lstrip("_")
            if hasattr(self, key):
                setattr(self, key, val)

    def render(self, code):
        """Renders the barcode to whatever the inheriting writer provides,
        using the registered callbacks.

        :parameters:
            code : List
                List of strings matching the writer spec
                (only contain 0 or 1).
        """
        if self._callbacks["initialize"] is not None:
            self._callbacks["initialize"](code)
        ypos = 1.0
        for cc, line in enumerate(code):
            """
            Pack line to list give better gfx result, otherwise in can
            result in aliasing gaps
            '11010111' -> [2, -1, 1, -1, 3]
            """
            line += " "
            c = 1
            mlist = []
            for i in range(0, len(line) - 1):
                if line[i] == line[i + 1]:
                    c += 1
                else:
                    if line[i] == "1":
                        mlist.append(c)
                    else:
                        mlist.append(-c)
                    c = 1
            # Left quiet zone is x startposition
            xpos = self.quiet_zone
            bxs = xpos  # x start of barcode
            for mod in mlist:
                if mod < 1:
                    color = self.background
                else:
                    color = self.foreground
                # remove painting for background colored tiles?
                self._callbacks["paint_module"](
                    xpos, ypos, self.module_width * abs(mod), color
                )
                xpos += self.module_width * abs(mod)
            bxe = xpos
            # Add right quiet zone to every line, except last line,
            # quiet zone already provided with background,
            # should it be removed complety?
            if (cc + 1) != len(code):
                self._callbacks["paint_module"](
                    xpos, ypos, self.quiet_zone, self.background
                )
            ypos += self.module_height
        if self.text and self._callbacks["paint_text"] is not None:
            ypos += self.text_distance
            if self.center_text:
                # better center position for text
                xpos = bxs + ((bxe - bxs) / 2.0)
            else:
                xpos = bxs
            self._callbacks["paint_text"](xpos, ypos)
        return self._callbacks["finish"]()


class SVGWriter(BaseWriter):
    def __init__(self):
        BaseWriter.__init__(
            self, self._init, self._create_module, self._create_text, self._finish
        )
        self.compress = False
        self.dpi = 25.4
        self._document = None
        self._root = None
        self._group = None
        self.supported_file_types = ["SVG"]
        self.file_type = "SVG"

    def _init(self, code):
        width, height = self.calculate_size(len(code[0]), len(code), self.dpi)
        self._document = create_svg_object()
        self._root = self._document.documentElement
        attributes = {"width": SIZE.format(width), "height": SIZE.format(height)}
        _set_attributes(self._root, **attributes)
        self._root.appendChild(self._document.createComment(COMMENT))
        # create group for easier handling in 3rd party software
        # like corel draw, inkscape, ...
        group = self._document.createElement("g")
        attributes = {"id": "barcode_group"}
        _set_attributes(group, **attributes)
        self._group = self._root.appendChild(group)
        background = self._document.createElement("rect")
        attributes = {
            "width": "100%",
            "height": "100%",
            "style": "fill:{0}".format(self.background),
        }
        _set_attributes(background, **attributes)
        self._group.appendChild(background)

    def _create_module(self, xpos, ypos, width, color):
        element = self._document.createElement("rect")
        attributes = {
            "x": SIZE.format(xpos),
            "y": SIZE.format(ypos),
            "width": SIZE.format(width),
            "height": SIZE.format(self.module_height),
            "style": "fill:{0};".format(color),
        }
        _set_attributes(element, **attributes)
        self._group.appendChild(element)

    def _create_text(self, xpos, ypos):
        # check option to override self.text with self.human (barcode as
        # human readable data, can be used to print own formats)
        if self.human != "":
            barcodetext = self.human
        else:
            barcodetext = self.text
        for subtext in barcodetext.split("\n"):
            element = self._document.createElement("text")
            attributes = {
                "x": SIZE.format(xpos),
                "y": SIZE.format(ypos),
                "style": "fill:{0};font-size:{1}pt;text-anchor:middle;".format(
                    self.foreground, self.font_size
                ),
            }
            _set_attributes(element, **attributes)
            text_element = self._document.createTextNode(subtext)
            element.appendChild(text_element)
            self._group.appendChild(element)
            ypos += pt2mm(self.font_size) + self.text_line_distance

    def _finish(self):
        if self.compress:
            return self._document.toxml(encoding="UTF-8")
        else:
            return self._document.toprettyxml(
                indent=4 * " ", newl=os.linesep, encoding="UTF-8"
            )

    def save(self, filename, output):
        if self.compress:
            _filename = "{0}.svgz".format(filename)
            f = gzip.open(_filename, "wb")
            f.write(output)
            f.close()
        else:
            _filename = "{0}.svg".format(filename)
            with open(_filename, "wb") as f:
                f.write(output)
        return _filename


if Image is None:
    ImageWriter = None
else:

    class ImageWriter(BaseWriter):
        def __init__(self, file_type="PNG"):
            BaseWriter.__init__(
                self, self._init, self._paint_module, self._paint_text, self._finish
            )
            self.dpi = 600
            self._image = None
            self._draw = None
            self.supported_file_types = [
                "PNG",
                "BMP",
                "GIF",
                "JPEG",
                "MSP",
                "PCX",
                "PNG",
                "TIFF",
                "XBM",
            ]
            self.file_type = file_type

        def _init(self, code):
            size = self.calculate_size(len(code[0]), len(code), self.dpi)
            self._image = Image.new("RGB", size, self.background)
            self._draw = ImageDraw.Draw(self._image)

        def _paint_module(self, xpos, ypos, width, color):
            size = [
                (mm2px(xpos, self.dpi), mm2px(ypos, self.dpi)),
                (
                    mm2px(xpos + width, self.dpi),
                    mm2px(ypos + self.module_height, self.dpi),
                ),
            ]
            self._draw.rectangle(size, outline=color, fill=color)

        def _paint_text(self, xpos, ypos):
            for subtext in self.text.split("\n"):
                font = ImageFont.truetype(FONT, self.font_size * 2)
                width, height = font.getsize(subtext)
                # determine the maximum width of each line
                pos = (
                    mm2px(xpos, self.dpi) - width // 2,
                    mm2px(ypos, self.dpi) - height // 4,
                )
                self._draw.text(pos, subtext, font=font, fill=self.foreground)
                ypos += pt2mm(self.font_size) / 2 + self.text_line_distance

        def _finish(self):
            return self._image

        def save(self, filename, output):
            filename = "{0}.{1}".format(filename, self.file_type.lower())
            output.save(filename, self.file_type.upper())
            return filename
