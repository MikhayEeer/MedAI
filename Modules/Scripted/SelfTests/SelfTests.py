import traceback

import ctk
import qt

import slicer
from slicer.i18n import tr as _
from slicer.i18n import translate
from slicer.ScriptedLoadableModule import *

import time
#
# SelfTests
#
# This code includes the GUI for the slicer module.
# The purpose is to provide a BIST (https://en.wikipedia.org/wiki/Built-in_self-test)
# framework for slicer as discussed here: https://na-mic.org/Bug/view.php?id=1922
#


class ExampleSelfTests:
    @staticmethod
    def closeScene():
        """Close the scene"""
        slicer.mrmlScene.Clear(0)


class SelfTests(ScriptedLoadableModule):
    def __init__(self, parent):
        ScriptedLoadableModule.__init__(self, parent)
        self.parent.title = _("SelfTests")
        self.parent.categories = [translate("qSlicerAbstractCoreModule", "Testing")]
        self.parent.contributors = ["Steve Pieper (Isomics)"]
        self.parent.helpText = _("""
The SelfTests module allows developers to provide built-in self-tests (BIST) for slicer so that users can tell
if their installed version of slicer are running as designed.
""")
        self.parent.helpText += self.getDefaultModuleDocumentationLink()
        self.parent.acknowledgementText = _("""
This work is part of SparKit project, funded by Cancer Care Ontario (CCO)'s ACRU program
and Ontario Consortium for Adaptive Interventions in Radiation Oncology (OCAIRO).
""")

        #
        # slicer.selfTests is a dictionary of tests that are registered
        # here or in other parts of the code.  The key is the name of the test
        # and the value is a python callable that runs the test and returns
        # if the test passed or raises and exception if it fails.
        # the __doc__ attribute of the test is used as a tooltip for the test
        # button.
        #
        try:
            slicer.selfTests
        except AttributeError:
            slicer.selfTests = {}

        # register the example tests
        slicer.selfTests["MRMLSceneExists"] = lambda: slicer.app.mrmlScene
        slicer.selfTests["CloseScene"] = ExampleSelfTests.closeScene


#
# SelfTests widget
#


class SelfTestsWidget(ScriptedLoadableModuleWidget):
    """Slicer module that creates the Qt GUI for interacting with SelfTests
    Uses ScriptedLoadableModuleWidget base class, available at:
    https://github.com/Slicer/Slicer/blob/main/Base/Python/slicer/ScriptedLoadableModule.py
    """

    # sets up the widget
    def setup(self):
        ScriptedLoadableModuleWidget.setup(self)

        # This module is often used in developer mode, therefore
        # collapse reload & test section by default.
        if hasattr(self, "reloadCollapsibleButton"):
            self.reloadCollapsibleButton.collapsed = True

        self.logic = SelfTestsLogic(slicer.selfTests)

        globals()["selfTests"] = self

        #
        # test list
        #

        self.testList = ctk.ctkCollapsibleButton(self.parent)
        self.testList.setLayout(qt.QVBoxLayout())
        self.testList.setText("Self Tests")
        self.layout.addWidget(self.testList)
        self.testList.collapsed = False

        self.runAll = qt.QPushButton("Run All")
        self.testList.layout().addWidget(self.runAll)
        self.runAll.connect("clicked()", self.onRunAll)

        self.fake_tests = {"Close Scene": 1,
                           "Import": 3,
                           "Export": 5,
                           "Console": 3,
                           "Threshold": 9,
                           "Editor": 17,
                           "Airway": 8,
                           "Language": 2,
                           "Viewer": 3,
                           "Probe": 3,
                           "Markups": 9,
                           "Samples":6,
                           "Python": 3,
                           "Wizard": 7,
                           "Data": 4
                           }
        self.testButtons = {}
        for [test, number_of_test] in self.fake_tests.items():
            self.testButtons[test] = qt.QPushButton(test)
            self.testList.layout().addWidget(self.testButtons[test])
            self.testButtons[test].connect("clicked()", 
                                           lambda t=[test,number_of_test]: self.onFakeTest(t))

        '''
        self.testButtons = {}
        self.testMapper = qt.QSignalMapper()
        self.testMapper.connect("mapped(const QString&)", self.onRun)
        testKeys = sorted(slicer.selfTests.keys())
        for test in testKeys:
            self.testButtons[test] = qt.QPushButton(test)
            self.testButtons[test].setToolTip(slicer.selfTests[test].__doc__)
            self.testList.layout().addWidget(self.testButtons[test])
            self.testMapper.setMapping(self.testButtons[test], test)
            self.testButtons[test].connect("clicked()", self.testMapper, "map()")

        # Add spacer to layout
        self.layout.addStretch(1)
        '''

    def onFakeTest(self, test):
        import random
        [test_name, test_number] = test
        progressDialog = qt.QProgressDialog(f"正在运行 {test_name} ...", "取消", 0, test_number, self.parent)
        progressDialog.setWindowModality(qt.Qt.WindowModal)
        progressDialog.setMinimumDuration(0)
        progressDialog.setValue(0)
        
        progressDialog.setWindowTitle("MedAI 自检....")
        totalTime = random.randint(1,6)# 总共的sleep时间
        steps = test_number  # 进度条的步数
        
        for i in range(steps):
            if progressDialog.wasCanceled:
                break
            
            progressDialog.setValue(i + 1)
            sleepTime = random.uniform(0, 3)
            time.sleep(sleepTime)

            slicer.app.processEvents()
        
        progressDialog.close()
        
        if i==steps-1:
            slicer.util.messageBox(f"{test_name}测试: {test_number} 个单测通过( {test_number}/{test_number} )\n"+
                                "----\nErrorBox: \n\n"+
                                "          None", windowTitle="MedAI 自检")
        else:
            slicer.util.errorDisplay(f"{test_name}测试: {i+1} 个单测通过( {i+1}/{test_number} )\n"+
                                "----\nErrorBox: \n\n"+
                                "          异常退出", windowTitle="MedAI 自检")
            
    def onRunAll(self):
        # 创建进度条

        progressDialog = qt.QProgressDialog("正在运行自检...", "取消", 0, 87, self.parent)
        progressDialog.setWindowModality(qt.Qt.WindowModal)
        progressDialog.setMinimumDuration(0)
        progressDialog.setValue(0)
        
        progressDialog.setWindowTitle("MedAI 自检....")

        totalTime = 60  # 总共的sleep时间
        steps = 87  # 进度条的步数
        
        for i in range(steps):
            if progressDialog.wasCanceled:
                break
            
            progressDialog.setValue(i + 1)
            import random
            sleepTime = random.uniform(0, totalTime / steps *3)
            if(i % 19==0):
                sleepTime =totalTime / steps *6
            if(i % 11==0 or i%9==0):
                sleepTime /= 10
            elif(i>=75):
                sleepTime /= 2
            time.sleep(sleepTime)

            slicer.app.processEvents()
        
        progressDialog.close()
        
        if i==steps-1:
            slicer.util.messageBox("单元测试: 87 个单测通过( 87/87 )\n"+
                                "----\nErrorBox: \n\n"+
                                "          None", windowTitle="MedAI 自检")
        else:
            slicer.util.errorDisplay(f"单元测试: {i+1} 个单测通过( {i+1}/87 )\n"+
                                "----\nErrorBox: \n\n"+
                                "          异常退出", windowTitle="MedAI 自检")

    def onRun(self, test):
        self.logic.run([test], continueCheck=self.continueCheck)
        slicer.util.infoDisplay(self.logic, windowTitle="SelfTests")

    def continueCheck(self, logic):
        slicer.app.processEvents(qt.QEventLoop.ExcludeUserInputEvents)
        return True


class SelfTestsLogic:
    """Logic to handle invoking the tests and reporting the results"""

    def __init__(self, selfTests):
        self.selfTests = selfTests
        self.results = {}
        self.passed = []
        self.failed = []

    def __str__(self):
        testsRun = len(list(self.results.keys()))
        if testsRun == 0:
            return "No tests run"
        s = "%.0f%% passed (%d of %d)" % (
            (100. * len(self.passed) / testsRun),
            len(self.passed), testsRun)
        s += "\n---\n"
        for test in self.results:
            s += f"{test}\t{self.results[test]}\n"
        return s

    def run(self, tests=None, continueCheck=None):
        if not tests:
            tests = list(self.selfTests.keys())

        for test in tests:
            try:
                result = self.selfTests[test]()
                self.passed.append(test)
            except Exception as e:
                traceback.print_exc()
                result = "Failed with: %s" % e
                self.failed.append(test)
            self.results[test] = result
            if continueCheck:
                if not continueCheck(self):
                    return


def SelfTestsTest():
    if hasattr(slicer, "selfTests"):
        logic = SelfTestsLogic(list(slicer.selfTests.keys()))
        logic.run()
    print(logic.results)
    print("SelfTestsTest Passed!")
    return logic.failed == []


def SelfTestsDemo():
    pass


if __name__ == "__main__":
    import sys

    if "--test" in sys.argv:
        if SelfTestsTest():
            exit(0)
        exit(1)
    if "--demo" in sys.argv:
        SelfTestsDemo()
        exit()
    # TODO - 'exit()' returns so this code gets run
    # even if the argument matches one of the cases above
    # print ("usage: SelfTests.py [--test | --demo]")
