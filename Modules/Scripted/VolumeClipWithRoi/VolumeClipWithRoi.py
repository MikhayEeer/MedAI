import os
import string
import unittest
import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *
from slicer.util import VTKObservationMixin
from slicer.i18n import tr as _
from slicer.i18n import translate

#
# VolumeClipWithRoi
#

class VolumeClipWithRoi(ScriptedLoadableModule):
  def __init__(self, parent):
    ScriptedLoadableModule.__init__(self, parent)
    self.parent.title = _("Volume clip with ROI")
    self.parent.categories = ["Segmentation"]
    self.parent.dependencies = []
    self.parent.contributors = ["Andras Lasso (Queen's University)"]
    self.parent.helpText = _("""
      Use this module to clip a volume with a ROI (fill with a constant value). 
      It can be used for removing certain regions of a scalar or labelmap volume.
      """)
    # TODO: replace "Nightly" by "$b.$c" in release builds (preferably implement a mechanism that does this automatically)
    self.parent.acknowledgementText ="""
      This work is part of SparKit project, funded by Cancer Care Ontario (CCO)'s ACRU program and
      Ontario Consortium for Adaptive Interventions in Radiation Oncology (OCAIRO).
      """

#
# VolumeClipWithRoiWidget
#

class VolumeClipWithRoiWidget(ScriptedLoadableModuleWidget):

  def __init__(self, parent):
    ScriptedLoadableModuleWidget.__init__(self, parent)
    self.logic = VolumeClipWithRoiLogic()
    self.parameterNode = None

  def setup(self):
    ScriptedLoadableModuleWidget.setup(self)

    # Instantiate and connect widgets ...

    #
    # Parameters Area
    #
    parametersCollapsibleButton = ctk.ctkCollapsibleButton()
    parametersCollapsibleButton.text = _("Parameters")
    self.layout.addWidget(parametersCollapsibleButton)

    # Layout within the dummy collapsible button
    parametersFormLayout = qt.QFormLayout(parametersCollapsibleButton)

    # Volume selector
    self.inputVolumeSelectorLabel = qt.QLabel()
    self.inputVolumeSelectorLabel.setText( _("Input volume: ") )
    self.inputVolumeSelector = slicer.qMRMLNodeComboBox()
    self.inputVolumeSelector.nodeTypes = ( "vtkMRMLScalarVolumeNode", "" )
    self.inputVolumeSelector.noneEnabled = False
    self.inputVolumeSelector.addEnabled = False
    self.inputVolumeSelector.removeEnabled = False
    self.inputVolumeSelector.setMRMLScene( slicer.mrmlScene )
    self.inputVolumeSelector.setToolTip( _("Pick the volume to clip") )
    parametersFormLayout.addRow(self.inputVolumeSelectorLabel, self.inputVolumeSelector)

    # ROI selector
    self.clippingRoiSelectorLabel = qt.QLabel()
    self.clippingRoiSelectorLabel.setText( _("Clipping ROI: ") )
    self.clippingRoiSelector = slicer.qMRMLNodeComboBox()
    self.clippingRoiSelector.nodeTypes = ["vtkMRMLMarkupsROINode", "vtkMRMLAnnotationROINode"]
    self.clippingRoiSelector.noneEnabled = False
    self.clippingRoiSelector.selectNodeUponCreation = True
    self.clippingRoiSelector.setMRMLScene( slicer.mrmlScene )
    self.clippingRoiSelector.setToolTip( _("Pick the clipping region of interest (ROI)") )
    parametersFormLayout.addRow(self.clippingRoiSelectorLabel, self.clippingRoiSelector)

    #
    # clip inside/outside the surface
    #
    self.clipOutsideSurfaceCheckBox = qt.QCheckBox()
    self.clipOutsideSurfaceCheckBox.checked = False
    self.clipOutsideSurfaceCheckBox.setToolTip(_("If checked, voxel values will be filled outside the clipping ROI."))
    parametersFormLayout.addRow(_("Clip outside: "), self.clipOutsideSurfaceCheckBox)

    # Fill value editor
    self.fillValueLabel = qt.QLabel(_("Fill value:"))
    self.fillValueEdit = qt.QDoubleSpinBox()
    self.fillValueEdit.minimum = -32768
    self.fillValueEdit.maximum = 65535
    parametersFormLayout.addRow(self.fillValueLabel, self.fillValueEdit)

    #
    # output volume selector
    #
    self.outputVolumeSelector = slicer.qMRMLNodeComboBox()
    self.outputVolumeSelector.nodeTypes = ( ("vtkMRMLScalarVolumeNode"), "" )
    self.outputVolumeSelector.selectNodeUponCreation = True
    self.outputVolumeSelector.addEnabled = True
    self.outputVolumeSelector.removeEnabled = True
    self.outputVolumeSelector.noneEnabled = False
    self.outputVolumeSelector.showHidden = False
    self.outputVolumeSelector.setMRMLScene( slicer.mrmlScene )
    self.outputVolumeSelector.setToolTip( _("Clipped output volume. It may be the same as the input volume for cumulative clipping.") )
    parametersFormLayout.addRow(_("Output Volume: "), self.outputVolumeSelector)

    # Apply button
    self.applyButton = qt.QPushButton(_("Apply"))
    self.applyButton.toolTip = _("Clip volume with ROI")
    parametersFormLayout.addWidget(self.applyButton)
    self.updateApplyButtonState()

    # connections
    self.applyButton.connect("clicked()", self.onApply)

    self.inputVolumeSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onInputVolumeSelect)
    self.clippingRoiSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onClippingRoiSelect)
    self.outputVolumeSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onOutputVolumeSelect)

    # Define list of widgets for updateGUIFromParameterNode, updateParameterNodeFromGUI, and addGUIObservers
    self.valueEditWidgets = {"ClipOutsideSurface": self.clipOutsideSurfaceCheckBox, "FillValue": self.fillValueEdit}
    self.nodeSelectorWidgets = {"InputVolume": self.inputVolumeSelector, "ClippingRoi": self.clippingRoiSelector, "OutputVolume": self.outputVolumeSelector}

    # Use singleton parameter node (it is created if does not exist yet)
    parameterNode = self.logic.getParameterNode()
    # Set parameter node (widget will observe it and also updates GUI)
    self.setAndObserveParameterNode(parameterNode)

    self.addGUIObservers()

    # Add vertical spacer
    self.layout.addStretch(1)

  def setAndObserveParameterNode(self, parameterNode):
    if parameterNode == self.parameterNode and self.parameterNodeObserver:
      # no change and node is already observed
      return
    # Remove observer to old parameter node
    if self.parameterNode and self.parameterNodeObserver:
      self.parameterNode.RemoveObserver(self.parameterNodeObserver)
      self.parameterNodeObserver = None
    # Set and observe new parameter node
    self.parameterNode = parameterNode
    if self.parameterNode:
      self.parameterNodeObserver = self.parameterNode.AddObserver(vtk.vtkCommand.ModifiedEvent, self.onParameterNodeModified)
    # Update GUI
    self.updateGUIFromParameterNode()

  def getParameterNode(self):
    return self.parameterNode

  def onParameterNodeModified(self, observer, eventid):
    self.updateGUIFromParameterNode()

  def getClassName(self, widget):
    import sys
    if sys.version_info.major == 2:
      return widget.metaObject().className()
    else:
      return widget.metaObject().getClassName()

  def updateGUIFromParameterNode(self):
    parameterNode = self.getParameterNode()
    for parameterName in self.valueEditWidgets:
      oldBlockSignalsState = self.valueEditWidgets[parameterName].blockSignals(True)
      widgetClassName = self.getClassName(self.valueEditWidgets[parameterName])
      if widgetClassName=="QCheckBox":
        checked = (int(parameterNode.GetParameter(parameterName)) != 0)
        self.valueEditWidgets[parameterName].setChecked(checked)
      elif widgetClassName=="QSpinBox" or widgetClassName=="QDoubleSpinBox":
        self.valueEditWidgets[parameterName].setValue(float(parameterNode.GetParameter(parameterName)))
      else:
        raise Exception("Unexpected widget class: {0}".format(widgetClassName))
      self.valueEditWidgets[parameterName].blockSignals(oldBlockSignalsState)
    for parameterName in self.nodeSelectorWidgets:
      oldBlockSignalsState = self.nodeSelectorWidgets[parameterName].blockSignals(True)
      self.nodeSelectorWidgets[parameterName].setCurrentNodeID(parameterNode.GetNodeReferenceID(parameterName))
      self.nodeSelectorWidgets[parameterName].blockSignals(oldBlockSignalsState)

  def updateParameterNodeFromGUI(self):
    parameterNode = self.getParameterNode()
    oldModifiedState = parameterNode.StartModify()
    for parameterName in self.valueEditWidgets:
      widgetClassName = self.getClassName(self.valueEditWidgets[parameterName])
      if widgetClassName=="QCheckBox":
        if self.valueEditWidgets[parameterName].checked:
          parameterNode.SetParameter(parameterName, "1")
        else:
          parameterNode.SetParameter(parameterName, "0")
      elif widgetClassName=="QSpinBox" or widgetClassName=="QDoubleSpinBox":
        parameterNode.SetParameter(parameterName, str(self.valueEditWidgets[parameterName].value))
      else:
        raise Exception("Unexpected widget class: {0}".format(widgetClassName))
    for parameterName in self.nodeSelectorWidgets:
      parameterNode.SetNodeReferenceID(parameterName, self.nodeSelectorWidgets[parameterName].currentNodeID)
    parameterNode.EndModify(oldModifiedState)

  def addGUIObservers(self):
    for parameterName in self.valueEditWidgets:
      widgetClassName = self.getClassName(self.valueEditWidgets[parameterName])
      if widgetClassName=="QSpinBox":
        self.valueEditWidgets[parameterName].connect("valueChanged(int)", self.updateParameterNodeFromGUI)
      if widgetClassName=="QDoubleSpinBox":
        self.valueEditWidgets[parameterName].connect("valueChanged(double)", self.updateParameterNodeFromGUI)
      elif widgetClassName=="QCheckBox":
        self.valueEditWidgets[parameterName].connect("clicked()", self.updateParameterNodeFromGUI)
    for parameterName in self.nodeSelectorWidgets:
      self.nodeSelectorWidgets[parameterName].connect("currentNodeIDChanged(QString)", self.updateParameterNodeFromGUI)

  def updateApplyButtonState(self):
    if self.clippingRoiSelector.currentNode() and self.inputVolumeSelector.currentNode() and self.outputVolumeSelector.currentNode():
      self.applyButton.enabled = True
    else:
      self.applyButton.enabled = False

  def onClippingRoiSelect(self, node):
    self.updateApplyButtonState()

  def onInputVolumeSelect(self, node):
    self.updateApplyButtonState()

  def onOutputVolumeSelect(self, node):
    self.updateApplyButtonState()

  def onApply(self):
    self.applyButton.text = _("Working...")
    self.applyButton.repaint()
    slicer.app.processEvents()
    clipOutsideSurface = self.clipOutsideSurfaceCheckBox.checked
    fillValue = self.fillValueEdit.value
    clippingRoi = self.clippingRoiSelector.currentNode()
    inputVolume = self.inputVolumeSelector.currentNode()
    outputVolume = self.outputVolumeSelector.currentNode()
    self.logic.clipVolumeWithRoi(clippingRoi, inputVolume, fillValue, clipOutsideSurface, outputVolume)
    self.logic.showInSliceViewers(outputVolume, ["Red", "Yellow", "Green"])
    self.applyButton.text = _("Apply")


#
# VolumeClipWithRoiLogic
#

class VolumeClipWithRoiLogic(ScriptedLoadableModuleLogic):
  """This class should implement all the actual
  computation done by your module.  The interface
  should be such that other python code can import
  this class and make use of the functionality without
  requiring an instance of the Widget
  """

  def __init__(self, parent = None):
    ScriptedLoadableModuleLogic.__init__(self, parent)

  def createParameterNode(self):
    # Set default parameters
    node = ScriptedLoadableModuleLogic.createParameterNode(self)
    node.SetName(slicer.mrmlScene.GetUniqueNameByString(self.moduleName))
    node.SetParameter("ClipOutsideSurface", "1")
    node.SetParameter("FillValue", "0")
    return node

  def clipVolumeWithRoi(self, roiNode, volumeNode, fillValue, clipOutsideSurface, outputVolume):

    # Create a box implicit function that will be used as a stencil to fill the volume

    roiBox = vtk.vtkBox()
    rasToBox = vtk.vtkMatrix4x4()

    # Determine the non-transformed ROI box and
    # the transform between the box and the world coordinate systems

    if roiNode.IsA("vtkMRMLMarkupsROINode"):
      # Markups ROI node
      roiDiameter = roiNode.GetSize()
      roiBox.SetBounds(-roiDiameter[0]/2, roiDiameter[0]/2, -roiDiameter[1]/2, roiDiameter[1]/2, -roiDiameter[2]/2, roiDiameter[2]/2)
      vtk.vtkMatrix4x4.Invert(roiNode.GetObjectToWorldMatrix(), rasToBox)
    else:
      # Legacy Annotation ROI node
      roiCenter = [0, 0, 0]
      roiNode.GetXYZ( roiCenter )
      roiRadius = [0, 0, 0]
      roiNode.GetRadiusXYZ( roiRadius )
      roiBox.SetBounds(roiCenter[0] - roiRadius[0], roiCenter[0] + roiRadius[0], roiCenter[1] - roiRadius[1], roiCenter[1] + roiRadius[1], roiCenter[2] - roiRadius[2], roiCenter[2] + roiRadius[2])
      if roiNode.GetTransformNodeID() != None:
        roiBoxTransformNode = slicer.mrmlScene.GetNodeByID(roiNode.GetTransformNodeID())
        boxToRas = vtk.vtkMatrix4x4()
        roiBoxTransformNode.GetMatrixTransformToWorld(boxToRas)
        rasToBox.DeepCopy(boxToRas)
        rasToBox.Invert()

    # Get transform between the box and volume IJK

    ijkToRas = vtk.vtkMatrix4x4()
    volumeNode.GetIJKToRASMatrix( ijkToRas )

    ijkToBox = vtk.vtkMatrix4x4()
    vtk.vtkMatrix4x4.Multiply4x4(rasToBox,ijkToRas,ijkToBox)
    ijkToBoxTransform = vtk.vtkTransform()
    ijkToBoxTransform.SetMatrix(ijkToBox)
    roiBox.SetTransform(ijkToBoxTransform)

    # Use the stencil to fill the volume

    imageData=volumeNode.GetImageData()

    # Convert the implicit function to a stencil
    functionToStencil = vtk.vtkImplicitFunctionToImageStencil()
    functionToStencil.SetInput(roiBox)
    functionToStencil.SetOutputOrigin(imageData.GetOrigin())
    functionToStencil.SetOutputSpacing(imageData.GetSpacing())
    functionToStencil.SetOutputWholeExtent(imageData.GetExtent())
    functionToStencil.Update()

    # Apply the stencil to the volume
    stencilToImage=vtk.vtkImageStencil()
    stencilToImage.SetInputData(imageData)
    stencilToImage.SetStencilData(functionToStencil.GetOutput())
    if clipOutsideSurface:
      stencilToImage.ReverseStencilOff()
    else:
      stencilToImage.ReverseStencilOn()
    stencilToImage.SetBackgroundValue(fillValue)
    stencilToImage.Update()

    # Update the volume with the stencil operation result
    outputImageData = vtk.vtkImageData()
    outputImageData.DeepCopy(stencilToImage.GetOutput())

    outputVolume.SetAndObserveImageData(outputImageData);
    outputVolume.SetIJKToRASMatrix(ijkToRas)

    # Add a default display node to output volume node if it does not exist yet
    if not outputVolume.GetDisplayNode:
      displayNode=slicer.vtkMRMLScalarVolumeDisplayNode()
      displayNode.SetAndObserveColorNodeID("vtkMRMLColorTableNodeGrey")
      slicer.mrmlScene.AddNode(displayNode)
      outputVolume.SetAndObserveDisplayNodeID(displayNode.GetID())

  def showInSliceViewers(self, volumeNode, sliceWidgetNames):
    # Displays volumeNode in the selected slice viewers as background volume
    # Existing background volume is pushed to foreground, existing foreground volume will not be shown anymore
    # sliceWidgetNames is a list of slice view names, such as ["Yellow", "Green"]
    if not volumeNode:
      return
    newVolumeNodeID = volumeNode.GetID()
    for sliceWidgetName in sliceWidgetNames:
      sliceLogic = slicer.app.layoutManager().sliceWidget(sliceWidgetName).sliceLogic()
      foregroundVolumeNodeID = sliceLogic.GetSliceCompositeNode().GetForegroundVolumeID()
      backgroundVolumeNodeID = sliceLogic.GetSliceCompositeNode().GetBackgroundVolumeID()
      if foregroundVolumeNodeID == newVolumeNodeID or backgroundVolumeNodeID == newVolumeNodeID:
        # new volume is already shown as foreground or background
        continue
      if backgroundVolumeNodeID:
        # there is a background volume, push it to the foreground because we will replace the background volume
        sliceLogic.GetSliceCompositeNode().SetForegroundVolumeID(backgroundVolumeNodeID)
      # show the new volume as background
      sliceLogic.GetSliceCompositeNode().SetBackgroundVolumeID(newVolumeNodeID)

class VolumeClipWithRoiTest(ScriptedLoadableModuleTest):
  """
  This is the test case for your scripted module.
  """

  def setUp(self):
    """ Do whatever is needed to reset the state - typically a scene clear will be enough.
    """
    slicer.mrmlScene.Clear(0)

  def runTest(self):
    """Run as few or as many tests as needed here.
    """
    self.setUp()
    self.test_VolumeClipWithRoi1()

  def test_VolumeClipWithRoi1(self):

    # Download MRHead from sample data
    import SampleData
    sampleDataLogic = SampleData.SampleDataLogic()
    self.delayDisplay("Getting MR Head Volume")
    mrHeadVolume = sampleDataLogic.downloadMRHead()

    # Create output volume
    outputVolume = slicer.vtkMRMLScalarVolumeNode()
    slicer.mrmlScene.AddNode(outputVolume)

    # Create clipping ROI
    roiNode = slicer.vtkMRMLAnnotationROINode()
    roiNode.SetXYZ(36, 17, -10)
    roiNode.SetRadiusXYZ(25,40,65)
    roiNode.Initialize(slicer.mrmlScene)

    fillValue = 17
    clipOutsideSurface = True

    logic = VolumeClipWithRoiLogic()
    logic.clipVolumeWithRoi(roiNode, mrHeadVolume, fillValue, clipOutsideSurface, outputVolume)

    self.delayDisplay("Test passed!")
