#-----------------------------------------------------------------------------
set(SegmentEditorEffects_PYTHON_SCRIPTS
  __init__
  AbstractScriptedSegmentEditorEffect
  AbstractScriptedSegmentEditorLabelEffect
  AbstractScriptedSegmentEditorPaintEffect
  AbstractScriptedSegmentEditorAutoCompleteEffect
  SegmentEditorDrawEffect
  SegmentEditorFillBetweenSlicesEffect
  SegmentEditorGrowFromSeedsEffect
  SegmentEditorHollowEffect
  SegmentEditorIslandsEffect
  SegmentEditorLevelTracingEffect
  SegmentEditorLogicalEffect
  SegmentEditorMarginEffect
  SegmentEditorMaskVolumeEffect
  SegmentEditorSmoothingEffect
  SegmentEditorThresholdEffect
  SegmentEditorDrawTubeEffect
  SegmentEditorEngraveEffect
  SegmentEditorFloodFillingEffect
  SegmentEditorLocalThresholdEffect
  SegmentEditorWatershedEffect
  SegmentEditorSplitVolumeEffect
  SegmentEditorSurfaceCutEffect
  SegmentEditorWrapSolidifyEffect
  )

set(SegmentEditorEffects_PYTHON_RESOURCES
  Resources/Icons/Draw.png
  Resources/Icons/FillBetweenSlices.png
  Resources/Icons/GrowFromSeeds.png
  Resources/Icons/Hollow.png
  Resources/Icons/Islands.png
  Resources/Icons/LevelTracing.png
  Resources/Icons/Logical.png
  Resources/Icons/Margin.png
  Resources/Icons/MaskVolume.png
  Resources/Icons/Smoothing.png
  Resources/Icons/Threshold.png
  Resources/Icons/DrawTube.png
  Resources/Icons/Engrave.png
  Resources/Icons/FloodFilling.png
  Resources/Icons/LocalThreshold.png
  Resources/Icons/Watershed.png
  Resources/Icons/SplitVolume.png
  Resources/Icons/SurfaceCut.png
  Resources/Icons/WrapSolidify.png

  Resources/UI/WrapSolidify.ui
  )

ctkMacroCompilePythonScript(
  TARGET_NAME SegmentEditorEffects
  SCRIPTS "${SegmentEditorEffects_PYTHON_SCRIPTS}"
  RESOURCES "${SegmentEditorEffects_PYTHON_RESOURCES}"
  DESTINATION_DIR ${Slicer_BINARY_DIR}/${Slicer_QTSCRIPTEDMODULES_LIB_DIR}/SegmentEditorEffects
  INSTALL_DIR ${Slicer_INSTALL_QTSCRIPTEDMODULES_LIB_DIR}/SegmentEditorEffects
  NO_INSTALL_SUBDIR
  )
