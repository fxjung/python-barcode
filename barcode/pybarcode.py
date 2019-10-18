import os
from argparse import ArgumentParser

import barcode
from barcode.version import version
from barcode.writer import ImageWriter, SVGWriter

# Optional PyQt4 GUI
try:
    from PyQt4 import QtCore
except ImportError:
    QtCore = None  # lint:ok

# No GUI available yet
QtCore = None
FILETYPES = ("SVG", "BMP", "GIF", "JPEG", "MSP", "PCX", "PNG", "TIFF", "XBM")


def open_gui(args, parser=None):
    pass


def list_types(args, parser=None):
    print("\npyBarcode available barcode filetypes:")
    print(", ".join(barcode.PROVIDED_BARCODES))
    print("\n")
    print("Available image filetypes")
    print("Standard: svg")
    if ImageWriter is not None:
        print("Pillow:", ", ".join(FILETYPES))
    else:
        print("Pillow: disabled")
    print("\n")


def create_barcode(args, parser):
    file_type = args.file_type.upper()
    if file_type != "SVG" and file_type not in FILETYPES:
        parser.error(
            f"Unknown type {file_type}. Try list action for available " "types."
        )

    args.barcode = args.barcode.lower()
    if args.barcode not in barcode.PROVIDED_BARCODES:
        parser.error(
            "Unknown barcode {bc}. Try list action for available "
            "barcodes.".format(bc=args.barcode)
        )
    writer_options = {}
    if file_type != "SVG":
        writer = ImageWriter(file_type=file_type)
    else:
        writer_options["compress"] = args.compress
        writer = SVGWriter()
    writer_options["font_size"] = args.font_size
    writer_options["text_distance"] = args.text_distance
    writer_options["module_height"] = args.module_height

    out = os.path.normpath(os.path.abspath(args.output))

    name = barcode.generate(
        name=args.barcode,
        code=args.code,
        writer=writer,
        output=out,
        writer_options=writer_options,
        text=args.text,
    )

    print("New barcode saved as {0}.".format(name))


def main():
    msg = []
    if ImageWriter is None:
        msg.append("Image output disabled (Pillow not found), --type option disabled.")
    else:
        msg.append(
            "Image output enabled, use --file_type option to give image "
            "file type (png, jpeg, ...)."
        )
    if QtCore is None:
        msg.append("PyQt not found, gui action disabled.")
    else:
        msg.append("PyQt found. Use gui action to get a simple GUI.")

    parser = ArgumentParser(
        description="Create standard barcodes via cli.", epilog=" ".join(msg)
    )

    parser.add_argument(
        "-v", "--version", action="version", version="%(prog)s " + version
    )

    subparsers = parser.add_subparsers(title="Actions")
    create_parser = subparsers.add_parser(
        "create", help="Create a barcode " "with the given options."
    )
    create_parser.add_argument("code", help="Code to render as barcode.")
    create_parser.add_argument(
        "output", help="Filename for output " "without extension, e. g. mybarcode."
    )
    create_parser.add_argument(
        "-c",
        "--compress",
        action="store_true",
        help="Compress output, only recognized if file type is svg.",
    )
    create_parser.add_argument(
        "-b", "--barcode", help="Barcode to use " "[default: %(default)s]."
    )
    create_parser.add_argument(
        "--text", help="Non-standard text to show under the " "barcode."
    )
    create_parser.add_argument(
        "--font_size",
        help="Size of the text beneath the barcode.",
        type=int,
        default=10,
    )
    create_parser.add_argument(
        "--text_distance",
        help="Padding between module and text.",
        type=float,
        default=5.0,
    )
    create_parser.add_argument(
        "--module_height",
        help="Height of the barcode module.",
        type=float,
        default=15.0,
    )

    if ImageWriter is not None:
        create_parser.add_argument(
            "-t", "--file_type", help="File type of output " "[default: %(default)s]."
        )

    list_parser = subparsers.add_parser(
        "list", help="List available " "image and code types."
    )
    list_parser.set_defaults(func=list_types)
    if QtCore is not None:
        gui_parser = subparsers.add_parser(
            "gui", help="Opens a simple " "PyQt GUI to create barcodes."
        )
        gui_parser.set_defaults(func=open_gui)
    create_parser.set_defaults(
        file_type="svg",
        compress=False,
        func=create_barcode,
        barcode="code39",
        text=None,
    )

    args = parser.parse_args()

    try:
        func = args.func
    except AttributeError:
        parser.error("You need to tell me what to do.")
    else:
        func(args, parser)


if __name__ == "__main__":
    main()
