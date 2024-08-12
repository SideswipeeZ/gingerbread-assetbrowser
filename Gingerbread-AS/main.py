import os
import sys
import subprocess
import platform
import json
import re

from Qt import QtWidgets, QtCompat, QtGui, QtCore
from qt_material import apply_stylesheet

import QToaster


class QListWidget_Custom(QtWidgets.QListWidget):
    def __init__(self, parent=None):
        super(QListWidget_Custom, self).__init__(parent)

        self.setGeometry(QtCore.QRect(60, 110, 421, 191))
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.sizePolicy().hasHeightForWidth())
        self.setSizePolicy(sizePolicy)
        self.setStyleSheet(u"background-color: transparent;")
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.AdjustToContents)
        self.setProperty("showDropIndicator", False)
        self.setDragDropMode(QtWidgets.QAbstractItemView.NoDragDrop)
        self.setDefaultDropAction(QtCore.Qt.IgnoreAction)
        self.setSelectionMode(QtWidgets.QAbstractItemView.NoSelection)
        self.setVerticalScrollMode(QtWidgets.QAbstractItemView.ScrollPerPixel)
        self.setFlow(QtWidgets.QListView.LeftToRight)
        self.setProperty("isWrapping", True)
        self.setResizeMode(QtWidgets.QListView.Adjust)
        self.setSpacing(10)
        self.setGridSize(QtCore.QSize(205, 275))


class QLabel_clickable(QtWidgets.QLabel):
    clicked = QtCore.Signal(list)

    def __init__(self, parent=None, indx=None, sizeParm=None):
        super(QLabel_clickable, self).__init__(parent)
        self.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        if not sizeParm:
            size = (195, 265)
        else:
            size = (sizeParm[0], sizeParm[1])
        self.setMaximumWidth(size[0] + 20)
        self.setMaximumHeight(size[1] + 20)
        self.setMinimumSize(size[0], size[1])
        self.resize(size[0], size[1])

        self.setStyleSheet('QToolTip { color: #717171; background-color: #ffffff; border: 1px solid white; }')

        self.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed))

        self.indx = indx

        self.anim = QtCore.QPropertyAnimation(self, b'size')
        # self.anim.setEasingCurve(QtCore.QEasingCurve.InOutBack)
        self.anim.setDuration(150)

    def mousePressEvent(self, ev):
        self.clicked.emit([self.pixmap(), self.indx])

    def enterEvent(self, event):
        self.anim.setDirection(self.anim.Forward)
        if self.anim.state() == self.anim.State.Stopped:
            self.anim.setStartValue(self.size())
            self.anim.setEndValue(QtCore.QSize(195 + 20, 265 + 20))

            self.anim.start()

        QtWidgets.QLabel.enterEvent(self, event)

    def leaveEvent(self, event):
        self.anim.setDirection(self.anim.Backward)
        if self.anim.state() == self.anim.State.Stopped: self.anim.start()
        QtWidgets.QLabel.leaveEvent(self, event)


class BrowseApp(QtWidgets.QMainWindow):
    # Initialization
    def __init__(self, parent=None, **kwargs):
        super(BrowseApp, self).__init__(parent)
        # QtWidgets.QMainWindow.__init__(self, parent=parent)  # call the init for the parent class

        # Set Parent
        self.changeStyle(0)  # Light Pink
        self.parent = parent

        self.root_path = None

        if kwargs.get("app"):
            self.app = kwargs.get("app")
        else:
            self.app = "standalone"

        if kwargs.get("rootpath"):
            root_path = kwargs.get("rootpath")
            if os.path.exists(root_path):
                self.root_path = root_path
            else:
                raise Exception("Error: Supplied Root Path not found.")
        else:
            self.root_path = self.getRootPath()

        if not self.root_path:
            self.root_path = self.getRootPath()

        # UI
        ui_file = os.path.join(self.root_path, "Assets", "UI", "asset_browser.ui")

        # If UI not found it will stop the app execution.
        if not os.path.exists(ui_file):
            raise Exception("UI File Not found at: {ui_file}".format(ui_file=ui_file))

        self.mw = QtCompat.loadUi(ui_file)
        self.setCentralWidget(self.mw)

        # Init
        self.version = "0.0.1"
        self.setWindowTitle("Asset Explorer: {v}".format(v=self.version))
        self.ico = QtGui.QIcon(os.path.join(self.root_path, "Assets", "UI", "icon.png"))
        self.setWindowIcon(self.ico)
        self.resize(1280, 720)

        self.QToaster = QToaster.QToaster()

        self.mw.actionLogo.setIcon(self.ico)
        # Actions
        # group = QtWidgets.QActionGroup(self.mw.toolBar)
        group = QtWidgets.QActionGroup(self.mw.toolBar)
        group.addAction(self.mw.actionLibrary)
        group.addAction(self.mw.actionSettings)
        group.setExclusive(True)

        self.mw.toolBar.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)

        self.mw.actionLibrary.triggered.connect(lambda: self.changeIndx(1))
        self.mw.actionSettings.triggered.connect(lambda: self.changeIndx(2))

        self.profile_name = None
        self.currentItem = None

        # Load Settings
        self.loadSettings()

        if self.mw.chk_startup.isChecked():  # True
            self.loadItems(init=True)

        self.details_layout = QtWidgets.QVBoxLayout()
        self.lbl_img = QLabel_clickable(sizeParm=(250, 250))
        self.details_layout.addWidget(self.lbl_img)
        self.mw.frame_lbl.setLayout(self.details_layout)

        self.mw.listDir.itemDoubleClicked.connect(self.loadfromMenu)

        # Connect the context menu event to the custom slot
        self.mw.lw_content.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.mw.lw_content.customContextMenuRequested.connect(self.show_context_menu)

        self.mw.bttn_details_openDir.clicked.connect(self.openDirectory)
        self.mw.bttn_profile_load.clicked.connect(self.loadSettingParms)
        self.mw.bttn_lib_refresh.clicked.connect(lambda: self.loadItems(init=False, clearList=True))
        self.mw.bttn_save_profile.clicked.connect(self.saveSettings)
        self.mw.bttn_add_content.clicked.connect(self.add_folder)

        self.mw.bttn_details_add.clicked.connect(self.importItem)

        # Logic to handle icons if dcc
        if self.app != "standalone":
            self.mw.actionLibrary.setIcon(QtGui.QIcon(os.path.join(self.root_path, "Assets", "UI", "lib.png")))
            self.mw.actionSettings.setIcon(QtGui.QIcon(os.path.join(self.root_path, "Assets", "UI", "settings.png")))


        self.changeIndx(1)

        # Show UI
        self.show()

    # Load Settings
    def loadSettings(self):
        self.settings = {}
        file = os.path.join(self.getRootPath(), "profiles.json")
        if os.path.exists(file):
            with open(file, "r") as profileJson:
                rd = profileJson.read()
                json_data = json.loads(rd)

            profiles = json_data.get("Profile")
            for p in profiles:
                for key, value in p.items():
                    self.settings[key] = value

            self.populateSettings()
            self.loadSettingParms()
        else:
            self.consoleOut("Settings not found...")

    def populateSettings(self):
        self.mw.cmb_profiles_load.clear()
        self.mw.cmb_profiles_delete.clear()
        self.mw.lw_content.clear()

        for key, value in self.settings.items():
            self.name = key
            self.version = value["version"]
            self.contents = value["contents"]
            self.startup = value["startup"]

            if self.version >= 1.0:
                self.mw.cmb_profiles_load.addItem(self.name)
                self.mw.cmb_profiles_delete.addItem(self.name)
        self.profile_name = self.mw.cmb_profiles_load.currentText()
    def loadSettingParms(self):
        profile_name = self.mw.cmb_profiles_load.currentText()
        profile = self.settings.get(profile_name)

        if profile:
            # Parms Here
            self.name = profile_name  # Use profile_name directly
            self.version = profile["version"]
            self.contents = profile["contents"]
            self.startup = profile["startup"]

            # Clear qt widgets
            self.mw.lw_content.clear()

            # Populate qt widgets
            self.mw.chk_startup.setChecked(self.startup)
            self.mw.lw_content.addItems(self.contents)

            # Connect the changes to the save method
            self.mw.chk_startup.stateChanged.connect(self.updateCurrentProfileSettings)
            self.mw.lw_content.itemChanged.connect(self.updateCurrentProfileSettings)
        else:
            self.consoleOut(f"Profile '{profile_name}' not found in settings.")
        self.loadItems(init=True, clearList=True)

    def updateCurrentProfileSettings(self):
        self.profile_name = self.mw.cmb_profiles_load.currentText()

        # Update the settings based on the current UI state
        self.settings[self.profile_name] = {
            "Name": self.profile_name,
            "version": self.version,
            "contents": [self.mw.lw_content.item(i).text() for i in range(self.mw.lw_content.count())],
            "startup": self.mw.chk_startup.isChecked()
        }

    def saveSettings(self):
        self.updateCurrentProfileSettings()
        file = os.path.join(self.getRootPath(), "profiles.json")

        json_data = {
            "Profile": [{key: value} for key, value in self.settings.items()]
        }

        with open(file, "w") as profileJson:
            json.dump(json_data, profileJson, indent=4)

        self.consoleOut("Settings saved successfully.")

    def add_folder(self):
        # Open a folder selection dialog
        folder = QtWidgets.QFileDialog.getExistingDirectory(self, 'Select Folder to Add.')

        if folder:
            # Convert forward slashes to backslashes
            folder = folder.replace('/', '\\')
            # Add the folder path to the QListWidget
            self.mw.lw_content.addItem(folder)

    def show_context_menu(self, position):
        # Create the context menu
        context_menu = QtWidgets.QMenu(self)

        # Create the "Remove" action
        remove_action = QtWidgets.QAction('Remove', self)
        remove_action.triggered.connect(self.remove_selected_item)
        context_menu.addAction(remove_action)

        # Show the context menu at the mouse cursor position
        context_menu.exec_(self.mw.lw_content.viewport().mapToGlobal(position))

    def remove_selected_item(self):
        # Get the selected item
        selected_item = self.mw.lw_content.currentItem()

        # Remove the selected item if it exists
        if selected_item:
            self.mw.lw_content.takeItem(self.mw.lw_content.row(selected_item))

    def getRootPath(self):
        if self.app == "standalone":
            try:
                # Check for complied standalone
                if sys._MEIPASS:
                    return sys._MEIPASS
            except AttributeError:
                return os.getcwd()
        else:
            # Houdini Logic
            if self.app == "hou":
                import hou
                root = hou.getenv("echopr_assetBrowser_PATH")
                if not root:
                    raise Exception("Error: Houdini Path Not Found.")
                else:
                    return root

            # Maya Logic
            if self.app == "pymel":
                pass

            # Nuke Logic
            if self.app == "nuke":
                pass

    # import item into context if applicable.
    def importItem(self, **kwargs):
        itemDict = self.parseCurrentItem()

        if self.app == "standalone":
            pass

        if self.app == "hou":
            import hou
            OBJ = hou.node('/obj/')
            # Create Geometry node
            geometry = OBJ.createNode('geo', run_init_scripts=False)
            geometry.setName(f'{itemDict["name"]}', unique_name=True)
            geometry.moveToGoodPosition()

            # Create File Node
            filesop = geometry.createNode("file", run_init_scripts=True)
            filesop.parm("file").set(f"{itemDict['path']}")

            self.QToaster.showMessage(self, "Loaded Item in Houdini.", iconType="success", desktop=False,
                                      animated=True)

    def parseCurrentItem(self):
        item = self.currentItem
        parseDict = {}

        ext = self.mw.cmb_fileTypes.currentText()
        if not ext.startswith('.'):
            ext = '.' + ext
        base, _ = os.path.splitext(item[1])
        parseDict["path"] = base + ext

        name = os.path.splitext(os.path.basename(item[1]))[0]
        parseDict["name"] = self.sanitize_name(name)

        return parseDict

    def sanitize_name(self, name):
        # To allow only letters, numbers, and underscores; cannot start with a number
        sanitized_name = re.sub(r'[^a-zA-Z0-9_]', '_', name)
        if sanitized_name[0].isdigit():
            sanitized_name = 'n_' + sanitized_name

        return sanitized_name

    # Set Console Text
    def consoleOut(self, message):
        self.mw.frame_console.setText(str(message))

    # Change the Index of Main Page Content
    def changeIndx(self, indx):
        self.mw.stackedWidget_main.setCurrentIndex(indx)
        self.consoleOut("...")


    # Set Stylesheet colour in runtime.
    def changeStyle(self, indx):
        if indx == 0:
            theme = "light_pink.xml"
            apply_stylesheet(self, theme='light_pink.xml', invert_secondary=(
                    'light' in theme and 'dark' not in theme))
        elif indx == 1:
            apply_stylesheet(self, theme='dark_pink.xml')

    def reset_tb(self):
        tb_widget = self.mw.tb_dirs

    def getSettingsData(self, **kwargs):
        if kwargs.get("images"):
            return ["png", "jpg"]

        if kwargs.get("fileExt"):
            return ["obj", "fbx", "stl"]

        if kwargs.get("path"):
            return self.settings[self.profile_name]["contents"]

    def openDirectory(self):
        foldername = self.mw.le_details_dir.text()
        if foldername:
            plat = (platform.platform().split("-")[0]).lower()
            if plat == "windows":
                os.startfile(foldername)
            else:
                subprocess.Popen(['xdg-open', foldername])
        else:
            self.QToaster.showMessage(self, "Error: No Directory Is Loaded.", iconType="error", desktop=False,
                                      animated=True)

    def loadItems(self, **kwargs):
        path = self.getSettingsData(path=True)

        img_exts = self.getSettingsData(images=True)
        file_exts = self.getSettingsData(fileExt=True)

        dirs = None
        for p in path:
            dirs = [x[0] for x in os.walk(p)]
            del dirs[0]

        self.itemDict = {}
        self.mw.listDir.clear()

        if kwargs:
            if kwargs.get("clearList"):
                try:
                    self.listWidget.clear()
                except AttributeError:
                    self.QToaster.showMessage(self, "ListWidget Not Found.", iconType="alert",
                                              desktop=False,
                                              animated=True)

        if not dirs:
            # QToaster Error
            self.QToaster.showMessage(self, "Error: No Directory Found in Settings.", iconType="error", desktop=False,
                                      animated=True)
            return

        for i in dirs:
            citemDict = {}  # Temp Dict
            appendList = False
            # get image files in dir
            imgList = []
            for file in os.listdir(i):
                if os.path.isfile(os.path.join(i, file)):
                    if file.endswith(tuple(img_exts)):
                        imgList.append(os.path.join(i, file))

            # Check for File Exts
            if imgList:
                # Check for Exts in the directory
                for f in imgList:
                    name, ext = os.path.splitext(f)
                    extless_path = os.path.join(i, name)
                    found = []
                    for exts in file_exts:
                        search_path = extless_path + "." + exts
                        if os.path.isfile(search_path):
                            # update types found
                            found.append(exts)

                    if found:
                        citemDict[f] = found
                        appendList = True
                    else:
                        citemDict[f] = ""

            if appendList:
                # Add Basename to List Widget for Directories.
                self.mw.listDir.addItem(QtWidgets.QListWidgetItem(os.path.basename(i)))
                # self.mw.listDir.itemDoubleClicked.connect(self.loadfromMenu)
                # Add to Dict if in list above.
                self.itemDict[os.path.basename(i)] = citemDict

        if kwargs:
            if kwargs.get("init"):
                # Populate first dir with items
                # Check if Dict is empty.
                if bool(self.itemDict):
                    # self.mw.lbl_count.setText(str(len(self.itemDict)))
                    first_key = next(iter(self.itemDict))
                    self.createListWidget(first_key)

    def createListWidget(self, dkey):
        try:
            if self.listWidget:
                self.listWidget.clear()
        except AttributeError:
            self.listWidget = QListWidget_Custom()
            self.listWidget.setObjectName("listItems")
            layout = QtWidgets.QVBoxLayout()
            layout.addWidget(self.listWidget)
            self.mw.listFrame.setLayout(layout)

        # print(dkey)
        items = self.itemDict[dkey]  # This is another Dictionary
        for key in items.keys():
            value = items[key]
            # print(key, value)
            pixmap = self.roundedPixmap(QtGui.QPixmap(key), 5)

            label_item = QLabel_clickable()
            label_item.setPixmap(pixmap)
            label_item.indx = [dkey, key, value]
            label_item.setToolTip(os.path.splitext(os.path.basename(key))[0])
            label_item.clicked.connect(self.clickedLabel)

            itemN = QtWidgets.QListWidgetItem()
            widget = QtWidgets.QWidget()
            widgetLayout = QtWidgets.QVBoxLayout()
            widgetLayout.addWidget(label_item)
            widgetLayout.addStretch()

            widgetLayout.setSizeConstraint(QtWidgets.QLayout.SetFixedSize)
            widget.setLayout(widgetLayout)
            itemN.setSizeHint(widget.sizeHint())

            self.listWidget.addItem(itemN)
            self.listWidget.setItemWidget(itemN, widget)

        self.mw.lbl_count.setText(str(len(items)) + " Items(s)")

    def clickedLabel(self, event):
        # print(event)

        pixmap = event[0]
        self.lbl_img.setPixmap(self.roundedPixmap(
            pixmap.scaled(250, 250, QtCore.Qt.AspectRatioMode.KeepAspectRatio, QtCore.Qt.SmoothTransformation), 10,
            False))

        details = event[1]
        self.currentItem = details

        name = os.path.splitext(os.path.basename(details[1]))[0]
        self.mw.lbl_details_name.setText(str(name))

        file_types = details[2]
        if file_types:
            self.mw.cmb_fileTypes.clear()
            for ft in file_types:
                self.mw.cmb_fileTypes.addItem(ft.upper())

        base_directory = os.path.dirname(details[1])
        self.mw.le_details_dir.setText(base_directory)

    def loadfromMenu(self, item):
        self.createListWidget(item.text())

    def roundedPixmap(self, pixmap, corner, resize=True):
        # newPix = QtGui.QPixmap(QtCore.QSize(195, 265))
        size = QtCore.QSize(195, 265)
        if not resize:
            size = QtCore.QSize(250, 250)
        newPix = pixmap.scaled(size, QtCore.Qt.AspectRatioMode.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
        # create empty pixmap of same size as original
        radius = corner
        rounded = QtGui.QPixmap(newPix.size())
        rounded.fill(QtGui.QColor("transparent"))

        # draw rounded rect on new pixmap using original pixmap as brush
        painter = QtGui.QPainter(rounded)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.setBrush(QtGui.QBrush(newPix))
        painter.setPen(QtCore.Qt.NoPen)
        painter.drawRoundedRect(newPix.rect(), radius, radius)
        painter.end()
        return rounded


##########################
# //////////MAIN//////// #
##########################
if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    app.setStyle('Fusion')
    window = BrowseApp()
    sys.exit(app.exec_())
