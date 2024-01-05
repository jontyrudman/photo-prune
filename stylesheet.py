stylesheet = """
ImageViewer {
    background-color: #ffffff;
}

ImageViewer QGraphicsView {
    background-color: #ffffff;
}

ImageViewer QMenu {
    color: white;
    background-color: black;
    border: 1px solid #222;
}

ImageViewer QMenu::item {
    background-color: black;
    padding: 5px 10px;
}

ImageViewer QMenu::item::selected {
    background-color: #222;
}

ImageViewer QMenu::separator {
    height: 15px;
}

ImageViewer NoMoreImages QLabel {
    color: black;
}

ImageViewer Overlay QLabel {
    color: grey;
    font-weight: bold;
}
"""
