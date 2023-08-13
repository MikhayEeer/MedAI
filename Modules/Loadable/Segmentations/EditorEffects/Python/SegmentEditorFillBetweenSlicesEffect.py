import os

import qt
import vtk

from SegmentEditorEffects import *


class SegmentEditorFillBetweenSlicesEffect(AbstractScriptedSegmentEditorAutoCompleteEffect):
    """ AutoCompleteEffect is an effect that can create a full segmentation
        from a partial segmentation (not all slices are segmented or only
        part of the target structures are painted).
    """

    def __init__(self, scriptedEffect):
        AbstractScriptedSegmentEditorAutoCompleteEffect.__init__(self, scriptedEffect)
        scriptedEffect.name = '填充切片'

    def clone(self):
        import qSlicerSegmentationsEditorEffectsPythonQt as effects
        clonedEffect = effects.qSlicerSegmentEditorScriptedEffect(None)
        clonedEffect.setPythonSource(__file__.replace('\\', '/'))
        return clonedEffect

    def icon(self):
        iconPath = os.path.join(os.path.dirname(__file__), 'Resources/Icons/FillBetweenSlices.png')
        if os.path.exists(iconPath):
            return qt.QIcon(iconPath)
        return qt.QIcon()

    def helpText(self):
        return """<html>切片之间的插值分割<br>。 说明：
<p><ul>
<li>使用任何编辑器效果在选定切片上创建完整的分割。
仅当切片被分割但没有直接邻居被分割时，分割才会扩展，
因此不要使用具有 Paint 效果的球体画笔，并且始终在分割的切片之间保留至少一个空切片。</li>
<li>所有可见分割都将被插值，而不仅仅是所选段。</li>
<li>完整的分割将通过在空切片中插入分割来创建。</li>
</ul><p>
屏蔽设置将被忽略。如果分割重叠，则分割表中较高的分割将具有优先权。
The effect uses  <a href="https://insight-journal.org/browse/publication/977">morphological contour interpolation method</a>.
<p></html>"""

    def computePreviewLabelmap(self, mergedImage, outputLabelmap):
        import vtkITK
        interpolator = vtkITK.vtkITKMorphologicalContourInterpolator()
        interpolator.SetInputData(mergedImage)
        interpolator.Update()
        outputLabelmap.DeepCopy(interpolator.GetOutput())
        imageToWorld = vtk.vtkMatrix4x4()
        mergedImage.GetImageToWorldMatrix(imageToWorld)
        outputLabelmap.SetImageToWorldMatrix(imageToWorld)
