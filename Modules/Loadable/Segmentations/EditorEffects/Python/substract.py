  def onApplyMy(self):
    # logging.warning("start cut lalalal")
    import vtkSegmentationCorePython as vtkSegmentationCore


      slicer.modules.SegmentEditorWidget.editor.selectNextSegment()
      seg_id=slicer.modules.SegmentEditorWidget.editor.currentSegmentID()

        slicer.modules.SegmentEditorWidget.editor.activeEffect().parameterSetNode().SetMaskSegmentID(segment_id_1)

        slicer.modules.SegmentEditorWidget.editor.activeEffect().self().logic.cutSurfaceWithModel(slicer.modules.SegmentEditorWidget.editor.activeEffect().self().segmentMarkupNode, slicer.modules.SegmentEditorWidget.editor.activeEffect().self().segmentModel)


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

void qSlicerSegmentEditorAbstractEffect::modifySelectedSegmentByLabelmap(vtkOrientedImageData* modifierLabelmap,
  ModificationMode modificationMode, const int modificationExtent[6], bool bypassMasking/*=false*/)
{
  this->modifySegmentByLabelmap(this->parameterSetNode()->GetSegmentationNode(),
    this->parameterSetNode()->GetSelectedSegmentID() ? this->parameterSetNode()->GetSelectedSegmentID() : "",
    modifierLabelmap, modificationMode, modificationExtent, bypassMasking);
}
void qSlicerSegmentEditorAbstractEffect::modifySegmentByLabelmap(vtkMRMLSegmentationNode* segmentationNode, const char* segmentID,
  vtkOrientedImageData* modifierLabelmapInput, ModificationMode modificationMode, const int modificationExtent[6], bool bypassMasking/*=false*/)
{
  Q_D(qSlicerSegmentEditorAbstractEffect);

  vtkMRMLSegmentEditorNode* parameterSetNode = this->parameterSetNode();
  if (!parameterSetNode)
    {
    qCritical() << Q_FUNC_INFO << ": Invalid segment editor parameter set node";
    this->defaultModifierLabelmap();
    return;
    }

  if (!segmentationNode)
    {
    qCritical() << Q_FUNC_INFO << ": Invalid segmentation";
    this->defaultModifierLabelmap();
    return;
    }

  vtkSegment* segment = nullptr;
  if (segmentID)
    {
    segment = segmentationNode->GetSegmentation()->GetSegment(segmentID);
    }
  if (!segment)
    {
    qCritical() << Q_FUNC_INFO << ": Invalid segment";
    this->defaultModifierLabelmap();
    return;
    }

  if (!modifierLabelmapInput)
    {
    // If per-segment flag is off, then it is not an error (the effect itself has written it back to segmentation)
    if (this->perSegment())
      {
      qCritical() << Q_FUNC_INFO << ": Cannot apply edit operation because modifier labelmap cannot be accessed";
      }
    this->defaultModifierLabelmap();
    return;
    }

  // Prevent disappearing and reappearing of 3D representation during update
  SlicerRenderBlocker renderBlocker;

  vtkSmartPointer<vtkOrientedImageData> modifierLabelmap = modifierLabelmapInput;
  if ((!bypassMasking && parameterSetNode->GetMaskMode() != vtkMRMLSegmentationNode::EditAllowedEverywhere) ||
    parameterSetNode->GetSourceVolumeIntensityMask())
    {
    vtkNew<vtkOrientedImageData> maskImage;
    maskImage->SetExtent(modifierLabelmap->GetExtent());
    maskImage->SetSpacing(modifierLabelmap->GetSpacing());
    maskImage->SetOrigin(modifierLabelmap->GetOrigin());
    maskImage->CopyDirections(modifierLabelmap);
    maskImage->AllocateScalars(VTK_UNSIGNED_CHAR, 1);
    vtkOrientedImageDataResample::FillImage(maskImage, m_EraseValue);

    // Apply mask to modifier labelmap if masking is enabled
    if (!bypassMasking && parameterSetNode->GetMaskMode() != vtkMRMLSegmentationNode::EditAllowedEverywhere)
      {
      vtkOrientedImageDataResample::ModifyImage(maskImage, this->maskLabelmap(), vtkOrientedImageDataResample::OPERATION_MAXIMUM);
      }

    // Apply threshold mask if paint threshold is turned on
    if (parameterSetNode->GetSourceVolumeIntensityMask())
      {
      vtkOrientedImageData* sourceVolumeOrientedImageData = this->sourceVolumeImageData();
      if (!sourceVolumeOrientedImageData)
        {
        qCritical() << Q_FUNC_INFO << ": Unable to get source volume image";
        this->defaultModifierLabelmap();
        return;
        }
      // Make sure the modifier labelmap has the same geometry as the source volume
      if (!vtkOrientedImageDataResample::DoGeometriesMatch(modifierLabelmap, sourceVolumeOrientedImageData))
        {
        qCritical() << Q_FUNC_INFO << ": Modifier labelmap should have the same geometry as the source volume";
        this->defaultModifierLabelmap();
        return;
        }

      // Create threshold image
      vtkSmartPointer<vtkImageThreshold> threshold = vtkSmartPointer<vtkImageThreshold>::New();
      threshold->SetInputData(sourceVolumeOrientedImageData);
      threshold->ThresholdBetween(parameterSetNode->GetSourceVolumeIntensityMaskRange()[0], parameterSetNode->GetSourceVolumeIntensityMaskRange()[1]);
      threshold->SetInValue(m_EraseValue);
      threshold->SetOutValue(m_FillValue);
      threshold->SetOutputScalarTypeToUnsignedChar();
      threshold->Update();

      vtkSmartPointer<vtkOrientedImageData> thresholdMask = vtkSmartPointer<vtkOrientedImageData>::New();
      thresholdMask->ShallowCopy(threshold->GetOutput());
      vtkSmartPointer<vtkMatrix4x4> modifierLabelmapToWorldMatrix = vtkSmartPointer<vtkMatrix4x4>::New();
      modifierLabelmap->GetImageToWorldMatrix(modifierLabelmapToWorldMatrix);
      thresholdMask->SetGeometryFromImageToWorldMatrix(modifierLabelmapToWorldMatrix);
      vtkOrientedImageDataResample::ModifyImage(maskImage, thresholdMask, vtkOrientedImageDataResample::OPERATION_MAXIMUM);
      }

    vtkSmartPointer<vtkOrientedImageData> segmentLayerLabelmap =
      vtkOrientedImageData::SafeDownCast(segment->GetRepresentation(segmentationNode->GetSegmentation()->GetSourceRepresentationName()));
    if (segmentLayerLabelmap
      && this->parameterSetNode()->GetMaskMode() == vtkMRMLSegmentationNode::EditAllowedInsideSingleSegment
      && modificationMode == qSlicerSegmentEditorAbstractEffect::ModificationModeRemove)
      {
      // If we are painting inside a segment, the erase effect can modify the current segment outside the masking region by adding back regions
      // in the current segment. Add the current segment to the editable area
      vtkNew<vtkImageThreshold> segmentInverter;
      segmentInverter->SetInputData(segmentLayerLabelmap);
      segmentInverter->SetInValue(m_EraseValue);
      segmentInverter->SetOutValue(m_FillValue);
      segmentInverter->ReplaceInOn();
      segmentInverter->ThresholdBetween(segment->GetLabelValue(), segment->GetLabelValue());
      segmentInverter->SetOutputScalarTypeToUnsignedChar();
      segmentInverter->Update();

      vtkNew<vtkOrientedImageData> invertedSegment;
      invertedSegment->ShallowCopy(segmentInverter->GetOutput());
      invertedSegment->CopyDirections(segmentLayerLabelmap);
      vtkOrientedImageDataResample::ModifyImage(maskImage, invertedSegment, vtkOrientedImageDataResample::OPERATION_MINIMUM);
      }

    // Apply the mask to the modifier labelmap. Make a copy so that we don't modify the original.
    modifierLabelmap = vtkSmartPointer<vtkOrientedImageData>::New();
    modifierLabelmap->DeepCopy(modifierLabelmapInput);
    vtkOrientedImageDataResample::ApplyImageMask(modifierLabelmap, maskImage, m_EraseValue, true);

    if (segmentLayerLabelmap && modificationMode == qSlicerSegmentEditorAbstractEffect::ModificationModeSet)
      {
      // If modification mode is "set", we don't want to erase the existing labelmap outside of the mask region,
      // so we need to add it to the modifier labelmap
      vtkNew<vtkImageThreshold> segmentThreshold;
      segmentThreshold->SetInputData(segmentLayerLabelmap);
      segmentThreshold->SetInValue(m_FillValue);
      segmentThreshold->SetOutValue(m_EraseValue);
      segmentThreshold->ReplaceInOn();
      segmentThreshold->ThresholdBetween(segment->GetLabelValue(), segment->GetLabelValue());
      segmentThreshold->SetOutputScalarTypeToUnsignedChar();
      segmentThreshold->Update();

      int segmentThresholdExtent[6] = { 0, -1, 0, -1, 0, -1 };
      segmentThreshold->GetOutput()->GetExtent(segmentThresholdExtent);
      if (segmentThresholdExtent[0] <= segmentThresholdExtent[1]
        && segmentThresholdExtent[2] <= segmentThresholdExtent[3]
        && segmentThresholdExtent[4] <= segmentThresholdExtent[5])
        {
        vtkNew<vtkOrientedImageData> segmentOutsideMask;
        segmentOutsideMask->ShallowCopy(segmentThreshold->GetOutput());
        segmentOutsideMask->CopyDirections(segmentLayerLabelmap);
        vtkOrientedImageDataResample::ModifyImage(segmentOutsideMask, maskImage, vtkOrientedImageDataResample::OPERATION_MINIMUM);
        vtkOrientedImageDataResample::ModifyImage(modifierLabelmap, segmentOutsideMask, vtkOrientedImageDataResample::OPERATION_MAXIMUM);
        }
      }
    }

  // Copy the temporary padded modifier labelmap to the segment.
  // Mask and threshold was already applied on modifier labelmap at this point if requested.
  const int* extent = modificationExtent;
  if (extent[0]>extent[1] || extent[2]>extent[3] || extent[4]>extent[5])
    {
    // invalid extent, it means we have to work with the entire modifier labelmap
    extent = nullptr;
    }

  std::vector<std::string> allSegmentIDs;
  segmentationNode->GetSegmentation()->GetSegmentIDs(allSegmentIDs);
  // remove selected segment, that is already handled
  allSegmentIDs.erase(std::remove(allSegmentIDs.begin(), allSegmentIDs.end(), segmentID), allSegmentIDs.end());

  std::vector<std::string> visibleSegmentIDs;
  vtkMRMLSegmentationDisplayNode* displayNode = vtkMRMLSegmentationDisplayNode::SafeDownCast(segmentationNode->GetDisplayNode());
  if (displayNode)
    {
    for (std::vector<std::string>::iterator segmentIDIt = allSegmentIDs.begin(); segmentIDIt != allSegmentIDs.end(); ++segmentIDIt)
      {
      if (displayNode->GetSegmentVisibility(*segmentIDIt))
        {
        visibleSegmentIDs.push_back(*segmentIDIt);
        }
      }
    }

  std::vector<std::string> segmentIDsToOverwrite;
  switch (this->parameterSetNode()->GetOverwriteMode())
    {
    case vtkMRMLSegmentEditorNode::OverwriteNone:
      // nothing to overwrite
      break;
    case vtkMRMLSegmentEditorNode::OverwriteVisibleSegments:
      segmentIDsToOverwrite = visibleSegmentIDs;
      break;
    case vtkMRMLSegmentEditorNode::OverwriteAllSegments:
      segmentIDsToOverwrite = allSegmentIDs;
      break;
    }

  if (bypassMasking)
    {
    segmentIDsToOverwrite.clear();
    }

  if (modificationMode == qSlicerSegmentEditorAbstractEffect::ModificationModeRemoveAll)
    {
    // If we want to erase all segments, then mark all segments as overwritable
    segmentIDsToOverwrite = allSegmentIDs;
    }

  // Create inverted binary labelmap
  vtkSmartPointer<vtkImageThreshold> inverter = vtkSmartPointer<vtkImageThreshold>::New();
  inverter->SetInputData(modifierLabelmap);
  inverter->SetInValue(VTK_UNSIGNED_CHAR_MAX);
  inverter->SetOutValue(m_EraseValue);
  inverter->ThresholdByLower(0);
  inverter->SetOutputScalarTypeToUnsignedChar();

  if (modificationMode == qSlicerSegmentEditorAbstractEffect::ModificationModeSet)
    {
    vtkSmartPointer<vtkImageThreshold> segmentInverter = vtkSmartPointer<vtkImageThreshold>::New();
    segmentInverter->SetInputData(segment->GetRepresentation(segmentationNode->GetSegmentation()->GetSourceRepresentationName()));
    segmentInverter->SetInValue(m_EraseValue);
    segmentInverter->SetOutValue(VTK_UNSIGNED_CHAR_MAX);
    segmentInverter->ReplaceInOn();
    segmentInverter->ThresholdBetween(segment->GetLabelValue(), segment->GetLabelValue());
    segmentInverter->SetOutputScalarTypeToUnsignedChar();
    segmentInverter->Update();
    vtkNew<vtkOrientedImageData> invertedModifierLabelmap;
    invertedModifierLabelmap->ShallowCopy(segmentInverter->GetOutput());
    vtkNew<vtkMatrix4x4> imageToWorldMatrix;
    modifierLabelmap->GetImageToWorldMatrix(imageToWorldMatrix.GetPointer());
    invertedModifierLabelmap->SetGeometryFromImageToWorldMatrix(imageToWorldMatrix.GetPointer());
    if (!vtkSlicerSegmentationsModuleLogic::SetBinaryLabelmapToSegment(
      invertedModifierLabelmap.GetPointer(), segmentationNode, segmentID, vtkSlicerSegmentationsModuleLogic::MODE_MERGE_MIN,
      nullptr, false, segmentIDsToOverwrite))
      {
      qCritical() << Q_FUNC_INFO << ": Failed to remove modifier labelmap from selected segment";
      }
    if (!vtkSlicerSegmentationsModuleLogic::SetBinaryLabelmapToSegment(
      modifierLabelmap, segmentationNode, segmentID, vtkSlicerSegmentationsModuleLogic::MODE_MERGE_MASK, extent, false, segmentIDsToOverwrite))
      {
      qCritical() << Q_FUNC_INFO << ": Failed to add modifier labelmap to selected segment";
      }
    }
  else if (modificationMode == qSlicerSegmentEditorAbstractEffect::ModificationModeAdd)
    {
    if (!vtkSlicerSegmentationsModuleLogic::SetBinaryLabelmapToSegment(
      modifierLabelmap, segmentationNode, segmentID, vtkSlicerSegmentationsModuleLogic::MODE_MERGE_MASK, extent, false, segmentIDsToOverwrite))
      {
      qCritical() << Q_FUNC_INFO << ": Failed to add modifier labelmap to selected segment";
      }
    }
  else if (modificationMode == qSlicerSegmentEditorAbstractEffect::ModificationModeRemove
    || modificationMode == qSlicerSegmentEditorAbstractEffect::ModificationModeRemoveAll)
    {
    inverter->Update();
    vtkNew<vtkOrientedImageData> invertedModifierLabelmap;
    invertedModifierLabelmap->ShallowCopy(inverter->GetOutput());
    vtkNew<vtkMatrix4x4> imageToWorldMatrix;
    modifierLabelmap->GetImageToWorldMatrix(imageToWorldMatrix.GetPointer());
    invertedModifierLabelmap->SetGeometryFromImageToWorldMatrix(imageToWorldMatrix.GetPointer());
    bool minimumOfAllSegments = modificationMode == qSlicerSegmentEditorAbstractEffect::ModificationModeRemoveAll;
    if (!vtkSlicerSegmentationsModuleLogic::SetBinaryLabelmapToSegment(
      invertedModifierLabelmap.GetPointer(), segmentationNode, segmentID, vtkSlicerSegmentationsModuleLogic::MODE_MERGE_MIN,
      extent, minimumOfAllSegments, segmentIDsToOverwrite))
      {
      qCritical() << Q_FUNC_INFO << ": Failed to remove modifier labelmap from selected segment";
      }
    }

  if (segment)
    {
    if (vtkSlicerSegmentationsModuleLogic::GetSegmentStatus(segment) == vtkSlicerSegmentationsModuleLogic::NotStarted)
      {
      vtkSlicerSegmentationsModuleLogic::SetSegmentStatus(segment, vtkSlicerSegmentationsModuleLogic::InProgress);
      }
    }

  std::vector<std::string> sharedSegmentIDs;
  segmentationNode->GetSegmentation()->GetSegmentIDsSharingBinaryLabelmapRepresentation(segmentID, sharedSegmentIDs, false);

  std::vector<std::string> segmentsToErase;
  for (std::string segmentIDToOverwrite : segmentIDsToOverwrite)
    {
    std::vector<std::string>::iterator foundSegmentIDIt = std::find(sharedSegmentIDs.begin(), sharedSegmentIDs.end(), segmentIDToOverwrite);
    if (foundSegmentIDIt == sharedSegmentIDs.end())
      {
      segmentsToErase.push_back(segmentIDToOverwrite);
      }
    }

  if (!segmentsToErase.empty() &&
     ( modificationMode == qSlicerSegmentEditorAbstractEffect::ModificationModeSet
    || modificationMode == qSlicerSegmentEditorAbstractEffect::ModificationModeAdd
    || modificationMode == qSlicerSegmentEditorAbstractEffect::ModificationModeRemoveAll))
    {
    inverter->Update();
    vtkNew<vtkOrientedImageData> invertedModifierLabelmap;
    invertedModifierLabelmap->ShallowCopy(inverter->GetOutput());
    vtkNew<vtkMatrix4x4> imageToWorldMatrix;
    modifierLabelmap->GetImageToWorldMatrix(imageToWorldMatrix.GetPointer());
    invertedModifierLabelmap->SetGeometryFromImageToWorldMatrix(imageToWorldMatrix.GetPointer());

    std::map<vtkDataObject*, bool> erased;
    for (std::string eraseSegmentID : segmentsToErase)
      {
      vtkSegment* currentSegment = segmentationNode->GetSegmentation()->GetSegment(eraseSegmentID);
      vtkDataObject* dataObject = currentSegment->GetRepresentation(vtkSegmentationConverter::GetBinaryLabelmapRepresentationName());
      if (erased[dataObject])
        {
        continue;
        }
      erased[dataObject] = true;

      vtkOrientedImageData* currentLabelmap = vtkOrientedImageData::SafeDownCast(dataObject);

      std::vector<std::string> dontOverwriteIDs;
      std::vector<std::string> currentSharedIDs;
      segmentationNode->GetSegmentation()->GetSegmentIDsSharingBinaryLabelmapRepresentation(eraseSegmentID, currentSharedIDs, true);
      for (std::string sharedSegmentID : currentSharedIDs)
        {
        if (std::find(segmentsToErase.begin(), segmentsToErase.end(), sharedSegmentID) == segmentsToErase.end())
          {
          dontOverwriteIDs.push_back(sharedSegmentID);
          }
        }

      vtkSmartPointer<vtkOrientedImageData> invertedModifierLabelmap2 = invertedModifierLabelmap;
      if (dontOverwriteIDs.size() > 0)
        {
        invertedModifierLabelmap2 = vtkSmartPointer<vtkOrientedImageData>::New();
        invertedModifierLabelmap2->DeepCopy(invertedModifierLabelmap);

        vtkNew<vtkOrientedImageData> maskImage;
        maskImage->CopyDirections(currentLabelmap);
        for (std::string dontOverwriteID : dontOverwriteIDs)
          {
          vtkSegment* dontOverwriteSegment = segmentationNode->GetSegmentation()->GetSegment(dontOverwriteID);
          vtkNew<vtkImageThreshold> threshold;
          threshold->SetInputData(currentLabelmap);
          threshold->ThresholdBetween(dontOverwriteSegment->GetLabelValue(), dontOverwriteSegment->GetLabelValue());
          threshold->SetInValue(1);
          threshold->SetOutValue(0);
          threshold->SetOutputScalarTypeToUnsignedChar();
          threshold->Update();
          maskImage->ShallowCopy(threshold->GetOutput());
          vtkOrientedImageDataResample::ApplyImageMask(invertedModifierLabelmap2, maskImage, VTK_UNSIGNED_CHAR_MAX, true);
          }
        }

      if (!vtkSlicerSegmentationsModuleLogic::SetBinaryLabelmapToSegment(
        invertedModifierLabelmap2, segmentationNode, eraseSegmentID, vtkSlicerSegmentationsModuleLogic::MODE_MERGE_MIN, extent, true, segmentIDsToOverwrite))
        {
        qCritical() << Q_FUNC_INFO << ": Failed to set modifier labelmap to segment " << (eraseSegmentID.c_str());
        }
      }
    }
  else if (modificationMode == qSlicerSegmentEditorAbstractEffect::ModificationModeRemove
    && this->parameterSetNode()->GetMaskMode() == vtkMRMLSegmentationNode::EditAllowedInsideSingleSegment
    && this->parameterSetNode()->GetMaskSegmentID()
    && strcmp(this->parameterSetNode()->GetMaskSegmentID(), segmentID) != 0)
    {
    // In general, we don't try to "add back" areas to other segments when an area is removed from the selected segment.
    // The only exception is when we draw inside one specific segment. In that case erasing adds to the mask segment. It is useful
    // for splitting a segment into two by painting.
    if (!vtkSlicerSegmentationsModuleLogic::SetBinaryLabelmapToSegment(
      modifierLabelmap, segmentationNode, this->parameterSetNode()->GetMaskSegmentID(), vtkSlicerSegmentationsModuleLogic::MODE_MERGE_MASK,
      extent, false, segmentIDsToOverwrite))
      {
      qCritical() << Q_FUNC_INFO << ": Failed to add back modifier labelmap to segment " << this->parameterSetNode()->GetMaskSegmentID();
      }
    }

  // Make sure the segmentation node is under the same parent as the source volume
  vtkMRMLScalarVolumeNode* sourceVolumeNode = d->ParameterSetNode->GetSourceVolumeNode();
  if (sourceVolumeNode)
    {
    vtkMRMLSubjectHierarchyNode* shNode = vtkMRMLSubjectHierarchyNode::GetSubjectHierarchyNode(d->ParameterSetNode->GetScene());
    if (shNode)
      {
      vtkIdType segmentationId = shNode->GetItemByDataNode(segmentationNode);
      vtkIdType sourceVolumeShId = shNode->GetItemByDataNode(sourceVolumeNode);
      if (segmentationId && sourceVolumeShId)
        {
        shNode->SetItemParent(segmentationId, shNode->GetItemParent(sourceVolumeShId));
        }
      else
        {
        qCritical() << Q_FUNC_INFO << ": Subject hierarchy items not found for segmentation or source volume";
        }
      }
    }
}
