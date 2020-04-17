# -*- coding: utf-8 -*-
"""
/***************************************************************************
 UAZ
                                 A QGIS plugin
 This plugin will be used to prepare UAZ file for feeding into OWI 
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                              -------------------
        begin                : 2019-04-10
        git sha              : $Format:%H$
        copyright            : (C) 2019 by Junaid Abdul Jabbar
        email                : junaid.abdul.jabbar@gmail.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
from PyQt5.QtCore import QSettings, QTranslator, qVersion, QCoreApplication, Qt
from PyQt5.QtGui import QIcon, QColor, QPixmap, QImage
from PyQt5.QtWidgets import QAction, QMessageBox, QGraphicsScene, QGraphicsPixmapItem, QFileDialog
from shutil import copyfile

# Initialize Qt resources from file resources.py
from .resources import *
from .style_rc import *
# Import the code for the dialog
from .UAZ_dialog import UAZDialog, SitDialog, SelDialog, LCDialog
import os.path
from qgis.core import *
from qgis.gui import *
from . import configuration as conf
from .worker import Worker
from PyQt5.QtWidgets import QCheckBox, QHeaderView, QComboBox, QPushButton
import random
import numpy as np
import matplotlib.pyplot as plt
from .LayerCheckWorker import LayerChecker

class UAZ:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'UAZ_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&UAZ Preparation')

        # Check if plugin was started the first time in current QGIS session
        # Must be set in initGui() to survive plugin reloads
        self.first_start = None

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('UAZ', message)

    def add_action(
            self,
            icon_path,
            text,
            callback,
            enabled_flag=True,
            add_to_menu=True,
            add_to_toolbar=True,
            status_tip=None,
            whats_this=None,
            parent=None):
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            # Adds plugin icon to Plugins toolbar
            self.iface.addToolBarIcon(action)

        if add_to_menu:
            self.iface.addPluginToMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/UAZ/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'UAZ Preparation'),
            callback=self.run,
            parent=self.iface.mainWindow())

        # will be set False in run()
        self.first_start = True

    def remove_connections(self):
        if self.first_start:
            return
        try:
            self.dlg_3.pushButton.clicked.disconnect()
            self.dlg_2.mMapLayerComboBox.layerChanged.disconnect()
            self.populate_layer_attributes()
            self.dlg_2.pushButton_2.clicked.disconnect()

            self.dlg.pushButton.clicked.disconnect()
            self.dlg.pushButton_10.clicked.disconnect()
            self.dlg.pushButton_14.clicked.disconnect()
            self.dlg.pushButton_3.clicked.disconnect()
            self.dlg.pushButton_12.clicked.disconnect()
            self.dlg.pushButton_15.clicked.disconnect()
        except:
            pass

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&UAZ Preparation'),
                action)
            self.iface.removeToolBarIcon(action)
        self.remove_connections()

    def addFactors(self, table_widget, labels_list, source='proximity'):
        """add new rows"""
        index_to_add = table_widget.rowCount()
        table_widget.setRowCount(index_to_add + 1)
        widget = self._insertLayerComboBox(index_to_add, source, table_widget)
        widget.setFilters(QgsMapLayerProxyModel.VectorLayer)
        widget.setShowCrs(True)
        table_widget.setCellWidget(index_to_add, labels_list.index('Shapefile'), widget)
        table_widget.setCellWidget(index_to_add, labels_list.index(''), QCheckBox(''))
        table_widget.resizeRowsToContents()
        if source != 'proximity':
            self.policy_source_populate(table_widget)


    def msgBox(self, msg: str):
        msgB = QMessageBox()
        msgB.setText(msg)
        msgB.setWindowTitle('Information!')
        msgB.show()
        msgB.exec_()

    def policy_layer_changed(self, row, tableWidget):

        fields = self.fetch_layer_fields(row, tableWidget)
        comb_box = tableWidget.cellWidget(row, conf.policy_factor_labels.index('Source Field'))
        try:
            comb_box.clear()
            if fields:
                comb_box.addItems(fields)
        except:
            pass

    def _insertLayerComboBox(self, row, source, table_widget):
        widget = QgsMapLayerComboBox()
        rand_gen = lambda: random.randint(0, 1000)
        widget.setObjectName('m_{0}_{1}_layercombox'.format(row, rand_gen()))
        if source != 'proximity':
            widget.layerChanged.connect(lambda : self.policy_layer_changed(row, table_widget))
        return widget

    def checkFieldExists(self, layer, field_to_check):
        layer = self.dlg.mMapLayerComboBox.currentLayer() if self.dlg.mMapLayerComboBox.currentLayer() else None
        return any([True for field in layer.fields() if field.name().lower() == field_to_check.lower()])

    def provideParameters(self, row):
        name = self.dlg.tableWidget.item(row, conf.labels.index('Name'))
        name = name.text() if name else None
        interval_value = self.dlg.tableWidget.item(row, conf.labels.index('Interval Value'))
        interval_value = interval_value.text() if interval_value else None
        Num_Intervals = self.dlg.tableWidget.item(row, conf.labels.index('No. Of Intervals'))
        Num_Intervals = Num_Intervals.text() if Num_Intervals else None
        result_fields = self.dlg.tableWidget.item(row, conf.labels.index('Result field'))
        result_fields = result_fields.text() if result_fields else None
        layer = self.dlg.tableWidget.cellWidget(row, conf.labels.index('Shapefile'))
        layer = layer.currentLayer() if layer else None
        return (name, interval_value, Num_Intervals, result_fields, layer)

    def checkFieldSelected(self, row):
        tableWIdget = self.dlg.tableWidget
        checkbox = tableWIdget.cellWidget(row, conf.labels.index(''))
        return checkbox.isChecked()

    def checkProxFctValidParam(self):
        tableWIdget = self.dlg.tableWidget
        attr_errors_in_row = []
        attr_field_exists = []
        layers_not_provided = []
        name_not_provided = []
        interval_not_provided = []
        interval_value_not_vld = []
        num_interval_not_provided = []
        num_interval_not_vld = []
        for num in range(tableWIdget.rowCount()):
            # CHeck for valid parameters
            if not self.checkFieldSelected(num):
                continue

            item = tableWIdget.item(num, conf.labels.index('Result field'))
            field_name = item.text() if item else None
            if not field_name or len(field_name) > 12:
                attr_errors_in_row.append(str(num + 1))
            layer = tableWIdget.cellWidget(num, conf.labels.index('Shapefile'))
            layer = layer.currentLayer() if layer else None
            if not layer:
                layers_not_provided.append(str(num + 1))
            else:
                if self.checkFieldExists(layer, field_name):
                    attr_field_exists.append(str(num + 1))

            name, interval_value, Num_Intervals, result_fields, layer = self.provideParameters(num)
            if not name:
                name_not_provided.append(str(num + 1))
            if not interval_value:
                interval_not_provided.append(str(num + 1))
            try:
                interval_value = float(interval_value)
            except:
                interval_value_not_vld.append(str(num + 1))
            # if not (isinstance(interval_value, int) and isinstance(interval_value, float)):
            #     interval_value_not_vld.append(str(num + 1))
            if not Num_Intervals:
                num_interval_not_provided.append(str(num + 1))
            try:
                Num_Intervals = float(Num_Intervals)
            except:
                num_interval_not_vld.append(str(num + 1))
            # if not (isinstance(Num_Intervals, int) or isinstance(Num_Intervals, float)):
            #     num_interval_not_vld.append(str(num + 1))

        if name_not_provided:
            self.msgBox(
                'Provide name(s) in following rows.\n{0}'.format(
                    '\n'.join(name_not_provided)))
            return False
        if interval_not_provided:
            self.msgBox(
                'Provide interval(s) in following rows.\n{0}'.format(
                    '\n'.join(interval_not_provided)))
            return False
        if interval_value_not_vld:
            self.msgBox(
                'Provide valid interval(s) in following rows.\n{0}'.format(
                    '\n'.join(interval_value_not_vld)))
            return False
        if num_interval_not_provided:
            self.msgBox(
                'Provide number of intervals in following rows.\n{0}'.format(
                    '\n'.join(num_interval_not_provided)))
            return False
        if num_interval_not_vld:
            self.msgBox(
                'Provide valid number of intervals in following rows.\n{0}'.format(
                    '\n'.join(num_interval_not_vld)))
            return False
        if attr_errors_in_row:
            self.msgBox(
                'Result Field should not be empty and less than 12 character.\nError in following rows.\n{0}'.format(
                    '\n'.join(attr_errors_in_row)))
            return False
        if layers_not_provided:
            self.msgBox(
                'Provide layers for the following rows.\n{0}'.format(
                    '\n'.join(layers_not_provided)))
            return False
        if attr_field_exists:
            self.msgBox(
                'Provide a field name that does not exist for the following rows.\n{0}'.format(
                    '\n'.join(attr_field_exists)))
            return False
        return True

    def startProcessingProxFct(self):
        if not self.checkProxFctValidParam():
            return
        parcel_layer = self.dlg.mMapLayerComboBox.currentLayer() if self.dlg.mMapLayerComboBox.currentLayer() else None
        progress_bar = self.dlg.progressBar_3
        progress_bar.reset()
        progress_bar.setMinimum(0)
        progress_bar.setMaximum(self.dlg.tableWidget.rowCount())
        for row in range(self.dlg.tableWidget.rowCount()):
            progress_bar.setValue(row + 1)
            if not self.checkFieldSelected(row):
                continue
            name, interval_value, Num_Intervals, result_fields, layer = self.provideParameters(row)
            iter_worker = Worker(layer, result_fields, parcel_layer, float(interval_value), int(Num_Intervals))
            iter_worker.populate_buff()


    def adjustTableWidget(self, tableWIdget):
        header = tableWIdget.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        tableWIdget.resizeColumnsToContents()
        # for num in range(1, tableWIdget.columnCount()):
        #     header.setSectionResizeMode(num, QHeaderView.Stretch)

    def prePopulateProximityTablwWidget(self):
        tableWIdget = self.dlg.tableWidget
        for num, factor in enumerate(conf.proximity_factors):
            self.addFactors(tableWIdget, conf.labels)
            tableWIdget.setItem(num, conf.labels.index('Name'), QgsTableWidgetItem(factor))
        self.adjustTableWidget(tableWIdget)

    def pre_populate_policy_table(self):
        tableWIdget = self.dlg.tableWidget_4
        for num, factor in enumerate(conf.policy_factors):
            self.addFactors(tableWIdget, conf.policy_factor_labels, 'policy')
            tableWIdget.setItem(num, conf.policy_factor_labels.index('Name'), QgsTableWidgetItem(factor))
        # self.policy_source_populate(tableWIdget)
        self.adjustTableWidget(tableWIdget)

    def pre_populate_composite_table(self):

        tableWIdget = self.dlg.tableWidget_5
        for num, factor in enumerate(conf.composite_factors):
            self.addFactors(tableWIdget, conf.policy_factor_labels, 'composite')
            tableWIdget.setItem(num, conf.policy_factor_labels.index('Name'), QgsTableWidgetItem(factor))
        # self.policy_source_populate(tableWIdget)
        self.adjustTableWidget(tableWIdget)

    def _combobox_cellwidget(self, row):
        """Creates a combobox widget"""
        widget = QComboBox()
        rand_gen = lambda: random.randint(0, 1000)
        widget.setObjectName('m_{0}_{1}_combox'.format(row, rand_gen()))
        return widget

    def fetch_layer_fields(self, row, tableWIdget):
        layer = tableWIdget.cellWidget(row, conf.policy_factor_labels.index('Shapefile'))
        layer = layer.currentLayer() if layer else None
        if not layer:
            return
        fields = layer.fields().names()
        return fields

    def policy_source_populate(self, tableWIdget):
        """The policy factor source fields are populated here"""
        row_number = tableWIdget.rowCount()
        for row in range(row_number):
            widget = tableWIdget.cellWidget(row, conf.policy_factor_labels.index('Source Field'))
            if isinstance(widget, QComboBox):
                continue
            comb_widget = self._combobox_cellwidget(row)
            fields = self.fetch_layer_fields(row, tableWIdget)
            if fields:
                comb_widget.addItems(fields)
            tableWIdget.setCellWidget(row, conf.policy_factor_labels.index('Source Field'), comb_widget)

    def intersection_join(self, tableWIdget, progress_bar, map_combox):

        progress_bar.reset()
        row_number = tableWIdget.rowCount()

        source_layer = map_combox.currentLayer() if map_combox.currentLayer() else None
        if not source_layer:
            self.msgBox('No Layer Selected!')
            return
        checked_list = [tableWIdget.cellWidget(row, conf.policy_factor_labels.index('')).isChecked() for row in range(row_number)]
        if not any(checked_list):
            self.msgBox('No check boxes selected!')
            return
        progress_bar.setMinimum(0)
        progress_bar.setMaximum(row_number)
        progress_bar.setValue(1)
        for row in range(row_number):
            check_state = tableWIdget.cellWidget(row, conf.policy_factor_labels.index(''))
            if check_state.isChecked():
                source_layer.startEditing()

                target_layer_widget = tableWIdget.cellWidget(row, conf.policy_factor_labels.index('Shapefile'))
                target_layer = target_layer_widget.currentLayer()
                source_field_widget = tableWIdget.cellWidget(row, conf.policy_factor_labels.index('Source Field'))
                source_field = source_field_widget.currentText()
                pr = source_layer.dataProvider()
                target_layer_fields = [field for field in target_layer.fields()]
                source_field_index = target_layer.fields().indexFromName(source_field)
                source_field_type = target_layer_fields[source_field_index].type()
                target_field_name = tableWIdget.item(row, conf.policy_factor_labels.index('Result Field')).text() if tableWIdget.item(row,
                                                                conf.policy_factor_labels.index('Result Field')).text() else None
                if not target_field_name:
                    self.msgBox('The Result Field cannot be empty!')
                    return
                if target_field_name in [field.name() for field in source_layer.fields()]:
                    self.msgBox('This field already exists!')
                    return
                pr.addAttributes([QgsField(target_field_name, source_field_type)])
                source_layer.updateFields()
                source_layer_features = source_layer.getFeatures()
                intersection_ids = []
                for sfeature in source_layer_features:
                    sgeom = sfeature.geometry()
                    target_layer_features = target_layer.getFeatures()
                    for tfeature in target_layer_features:
                        tgeom = tfeature.geometry()
                        if sgeom.intersects(tgeom):
                            sfeature[target_field_name] = tfeature[source_field]
                            source_layer.updateFeature(sfeature)
                            intersection_ids.append(sfeature.id())
                # for sfeature in source_layer.getFeatures():
                #     feat_id = sfeature.id()
                #     if feat_id not in intersection_ids:
                #         source_layer.deleteFeature(feat_id)
                source_layer.commitChanges()
            progress_bar.setValue(row+1)
        source_layer.triggerRepaint()
        QgsProject.instance().addMapLayer(source_layer)

    def populate_layer_attributes(self):
        """The situational analysis layer attributes are populated from here"""
        layer = self.dlg_2.mMapLayerComboBox.currentLayer() if self.dlg_2.mMapLayerComboBox.currentLayer() else None
        if not layer or isinstance(layer, QgsRasterLayer):
            return
        fields = layer.fields().names()
        self.dlg_2.comboBox.clear()
        self.dlg_2.comboBox.addItems(fields)

    def render_chart(self, unique_values, count_list, attribute_name):
        show_sum = self.dlg_2.radioButton.isChecked()
        fig, ax = plt.subplots(figsize=(6, 3), subplot_kw=dict(aspect="equal"))
        total_count = sum(count_list)
        if show_sum:
            unique_values = [str(round(count_list[index], 5)) + 'km2 ' + str(val) for index, val in enumerate(unique_values)]
        else:
            unique_values = [str(round(count_list[index] / total_count * 100, 2)) + '% ' + str(val) for index, val in
                             enumerate(unique_values)]

        def func(pct, allvals):
            absolute = int(pct / 100. * np.sum(allvals))
            return ''


        wedges, texts, autotexts = ax.pie(count_list, autopct=lambda pct: func(pct, count_list),
                                          textprops=dict(color="w"))

        ax.legend(wedges, unique_values,
                  title=attribute_name,
                  loc="center left",
                  bbox_to_anchor=(1, 0, 0.5, 1))

        ax.set_title("Value Percentage")
        plt.savefig(self.plugin_dir + "/pie_chart.png", bbox_inches='tight', pad_inches=0)
        pie_chart = QImage(self.plugin_dir+"/pie_chart.png")
        scene = QGraphicsScene()
        self.dlg_2.graphicsView.setScene(scene)
        graphics_item = QGraphicsPixmapItem(QPixmap().fromImage(pie_chart))
        scene.addItem(graphics_item)
        self.dlg_2.graphicsView.show()

    def layer_colorize(self, vlayer, unique_values, attribute_name):
        symbol = QgsSymbol.defaultSymbol(vlayer.geometryType())
        renderer = QgsRuleBasedRenderer(symbol)
        hex_gen = lambda: random.randint(0, 255)
        root_rule = renderer.rootRule()
        for val in unique_values:
            if not val:
                val = 'NULL'
            color = '#{:02x}{:02x}{:02x}'.format(hex_gen(), hex_gen(), hex_gen())

            rule = root_rule.children()[0].clone()
            rule.setLabel(str(val))
            rule.setFilterExpression(f'"{attribute_name}" = ' + f"'{val}'")
            rule.symbol().setColor(QColor(color))
            root_rule.appendChild(rule)
        root_rule.removeChildAt(0)
        vlayer.setRenderer(renderer)
        vlayer.triggerRepaint()

    def fetch_unique_values(self, layer, attribute_name):
        features = layer.getFeatures()
        attr_dict = {}
        area = QgsDistanceArea()
        for feat in features:
            m = area.measureArea(feat.geometry())/1000000
            # m = area.convertAreaMeasurement(m, QgsUnitTypes.AreaSquareKilometers)
            if feat[attribute_name] in attr_dict.keys():
                attr_dict[feat[attribute_name]] = attr_dict[feat[attribute_name]] + m
            else:
                attr_dict[feat[attribute_name]] = m
        QgsMessageLog.logMessage(str(attr_dict))

        unique_values = [x if x else 'null' for x in list(attr_dict.keys())]
        values_count = list(attr_dict.values())
        return unique_values, values_count

    def set_attribution_classifier_progress(self, value):
        self.dlg_2.progressBar.setValue(value)

    def attribute_classifier(self):
        layer = self.dlg_2.mMapLayerComboBox.currentLayer() if self.dlg_2.mMapLayerComboBox.currentLayer() else None
        if not layer:
            self.msgBox('No layer selected!')
            return
        self.set_attribution_classifier_progress(0)
        attribute_name = self.dlg_2.comboBox.currentText()
        QCoreApplication.processEvents()
        unique_values, values_count_list = self.fetch_unique_values(layer, attribute_name)
        QCoreApplication.processEvents()
        self.set_attribution_classifier_progress(1)
        QCoreApplication.processEvents()
        self.layer_colorize(layer, unique_values, attribute_name)
        QCoreApplication.processEvents()
        self.set_attribution_classifier_progress(2)
        QCoreApplication.processEvents()
        self.render_chart(unique_values, values_count_list, attribute_name)
        QCoreApplication.processEvents()
        self.set_attribution_classifier_progress(3)
        QCoreApplication.processEvents()
        self.dlg_2.pushButton.setEnabled(True)

    # def mode_selection(self):
    #     if self.dlg_3.radioButton.isChecked() and self.dlg_3.radioButton_2.isChecked():
    #         self.msgBox('Only one selection is allowed at a time!')
    #         return
    #     if self.dlg_3.radioButton.isChecked():
    #         self.dlg_3.hide()
    #         self.dlg.show()
    #     elif self.dlg_3.radioButton_2.isChecked():
    #         self.dlg_3.hide()
    #         self.dlg_2.show()

    def resetDialog(self):
        widget = self.dlg_4.listWidget
        from PyQt5.QtWidgets import QTableWidget
        for num in widget.rowCount():
            widget.setItem(num, 2, QTableWidget(''))
            widget.setItem(num, 1, QTableWidget(''))
        widget .resizeColumnsToContents()

    def openDIalog(self, dlg):
        self.dlg_3.hide()
        if dlg == self.dlg_4:
            self.dlg_4.listWidget.resizeColumnsToContents()
            self.dlg_4.label_2.setText(conf.ready_text)

        dlg.show()

    def startChecking(self):
        dlg = self.dlg_4
        layer = dlg.mMapLayerComboBox.currentLayer()
        progress_bar = dlg.progressBar_3
        progress_bar.reset()
        if not layer:
            self.msgBox('Provide a vector layer')
            return
        checked_items = {}
        for num in range(dlg.listWidget.rowCount()):
            if num in (0, 6):
                continue
            item = dlg.listWidget.item(num, 0)
            if item.checkState() == Qt.Checked:
                checked_items[num] = item.text()
        if not checked_items:
            self.msgBox('Provide checks to run')
            return
        progress_bar.setMinimum(0)
        progress_bar.setMaximum(len(checked_items))
        worker = LayerChecker(checked_items, progress_bar, layer, dlg)
        output = worker.run()
        progress_bar.setValue(progress_bar.maximum())
        # if output:
        #     output_str = 'Results:\n\n\n'
        #     for num, item in enumerate(output):
        #         output_str += '{0}- {1}.\n'.format(num, item)
        #     self.msgBox(output_str)

    def exportChart(self):
        path = QFileDialog().getSaveFileName(self.dlg_2, None, None, 'Images (*.png)')[0]
        if not path:
            return

        copyfile(self.plugin_dir + os.sep + 'pie_chart.png', path)
        self.msgBox('Exported!!')

    def run(self):
        """Run method that performs all the real work"""

        # Create the dialog with elements (after translation) and keep reference
        # Only create GUI ONCE in callback, so that it will only load when the plugin is started
        if self.first_start == True:
            self.first_start = False
            self.dlg = UAZDialog()
            self.dlg_2 = SitDialog()
            self.dlg_3 = SelDialog()
            self.dlg_4 = LCDialog()
            self.dlg.setWindowIcon(QIcon(self.plugin_dir + os.sep + 'icon.png'))
            self.dlg_2.setWindowIcon(QIcon(self.plugin_dir + os.sep + 'icon.png'))
            self.dlg_3.setWindowIcon(QIcon(self.plugin_dir + os.sep + 'icon.png'))
            self.dlg_4.setWindowIcon(QIcon(self.plugin_dir + os.sep + 'icon.png'))
            self.dlg.setWindowTitle('UAZ Preparation')
            self.dlg_2.setWindowTitle('Situational Analysis')
            self.dlg_3.setWindowTitle('UAZ Preparation Tool')
            self.dlg_4.setWindowTitle('Layer Checking')

            self.dlg_4.checkPushButton.clicked.connect(self.startChecking)

            self.dlg_3.pushButton.clicked.connect(lambda: self.dlg_3.close())
            self.dlg_3.sitPushButton.clicked.connect(lambda: self.openDIalog(self.dlg_2))
            self.dlg_3.sitPushButton.setIcon(QIcon(self.plugin_dir + os.sep + 'icons' + os.sep + 'analysis.png'))

            self.dlg_3.uazPushButton.clicked.connect(lambda: self.openDIalog(self.dlg))
            self.dlg_3.uazPushButton.setIcon(QIcon(self.plugin_dir + os.sep + 'icons' + os.sep + 'qa.png'))

            self.dlg_3.layerPushButton.clicked.connect(lambda: self.openDIalog(self.dlg_4))
            self.dlg_3.layerPushButton.setIcon(QIcon(self.plugin_dir + os.sep + 'icons' + os.sep + 'task-list.png'))



            self.dlg_2.mMapLayerComboBox.setFilters(QgsMapLayerProxyModel.VectorLayer)
            self.dlg_2.mMapLayerComboBox.layerChanged.connect(self.populate_layer_attributes)
            self.populate_layer_attributes()
            self.dlg_2.pushButton_2.clicked.connect(self.attribute_classifier)
            self.dlg_2.pushButton.clicked.connect(self.exportChart)

            self.dlg.pushButton.clicked.connect(lambda: self.addFactors(self.dlg.tableWidget, conf.labels))
            self.dlg.pushButton_10.clicked.connect(lambda: self.addFactors(self.dlg.tableWidget_4,
                                                                           conf.policy_factor_labels, 'policy'))
            self.dlg.pushButton_14.clicked.connect(lambda: self.addFactors(self.dlg.tableWidget_5,
                                                                           conf.composite_factor_labels, 'composite'))
            self.dlg.pushButton_3.clicked.connect(self.startProcessingProxFct)
            self.dlg.mMapLayerComboBox.setFilters(QgsMapLayerProxyModel.VectorLayer)
            self.dlg_4.mMapLayerComboBox.setFilters(QgsMapLayerProxyModel.VectorLayer)
            self.prePopulateProximityTablwWidget()
            self.pre_populate_policy_table()
            self.pre_populate_composite_table()
            self.dlg.pushButton_12.clicked.connect(lambda: self.intersection_join(self.dlg.tableWidget_4,
                                                                                  self.dlg.progressBar,
                                                                                  self.dlg.mMapLayerComboBox_4))
            self.dlg.pushButton_15.clicked.connect(lambda: self.intersection_join(self.dlg.tableWidget_5,
                                                                                  self.dlg.progressBar_2,
                                                                                  self.dlg.mMapLayerComboBox_5))



        # show the dialog
        self.dlg.hide()
        self.dlg_2.hide()
        # self.dlg_2.pushButton.setEnabled(False)
        self.dlg_4.hide()
        self.dlg_3.show()
        # Run the dialog event loop
        # result = self.dlg.exec_()
        # See if OK was pressed
        # if result:
            # Do something useful here - delete the line containing pass and
            # substitute with your code.
            # pass
