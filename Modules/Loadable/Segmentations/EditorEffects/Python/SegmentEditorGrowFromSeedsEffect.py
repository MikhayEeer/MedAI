import logging
import os
import time

import qt
import vtk

import slicer

from SegmentEditorEffects import *
from slicer.i18n import tr as _
from slicer.i18n import translate

class SegmentEditorGrowFromSeedsEffect(AbstractScriptedSegmentEditorAutoCompleteEffect):
    """ AutoCompleteEffect is an effect that can create a full segmentation
        from a partial segmentation (not all slices are segmented or only
        part of the target structures are painted).
    """

    def __init__(self, scriptedEffect):
        AbstractScriptedSegmentEditorAutoCompleteEffect.__init__(self, scriptedEffect)
        scriptedEffect.name = _("Grow from seeds")
        self.minimumNumberOfSegments = 2
        self.clippedMasterImageDataRequired = True  # source volume intensities are used by this effect
        self.clippedMaskImageDataRequired = True  # masking is used
        self.growCutFilter = None

    def clone(self):
        import qSlicerSegmentationsEditorEffectsPythonQt as effects
        clonedEffect = effects.qSlicerSegmentEditorScriptedEffect(None)
        clonedEffect.setPythonSource(__file__.replace('\\', '/'))
        return clonedEffect

    def icon(self):
        iconPath = os.path.join(os.path.dirname(__file__), 'Resources/Icons/GrowFromSeeds.png')
        if os.path.exists(iconPath):
            return qt.QIcon(iconPath)
        return qt.QIcon()

    def helpText(self):
        return _("""<html>使分割生长成完整的分割<br>。
考虑初始分割的位置、大小和形状以及源卷的内容。
最终的分割边界将放置在源体积亮度突然变化的位置。说明：<p>
<ul style="margin: 0">
<li>使用 绘画 或其他效果在应属于单独片段的每个区域中绘制种子。
用不同的部分为每颗种子涂上不同的部分。至少需要两段。</li>
<li>点击 <dfn>初始化</dfn> 来计算完整分割的预览。</li>
<li>浏览图像切片。如果预览的分割结果不正确，则切换到“绘画”或其他效果，
                 并在错误分类的区域中添加更多种子。完整分割将在几秒钟内自动更新</li>
<li>点击 <dfn>应用</dfn> 使用预览结果更新分割。</li>
</ul><p>
如果分割重叠，则分割表中较前的分割将具有优先权。
<p></html>""")

    def reset(self):
        self.growCutFilter = None
        AbstractScriptedSegmentEditorAutoCompleteEffect.reset(self)
        self.updateGUIFromMRML()

    def setupOptionsFrame(self):
        AbstractScriptedSegmentEditorAutoCompleteEffect.setupOptionsFrame(self)

        # Object scale slider
        self.seedLocalityFactorSlider = slicer.qMRMLSliderWidget()
        self.seedLocalityFactorSlider.setMRMLScene(slicer.mrmlScene)
        self.seedLocalityFactorSlider.minimum = 0
        self.seedLocalityFactorSlider.maximum = 10
        self.seedLocalityFactorSlider.value = 0.0
        self.seedLocalityFactorSlider.decimals = 1
        self.seedLocalityFactorSlider.singleStep = 0.1
        self.seedLocalityFactorSlider.pageStep = 1.0
        self.seedLocalityFactorSlider.setToolTip(_("""增加该值会使种子的影响更加局部化，从而减少泄漏，但要求种子区域在图像中分布更均匀。
                                                该值被指定为每“单位距离”的附加“强度水平差”。'"""))
        self.scriptedEffect.addLabeledOptionsWidget(_("种子点位置："), self.seedLocalityFactorSlider)
        self.seedLocalityFactorSlider.connect('valueChanged(double)', self.updateAlgorithmParameterFromGUI)

    def setMRMLDefaults(self):
        AbstractScriptedSegmentEditorAutoCompleteEffect.setMRMLDefaults(self)
        self.scriptedEffect.setParameterDefault("SeedLocalityFactor", 0.0)

    def updateGUIFromMRML(self):
        AbstractScriptedSegmentEditorAutoCompleteEffect.updateGUIFromMRML(self)
        if self.scriptedEffect.parameterDefined("SeedLocalityFactor"):
            seedLocalityFactor = self.scriptedEffect.doubleParameter("SeedLocalityFactor")
        else:
            seedLocalityFactor = 0.0
        wasBlocked = self.seedLocalityFactorSlider.blockSignals(True)
        self.seedLocalityFactorSlider.value = abs(seedLocalityFactor)
        self.seedLocalityFactorSlider.blockSignals(wasBlocked)

    def updateMRMLFromGUI(self):
        AbstractScriptedSegmentEditorAutoCompleteEffect.updateMRMLFromGUI(self)
        self.scriptedEffect.setParameter("SeedLocalityFactor", self.seedLocalityFactorSlider.value)

    def updateAlgorithmParameterFromGUI(self):
        self.updateMRMLFromGUI()

        # Trigger preview update
        if self.getPreviewNode():
            self.delayedAutoUpdateTimer.start()

    def computePreviewLabelmap(self, mergedImage, outputLabelmap):
        import vtkITK

        if not self.growCutFilter:
            self.growCutFilter = vtkITK.vtkITKGrowCut()
            self.growCutFilter.SetIntensityVolume(self.clippedMasterImageData)
            self.growCutFilter.SetMaskVolume(self.clippedMaskImageData)
            maskExtent = self.clippedMaskImageData.GetExtent() if self.clippedMaskImageData else None
            if maskExtent is not None and maskExtent[0] <= maskExtent[1] and maskExtent[2] <= maskExtent[3] and maskExtent[4] <= maskExtent[5]:
                # Mask is used.
                # Grow the extent more, as background segment does not surround region of interest.
                self.extentGrowthRatio = 0.50
            else:
                # No masking is used.
                # Background segment is expected to surround region of interest, so narrower margin is enough.
                self.extentGrowthRatio = 0.20

        if self.scriptedEffect.parameterDefined("SeedLocalityFactor"):
            seedLocalityFactor = self.scriptedEffect.doubleParameter("SeedLocalityFactor")
        else:
            seedLocalityFactor = 0.0
        self.growCutFilter.SetDistancePenalty(seedLocalityFactor)
        self.growCutFilter.SetSeedLabelVolume(mergedImage)
        startTime = time.time()
        self.growCutFilter.Update()
        logging.info('Grow-cut operation on volume of {}x{}x{} voxels was completed in {:3.1f} seconds.'.format(
            self.clippedMasterImageData.GetDimensions()[0],
            self.clippedMasterImageData.GetDimensions()[1],
            self.clippedMasterImageData.GetDimensions()[2],
            time.time() - startTime))

        outputLabelmap.DeepCopy(self.growCutFilter.GetOutput())
        imageToWorld = vtk.vtkMatrix4x4()
        mergedImage.GetImageToWorldMatrix(imageToWorld)
        outputLabelmap.SetImageToWorldMatrix(imageToWorld)
