# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'amrlib/amr_view/mainwindow.ui'
#
# Created by: PyQt5 UI code generator 5.15.0
#
# WARNING: Any manual changes made to this file will be lost when pyuic5 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(1175, 981)
        MainWindow.setMinimumSize(QtCore.QSize(200, 300))
        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.gridLayout = QtWidgets.QGridLayout(self.centralwidget)
        self.gridLayout.setObjectName("gridLayout")
        self.verticalLayout_2 = QtWidgets.QVBoxLayout()
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.inputSentLBL = QtWidgets.QLabel(self.centralwidget)
        self.inputSentLBL.setObjectName("inputSentLBL")
        self.horizontalLayout_2.addWidget(self.inputSentLBL)
        spacerItem = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_2.addItem(spacerItem)
        self.verticalLayout_2.addLayout(self.horizontalLayout_2)
        self.verticalLayout = QtWidgets.QVBoxLayout()
        self.verticalLayout.setObjectName("verticalLayout")
        self.inputSentLE = QtWidgets.QLineEdit(self.centralwidget)
        self.inputSentLE.setObjectName("inputSentLE")
        self.verticalLayout.addWidget(self.inputSentLE)
        self.verticalLayout_2.addLayout(self.verticalLayout)
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.amrLBL = QtWidgets.QLabel(self.centralwidget)
        self.amrLBL.setObjectName("amrLBL")
        self.horizontalLayout.addWidget(self.amrLBL)
        spacerItem1 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout.addItem(spacerItem1)
        self.showGraphPB = QtWidgets.QPushButton(self.centralwidget)
        self.showGraphPB.setObjectName("showGraphPB")
        self.horizontalLayout.addWidget(self.showGraphPB)
        self.toAmrPB = QtWidgets.QPushButton(self.centralwidget)
        self.toAmrPB.setObjectName("toAmrPB")
        self.horizontalLayout.addWidget(self.toAmrPB)
        self.verticalLayout_2.addLayout(self.horizontalLayout)
        self.amrTE = QtWidgets.QPlainTextEdit(self.centralwidget)
        self.amrTE.setLineWrapMode(QtWidgets.QPlainTextEdit.NoWrap)
        self.amrTE.setObjectName("amrTE")
        self.verticalLayout_2.addWidget(self.amrTE)
        self.horizontalLayout_4 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_4.setObjectName("horizontalLayout_4")
        self.generatedLBL = QtWidgets.QLabel(self.centralwidget)
        self.generatedLBL.setObjectName("generatedLBL")
        self.horizontalLayout_4.addWidget(self.generatedLBL)
        spacerItem2 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_4.addItem(spacerItem2)
        self.generatePB = QtWidgets.QPushButton(self.centralwidget)
        self.generatePB.setObjectName("generatePB")
        self.horizontalLayout_4.addWidget(self.generatePB)
        self.verticalLayout_2.addLayout(self.horizontalLayout_4)
        self.generatedTE = QtWidgets.QPlainTextEdit(self.centralwidget)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.generatedTE.sizePolicy().hasHeightForWidth())
        self.generatedTE.setSizePolicy(sizePolicy)
        self.generatedTE.setMinimumSize(QtCore.QSize(0, 80))
        self.generatedTE.setMaximumSize(QtCore.QSize(16777215, 80))
        self.generatedTE.setLineWrapMode(QtWidgets.QPlainTextEdit.NoWrap)
        self.generatedTE.setObjectName("generatedTE")
        self.verticalLayout_2.addWidget(self.generatedTE)
        self.horizontalLayout_5 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_5.setObjectName("horizontalLayout_5")
        spacerItem3 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_5.addItem(spacerItem3)
        self.exitPB = QtWidgets.QPushButton(self.centralwidget)
        self.exitPB.setObjectName("exitPB")
        self.horizontalLayout_5.addWidget(self.exitPB)
        self.verticalLayout_2.addLayout(self.horizontalLayout_5)
        self.gridLayout.addLayout(self.verticalLayout_2, 0, 0, 1, 1)
        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtWidgets.QMenuBar(MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 1175, 22))
        self.menubar.setObjectName("menubar")
        self.menuFile = QtWidgets.QMenu(self.menubar)
        self.menuFile.setObjectName("menuFile")
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QtWidgets.QStatusBar(MainWindow)
        self.statusbar.setObjectName("statusbar")
        MainWindow.setStatusBar(self.statusbar)
        self.actionLoadAMR = QtWidgets.QAction(MainWindow)
        self.actionLoadAMR.setObjectName("actionLoadAMR")
        self.actionSaveAMR = QtWidgets.QAction(MainWindow)
        self.actionSaveAMR.setObjectName("actionSaveAMR")
        self.menuFile.addAction(self.actionLoadAMR)
        self.menuFile.addAction(self.actionSaveAMR)
        self.menubar.addAction(self.menuFile.menuAction())

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "MainWindow"))
        self.inputSentLBL.setText(_translate("MainWindow", "Input Sentence"))
        self.amrLBL.setText(_translate("MainWindow", "AMR"))
        self.showGraphPB.setText(_translate("MainWindow", "Show Graph"))
        self.toAmrPB.setText(_translate("MainWindow", "To AMR"))
        self.generatedLBL.setText(_translate("MainWindow", "Generated"))
        self.generatePB.setText(_translate("MainWindow", "Generate"))
        self.exitPB.setText(_translate("MainWindow", "Exit"))
        self.menuFile.setTitle(_translate("MainWindow", "File"))
        self.actionLoadAMR.setText(_translate("MainWindow", "Load AMR"))
        self.actionSaveAMR.setText(_translate("MainWindow", "Save AMR"))
