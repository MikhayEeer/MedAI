import os
import vtk, qt, slicer
import logging
import numpy as np
import vtkSegmentationCorePython as vtkSegmentationCore
from SegmentEditorEffects import *

class SegmentEditorSurfaceCutEffect(AbstractScriptedSegmentEditorEffect):
  """This effect uses markup fiducials to segment the input volume"""

  def __init__(self, scriptedEffect):
    scriptedEffect.name = '表面切割'
    scriptedEffect.perSegment = True # this effect operates on a single selected segment
    AbstractScriptedSegmentEditorEffect.__init__(self, scriptedEffect)

    self.logic = SurfaceCutLogic(scriptedEffect)

    # Effect-specific members
    self.segmentMarkupNode = None
    self.segmentMarkupNodeObservers = []
    self.segmentEditorNode = None
    self.segmentEditorNodeObserver = None
    self.segmentModel = None
    self.observedSegmentation = None
    self.segmentObserver = None
    self.buttonToOperationNameMap = {}
    self.pointsBeingEdited = ""  # list of coordinates of points that were being edited when the effect was deactivated

  def clone(self):
    # It should not be necessary to modify this method
    import qSlicerSegmentationsEditorEffectsPythonQt as effects
    clonedEffect = effects.qSlicerSegmentEditorScriptedEffect(None)
    clonedEffect.setPythonSource(__file__.replace('\\','/'))
    return clonedEffect

  def icon(self):
    # It should not be necessary to modify this method
    iconPath = os.path.join(os.path.dirname(__file__), './Resources/Icons/SurfaceCut.png')
    if os.path.exists(iconPath):
      return qt.QIcon(iconPath)
    return qt.QIcon()

  def helpText(self):
    return """<html>使用基础标记填充分割<br>。曲面由放置的点生成。
</html>"""

  def setupOptionsFrame(self):
    self.operationRadioButtons = []

    #Fiducial Placement widget
    self.fiducialPlacementToggle = slicer.qSlicerMarkupsPlaceWidget()
    self.fiducialPlacementToggle.setMRMLScene(slicer.mrmlScene)
    self.fiducialPlacementToggle.placeMultipleMarkups = self.fiducialPlacementToggle.ForcePlaceMultipleMarkups
    self.fiducialPlacementToggle.buttonsVisible = False
    self.fiducialPlacementToggle.show()
    self.fiducialPlacementToggle.placeButton().show()
    self.fiducialPlacementToggle.deleteButton().show()

    # Edit surface button
    self.editButton = qt.QPushButton("编辑")
    self.editButton.objectName = self.__class__.__name__ + 'Edit'
    self.editButton.setToolTip("编辑先前放置的组")

    fiducialAction = qt.QHBoxLayout()
    fiducialAction.addWidget(self.fiducialPlacementToggle)
    fiducialAction.addWidget(self.editButton)
    self.scriptedEffect.addLabeledOptionsWidget("基础放置：", fiducialAction)

    #Operation buttons
    self.eraseInsideButton = qt.QRadioButton("擦除内部")
    self.operationRadioButtons.append(self.eraseInsideButton)
    self.buttonToOperationNameMap[self.eraseInsideButton] = 'ERASE_INSIDE'

    self.eraseOutsideButton = qt.QRadioButton("擦除外部")
    self.operationRadioButtons.append(self.eraseOutsideButton)
    self.buttonToOperationNameMap[self.eraseOutsideButton] = 'ERASE_OUTSIDE'

    self.fillInsideButton = qt.QRadioButton("填充内部")
    self.operationRadioButtons.append(self.fillInsideButton)
    self.buttonToOperationNameMap[self.fillInsideButton] = 'FILL_INSIDE'

    self.fillOutsideButton = qt.QRadioButton("填充外部")
    self.operationRadioButtons.append(self.fillOutsideButton)
    self.buttonToOperationNameMap[self.fillOutsideButton] = 'FILL_OUTSIDE'

    self.setButton = qt.QRadioButton("设定")
    self.operationRadioButtons.append(self.setButton)
    self.buttonToOperationNameMap[self.setButton] = 'SET'

    #Operation buttons layout
    operationLayout = qt.QGridLayout()
    operationLayout.addWidget(self.eraseInsideButton, 0, 0)
    operationLayout.addWidget(self.eraseOutsideButton, 1, 0)
    operationLayout.addWidget(self.fillInsideButton, 0, 1)
    operationLayout.addWidget(self.fillOutsideButton, 1, 1)
    operationLayout.addWidget(self.setButton, 0, 2)

    self.scriptedEffect.addLabeledOptionsWidget("操作：", operationLayout)

    # Smooth model checkbox layout
    self.smoothModelCheckbox = qt.QCheckBox()
    self.smoothModelCheckbox.setChecked(True) # model smoothing initial default is True
    self.smoothModelCheckbox.setToolTip("勾选后，则模型是平滑的；不勾选则是分面的。")
    self.scriptedEffect.addLabeledOptionsWidget("平滑模型：", self.smoothModelCheckbox)

    # 是否保留原段
    self.keepOriginSegmentCheckbox = qt.QCheckBox()
    self.keepOriginSegmentCheckbox.setChecked(True) # model smoothing initial default is True
    self.keepOriginSegmentCheckbox.setToolTip("勾选后，则保留原来的分割；不勾选则是不保留原来的分割。")
    self.scriptedEffect.addLabeledOptionsWidget("保留原分割：", self.keepOriginSegmentCheckbox)

    # Apply button
    self.applyButton = qt.QPushButton("应用")
    self.applyButton.objectName = self.__class__.__name__ + 'Apply'
    self.applyButton.setToolTip("从基础标记生成曲面。")
    self.scriptedEffect.addOptionsWidget(self.applyButton)

    # Cancel button
    self.cancelButton = qt.QPushButton("取消")
    self.cancelButton.objectName = self.__class__.__name__ + 'Cancel'
    self.cancelButton.setToolTip("清除并从场景移除标记。")

    #Finish action buttons
    finishAction = qt.QHBoxLayout()
    finishAction.addWidget(self.cancelButton)
    finishAction.addWidget(self.applyButton)
    self.scriptedEffect.addOptionsWidget(finishAction)

    # connections
    for button in self.operationRadioButtons:
      button.connect('toggled(bool)',
      lambda toggle, widget=self.buttonToOperationNameMap[button]: self.onOperationSelectionChanged(widget, toggle))
    self.smoothModelCheckbox.connect('stateChanged(int)', self.onSmoothModelCheckboxStateChanged)
    self.keepOriginSegmentCheckbox.connect('stateChanged(int)', self.onKeepOriginSegmentCheckboxStateChanged)
    self.applyButton.connect('clicked()', self.onApply)
    self.cancelButton.connect('clicked()', self.onCancel)
    self.editButton.connect('clicked()', self.onEdit)
    self.fiducialPlacementToggle.placeButton().clicked.connect(self.onFiducialPlacementToggleChanged)

  def activate(self):
    self.scriptedEffect.showEffectCursorInSliceView = False
    # Create model node prior to markup node to display markups over the model
    if not self.segmentModel:
      self.createNewModelNode()
    # Create empty markup fiducial node
    if not self.segmentMarkupNode:
      self.createNewMarkupNode()
      self.fiducialPlacementToggle.setCurrentNode(self.segmentMarkupNode)
      self.setAndObserveSegmentMarkupNode(self.segmentMarkupNode)
      self.fiducialPlacementToggle.setPlaceModeEnabled(False)
    self.setAndObserveSegmentEditorNode(self.scriptedEffect.parameterSetNode())
    self.observeSegmentation(True)
    self.updateGUIFromMRML()

    if self.pointsBeingEdited:
      self.logic.setPointsFromString(self.segmentMarkupNode, self.pointsBeingEdited)

  def deactivate(self):
    # Save points when the effect is deactivated to prevent the user from losing his work
    self.pointsBeingEdited = self.logic.getPointsAsString(self.segmentMarkupNode)

    self.reset()
    self.observeSegmentation(False)
    self.setAndObserveSegmentEditorNode(None)

  def createCursor(self, widget):
    # Turn off effect-specific cursor for this effect
    return slicer.util.mainWindow().cursor

  def setMRMLDefaults(self):
    self.scriptedEffect.setParameterDefault("Operation", "ERASE_INSIDE")
    self.scriptedEffect.setParameterDefault("SmoothModel", 1)
    self.scriptedEffect.setParameterDefault("keepOriginSegment", 1)

  def updateGUIFromMRML(self):
    if slicer.mrmlScene.IsClosing():
      return

    if self.segmentMarkupNode:
      self.cancelButton.setEnabled(self.getNumberOfDefinedControlPoints() != 0)
      self.applyButton.setEnabled(self.getNumberOfDefinedControlPoints() >= 3)

    segmentID = self.scriptedEffect.parameterSetNode().GetSelectedSegmentID()
    segmentationNode = self.scriptedEffect.parameterSetNode().GetSegmentationNode()
    if segmentID and segmentationNode:
      segment = segmentationNode.GetSegmentation().GetSegment(segmentID)
      if segment:
        self.editButton.setVisible(segment.HasTag("SurfaceCutEffectMarkupPositions"))

    operationName = self.scriptedEffect.parameter("Operation")
    if operationName != "":
      operationButton = list(self.buttonToOperationNameMap.keys())[list(self.buttonToOperationNameMap.values()).index(operationName)]
      operationButton.setChecked(True)

    self.smoothModelCheckbox.setChecked(
      self.scriptedEffect.integerParameter("SmoothModel") != 0)
    
    self.keepOriginSegmentCheckbox.setChecked(
      self.scriptedEffect.integerParameter("keepOriginSegment") != 0)
  #
  # Effect specific methods (the above ones are the API methods to override)
  #

  def onOperationSelectionChanged(self, operationName, toggle):
    if not toggle:
      return
    self.scriptedEffect.setParameter("Operation", operationName)

  def onKeepOriginSegmentCheckboxStateChanged(self, newState):
    keep = 1 if self.keepOriginSegmentCheckbox.isChecked() else 0
    self.scriptedEffect.setParameter("keepOriginSegment", keep)
    self.updateGUIFromMRML()

  def onSmoothModelCheckboxStateChanged(self, newState):
    smoothing = 1 if self.smoothModelCheckbox.isChecked() else 0
    self.scriptedEffect.setParameter("SmoothModel", smoothing)
    self.updateModelFromSegmentMarkupNode()
    self.updateGUIFromMRML()

  def onFiducialPlacementToggleChanged(self):
    if self.fiducialPlacementToggle.placeButton().isChecked():
      # Create empty model node
      if self.segmentModel is None:
        self.createNewModelNode()

      # Create empty markup fiducial node
      if self.segmentMarkupNode is None:
        self.createNewMarkupNode()
        self.fiducialPlacementToggle.setCurrentNode(self.segmentMarkupNode)

  def onSegmentModified(self, caller, event):
    if not self.editButton.isEnabled() and self.segmentMarkupNode.GetNumberOfControlPoints() != 0:
      self.reset()
      # Create model node prior to markup node for display order
      self.createNewModelNode()
      self.createNewMarkupNode()
      self.fiducialPlacementToggle.setCurrentNode(self.segmentMarkupNode)
    else:
      self.updateGUIFromMRML()

    if self.segmentModel:
      # Get color of edited segment
      segmentationNode = self.scriptedEffect.parameterSetNode().GetSegmentationNode()
      displayNode = segmentationNode.GetDisplayNode()
      if displayNode is None:
        logging.error("preview: Invalid segmentation display node!")
        color = [0.5, 0.5, 0.5]
      if self.segmentModel.GetDisplayNode():
        segmentID = self.scriptedEffect.parameterSetNode().GetSelectedSegmentID()
        if segmentID:
          segment = segmentationNode.GetSegmentation().GetSegment(segmentID)
          if segment:
            r, g, b = segment.GetColor()
            if (r,g,b) != self.segmentModel.GetDisplayNode().GetColor():
              self.segmentModel.GetDisplayNode().SetColor(r, g, b)  # Edited segment color

  def onCancel(self):
    self.reset()
    # Create model node prior to markup node for display order
    self.createNewModelNode()
    self.createNewMarkupNode()
    self.fiducialPlacementToggle.setCurrentNode(self.segmentMarkupNode)

  def onEdit(self):
    # Create empty model node
    if self.segmentModel is None:
      self.createNewModelNode()

    segmentID = self.scriptedEffect.parameterSetNode().GetSelectedSegmentID()
    segmentationNode = self.scriptedEffect.parameterSetNode().GetSegmentationNode()
    segment = segmentationNode.GetSegmentation().GetSegment(segmentID)

    fPosStr = vtk.mutable("")
    segment.GetTag("SurfaceCutEffectMarkupPositions", fPosStr)
    self.logic.setPointsFromString(self.segmentMarkupNode, fPosStr)

    self.editButton.setEnabled(False)
    self.updateModelFromSegmentMarkupNode()

  def reset(self):
    if self.fiducialPlacementToggle.placeModeEnabled:
      self.fiducialPlacementToggle.setPlaceModeEnabled(False)

    if not self.editButton.isEnabled():
      self.editButton.setEnabled(True)

    if self.segmentModel:
      if self.segmentModel.GetScene():
        slicer.mrmlScene.RemoveNode(self.segmentModel)
      self.segmentModel = None

    if self.segmentMarkupNode:
      if self.segmentMarkupNode.GetScene():
        slicer.mrmlScene.RemoveNode(self.segmentMarkupNode)
      self.setAndObserveSegmentMarkupNode(None)

  def extend_surface_2(self,points, expansion_factor=1.3,height=100.0):
      # 计算新的扩展点
      expanded_points = []

      for point in points:
          vector = np.array(point) - np.mean(points, axis=0)
          expanded_point = np.array(point) + vector * expansion_factor+(0,0,height)
          expanded_points.append(expanded_point.tolist())
      return expanded_points    
    
  def extend_surface_1(self,points, expansion_factor=1.3):
      # 计算新的扩展点
      expanded_points = []

      for point in points:
          vector = np.array(point) - np.mean(points, axis=0)
          expanded_point = np.array(point) + vector * expansion_factor
          expanded_points.append(expanded_point.tolist())
      return expanded_points

  def getBoundPoints(self,points):
      # 创建vtkPoints对象并插入点
      vtk_points = vtk.vtkPoints()
      for point in points:
        vtk_points.InsertNextPoint(point)

      # 创建一个PolyData对象来存储点
      poly_data = vtk.vtkPolyData()
      poly_data.SetPoints(vtk_points)

      # 使用Delaunay2D进行三角化
      delaunay = vtk.vtkDelaunay2D()
      delaunay.SetInputData(poly_data)
      delaunay.Update()

      # 提取最外围的点
      boundary_filter = vtk.vtkFeatureEdges()
      boundary_filter.SetInputData(delaunay.GetOutput())
      boundary_filter.BoundaryEdgesOn()
      boundary_filter.NonManifoldEdgesOff()
      boundary_filter.FeatureEdgesOff()
      boundary_filter.ManifoldEdgesOff()
      boundary_filter.Update()

      # 获取最外围点
      boundary_points = boundary_filter.GetOutput().GetPoints()

      pp = [boundary_points.GetPoint(i) for i in range(boundary_points.GetNumberOfPoints())]

      return pp

  # 未修改前
  def onApplyBefore(self):
    logging.warning("start cut lalalal")

    if self.getNumberOfDefinedControlPoints() < 3:
      logging.warning("Cannot apply, segment markup node has less than 3 control points")
      return

    # Allow users revert to this state by clicking Undo
    self.scriptedEffect.saveStateForUndo()

    # This can be a long operation - indicate it to the user
    qt.QApplication.setOverrideCursor(qt.Qt.WaitCursor)
    self.observeSegmentation(False)
    self.logic.cutSurfaceWithModel(self.segmentMarkupNode, self.segmentModel)
    self.reset()
    # Create model node prior to markup node for display order
    self.createNewModelNode()
    self.createNewMarkupNode()
    self.fiducialPlacementToggle.setCurrentNode(self.segmentMarkupNode)
    self.observeSegmentation(True)
    qt.QApplication.restoreOverrideCursor()


  def onApplyMy(self):
    logging.warning("start cut lalalal")

    f = slicer.modules.SegmentEditorWidget.editor.activeEffect().self().segmentMarkupNode
    points  = [f.GetNthControlPointPosition(i) for i in range(f.GetNumberOfControlPoints())]

    points=self.getBoundPoints(points)
    ext_points=self.extend_surface_1(points,1.4)

    cur_segment_id=slicer.modules.SegmentEditorWidget.editor.currentSegmentID()
    cur_segment=slicer.modules.SegmentEditorWidget.editor.activeEffect().parameterSetNode().GetSegmentationNode().GetSegmentation().GetSegment(cur_segment_id)
    cur_segment_name=cur_segment.GetName()

    slicer.modules.SegmentEditorWidget.editor.activeEffect().parameterSetNode().SetMaskSegmentID(cur_segment_id)

    segment_id_1=slicer.modules.SegmentEditorWidget.editor.activeEffect().parameterSetNode().GetSegmentationNode().GetSegmentation().GenerateUniqueSegmentID(cur_segment_id)
    segment_id_2=slicer.modules.SegmentEditorWidget.editor.activeEffect().parameterSetNode().GetSegmentationNode().GetSegmentation().GenerateUniqueSegmentID(cur_segment_id)

    segment_1 = vtkSegmentationCore.vtkSegment()
    segment_1.DeepCopy(cur_segment)
    segment_2 = vtkSegmentationCore.vtkSegment()
    segment_2.DeepCopy(cur_segment)

    slicer.modules.SegmentEditorWidget.editor.activeEffect().parameterSetNode().GetSegmentationNode().GetSegmentation().AddSegment(segment_1,segment_id_1)
    slicer.modules.SegmentEditorWidget.editor.activeEffect().parameterSetNode().GetSegmentationNode().GetSegmentation().AddSegment(segment_2,segment_id_2)

    slicer.modules.SegmentEditorWidget.editor.activeEffect().parameterSetNode().GetSegmentationNode().GetSegmentation().GetSegment(segment_id_1).SetName(cur_segment_name+"-1")
    slicer.modules.SegmentEditorWidget.editor.activeEffect().parameterSetNode().GetSegmentationNode().GetSegmentation().GetSegment(segment_id_2).SetName(cur_segment_name+"-2")


    ext_points1=ext_points+self.extend_surface_2(ext_points,1.4,300)    
    ext_points2=points+ext_points+self.extend_surface_2(ext_points,1.4,-300)

    for p in ext_points1:
      f.AddControlPoint([p[0],p[1],p[2]])

    # Allow users revert to this state by clicking Undo
    slicer.modules.SegmentEditorWidget.editor.activeEffect().self().scriptedEffect.saveStateForUndo()

    # This can be a long operation - indicate it to the user
    qt.QApplication.setOverrideCursor(qt.Qt.WaitCursor)
    slicer.modules.SegmentEditorWidget.editor.activeEffect().self().observeSegmentation(False)

    for i in range(100):
      slicer.modules.SegmentEditorWidget.editor.selectNextSegment()
      seg_id=slicer.modules.SegmentEditorWidget.editor.currentSegmentID()
      if seg_id==segment_id_1:
        slicer.modules.SegmentEditorWidget.editor.activeEffect().parameterSetNode().SetMaskSegmentID(segment_id_1)

        slicer.modules.SegmentEditorWidget.editor.activeEffect().self().logic.cutSurfaceWithModel(slicer.modules.SegmentEditorWidget.editor.activeEffect().self().segmentMarkupNode, slicer.modules.SegmentEditorWidget.editor.activeEffect().self().segmentModel)

        f.RemoveAllControlPoints()
        slicer.modules.SegmentEditorWidget.editor.selectNextSegment()
        slicer.modules.SegmentEditorWidget.editor.activeEffect().parameterSetNode().SetMaskSegmentID(segment_id_2)

        # 自定义相减逻辑
        modifierSegmentID=segment_id_1
        modifierSegmentLabelmap = slicer.vtkOrientedImageData()
        segmentationNode=slicer.modules.SegmentEditorWidget.editor.activeEffect().parameterSetNode().GetSegmentationNode()
        segmentationNode.GetBinaryLabelmapRepresentation(modifierSegmentID, modifierSegmentLabelmap)
        # Get common geometry
        commonGeometryString = segmentationNode.GetSegmentation().DetermineCommonLabelmapGeometry(
            vtkSegmentationCore.vtkSegmentation.EXTENT_UNION_OF_SEGMENTS, None)
        if not commonGeometryString:
            logging.info("Logical operation skipped: all segments are empty")
            return
        commonGeometryImage = slicer.vtkOrientedImageData()
        vtkSegmentationCore.vtkSegmentationConverter.DeserializeImageGeometry(commonGeometryString, commonGeometryImage, False)

        # Make sure modifier segment has correct geometry
        # (if modifier segment has been just copied over from another segment then its geometry may be different)
        if not vtkSegmentationCore.vtkOrientedImageDataResample.DoGeometriesMatch(commonGeometryImage, modifierSegmentLabelmap):
            modifierSegmentLabelmap_CommonGeometry = slicer.vtkOrientedImageData()
            vtkSegmentationCore.vtkOrientedImageDataResample.ResampleOrientedImageToReferenceOrientedImage(
                modifierSegmentLabelmap, commonGeometryImage, modifierSegmentLabelmap_CommonGeometry,
                False,  # nearest neighbor interpolation,
                True  # make sure resampled modifier segment is not cropped
            )
            modifierSegmentLabelmap = modifierSegmentLabelmap_CommonGeometry    
        bypassMasking=1
        self.scriptedEffect.modifySelectedSegmentByLabelmap(
          modifierSegmentLabelmap, slicer.qSlicerSegmentEditorAbstractEffect.ModificationModeRemove, bypassMasking)

        # 删除原段
        if not self.keepOriginSegmentCheckbox.isChecked():
          slicer.modules.SegmentEditorWidget.editor.activeEffect().parameterSetNode().GetSegmentationNode().GetSegmentation().RemoveSegment(cur_segment)

        break
      if seg_id==cur_segment_id:
        break
    slicer.modules.SegmentEditorWidget.editor.activeEffect().self().reset()
    # Create model node prior to markup node for display order
    slicer.modules.SegmentEditorWidget.editor.activeEffect().self().createNewModelNode()
    slicer.modules.SegmentEditorWidget.editor.activeEffect().self().createNewMarkupNode()
    slicer.modules.SegmentEditorWidget.editor.activeEffect().self().fiducialPlacementToggle.setCurrentNode(slicer.modules.SegmentEditorWidget.editor.activeEffect().self().segmentMarkupNode)

    slicer.modules.SegmentEditorWidget.editor.activeEffect().self().observeSegmentation(True)
    qt.QApplication.restoreOverrideCursor()

  def onApply(self):
    if 'ERASE_INSIDE' != self.scriptedEffect.parameter("Operation"):
      logging.warning("before start cut lalalal ")
      self.onApplyBefore()
      return

    logging.warning("my start cut lalalal ")
    self.onApplyMy()
    return

    logging.warning("start cut lalalal")
    if self.getNumberOfDefinedControlPoints() < 3:
      logging.warning("Cannot apply, segment markup node has less than 3 control points")
      return

    points=self.getBoundPoints(points)
    ext_points=self.extend_surface_1(points,1.4)

    cur_segment_id=slicer.modules.SegmentEditorWidget.editor.currentSegmentID()
    cur_segment=slicer.modules.SegmentEditorWidget.editor.activeEffect().parameterSetNode().GetSegmentationNode().GetSegmentation().GetSegment(cur_segment_id)
    cur_segment_name=cur_segment.GetName()

    slicer.modules.SegmentEditorWidget.editor.activeEffect().parameterSetNode().SetMaskSegmentID(cur_segment_id)

    segment_id_1=slicer.modules.SegmentEditorWidget.editor.activeEffect().parameterSetNode().GetSegmentationNode().GetSegmentation().GenerateUniqueSegmentID(cur_segment_id)
    segment_id_2=slicer.modules.SegmentEditorWidget.editor.activeEffect().parameterSetNode().GetSegmentationNode().GetSegmentation().GenerateUniqueSegmentID(cur_segment_id)

    segment_1 = vtkSegmentationCore.vtkSegment()
    segment_1.DeepCopy(cur_segment)
    segment_2 = vtkSegmentationCore.vtkSegment()
    segment_2.DeepCopy(cur_segment)

    slicer.modules.SegmentEditorWidget.editor.activeEffect().parameterSetNode().GetSegmentationNode().GetSegmentation().AddSegment(segment_1,segment_id_1)
    slicer.modules.SegmentEditorWidget.editor.activeEffect().parameterSetNode().GetSegmentationNode().GetSegmentation().AddSegment(segment_2,segment_id_2)

    slicer.modules.SegmentEditorWidget.editor.activeEffect().parameterSetNode().GetSegmentationNode().GetSegmentation().GetSegment(segment_id_1).SetName(cur_segment_name+"-1")
    slicer.modules.SegmentEditorWidget.editor.activeEffect().parameterSetNode().GetSegmentationNode().GetSegmentation().GetSegment(segment_id_2).SetName(cur_segment_name+"-2")
    

    f = self.segmentMarkupNode
    points  = [f.GetNthControlPointPosition(i) for i in range(f.GetNumberOfControlPoints())]
    
    ext_points1=ext_points+self.extend_surface_2(ext_points,1.4,300)    
    ext_points2=points+ext_points+self.extend_surface_2(ext_points,1.4,-300)

    for p in ext_points1:
      f.AddControlPoint([p[0],p[1],p[2]])

    # Allow users revert to this state by clicking Undo
    self.scriptedEffect.saveStateForUndo()

    # This can be a long operation - indicate it to the user
    qt.QApplication.setOverrideCursor(qt.Qt.WaitCursor)
    self.observeSegmentation(False)
    
    for i in range(100):
      slicer.modules.SegmentEditorWidget.editor.selectNextSegment()
      seg_id=slicer.modules.SegmentEditorWidget.editor.currentSegmentID()
      if seg_id==segment_1:
        slicer.modules.SegmentEditorWidget.editor.activeEffect().parameterSetNode().SetMaskSegmentID(segment_1)

        self.logic.cutSurfaceWithModel(self.segmentMarkupNode, self.segmentModel)
        self.reset()
        # Create model node prior to markup node for display order
        self.createNewModelNode()
        self.createNewMarkupNode()
        self.fiducialPlacementToggle.setCurrentNode(self.segmentMarkupNode)

        slicer.modules.SegmentEditorWidget.editor.activeEffect().parameterSetNode().SetMaskSegmentID(segment_2)

        for p in ext_points2:
          f.AddControlPoint([p[0],p[1],p[2]])

        slicer.modules.SegmentEditorWidget.editor.selectNextSegment()
        self.logic.cutSurfaceWithModel(self.segmentMarkupNode, self.segmentModel)

        break
      if seg_id==cur_segment_id:
        break

    self.observeSegmentation(True)
    qt.QApplication.restoreOverrideCursor()

  def observeSegmentation(self, observationEnabled):
    import vtkSegmentationCorePython as vtkSegmentationCore
    if self.scriptedEffect.parameterSetNode().GetSegmentationNode():
      segmentation = self.scriptedEffect.parameterSetNode().GetSegmentationNode().GetSegmentation()
    else:
      segmentation = None
    # Remove old observer
    if self.observedSegmentation:
      self.observedSegmentation.RemoveObserver(self.segmentObserver)
      self.segmentObserver = None
    # Add new observer
    if observationEnabled and segmentation is not None:
      self.observedSegmentation = segmentation
      self.segmentObserver = self.observedSegmentation.AddObserver(vtkSegmentationCore.vtkSegmentation.SegmentModified,
                                                                   self.onSegmentModified)

  def createNewModelNode(self):
    if self.segmentModel is None:
      self.segmentModel = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLModelNode")
      self.segmentModel.SetName("SegmentEditorSurfaceCutModel")
      self.segmentModel.SetSaveWithScene(False)  # prevent temporary node from being saved into the scene

      modelDisplayNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLModelDisplayNode")
      modelDisplayNode.SetSaveWithScene(False)  # prevent temporary node from being saved into the scene
      self.logic.setUpModelDisplayNode(modelDisplayNode)
      self.segmentModel.SetAndObserveDisplayNodeID(modelDisplayNode.GetID())

      self.segmentModel.GetDisplayNode().Visibility2DOn()

  def createNewMarkupNode(self):
    # Create empty markup fiducial node
    if self.segmentMarkupNode is None:
      self.segmentMarkupNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsFiducialNode")
      self.segmentMarkupNode.SetSaveWithScene(False)  # prevent temporary node from being saved into the scene
      self.segmentMarkupNode.CreateDefaultDisplayNodes()  # creates a display node if there is not one already for this node
      displayNode = self.segmentMarkupNode.GetDisplayNode()
      displayNode.SetSaveWithScene(False)  # prevent temporary node from being saved into the scene
      displayNode.SetTextScale(0)
      # Need to disable snapping to visible surface, as it would result in the surface iteratively crawling
      # towards the camera as the point is moved.
      displayNode.SetSnapMode(displayNode.SnapModeUnconstrained)
      # Prevent "Edit properties..." from being displayed
      # (Edit properties would switch module, which would deactive the effect, thus remove the markups node
      # while the markups node's event is being processed, causing a crash)
      self.segmentMarkupNode.SetHideFromEditors(True)

      # Only show "Delete point" action in view context menu to not allow the user to delete the node
      pluginHandler = slicer.qSlicerSubjectHierarchyPluginHandler.instance()
      pluginLogic = pluginHandler.pluginLogic()
      itemId = pluginHandler.subjectHierarchyNode().GetItemByDataNode(self.segmentMarkupNode)
      pluginLogic.setAllowedViewContextMenuActionNamesForItem(itemId, ["DeletePointAction"])

      self.segmentMarkupNode.SetName('C')
      self.setAndObserveSegmentMarkupNode(self.segmentMarkupNode)
      self.updateGUIFromMRML()

  def setAndObserveSegmentMarkupNode(self, segmentMarkupNode):
    if segmentMarkupNode == self.segmentMarkupNode and self.segmentMarkupNodeObservers:
      # no change and node is already observed
      return
    # Remove observer to old parameter node
    if self.segmentMarkupNode and self.segmentMarkupNodeObservers:
      for observer in self.segmentMarkupNodeObservers:
        self.segmentMarkupNode.RemoveObserver(observer)
      self.segmentMarkupNodeObservers = []
    # Set and observe new parameter node
    self.segmentMarkupNode = segmentMarkupNode
    if self.segmentMarkupNode:
      eventIds = [ vtk.vtkCommand.ModifiedEvent,
        slicer.vtkMRMLMarkupsNode.PointModifiedEvent,
        slicer.vtkMRMLMarkupsNode.PointAddedEvent,
        slicer.vtkMRMLMarkupsNode.PointRemovedEvent ]
      for eventId in eventIds:
        self.segmentMarkupNodeObservers.append(self.segmentMarkupNode.AddObserver(eventId, self.onSegmentMarkupNodeModified))
    # Update GUI
    self.updateModelFromSegmentMarkupNode()

  def onSegmentMarkupNodeModified(self, observer, eventid):
    self.updateModelFromSegmentMarkupNode()
    self.updateGUIFromMRML()

  def setAndObserveSegmentEditorNode(self, segmentEditorNode):
    if segmentEditorNode == self.segmentEditorNode and self.segmentEditorNodeObserver:
      # no change and node is already observed
      return
      # Remove observer to old parameter node
    if self.segmentEditorNode and self.segmentEditorNodeObserver:
      self.segmentEditorNode.RemoveObserver(self.segmentEditorNodeObserver)
      self.segmentEditorNodeObserver = None
      # Set and observe new parameter node
    self.segmentEditorNode = segmentEditorNode
    if self.segmentEditorNode:
      self.segmentEditorNodeObserver = self.segmentEditorNode.AddObserver(vtk.vtkCommand.ModifiedEvent,
                                                                          self.onSegmentEditorNodeModified)

  def onSegmentEditorNodeModified(self, observer, eventid):
    if self.scriptedEffect.parameterSetNode() is None:
      return

    # Get color of edited segment
    segmentationNode = self.scriptedEffect.parameterSetNode().GetSegmentationNode()
    segmentID = self.scriptedEffect.parameterSetNode().GetSelectedSegmentID()
    if segmentID and self.segmentModel:
      if self.segmentModel.GetDisplayNode():
        r, g, b = segmentationNode.GetSegmentation().GetSegment(segmentID).GetColor()
        if (r, g, b) != self.segmentModel.GetDisplayNode().GetColor():
          self.segmentModel.GetDisplayNode().SetColor(r, g, b)  # Edited segment color

    self.updateGUIFromMRML()

  def updateModelFromSegmentMarkupNode(self):
    if not self.segmentMarkupNode or not self.segmentModel:
      return
    smoothing = self.scriptedEffect.integerParameter("SmoothModel") != 0
    self.logic.updateModelFromMarkup(self.segmentMarkupNode, self.segmentModel, smoothing)

  def interactionNodeModified(self, interactionNode):
    # Override default behavior: keep the effect active if markup placement mode is activated
    pass

  def getNumberOfDefinedControlPoints(self):
    count = 0
    if self.segmentMarkupNode:
      count = self.segmentMarkupNode.GetNumberOfDefinedControlPoints()
    return count

class SurfaceCutLogic:

  def __init__(self, scriptedEffect):
    self.scriptedEffect = scriptedEffect

  def setUpModelDisplayNode(self, modelDisplayNode):
    # Get color of edited segment
    segmentationNode = self.scriptedEffect.parameterSetNode().GetSegmentationNode()
    segmentID = self.scriptedEffect.parameterSetNode().GetSelectedSegmentID()
    r, g, b = segmentationNode.GetSegmentation().GetSegment(segmentID).GetColor()

    modelDisplayNode.SetColor(r, g, b)  # Edited segment color
    modelDisplayNode.BackfaceCullingOff()
    modelDisplayNode.Visibility2DOn()
    modelDisplayNode.SetSliceIntersectionThickness(4)
    modelDisplayNode.SetOpacity(0.6)  # Between 0-1, 1 being opaque

  def updateModelFromMarkup(self, inputMarkup, outputModel, smoothModelFlag=True):
    """
    Update model to enclose all points in the input markup list
    """
    # create surface from points
    markupsToModel = slicer.modules.markupstomodel.logic()
    markupsToModel.UpdateClosedSurfaceModel(inputMarkup, outputModel, smoothModelFlag)
    displayNode = outputModel.GetDisplayNode()
    # Set flat interpolation for nice display of large planar facets
    if displayNode:
      if smoothModelFlag:
        displayNode.SetInterpolation(slicer.vtkMRMLDisplayNode.GouraudInterpolation)
      else:
        displayNode.SetInterpolation(slicer.vtkMRMLDisplayNode.FlatInterpolation)

  def setPointsFromString(self, segmentMarkupNode, fPosStr):
    # convert from space-separated list o fnumbers to 1D array
    import numpy
    fPos = numpy.fromstring(str(fPosStr), sep=' ')
    # convert from 1D array (N*3) to 2D array (N,3)
    fPosNum = int(len(fPos)/3)
    fPos = fPos.reshape((fPosNum, 3))
    wasModified = segmentMarkupNode.StartModify()
    segmentMarkupNode.RemoveAllControlPoints()
    for i in range(fPosNum):
      segmentMarkupNode.AddControlPoint(fPos[i])
    segmentMarkupNode.EndModify(wasModified)

  def getPointsAsString(self, segmentMarkupNode):
    # get fiducial positions as space-separated list
    import numpy
    n = segmentMarkupNode.GetNumberOfControlPoints()
    fPos = []
    for i in range(n):
      coord = segmentMarkupNode.GetNthControlPointPosition(i)
      fPos.extend(coord)
    fPosString = ' '.join(map(str, fPos))
    return fPosString

  def cutSurfaceWithModel(self, segmentMarkupNode, segmentModel):

    import vtkSegmentationCorePython as vtkSegmentationCore

    if not segmentMarkupNode:
      raise AttributeError(f"{self.__class__.__name__}: segment markup node not set.")
    if not segmentModel:
      raise AttributeError(f"{self.__class__.__name__}: segment model not set.")

    if segmentMarkupNode and segmentModel.GetPolyData().GetNumberOfPolys() > 0:
      operationName = self.scriptedEffect.parameter("Operation")

      segmentationNode = self.scriptedEffect.parameterSetNode().GetSegmentationNode()
      if not segmentationNode:
        raise AttributeError(f"{self.__class__.__name__}: Segmentation node not set.")

      modifierLabelmap = self.scriptedEffect.defaultModifierLabelmap()
      if not modifierLabelmap:
        raise AttributeError("{}: ModifierLabelmap not set. This can happen for various reasons:\n"
                             "No source volume set for segmentation,\n"
                             "No existing segments for segmentation, or\n"
                             "No referenceImageGeometry is specified in the segmentation".format(self.__class__.__name__))

      WorldToModifierLabelmapIjkTransform = vtk.vtkTransform()

      WorldToModifierLabelmapIjkTransformer = vtk.vtkTransformPolyDataFilter()
      WorldToModifierLabelmapIjkTransformer.SetTransform(WorldToModifierLabelmapIjkTransform)
      WorldToModifierLabelmapIjkTransformer.SetInputConnection(segmentModel.GetPolyDataConnection())

      segmentationToSegmentationIjkTransformMatrix = vtk.vtkMatrix4x4()
      modifierLabelmap.GetImageToWorldMatrix(segmentationToSegmentationIjkTransformMatrix)
      segmentationToSegmentationIjkTransformMatrix.Invert()
      WorldToModifierLabelmapIjkTransform.Concatenate(segmentationToSegmentationIjkTransformMatrix)

      worldToSegmentationTransformMatrix = vtk.vtkMatrix4x4()
      slicer.vtkMRMLTransformNode.GetMatrixTransformBetweenNodes(None, segmentationNode.GetParentTransformNode(),
                                                                 worldToSegmentationTransformMatrix)
      WorldToModifierLabelmapIjkTransform.Concatenate(worldToSegmentationTransformMatrix)
      WorldToModifierLabelmapIjkTransformer.Update()

      polyToStencil = vtk.vtkPolyDataToImageStencil()
      polyToStencil.SetOutputSpacing(1.0, 1.0, 1.0)
      polyToStencil.SetInputConnection(WorldToModifierLabelmapIjkTransformer.GetOutputPort())
      boundsIjk = WorldToModifierLabelmapIjkTransformer.GetOutput().GetBounds()
      modifierLabelmapExtent = self.scriptedEffect.modifierLabelmap().GetExtent()
      polyToStencil.SetOutputWholeExtent(modifierLabelmapExtent[0], modifierLabelmapExtent[1],
                                         modifierLabelmapExtent[2], modifierLabelmapExtent[3],
                                         int(round(boundsIjk[4])), int(round(boundsIjk[5])))
      polyToStencil.Update()

      stencilData = polyToStencil.GetOutput()
      stencilExtent = [0, -1, 0, -1, 0, -1]
      stencilData.SetExtent(stencilExtent)

      stencilToImage = vtk.vtkImageStencilToImage()
      stencilToImage.SetInputConnection(polyToStencil.GetOutputPort())
      if operationName in ("FILL_INSIDE", "ERASE_INSIDE", "SET"):
        stencilToImage.SetInsideValue(1.0)
        stencilToImage.SetOutsideValue(0.0)
      else:
        stencilToImage.SetInsideValue(0.0)
        stencilToImage.SetOutsideValue(1.0)
      stencilToImage.SetOutputScalarType(modifierLabelmap.GetScalarType())

      stencilPositioner = vtk.vtkImageChangeInformation()
      stencilPositioner.SetInputConnection(stencilToImage.GetOutputPort())
      stencilPositioner.SetOutputSpacing(modifierLabelmap.GetSpacing())
      stencilPositioner.SetOutputOrigin(modifierLabelmap.GetOrigin())

      stencilPositioner.Update()
      orientedStencilPositionerOutput = vtkSegmentationCore.vtkOrientedImageData()
      orientedStencilPositionerOutput.ShallowCopy(stencilToImage.GetOutput())
      imageToWorld = vtk.vtkMatrix4x4()
      modifierLabelmap.GetImageToWorldMatrix(imageToWorld)
      orientedStencilPositionerOutput.SetImageToWorldMatrix(imageToWorld)

      vtkSegmentationCore.vtkOrientedImageDataResample.ModifyImage(
        modifierLabelmap, orientedStencilPositionerOutput,
        vtkSegmentationCore.vtkOrientedImageDataResample.OPERATION_MAXIMUM)

      modMode = slicer.qSlicerSegmentEditorAbstractEffect.ModificationModeAdd
      if operationName == "ERASE_INSIDE" or operationName == "ERASE_OUTSIDE":
        modMode = slicer.qSlicerSegmentEditorAbstractEffect.ModificationModeRemove
      elif operationName == "SET":
        modMode = slicer.qSlicerSegmentEditorAbstractEffect.ModificationModeSet

      self.scriptedEffect.modifySelectedSegmentByLabelmap(modifierLabelmap, modMode)

      fPosString = self.getPointsAsString(segmentMarkupNode)
      segmentID = self.scriptedEffect.parameterSetNode().GetSelectedSegmentID()
      segment = segmentationNode.GetSegmentation().GetSegment(segmentID)
      segment.SetTag("SurfaceCutEffectMarkupPositions", fPosString)

