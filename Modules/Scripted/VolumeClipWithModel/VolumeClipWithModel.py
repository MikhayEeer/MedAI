import os
import unittest
import logging
import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *
from slicer.util import VTKObservationMixin
from slicer.i18n import tr as _
from slicer.i18n import translate

#
# VolumeClipWithModel
#

class VolumeClipWithModel(ScriptedLoadableModule):
  def __init__(self, parent):
    ScriptedLoadableModule.__init__(self, parent)
    self.parent.title = _("Volume clip with model")
    self.parent.categories = ["Segmentation"]
    self.parent.dependencies = []
    self.parent.contributors = ["Andras Lasso, Matt Lougheed (PerkLab, Queen's University)"]
    self.parent.helpText = """
      Clip volume with a surface model. 
      Optionally the surface model can be automatically 
      generated from a set of sample markup points.
      """
    # TODO: replace "Nightly" by "$b.$c" in release builds (preferably implement a mechanism that does this automatically)
    self.parent.acknowledgementText ="""
      This work is part of SparKit project, funded by Cancer Care Ontario (CCO)'s ACRU program and
      Ontario Consortium for Adaptive Interventions in Radiation Oncology (OCAIRO).
      """

#
# VolumeClipWithModelWidget
#

class VolumeClipWithModelWidget(ScriptedLoadableModuleWidget):

  def __init__(self, parent):
    ScriptedLoadableModuleWidget.__init__(self, parent)
    self.logic = VolumeClipWithModelLogic()
    self.parameterNode = None
    self.parameterNodeObserver = None
    self.clippingMarkupNode = None
    self.clippingMarkupNodeObservers = []

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

    #
    # input volume selector
    #
    self.inputVolumeSelector = slicer.qMRMLNodeComboBox()
    self.inputVolumeSelector.nodeTypes = ( ("vtkMRMLScalarVolumeNode"), "" )
    self.inputVolumeSelector.addEnabled = False
    self.inputVolumeSelector.removeEnabled = False
    self.inputVolumeSelector.noneEnabled = False
    self.inputVolumeSelector.showHidden = False
    self.inputVolumeSelector.setMRMLScene( slicer.mrmlScene )
    self.inputVolumeSelector.setToolTip( _("Input volume that will be clipped.") )
    parametersFormLayout.addRow(_("Input Volume: "), self.inputVolumeSelector)

    #
    # clipping model selector
    #
    self.clippingModelSelector = slicer.qMRMLNodeComboBox()
    self.clippingModelSelector.nodeTypes = (("vtkMRMLModelNode"), "")
    self.clippingModelSelector.addEnabled = True
    self.clippingModelSelector.removeEnabled = False
    self.clippingModelSelector.noneEnabled = True
    self.clippingModelSelector.showHidden = False
    self.clippingModelSelector.renameEnabled = True
    self.clippingModelSelector.selectNodeUponCreation = True
    self.clippingModelSelector.showChildNodeTypes = False
    self.clippingModelSelector.setMRMLScene(slicer.mrmlScene)
    self.clippingModelSelector.setToolTip(_("Choose the clipping surface model."))
    parametersFormLayout.addRow(_("Clipping surface: "), self.clippingModelSelector)

    #
    # markup selector
    #
    self.clippingMarkupSelector = slicer.qMRMLNodeComboBox()
    self.clippingMarkupSelector.nodeTypes = (("vtkMRMLMarkupsFiducialNode"), "")
    self.clippingMarkupSelector.addEnabled = True
    self.clippingMarkupSelector.removeEnabled = False
    self.clippingMarkupSelector.noneEnabled = True
    self.clippingMarkupSelector.showHidden = False
    self.clippingMarkupSelector.renameEnabled = True
    self.clippingMarkupSelector.baseName = "C"
    self.clippingMarkupSelector.setMRMLScene(slicer.mrmlScene)
    self.clippingMarkupSelector.setToolTip(_("If markups are selected then the clipping surface will be generated from the markup points. The surface is updated automatically when markups are moved."))
    parametersFormLayout.addRow(_("Clipping surface from markups: "), self.clippingMarkupSelector)

    #
    # clip outside the surface
    #
    self.clipOutsideSurfaceCheckBox = qt.QCheckBox()
    self.clipOutsideSurfaceCheckBox.checked = False
    self.clipOutsideSurfaceCheckBox.setToolTip(_("If checked, voxel values will be filled outside the clipping surface."))
    parametersFormLayout.addRow(_("Clip outside: "), self.clipOutsideSurfaceCheckBox)

    #
    # outside fill value
    #
    self.fillOutsideValueEdit = qt.QSpinBox()
    self.fillOutsideValueEdit.setToolTip(_("Choose the voxel intensity that will be used to fill outside the clipped regions"))
    self.fillOutsideValueEdit.minimum = -32768
    self.fillOutsideValueEdit.maximum = 65535
    self.fillOutsideValueEdit.value = 255
    parametersFormLayout.addRow(_("Outside Fill value: "), self.fillOutsideValueEdit)

    #
    # clip inside the surface
    #
    self.clipInsideSurfaceCheckBox = qt.QCheckBox()
    self.clipInsideSurfaceCheckBox.checked = False
    self.clipInsideSurfaceCheckBox.setToolTip(_("If checked, voxel values will be filled inside the clipping surface."))
    parametersFormLayout.addRow(_("Clip inside: "), self.clipInsideSurfaceCheckBox)

    #
    # outside fill value
    #
    self.fillInsideValueEdit = qt.QSpinBox()
    self.fillInsideValueEdit.setToolTip(_("Choose the voxel intensity that will be used to fill Inside the clipped regions"))
    self.fillInsideValueEdit.minimum = -32768
    self.fillInsideValueEdit.maximum = 65535
    self.fillInsideValueEdit.value = 255
    parametersFormLayout.addRow(_("Inside Fill value: "), self.fillInsideValueEdit)

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
    self.outputVolumeSelector.setToolTip( "Clipped output volume. It may be the same as the input volume for cumulative clipping." )
    parametersFormLayout.addRow(_("Output Volume: "), self.outputVolumeSelector)

    #
    # apply Button
    #
    self.applyButton = qt.QPushButton(_("Apply"))
    self.applyButton.toolTip = _("Clip volume with surface model.")
    self.applyButton.enabled = False
    parametersFormLayout.addRow(self.applyButton)

    # connections
    self.applyButton.connect('clicked(bool)', self.onApplyButton)
    self.inputVolumeSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onInputVolumeSelect)
    self.clippingModelSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onClippingModelSelect)
    self.clippingMarkupSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onClippingMarkupSelect)
    self.outputVolumeSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onOutputVolumeSelect)

    # Define list of widgets for updateGUIFromParameterNode, updateParameterNodeFromGUI, and addGUIObservers
    self.valueEditWidgets = {"clipOutsideSurface": self.clipOutsideSurfaceCheckBox, "fillOutsideValue": self.fillOutsideValueEdit, "clipInsideSurface": self.clipInsideSurfaceCheckBox, "fillInsideValue": self.fillInsideValueEdit}
    self.nodeSelectorWidgets = {"InputVolume": self.inputVolumeSelector, "ClippingModel": self.clippingModelSelector, "ClippingMarkup": self.clippingMarkupSelector, "OutputVolume": self.outputVolumeSelector}

    # Use singleton parameter node (it is created if does not exist yet)
    parameterNode = self.logic.getParameterNode()
    # Set parameter node (widget will observe it and also updates GUI)
    self.setAndObserveParameterNode(parameterNode)

    self.setAndObserveClippingMarkupNode(self.clippingMarkupSelector.currentNode())

    self.addGUIObservers()

    # Add vertical spacer
    self.layout.addStretch(1)

    self.updateApplyButtonState()

  def cleanup(self):
    self.removeGUIObservers()
    self.setAndObserveParameterNode(None)
    self.setAndObserveClippingMarkupNode(None)
    pass

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

  def setAndObserveClippingMarkupNode(self, clippingMarkupNode):
    if clippingMarkupNode == self.clippingMarkupNode and self.clippingMarkupNodeObservers:
      # no change and node is already observed
      return
    # Remove observer to old parameter node
    if self.clippingMarkupNode and self.clippingMarkupNodeObservers:
      for observer in self.clippingMarkupNodeObservers:
        self.clippingMarkupNode.RemoveObserver(observer)
      self.clippingMarkupNodeObservers = []
    # Set and observe new parameter node
    self.clippingMarkupNode = clippingMarkupNode
    if self.clippingMarkupNode:
      if (slicer.app.majorVersion >= 5) or (slicer.app.majorVersion >= 4 and slicer.app.minorVersion >= 11):
        eventIds = [ vtk.vtkCommand.ModifiedEvent,
          slicer.vtkMRMLMarkupsNode.PointModifiedEvent,
          slicer.vtkMRMLMarkupsNode.PointAddedEvent,
          slicer.vtkMRMLMarkupsNode.PointRemovedEvent ]
      else:
        eventIds = [ vtk.vtkCommand.ModifiedEvent ]
      for eventId in eventIds:
        self.clippingMarkupNodeObservers.append(self.clippingMarkupNode.AddObserver(eventId, self.onClippingMarkupNodeModified))

      self.clippingMarkupNodeObserver = self.clippingMarkupNode.AddObserver(vtk.vtkCommand.ModifiedEvent, self.onClippingMarkupNodeModified)
    # Update GUI
    self.updateModelFromClippingMarkupNode()

  def getParameterNode(self):
    return self.parameterNode

  def onClippingMarkupNodeModified(self, observer, eventid):
    self.updateModelFromClippingMarkupNode()

  def onParameterNodeModified(self, observer, eventid):
    self.updateGUIFromParameterNode()

  def updateModelFromClippingMarkupNode(self):
    if not self.clippingMarkupNode or not self.clippingModelSelector.currentNode():
      return
    self.logic.updateModelFromMarkup(self.clippingMarkupNode, self.clippingModelSelector.currentNode())

  def getClassName(self, widget):
    import sys
    if sys.version_info.major == 2:
      return widget.metaObject().className()
    else:
      return widget.metaObject().getClassName()

  def updateGUIFromParameterNode(self):
    parameterNode = self.getParameterNode()
    if not parameterNode:
      return
    for parameterName in self.valueEditWidgets:
      oldBlockSignalsState = self.valueEditWidgets[parameterName].blockSignals(True)
      widgetClassName = self.getClassName(self.valueEditWidgets[parameterName])
      if widgetClassName=="QCheckBox":
        checked = (int(parameterNode.GetParameter(parameterName)) != 0)
        self.valueEditWidgets[parameterName].setChecked(checked)
      elif widgetClassName=="QSpinBox":
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
      elif widgetClassName=="QSpinBox":
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
      elif widgetClassName=="QCheckBox":
        self.valueEditWidgets[parameterName].connect("clicked()", self.updateParameterNodeFromGUI)
    for parameterName in self.nodeSelectorWidgets:
      self.nodeSelectorWidgets[parameterName].connect("currentNodeIDChanged(QString)", self.updateParameterNodeFromGUI)

  def removeGUIObservers(self):
    for parameterName in self.valueEditWidgets:
      widgetClassName = self.getClassName(self.valueEditWidgets[parameterName])
      if widgetClassName=="QSpinBox":
        self.valueEditWidgets[parameterName].disconnect("valueChanged(int)", self.updateParameterNodeFromGUI)
      elif widgetClassName=="QCheckBox":
        self.valueEditWidgets[parameterName].disconnect("clicked()", self.updateParameterNodeFromGUI)
    for parameterName in self.nodeSelectorWidgets:
      self.nodeSelectorWidgets[parameterName].disconnect("currentNodeIDChanged(QString)", self.updateParameterNodeFromGUI)

  def updateApplyButtonState(self):
    if not self.inputVolumeSelector.currentNode():
      self.applyButton.toolTip = "Input volume is required. Clip volume with surface model is disabled."
      self.applyButton.enabled = False
    elif not self.clippingModelSelector.currentNode():
      self.applyButton.toolTip = "Clipping surface is required (create new model or select existing model). Clip volume with surface model is disabled."
      self.applyButton.enabled = False
    elif not self.outputVolumeSelector.currentNode():
      self.applyButton.toolTip = "Output volume is required (create new volume or select existing volume). Clip volume with surface model is disabled."
      self.applyButton.enabled = False
    else:
      self.applyButton.toolTip = _("Clip volume with surface model.")
      self.applyButton.enabled = True

  def onInputVolumeSelect(self, node):
    self.updateApplyButtonState()

  def onClippingModelSelect(self, node):
    self.updateApplyButtonState()

  def onClippingMarkupSelect(self, node):
    self.setAndObserveClippingMarkupNode(self.clippingMarkupSelector.currentNode())

  def onOutputVolumeSelect(self, node):
    self.updateApplyButtonState()

  def onApplyButton(self):
    inputVolume = self.inputVolumeSelector.currentNode()
    outputVolume = self.outputVolumeSelector.currentNode()
    clippingModel = self.clippingModelSelector.currentNode()
    clipOutsideSurface = self.clipOutsideSurfaceCheckBox.checked
    clipInsideSurface = self.clipInsideSurfaceCheckBox.checked
    fillOutsideValue = self.fillOutsideValueEdit.value
    fillInsideValue = self.fillInsideValueEdit.value
    self.logic.clipVolumeWithModel(inputVolume, clippingModel, clipOutsideSurface, fillOutsideValue, clipInsideSurface, fillInsideValue, outputVolume)
    self.logic.showInSliceViewers(outputVolume, ["Red", "Yellow", "Green"])

#
# VolumeClipWithModelLogic
#

class VolumeClipWithModelLogic(ScriptedLoadableModuleLogic):
  """This class should implement all the actual
  computation done by your module.  The interface
  should be such that other python code can import
  this class and make use of the functionality without
  requiring an instance of the Widget
  """

  def createParameterNode(self):
    # Set default parameters
    node = ScriptedLoadableModuleLogic.createParameterNode(self)
    node.SetName(slicer.mrmlScene.GetUniqueNameByString(self.moduleName))
    node.SetParameter("clipOutsideSurface", "1")
    node.SetParameter("fillOutsideValue", "0")
    node.SetParameter("clipInsideSurface", "1")
    node.SetParameter("fillInsideValue", "255")
    return node

  def clipVolumeWithModel(self, inputVolume, clippingModel, clipOutsideSurface, fillOutsideValue, clipInsideSurface, fillInsideValue, outputVolume):
    """
    Fill voxels of the input volume inside/outside the clipping model with the provided fill value
    """

    # Determine the transform between the box and the image IJK coordinate systems

    rasToModel = vtk.vtkMatrix4x4()
    if clippingModel.GetTransformNodeID() != None:
      modelTransformNode = slicer.mrmlScene.GetNodeByID(clippingModel.GetTransformNodeID())
      boxToRas = vtk.vtkMatrix4x4()
      modelTransformNode.GetMatrixTransformToWorld(boxToRas)
      rasToModel.DeepCopy(boxToRas)
      rasToModel.Invert()

    ijkToRas = vtk.vtkMatrix4x4()
    inputVolume.GetIJKToRASMatrix( ijkToRas )

    ijkToModel = vtk.vtkMatrix4x4()
    vtk.vtkMatrix4x4.Multiply4x4(rasToModel,ijkToRas,ijkToModel)
    modelToIjkTransform = vtk.vtkTransform()
    modelToIjkTransform.SetMatrix(ijkToModel)
    modelToIjkTransform.Inverse()

    transformModelToIjk=vtk.vtkTransformPolyDataFilter()
    transformModelToIjk.SetTransform(modelToIjkTransform)
    transformModelToIjk.SetInputConnection(clippingModel.GetPolyDataConnection())

    # Use the stencil to fill the volume

    # Convert model to stencil
    polyToStencil = vtk.vtkPolyDataToImageStencil()
    polyToStencil.SetInputConnection(transformModelToIjk.GetOutputPort())
    polyToStencil.SetOutputSpacing(inputVolume.GetImageData().GetSpacing())
    polyToStencil.SetOutputOrigin(inputVolume.GetImageData().GetOrigin())
    polyToStencil.SetOutputWholeExtent(inputVolume.GetImageData().GetExtent())

    # Apply the stencil to the volume
    stencilToImage=vtk.vtkImageStencil()
    stencilToImage.SetInputConnection(inputVolume.GetImageDataConnection())
    stencilToImage.SetStencilConnection(polyToStencil.GetOutputPort())

    # Create a copy of the input volume to work on
    outputImageData = vtk.vtkImageData()
    outputImageData.DeepCopy(inputVolume.GetImageData())
    outputVolume.SetAndObserveImageData(outputImageData);
    outputVolume.SetIJKToRASMatrix(ijkToRas)

    # Update volume with the stencil operation result depending on user choices
    if clipOutsideSurface:
      stencilToImage.ReverseStencilOff()
      stencilToImage.SetBackgroundValue(fillOutsideValue)
      stencilToImage.Update()
      outputImageData.DeepCopy(stencilToImage.GetOutput())
      outputVolume.SetAndObserveImageData(outputImageData);
      outputVolume.SetIJKToRASMatrix(ijkToRas)

    if clipInsideSurface:
      stencilToImage.SetInputConnection(outputVolume.GetImageDataConnection())
      stencilToImage.ReverseStencilOn()
      stencilToImage.SetBackgroundValue(fillInsideValue)
      stencilToImage.Update()
      outputImageData.DeepCopy(stencilToImage.GetOutput())
      outputVolume.SetAndObserveImageData(outputImageData);
      outputVolume.SetIJKToRASMatrix(ijkToRas)

    # Add a default display node to output volume node if it does not exist yet
    if not outputVolume.GetDisplayNode:
      displayNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLScalarVolumeDisplayNode")
      displayNode.SetAndObserveColorNodeID("vtkMRMLColorTableNodeGrey")
      outputVolume.SetAndObserveDisplayNodeID(displayNode.GetID())

    return True

  def updateModelFromMarkup(self, inputMarkup, outputModel):
    """
    Update model to enclose all points in the input markup list
    """

    # Delaunay triangulation is robust and creates nice smooth surfaces from a small number of points,
    # however it can only generate convex surfaces robustly.
    useDelaunay = True

    # Create polydata point set from markup points

    points = vtk.vtkPoints()
    cellArray = vtk.vtkCellArray()

    numberOfPoints = inputMarkup.GetNumberOfFiducials()

    # Surface generation algorithms behave unpredictably when there are not enough points
    # return if there are very few points
    if useDelaunay:
      if numberOfPoints<3:
        return
    else:
      if numberOfPoints<10:
        return

    points.SetNumberOfPoints(numberOfPoints)
    new_coord = [0.0, 0.0, 0.0]

    for i in range(numberOfPoints):
      inputMarkup.GetNthFiducialPosition(i,new_coord)
      points.SetPoint(i, new_coord)

    cellArray.InsertNextCell(numberOfPoints)
    for i in range(numberOfPoints):
      cellArray.InsertCellPoint(i)

    pointPolyData = vtk.vtkPolyData()
    pointPolyData.SetLines(cellArray)
    pointPolyData.SetPoints(points)


    # Create surface from point set

    if useDelaunay:

      delaunay = vtk.vtkDelaunay3D()
      delaunay.SetInputData(pointPolyData)

      surfaceFilter = vtk.vtkDataSetSurfaceFilter()
      surfaceFilter.SetInputConnection(delaunay.GetOutputPort())

      smoother = vtk.vtkButterflySubdivisionFilter()
      smoother.SetInputConnection(surfaceFilter.GetOutputPort())
      smoother.SetNumberOfSubdivisions(3)
      smoother.Update()

      outputModel.SetPolyDataConnection(smoother.GetOutputPort())

    else:

      surf = vtk.vtkSurfaceReconstructionFilter()
      surf.SetInputData(pointPolyData)
      surf.SetNeighborhoodSize(20)
      surf.SetSampleSpacing(80) # lower value follows the small details more closely but more dense pointset is needed as input

      cf = vtk.vtkContourFilter()
      cf.SetInputConnection(surf.GetOutputPort())
      cf.SetValue(0, 0.0)

      # Sometimes the contouring algorithm can create a volume whose gradient
      # vector and ordering of polygon (using the right hand rule) are
      # inconsistent. vtkReverseSense cures this problem.
      reverse = vtk.vtkReverseSense()
      reverse.SetInputConnection(cf.GetOutputPort())
      reverse.ReverseCellsOff()
      reverse.ReverseNormalsOff()

      outputModel.SetPolyDataConnection(reverse.GetOutputPort())

    # Create default model display node if does not exist yet
    if not outputModel.GetDisplayNode():
      modelDisplayNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLModelDisplayNode")
      modelDisplayNode.SetColor(0,0,1) # Blue
      modelDisplayNode.BackfaceCullingOff()
      if slicer.app.majorVersion >= 5 or (slicer.app.majorVersion == 4 and slicer.app.minorVersion >= 11):
        modelDisplayNode.Visibility2DOn()
      else:
        modelDisplayNode.SliceIntersectionVisibilityOn()
      modelDisplayNode.SetOpacity(0.3) # Between 0-1, 1 being opaque
      outputModel.SetAndObserveDisplayNodeID(modelDisplayNode.GetID())

    if slicer.app.majorVersion >= 5 or (slicer.app.majorVersion == 4 and slicer.app.minorVersion >= 11):
      outputModel.GetDisplayNode().Visibility2DOn()
    else:
      outputModel.GetDisplayNode().SliceIntersectionVisibilityOn()

    outputModel.Modified()

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

class VolumeClipWithModelTest(ScriptedLoadableModuleTest):
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
    self.test_VolumeClipWithModel1()

  def test_VolumeClipWithModel1(self):

    # Download MRHead from sample data
    import SampleData
    sampleDataLogic = SampleData.SampleDataLogic()
    self.delayDisplay("Getting MR Head Volume")
    inputVolume = sampleDataLogic.downloadMRHead()

    # Create empty model node
    clippingModel = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLModelNode")

    # Create markup fiducials
    displayNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsDisplayNode")
    inputMarkup = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsFiducialNode")
    inputMarkup.SetName('C')
    inputMarkup.SetAndObserveDisplayNodeID(displayNode.GetID())
    inputMarkup.AddFiducial(35,-10,-10)
    inputMarkup.AddFiducial(-15,20,-10)
    inputMarkup.AddFiducial(-25,-25,-10)
    inputMarkup.AddFiducial(-5,-60,-15)
    inputMarkup.AddFiducial(-5,5,60)
    inputMarkup.AddFiducial(-5,-35,-30)

    # Create output volume
    outputVolume = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLScalarVolumeNode")

    # Clip volume
    logic = VolumeClipWithModelLogic()
    clipOutsideSurface = True
    fillOutsideValue = 0
    clipInsideSurface = True
    fillInsideValue = 255

    logic.updateModelFromMarkup(inputMarkup, clippingModel)
    logic.clipVolumeWithModel(inputVolume, clippingModel, clipOutsideSurface, fillOutsideValue, clipInsideSurface, fillInsideValue, outputVolume)
    logic.showInSliceViewers(outputVolume, ["Red", "Yellow", "Green"])

    self.delayDisplay("Test passed!")
