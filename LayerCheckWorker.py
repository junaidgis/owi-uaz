from qgis.core import QgsField
from qgis.core import QgsUnitTypes, QgsDistanceArea
from PyQt5.QtCore import QVariant, Qt
from PyQt5.QtWidgets import QTableWidgetItem, QLabel
from PyQt5.QtGui import QPixmap, QImage
import os

class LayerChecker:
    def __init__(self, checked_items:dict, progress_bar, layer, dlg):
        self.checked_items = checked_items
        self.progress_bar = progress_bar
        self.layer = layer
        self.dlg = dlg

    def checkLayerPolygon(self):
        return True if self.layer.geometryType() == 2 else False

    def checkLayerProjected(self):
        return False if self.layer.sourceCrs().isGeographic() else True

    def updateProgress(self):
        self.progress_bar.setValue(self.progress_bar.value() + 1)

    def checkAreaExists(self):
        return True if 'area' in [x.name().lower() for x in self.layer.fields()] else False

    def populateAreaAttribute(self):
        self.layer.startEditing()
        for feature in self.layer.getFeatures():
            area = QgsDistanceArea()
            m = area.measureArea(feature.geometry())/1000000
            # m = area.convertAreaMeasurement(m, QgsUnitTypes.AreaSquareKilometers)
            m = round(m, 5)
            feature['area'] = str(m)
            self.layer.updateFeature(feature)
        self.layer.commitChanges()

    def createAreaAttribute(self):
        self.layer.startEditing()
        field = QgsField('area', QVariant.String)
        self.layer.dataProvider().addAttributes([field])
        self.layer.commitChanges()
        self.layer.updateFields()

    def set_check_text(self, check):
        self.dlg.label_2.setText("Processing Check : \"%s\"" % check)

    def return_img_path(self, path: str):
        icon = QPixmap()
        icon.load(path)
        label = QLabel()
        label.setAlignment(Qt.AlignCenter)
        label.setPixmap(icon)
        label.setStyleSheet("background-color: #CECECE;")
        return label

    def set_result_tb(self, index: int, passed: bool, text: str):
        if passed:
            text = 'Condition Satisfied'
            path = os.path.join(os.path.dirname(__file__), 'icons', 'true.png')
            label = self.return_img_path(path)
            widget = QTableWidgetItem(text)
        else:
            path = os.path.join(os.path.dirname(__file__), 'icons', 'false.png')
            label = self.return_img_path(path)
            label.setStyleSheet("background-color: #CECECE;")

            widget = QTableWidgetItem(text)
        self.dlg.listWidget.setCellWidget(index, 1, label)
        self.dlg.listWidget.setItem(index, 2, widget)

    def run(self):
        for index, check in self.checked_items.items():
            if index == 1:
                self.set_check_text(check)
                if not self.checkLayerPolygon():
                    print('here')
                    passed = False
                else:
                    passed = True
                self.set_result_tb(index, passed, 'This is not polygon layer. Skipping further checks')
                if passed == False:
                    break
                self.updateProgress()
            elif index == 2:
                self.set_check_text(check)
                if not self.checkLayerProjected():
                    passed = False
                else:
                    passed = True
                self.set_result_tb(index, passed, 'Layer does not have projected coordinate system. Kindly transform the layer into projected coordinate systems.')
                self.updateProgress()
            elif index == 3:
                self.set_check_text(check)
                self.set_result_tb(index, False, 'There are sliver polygons in the data. Kindly use the topology checker from "Vector" menu to identify and fix sliver polygons.')
                self.updateProgress()
            elif index == 4:
                self.set_check_text(check)
                self.set_result_tb(index, False,'There are ovelapping polygons in the data. Kindly use the topology checker from "Vector" menu to identify and fix overlapping polygons.')
                self.updateProgress()
            elif index == 5:
                self.set_check_text(check)
                self.set_result_tb(index, False, 'There are empty polygons in the data. Kindly use the topology checker from "Vector" menu to identify and fix empty polygons.')
                self.updateProgress()
            elif index == 7:
                self.set_check_text(check)
                if not self.checkAreaExists():
                    self.createAreaAttribute()
                    self.populateAreaAttribute()
                    passed = False
                else:
                    passed = True
                self.set_result_tb(index, passed, 'Area field was missing in the data, it is now added and populated with area values in square kilometers.')
                self.updateProgress()
        self.dlg.label_2.setText("Processing Complete")
        return

