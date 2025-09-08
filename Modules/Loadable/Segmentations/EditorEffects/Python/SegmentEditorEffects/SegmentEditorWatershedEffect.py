import os
import vtk, qt, ctk, slicer
import logging
from SegmentEditorEffects import *

class SegmentEditorWatershedEffect(AbstractScriptedSegmentEditorAutoCompleteEffect):
  """This effect uses Watershed algorithm to partition the input volume"""

  def __init__(self, scriptedEffect):
    AbstractScriptedSegmentEditorAutoCompleteEffect.__init__(self, scriptedEffect)
    scriptedEffect.name = '分水岭'
    self.minimumNumberOfSegments = 2
    self.clippedMasterImageDataRequired = True # source volume intensities are used by this effect
    self.growCutFilter = None

  def clone(self):
    import qSlicerSegmentationsEditorEffectsPythonQt as effects
    clonedEffect = effects.qSlicerSegmentEditorScriptedEffect(None)
    clonedEffect.setPythonSource(__file__.replace('\\','/'))
    return clonedEffect

  def icon(self):
    iconPath = os.path.join(os.path.dirname(__file__), './Resources/Icons/Watershed.png')
    if os.path.exists(iconPath):
      return qt.QIcon(iconPath)
    return qt.QIcon()

  def helpText(self):
    return """<html>不断增长分割以创建完整的分割<br>.
考虑初始分割的位置、大小和形状以及源卷的内容。
最终的分割边界将放置在源体数据强度突然变化的位置。是一种基于分水岭算法的区域生长。说明：<p>
<ul style="margin: 0">
<li>使用 绘制功能 或其他效果功能在应属于单独分割的每个区域中绘制种子。
用不同的部分为每颗种子涂上不同的部分。至少需要两段分割。</li>
<li>点击 <dfn>初始化</dfn> 计算完整分割预览。</li>
<li>浏览图像切片，如果预览分割不正确，则切换到绘制或其他功能，
在错误分类的区域添加更多种子点，完整分割将在几秒后自动更新。</li>
<li>点击 <dfn>应用</dfn> 使用预览结果更新分割。</li>
</ul><p>
该效果于“区域生长”功能的效果不同，可以定义结构的平滑度，从而可以防止泄露。<p>
蒙版设置被绕过，如果分割重叠，则分割表中的排在上面的分割有优先权。
<p></html>"""

  def reset(self):
    self.growCutFilter = None
    AbstractScriptedSegmentEditorAutoCompleteEffect.reset(self)
    self.updateGUIFromMRML()

  def setupOptionsFrame(self):
    AbstractScriptedSegmentEditorAutoCompleteEffect.setupOptionsFrame(self)

     # Object scale slider
    self.objectScaleMmSlider = slicer.qMRMLSliderWidget()
    self.objectScaleMmSlider.setMRMLScene(slicer.mrmlScene)
    self.objectScaleMmSlider.quantity = "length" # get unit, precision, etc. from MRML unit node
    self.objectScaleMmSlider.minimum = 0.0001  # object scale of 0 would throw an exception when calling sitk.GradientMagnitudeRecursiveGaussian
    self.objectScaleMmSlider.maximum = 10
    self.objectScaleMmSlider.value = 2.0
    self.objectScaleMmSlider.setToolTip('该值越大，越能平滑分割并减少泄露。这是用于边缘检测的求和。')
    self.scriptedEffect.addLabeledOptionsWidget("对象规模：", self.objectScaleMmSlider)#Object scale:
    self.objectScaleMmSlider.connect('valueChanged(double)', self.updateAlgorithmParameterFromGUI)

  def setMRMLDefaults(self):
    AbstractScriptedSegmentEditorAutoCompleteEffect.setMRMLDefaults(self)
    self.scriptedEffect.setParameterDefault("ObjectScaleMm", 2.0)

  def updateGUIFromMRML(self):
    AbstractScriptedSegmentEditorAutoCompleteEffect.updateGUIFromMRML(self)
    objectScaleMm = self.scriptedEffect.doubleParameter("ObjectScaleMm")
    wasBlocked = self.objectScaleMmSlider.blockSignals(True)
    self.objectScaleMmSlider.value = abs(objectScaleMm)
    self.objectScaleMmSlider.blockSignals(wasBlocked)

  def updateMRMLFromGUI(self):
    AbstractScriptedSegmentEditorAutoCompleteEffect.updateMRMLFromGUI(self)
    self.scriptedEffect.setParameter("ObjectScaleMm", self.objectScaleMmSlider.value)

  def updateAlgorithmParameterFromGUI(self):
    self.updateMRMLFromGUI()

    # Trigger preview update
    if self.getPreviewNode():
      self.delayedAutoUpdateTimer.start()

  def computePreviewLabelmap(self, mergedImage, outputLabelmap):

    import vtkSegmentationCorePython as vtkSegmentationCore
    import vtkSlicerSegmentationsModuleLogicPython as vtkSlicerSegmentationsModuleLogic

    # This can be a long operation - indicate it to the user
    qt.QApplication.setOverrideCursor(qt.Qt.WaitCursor)

    sourceVolumeNode = slicer.vtkMRMLScalarVolumeNode()
    slicer.mrmlScene.AddNode(sourceVolumeNode)
    slicer.vtkSlicerSegmentationsModuleLogic.CopyOrientedImageDataToVolumeNode(self.clippedMasterImageData, sourceVolumeNode)

    mergedLabelmapNode = slicer.vtkMRMLLabelMapVolumeNode()
    slicer.mrmlScene.AddNode(mergedLabelmapNode)
    slicer.vtkSlicerSegmentationsModuleLogic.CopyOrientedImageDataToVolumeNode(mergedImage, mergedLabelmapNode)

    outputRasToIjk = vtk.vtkMatrix4x4()
    mergedImage.GetImageToWorldMatrix(outputRasToIjk)
    outputExtent = mergedImage.GetExtent()

    # Run segmentation algorithm
    import SimpleITK as sitk
    import sitkUtils
    # Read input data from Slicer into SimpleITK
    labelImage = sitk.ReadImage(sitkUtils.GetSlicerITKReadWriteAddress(mergedLabelmapNode.GetName()))
    backgroundImage = sitk.ReadImage(sitkUtils.GetSlicerITKReadWriteAddress(sourceVolumeNode.GetName()))
    # Run watershed filter
    featureImage = sitk.GradientMagnitudeRecursiveGaussian(backgroundImage, float(self.scriptedEffect.doubleParameter("ObjectScaleMm")))
    del backgroundImage
    f = sitk.MorphologicalWatershedFromMarkersImageFilter()
    f.SetMarkWatershedLine(False)
    f.SetFullyConnected(False)
    labelImage = f.Execute(featureImage, labelImage)
    del featureImage
    # Pixel type of watershed output is the same as the input. Convert it to int16 now.
    if labelImage.GetPixelID() != sitk.sitkInt16:
      labelImage = sitk.Cast(labelImage, sitk.sitkInt16)
    # Write result from SimpleITK to Slicer. This currently performs a deep copy of the bulk data.
    sitk.WriteImage(labelImage, sitkUtils.GetSlicerITKReadWriteAddress(mergedLabelmapNode.GetName()))

    # Update segmentation from labelmap node and remove temporary nodes
    outputLabelmap.ShallowCopy(mergedLabelmapNode.GetImageData())
    outputLabelmap.SetImageToWorldMatrix(outputRasToIjk)
    outputLabelmap.SetExtent(outputExtent)

    slicer.mrmlScene.RemoveNode(sourceVolumeNode)
    slicer.mrmlScene.RemoveNode(mergedLabelmapNode)

    qt.QApplication.restoreOverrideCursor()
