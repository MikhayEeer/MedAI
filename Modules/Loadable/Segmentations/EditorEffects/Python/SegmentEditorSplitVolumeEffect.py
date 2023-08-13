# This is a complete example that computes histogram for each region of a volume defined by a segment.
# This script requires installation of  SegmentEditorExtraEffects extension, as it uses the Split volume effect,
# which is provided by this extension.

import os
import vtk, qt, ctk, slicer
import logging
from SegmentEditorEffects import *
import vtkSegmentationCorePython as vtkSegmentationCore
import sitkUtils
import SimpleITK as sitk


class SegmentEditorSplitVolumeEffect(AbstractScriptedSegmentEditorEffect):
  """This effect creates a volume for each segment, cropped to the segment extent with optional padding."""

  def __init__(self, scriptedEffect):
    scriptedEffect.name = '划分体数据'
    scriptedEffect.perSegment = True # this effect operates on a single selected segment
    AbstractScriptedSegmentEditorEffect.__init__(self, scriptedEffect)

  def clone(self):
    # It should not be necessary to modify this method
    import qSlicerSegmentationsEditorEffectsPythonQt as effects
    clonedEffect = effects.qSlicerSegmentEditorScriptedEffect(None)
    clonedEffect.setPythonSource(__file__.replace('\\','/'))
    return clonedEffect

  def icon(self):
    # It should not be necessary to modify this method
    iconPath = os.path.join(os.path.dirname(__file__), 'Resources/Icons/SplitVolume.png')
    if os.path.exists(iconPath):
      return qt.QIcon(iconPath)
    return qt.QIcon()

  def helpText(self):
    return """为裁剪到分割范围的每个可见分割或仅选定分割创建数据节点。\n
“Extent”沿每个轴按指定数量的填充体素展开。分割外的体素将设置为请求的填充值。
生成的数据不受分割撤消/重做操作的影响。
</html>"""

  def setMRMLDefaults(self):
    self.scriptedEffect.setParameterDefault("FillValue", "0")
    self.scriptedEffect.setParameterDefault("PaddingVoxels", "5")
    self.scriptedEffect.setParameterDefault("ApplyToAllVisibleSegments", "1")

  def updateGUIFromMRML(self):
    wasBlocked = self.fillValueEdit.blockSignals(True)
    try:
      self.fillValueEdit.setValue(int(self.scriptedEffect.parameter("FillValue")))
    except:
      self.fillValueEdit.setValue(0)
    self.fillValueEdit.blockSignals(wasBlocked)

    wasBlocked = self.padEdit.blockSignals(True)
    try:
      self.padEdit.setValue(int(self.scriptedEffect.parameter("PaddingVoxels")))
    except:
      self.padEdit.setValue(5)
    self.padEdit.blockSignals(wasBlocked)

    wasBlocked = self.applyToAllVisibleSegmentsCheckBox.blockSignals(True)
    checked = (self.scriptedEffect.integerParameter("ApplyToAllVisibleSegments") != 0)
    self.applyToAllVisibleSegmentsCheckBox.setChecked(checked)
    self.applyToAllVisibleSegmentsCheckBox.blockSignals(wasBlocked)

  def updateMRMLFromGUI(self):
    self.scriptedEffect.setParameter("FillValue", self.fillValueEdit.value)
    self.scriptedEffect.setParameter("PaddingVoxels", self.padEdit.value)
    self.scriptedEffect.setParameter("ApplyToAllVisibleSegments", "1" if  (self.applyToAllVisibleSegmentsCheckBox.isChecked()) else "0")

  def onAllSegmentsCheckboxStateChanged(self, newState):
    self.scriptedEffect.setParameter("ApplyToAllVisibleSegments", "1" if  (self.applyToAllVisibleSegmentsCheckBox.isChecked()) else "0")

  def setupOptionsFrame(self):

    # input volume selector
    self.inputVolumeSelector = slicer.qMRMLNodeComboBox()
    self.inputVolumeSelector.nodeTypes = ["vtkMRMLScalarVolumeNode"]
    self.inputVolumeSelector.selectNodeUponCreation = True
    self.inputVolumeSelector.addEnabled = True
    self.inputVolumeSelector.removeEnabled = True
    self.inputVolumeSelector.noneEnabled = True
    self.inputVolumeSelector.noneDisplay = "(Source volume)"
    self.inputVolumeSelector.showHidden = False
    self.inputVolumeSelector.setMRMLScene(slicer.mrmlScene)
    self.inputVolumeSelector.setToolTip("要拆分的数据。 默认为当前源数据节点。")
    self.inputVolumeSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.updateMRMLFromGUI)

    inputLayout = qt.QHBoxLayout()
    inputLayout.addWidget(self.inputVolumeSelector)
    self.scriptedEffect.addLabeledOptionsWidget("输入体数据：", inputLayout)

    # Pad size
    self.padEdit = qt.QSpinBox()
    self.padEdit.setToolTip("选择用于在每个维度中填充图像的体素数量")
    self.padEdit.minimum = 0
    self.padEdit.maximum = 1000
    self.padEdit.connect("valueChanged(int)", self.updateMRMLFromGUI)
    self.padLabel = qt.QLabel("填充体素：")

    # Fill value layouts
    # addWidget(*Widget, row, column, rowspan, colspan)
    padValueLayout = qt.QFormLayout()
    padValueLayout.addRow(self.padLabel, self.padEdit)

    self.scriptedEffect.addOptionsWidget(padValueLayout)

    self.fillValueEdit = qt.QSpinBox()
    self.fillValueEdit.setToolTip("选择将用于填充输出体数据的体素强度。")
    self.fillValueEdit.minimum = -32768
    self.fillValueEdit.maximum = 65535
    self.fillValueEdit.value=0
    self.fillValueEdit.connect("valueChanged(int)", self.updateMRMLFromGUI)
    self.fillValueLabel = qt.QLabel("填充值：")

    fillValueLayout = qt.QFormLayout()
    fillValueLayout.addRow(self.fillValueLabel, self.fillValueEdit)
    self.scriptedEffect.addOptionsWidget(fillValueLayout)

    # Segment scope checkbox layout
    self.applyToAllVisibleSegmentsCheckBox = qt.QCheckBox()
    self.applyToAllVisibleSegmentsCheckBox.setChecked(True)
    self.applyToAllVisibleSegmentsCheckBox.setToolTip("应用于所有可见分割，或仅用于选定分割")
    self.scriptedEffect.addLabeledOptionsWidget("应用到可见分割", self.applyToAllVisibleSegmentsCheckBox)
    # Connection
    self.applyToAllVisibleSegmentsCheckBox.connect('stateChanged(int)', self.onAllSegmentsCheckboxStateChanged)

    # Apply button
    self.applyButton = qt.QPushButton("应用")
    self.applyButton.objectName = self.__class__.__name__ + 'Apply'
    self.applyButton.setToolTip("为每个可见分割生成体数据")
    self.scriptedEffect.addOptionsWidget(self.applyButton)
    self.applyButton.connect('clicked()', self.onApply)

  def createCursor(self, widget):
    # Turn off effect-specific cursor for this effect
    return slicer.util.mainWindow().cursor

  def getInputVolume(self):
    inputVolume = self.inputVolumeSelector.currentNode()
    if inputVolume is None:
      inputVolume = self.scriptedEffect.parameterSetNode().GetSourceVolumeNode()
    return inputVolume

  def onApply(self):
    import SegmentEditorEffects
    maskVolumeWithSegment = SegmentEditorEffects.SegmentEditorMaskVolumeEffect.maskVolumeWithSegment

    inputVolume = self.getInputVolume()
    currentSegmentID = self.scriptedEffect.parameterSetNode().GetSelectedSegmentID()
    segmentationNode = self.scriptedEffect.parameterSetNode().GetSegmentationNode()
    volumesLogic = slicer.modules.volumes.logic()
    scene = inputVolume.GetScene()
    padExtent = [-self.padEdit.value, self.padEdit.value, -self.padEdit.value, self.padEdit.value, -self.padEdit.value, self.padEdit.value]
    fillValue = self.fillValueEdit.value

    # Create a new folder in subject hierarchy where all the generated volumes will be placed into
    shNode = slicer.vtkMRMLSubjectHierarchyNode.GetSubjectHierarchyNode(slicer.mrmlScene)
    inputVolumeParentItem = shNode.GetItemParent(shNode.GetItemByDataNode(inputVolume))
    outputShFolder = shNode.CreateFolderItem(inputVolumeParentItem, inputVolume.GetName()+" split")

    # Filter out visible segments, or only the selected segment, irrespective of its visibility.
    slicer.app.setOverrideCursor(qt.Qt.WaitCursor)
    visibleSegmentIDs = vtk.vtkStringArray()
    segmentationNode.GetDisplayNode().GetVisibleSegmentIDs(visibleSegmentIDs)
    if (self.scriptedEffect.integerParameter("ApplyToAllVisibleSegments") != 0):
        inputSegments = []
        for segmentIndex in range(visibleSegmentIDs.GetNumberOfValues()):
            inputSegments.append(visibleSegmentIDs.GetValue(segmentIndex))
    else:
        inputSegments = [currentSegmentID]
    # Iterate over targeted segments
    for segmentID in inputSegments:
      # Create volume for output
      outputVolumeName = inputVolume.GetName() + ' ' + segmentationNode.GetSegmentation().GetSegment(segmentID).GetName()
      outputVolume = volumesLogic.CloneVolumeGeneric(scene, inputVolume, outputVolumeName, False)

      # Crop segment
      maskExtent = [0] * 6
      maskVolumeWithSegment(segmentationNode, segmentID, "FILL_OUTSIDE", [fillValue], inputVolume, outputVolume, maskExtent)

      # Calculate padded extent of segment
      extent = [0] * 6
      for i in range(len(extent)):
        extent[i] = maskExtent[i] + padExtent[i]

      # Calculate the new origin
      ijkToRas = vtk.vtkMatrix4x4()
      outputVolume.GetIJKToRASMatrix(ijkToRas)
      origin_IJK = [extent[0], extent[2], extent[4], 1]
      origin_RAS = ijkToRas.MultiplyPoint(origin_IJK)

      # Pad and crop
      padFilter = vtk.vtkImageConstantPad()
      padFilter.SetInputData(outputVolume.GetImageData())
      padFilter.SetConstant(fillValue)
      padFilter.SetOutputWholeExtent(extent)
      padFilter.Update()
      paddedImg = padFilter.GetOutput()

      # Normalize output image
      paddedImg.SetOrigin(0,0,0)
      paddedImg.SetSpacing(1.0, 1.0, 1.0)
      paddedImg.SetExtent(0, extent[1]-extent[0], 0, extent[3]-extent[2], 0, extent[5]-extent[4])
      outputVolume.SetAndObserveImageData(paddedImg)
      outputVolume.SetOrigin(origin_RAS[0], origin_RAS[1], origin_RAS[2])

      # Place output image in subject hierarchy folder
      shNode.SetItemParent(shNode.GetItemByDataNode(outputVolume), outputShFolder)

    qt.QApplication.restoreOverrideCursor()
