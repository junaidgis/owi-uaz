import os
from qgis.core import *
from PyQt5.QtCore import QVariant
from qgis.core import QgsSpatialIndex
from qgis.core import QgsMessageLog

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
        QgsMessageLog.logMessage('new')
        base_layer = [feature for feature in self.parcels_layer.getFeatures()]
        factor_layer = [feature for feature in self.layer.getFeatures()]
        to_transform_parcels = True if self.parcels_layer.crs().postgisSrid() != 3857 else False
        to_transform_olayer = True if self.layer.crs().postgisSrid() != 3857 else False

        index = QgsSpatialIndex()
        for poly in base_layer:
            index.insertFeature(poly)


        for i in range(self.no_of_int-1):
            if not i:
                parameter_val = '<=' + str((self.buffer_int)/1000)
            elif i == self.no_of_int - 1:
                parameter_val = '>=' + str((self.buffer_int * (self.no_of_int - 1))/1000)
            else:
                parameter_val = str((self.buffer_int * i)/1000) + '-' + str((self.buffer_int * (i + 1))/1000)

            for feat in factor_layer:
                fids = []
                geom = feat.geometry()
                parameter_buff = geom.buffer(self.buffer_int * (i + 1), 5)
                for id in index.intersects(parameter_buff.boundingBox()):
                    fids.append(id)
               # QgsMessageLog.logMessage(str(i))
                #QgsMessageLog.logMessage(str(parameter_val))
                #QgsMessageLog.logMessage(str(self.buffer_int * (i + 1)))
              #  QgsMessageLog.logMessage(str(len([f for f in self.parcels_layer.getFeatures(request)])))
                #QgsMessageLog.logMessage(str(fids))
                #    self.parcels_layer.changeAttributeValue(feat.id(), 2, 30)
                # assume a list of feature ids returned from index and a QgsVectorLayer 'lyr'
                request = QgsFeatureRequest()
                request.setFilterFids(fids)
                features = self.parcels_layer.getFeatures(request)

                # can now iterate and do fun stuff:
                #for feat in factor_layer:
                 #   geom = feat.geometry()
                 #   parameter_buff = geom.buffer(self.buffer_int * (i + 1), 5)
                for feature in features:
                    if feature.geometry().intersects(parameter_buff):
                        if not feature[self.att_name]:
                            feature[self.att_name] = parameter_val
                            self.parcels_layer.updateFeature(feature)

        parameter_val = '>=' + str((self.buffer_int * (self.no_of_int - 1))/1000)
        for feature in self.parcels_layer.getFeatures():
            if not feature[self.att_name]:
                feature[self.att_name] = parameter_val
                self.parcels_layer.updateFeature(feature)
        self.parcels_layer.commitChanges()

 #                   QgsMessageLog.logMessage(str(feature))






