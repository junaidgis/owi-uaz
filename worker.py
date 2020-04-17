import os
from qgis.core import *
from PyQt5.QtCore import QVariant

class Worker:
    def __init__(self, layer, att_name, parcels_layer, buffer_int, no_of_int):
        self.data_dir = None
        self.layer = layer
        self.att_name = att_name
        self.parcels_layer = parcels_layer
        self.buffer_int = buffer_int
        self.no_of_int = no_of_int


    def checkFieldExists(self):
        return any([True for field in self.parcels_layer.fields() if field.name().lower() == self.att_name.lower()])

    def transform_geom(self, geom, layer_crs, ):
        sourceCrs = QgsCoordinateReferenceSystem(layer_crs)
        destCrs = QgsCoordinateReferenceSystem(3857)
        tr = QgsCoordinateTransform(sourceCrs, destCrs, QgsProject.instance())
        geom1 = QgsGeometry(geom)
        geom1.transform(tr)
        return geom1

    def populate_buff(self):
        # parameter layers path
        self.parcels_layer.startEditing()
        self.parcels_layer.dataProvider().addAttributes([QgsField(self.att_name, QVariant.String)])
        self.parcels_layer.updateFields()
        to_transform_parcels = True if self.parcels_layer.crs().postgisSrid() != 3857 else False
        to_transform_olayer = True if self.layer.crs().postgisSrid() != 3857 else False
        for i in range(self.no_of_int):
            if not i:
                parameter_val = '<=' + str(self.buffer_int)
            elif i == self.no_of_int - 1:
                parameter_val = '>=' + str(self.buffer_int * (self.no_of_int - 1))
            else:
                parameter_val = str(self.buffer_int * i) + '-' + str(self.buffer_int * (i + 1))
            for feat in self.layer.getFeatures():
                geom = feat.geometry()
                if to_transform_olayer:
                    geom = self.transform_geom(geom, self.layer.crs().postgisSrid())
                parameter_buff = geom.buffer(self.buffer_int * (i + 1), 5)
                for feat1 in self.parcels_layer.getFeatures():
                    parcel_geom = feat1.geometry()
                    if to_transform_parcels:
                        parcel_geom = self.transform_geom(parcel_geom, self.parcels_layer.crs().postgisSrid())
                    if parcel_geom.intersects(parameter_buff):
                        if not feat1[self.att_name]:
                            feat1[self.att_name] = parameter_val
                            self.parcels_layer.updateFeature(feat1)
        self.parcels_layer.commitChanges()