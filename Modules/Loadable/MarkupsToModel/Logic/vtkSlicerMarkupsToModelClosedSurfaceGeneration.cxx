﻿#include "vtkSlicerMarkupsToModelClosedSurfaceGeneration.h"

#include "vtkMRMLModelNode.h"
#include "vtkMRMLMarkupsFiducialNode.h"

#include <vtkButterflySubdivisionFilter.h>
#include <vtkCleanPolyData.h>
#include <vtkCubeSource.h>
#include <vtkDataSetSurfaceFilter.h>
#include <vtkDelaunay3D.h>
#include <vtkDelaunay2D.h>
#include <vtkGlyph3D.h>
#include <vtkLinearSubdivisionFilter.h>
#include <vtkLineSource.h>
#include <vtkNew.h>
#include <vtkOBBTree.h>
#include <vtkPolyDataNormals.h>
#include <vtkRegularPolygonSource.h>
#include <vtkTransform.h>
#include <vtkTransformFilter.h>
#include <vtkUnstructuredGrid.h>

//------------------------------------------------------------------------------
// constants within this file
static const double COMPARE_TO_ZERO_TOLERANCE = 0.0001;
// static const double MINIMUM_SURFACE_EXTRUSION_AMOUNT = 0.01; // if a surface is flat/linear, give it at least this much depth
static const double MINIMUM_SURFACE_EXTRUSION_AMOUNT = 0.0; // if a surface is flat/linear, give it at least this much depth

//------------------------------------------------------------------------------
vtkStandardNewMacro(vtkSlicerMarkupsToModelClosedSurfaceGeneration);

//------------------------------------------------------------------------------
vtkSlicerMarkupsToModelClosedSurfaceGeneration::vtkSlicerMarkupsToModelClosedSurfaceGeneration()
{
}

//------------------------------------------------------------------------------
vtkSlicerMarkupsToModelClosedSurfaceGeneration::~vtkSlicerMarkupsToModelClosedSurfaceGeneration()
{
}

//------------------------------------------------------------------------------
bool vtkSlicerMarkupsToModelClosedSurfaceGeneration::GenerateClosedSurfaceModel(vtkPoints* inputPoints, vtkPolyData* outputPolyData,
    double delaunayAlpha, bool smoothing, bool forceConvex)
{
    vtkGenericWarningMacro("GenerateClosedSurfaceModel____"); // 输出警告信息
    if (inputPoints == NULL)
    {
        vtkGenericWarningMacro("Input points are null. No model generated."); // 如果inputPoints为空，输出警告信息
        return false; // 返回false表示失败
    }

    if (outputPolyData == NULL)
    {
        vtkGenericWarningMacro("Output poly data is null. No model generated.");// 如果outputPolyData为空，输出警告信息
        return false;// 返回false表示失败
    }

    int numberOfPoints = inputPoints->GetNumberOfPoints();// 获取输入点的数量
    if (numberOfPoints == 0)
    {
        // No markup points, the output should be empty // 如果没有标记点，输出应为空
        return true; // 返回true表示成功但没有生成模型
    }

    vtkSmartPointer< vtkCellArray > inputCellArray = vtkSmartPointer< vtkCellArray >::New();
    inputCellArray->InsertNextCell(numberOfPoints);// 插入一个包含所有点的单元
    for (int i = 0; i < numberOfPoints; i++)
    {
        inputCellArray->InsertCellPoint(i);// 将每个点插入单元中
    }

    vtkSmartPointer< vtkPolyData > inputPolyData = vtkSmartPointer< vtkPolyData >::New();// 创建一个新的vtkPolyData对象
    inputPolyData->SetLines(inputCellArray);// 设置线条数据
    inputPolyData->SetPoints(inputPoints);// 设置线条数据

    // 使用 vtkDelaunay2D 进行二维三角化
    vtkSmartPointer<vtkDelaunay2D> delaunay = vtkSmartPointer<vtkDelaunay2D>::New();
    delaunay->SetInputData(inputPolyData);
    delaunay->SetAlpha(delaunayAlpha);
    delaunay->Update();
    //vtkSmartPointer< vtkDelaunay3D > delaunay = vtkSmartPointer< vtkDelaunay3D >::New();// 创建一个新的Delaunay3D对象
    //delaunay->SetAlpha(delaunayAlpha);// 设置alpha值
    //delaunay->AlphaTrisOff();// 关闭alpha三角形
    //delaunay->AlphaLinesOff();// 关闭alpha线条
    //delaunay->AlphaVertsOff();// 关闭alpha顶点

    vtkSmartPointer< vtkMatrix4x4 > boundingAxesToRasTransformMatrix = vtkSmartPointer< vtkMatrix4x4 >::New();// 创建一个新的4x4矩阵
    ComputeTransformMatrixFromBoundingAxes(inputPoints, boundingAxesToRasTransformMatrix); // 计算从边界轴到RAS的变换矩阵

    vtkSmartPointer< vtkMatrix4x4 > rasToBoundingAxesTransformMatrix = vtkSmartPointer< vtkMatrix4x4 >::New();// 创建一个新的4x4矩阵
    vtkMatrix4x4::Invert(boundingAxesToRasTransformMatrix, rasToBoundingAxesTransformMatrix);// 计算变换矩阵的逆矩阵

    double smallestBoundingExtentRanges[3] = { 0.0, 0.0, 0.0 }; // temporary values // 初始化一个包含三个元素的数组，用于存储最小边界范围
    ComputeTransformedExtentRanges(inputPoints, rasToBoundingAxesTransformMatrix, smallestBoundingExtentRanges);// 计算变换后的范围

    PointArrangement pointArrangement = ComputePointArrangement(smallestBoundingExtentRanges);// 计算点排列类型

    switch (pointArrangement)// 根据点排列类型选择处理方式
    {
    case POINT_ARRANGEMENT_NONPLANAR:// 非平面排列情况--- 其他的都是无用的代码
    {
        vtkGenericWarningMacro("POINT_ARRANGEMENT_NONPLANAR____");
        delaunay->SetInputData(inputPolyData);// 设置Delaunay的输入数据
        break;
    }
    default: // unsupported or invalid // 不支持或无效的排列情况
    {
        vtkGenericWarningMacro("unsupported。。。。");
        vtkGenericWarningMacro("Unsupported pointArrangementType detected: " << pointArrangement << ". Aborting closed surface generation.");
        return false; // 返回false表示失败
    }
    }

    vtkSmartPointer< vtkDataSetSurfaceFilter > surfaceFilter = vtkSmartPointer< vtkDataSetSurfaceFilter >::New();// 创建一个新的DataSetSurfaceFilter对象
    surfaceFilter->SetInputConnection(delaunay->GetOutputPort());// 设置输入连接
    surfaceFilter->Update();// 更新数据

    vtkSmartPointer<vtkPolyDataNormals> normals = vtkSmartPointer<vtkPolyDataNormals>::New(); // 创建一个新的PolyDataNormals对象
    //normals->SetFeatureAngle(0); //  原来是100 TODO: This needs some justification, or set as an input parameter // 设置特征角
    normals->SetFeatureAngle(180); // 设置特征角为180度以确保法线计算不会闭合曲面

    if (smoothing && pointArrangement == POINT_ARRANGEMENT_NONPLANAR)// 如果需要平滑处理并且点排列类型为非平面
    {// 创建一个新的ButterflySubdivisionFilter对象
        vtkSmartPointer< vtkButterflySubdivisionFilter > subdivisionFilter = vtkSmartPointer< vtkButterflySubdivisionFilter >::New();
        subdivisionFilter->SetInputConnection(surfaceFilter->GetOutputPort());// 设置输入连接
        subdivisionFilter->SetNumberOfSubdivisions(3);// 设置细分次数
        subdivisionFilter->Update();// 更新数据
        if (forceConvex)// 如果需要强制凸性
        {
            vtkSmartPointer< vtkDelaunay3D > convexHull = vtkSmartPointer< vtkDelaunay3D >::New();// 创建一个新的Delaunay3D对象
            convexHull->SetInputConnection(subdivisionFilter->GetOutputPort());// 设置输入连接
            convexHull->Update();// 更新数据
            vtkSmartPointer< vtkDataSetSurfaceFilter > surfaceFilter = vtkSmartPointer< vtkDataSetSurfaceFilter >::New();// 创建一个新的DataSetSurfaceFilter对象
            surfaceFilter->SetInputData(convexHull->GetOutput()); // 设置输入数据
            surfaceFilter->Update();// 更新数据
            normals->SetInputConnection(surfaceFilter->GetOutputPort());// 设置法线计算的输入连接
        }
        else
        {
            normals->SetInputConnection(subdivisionFilter->GetOutputPort());// 设置法线计算的输入连接
        }
    }
    else
    {
        //vtkNew<vtkLinearSubdivisionFilter> linearSubdivision;// 创建一个新的LinearSubdivisionFilter对象
        //linearSubdivision->SetInputConnection(surfaceFilter->GetOutputPort());// 设置输入连接
        //normals->SetInputConnection(linearSubdivision->GetOutputPort()); // 设置法线计算的输入连接
    }
    normals->SetInputConnection(surfaceFilter->GetOutputPort());
    normals->Update();// 更新数据

    outputPolyData->DeepCopy(normals->GetOutput());// 深拷贝结果到输出数据
    return true; // 返回true表示成功
}

//------------------------------------------------------------------------------
// Compute the principal axes of the point cloud. The x axis represents the axis
// with maximum variation, and the z axis has minimum variation.
// This function is currently implemented using the vtkOBBTree object.
// There are two limitations with this approach:
// 1. vtkOBBTree may have a performance impact
// 2. The axes returned are based on variation of coordinates, not the range
//    (so the return result is not necessarily intuitive, variation != length).
// Neither of these limitations will prevent the overall logic from functioning
// correctly, but it is worth keeping in mind, and worth changing should a need
// arise
void vtkSlicerMarkupsToModelClosedSurfaceGeneration::ComputeTransformMatrixFromBoundingAxes(vtkPoints* points, vtkMatrix4x4* boundingAxesToRasTransformMatrix)
{
    if (points == NULL)
    {
        vtkGenericWarningMacro("Points object is null. Cannot compute best fit planes.");
        return;
    }

    if (boundingAxesToRasTransformMatrix == NULL)
    {
        vtkGenericWarningMacro("Output matrix object is null. Cannot compute best fit planes.");
        return;
    }

    // the output matrix should start as identity, so no translation etc.
    boundingAxesToRasTransformMatrix->Identity();

    // Compute the plane using the smallest bounding box that can have arbitrary axes
    vtkSmartPointer<vtkOBBTree> obbTree = vtkSmartPointer<vtkOBBTree>::New();
    double cornerOBBOrigin[3] = { 0.0, 0.0, 0.0 }; // unused
    double variationMaximumOBBAxis[3] = { 0.0, 0.0, 0.0 };
    double variationMediumOBBAxis[3] = { 0.0, 0.0, 0.0 };
    double variationMinimumOBBAxis[3] = { 0.0, 0.0, 0.0 };
    double relativeAxisSizes[3] = { 0.0, 0.0, 0.0 }; // unused, the values represented herein are unclear
    obbTree->ComputeOBB(points, cornerOBBOrigin, variationMaximumOBBAxis, variationMediumOBBAxis, variationMinimumOBBAxis, relativeAxisSizes);

    // now to store the desired results in the appropriate axis of the output matrix.
    // must check each axis to make sure it was actually computed (non-zero)
    // do the maxmimum variation axis
    if (vtkMath::Norm(variationMaximumOBBAxis) < COMPARE_TO_ZERO_TOLERANCE)
    {
        // there is no variation in the points whatsoever.
        // i.e. all points are in a single position.
        // return arbitrary orthonormal axes (the standard axes will do).
        boundingAxesToRasTransformMatrix->Identity();
        return;
    }
    vtkMath::Normalize(variationMaximumOBBAxis);
    SetNthColumnInMatrix(boundingAxesToRasTransformMatrix, 0, variationMaximumOBBAxis);

    // do the medium variation axis
    if (vtkMath::Norm(variationMediumOBBAxis) < COMPARE_TO_ZERO_TOLERANCE)
    {
        // the points are colinear along only the maximum axis
        // any two perpendicular orthonormal vectors will do for the remaining axes.
        double thetaAngle = 0.0; // this can be arbitrary
        vtkMath::Perpendiculars(variationMaximumOBBAxis, variationMediumOBBAxis, variationMinimumOBBAxis, thetaAngle);
    }
    vtkMath::Normalize(variationMediumOBBAxis);
    SetNthColumnInMatrix(boundingAxesToRasTransformMatrix, 1, variationMediumOBBAxis);

    // do the minimum variation axis
    if (vtkMath::Norm(variationMinimumOBBAxis) < COMPARE_TO_ZERO_TOLERANCE)
    {
        // all points lie exactly on a plane.
        // the remaining perpendicular vector found using cross product.
        vtkMath::Cross(variationMaximumOBBAxis, variationMediumOBBAxis, variationMinimumOBBAxis);
    }
    vtkMath::Normalize(variationMinimumOBBAxis);
    SetNthColumnInMatrix(boundingAxesToRasTransformMatrix, 2, variationMinimumOBBAxis);
}

//------------------------------------------------------------------------------
// It is assumed that sortedExtentRanges is pre-sorted in descending order (largest to smallest)
vtkSlicerMarkupsToModelClosedSurfaceGeneration::PointArrangement vtkSlicerMarkupsToModelClosedSurfaceGeneration::ComputePointArrangement(const double sortedExtentRanges[3])
{
    if (sortedExtentRanges == NULL)
    {
        vtkGenericWarningMacro("Input sortedExtentRanges is null. Returning singularity result.");
        return POINT_ARRANGEMENT_SINGULAR;
    }

    double longestExtentRange = sortedExtentRanges[0];
    double mediumExtentRange = sortedExtentRanges[1];
    double shortestExtentRange = sortedExtentRanges[2];

    // sanity checking
    bool longestExtentSmallerThanMedium = longestExtentRange >= COMPARE_TO_ZERO_TOLERANCE && longestExtentRange < mediumExtentRange;
    bool longestExtentSmallerThanShortest = longestExtentRange >= COMPARE_TO_ZERO_TOLERANCE && longestExtentRange < shortestExtentRange;
    bool mediumExtentSmallerThanShortest = mediumExtentRange >= COMPARE_TO_ZERO_TOLERANCE && mediumExtentRange < shortestExtentRange;
    if (longestExtentSmallerThanMedium || longestExtentSmallerThanShortest || mediumExtentSmallerThanShortest)
    {
        // Don't correct the problem here. Code external to this function should pass
        // extent ranges already sorted, so it indicates a problem elsewhere.
        vtkGenericWarningMacro("Extent ranges not provided in order largest to smallest. Unexpected results may occur.");
    }

    if (longestExtentRange < COMPARE_TO_ZERO_TOLERANCE)
    {
        return POINT_ARRANGEMENT_SINGULAR;
    }

    // We need to compare relative lengths of the short and medium axes against
    // the longest axis.
    double mediumToLongestRatio = mediumExtentRange / longestExtentRange;

    // The Delaunay3D class tends to fail with thin planes/lines, so it is important
    // to capture these cases, even liberally. It was experimentally determined that
    // extents less than 1/10th of the maximum extent tend to produce errors.
    const double RATIO_THRESHOLD = 0.1;

    if (mediumToLongestRatio < RATIO_THRESHOLD)
    {
        return POINT_ARRANGEMENT_LINEAR;
    }

    double shortestToLongestRatio = shortestExtentRange / longestExtentRange;
    if (shortestToLongestRatio < RATIO_THRESHOLD)
    {
        return POINT_ARRANGEMENT_PLANAR;
    }

    return POINT_ARRANGEMENT_NONPLANAR;
}

//------------------------------------------------------------------------------
void vtkSlicerMarkupsToModelClosedSurfaceGeneration::ComputeTransformedExtentRanges(vtkPoints* points, vtkMatrix4x4* transformMatrix, double outputExtentRanges[3])
{
    if (points == NULL)
    {
        vtkGenericWarningMacro("points is null. Aborting output extent computation.");
        return;
    }

    if (transformMatrix == NULL)
    {
        vtkGenericWarningMacro("transformMatrix is null. Aborting output extent computation.");
        return;
    }

    if (outputExtentRanges == NULL)
    {
        vtkGenericWarningMacro("outputExtentRanges is null. Aborting output extent computation.");
        return;
    }

    vtkSmartPointer< vtkTransform > transform = vtkSmartPointer< vtkTransform >::New();
    transform->SetMatrix(transformMatrix);
    transform->Update();

    // can't transform points directly, so need to store in a container
    vtkSmartPointer< vtkPolyData > polyDataWithPoints = vtkSmartPointer< vtkPolyData >::New();
    polyDataWithPoints->SetPoints(points);

    vtkSmartPointer< vtkTransformFilter > transformFilter = vtkSmartPointer< vtkTransformFilter >::New();
    transformFilter->SetTransform(transform);
    transformFilter->SetInputData(polyDataWithPoints);
    transformFilter->Update();

    // the extent can be extracted from the output points object (poly data bounds does not work)
    vtkPoints* transformedPoints = transformFilter->GetPolyDataOutput()->GetPoints();
    transformedPoints->ComputeBounds();
    double* extents = transformedPoints->GetBounds(); // { xmin, xmax, ymin, ymax, zmin, zmax }

    for (int i = 0; i < 3; i++)
    {
        double axisIMin = extents[2 * i];
        double axisIMax = extents[2 * i + 1];
        double axisIRange = axisIMax - axisIMin;
        outputExtentRanges[i] = axisIRange;
    }
}

//------------------------------------------------------------------------------
double vtkSlicerMarkupsToModelClosedSurfaceGeneration::ComputeSurfaceExtrusionAmount(const double extents[3])
{
    // MINIMUM_SURFACE_EXTRUSION_AMOUNT is the value returned by default, and the final result cannot be less than this.
    if (extents == NULL)
    {
        vtkGenericWarningMacro("extents is null. Returning MINIMUM_SURFACE_EXTRUSION_AMOUNT: " << MINIMUM_SURFACE_EXTRUSION_AMOUNT << ".");
        return MINIMUM_SURFACE_EXTRUSION_AMOUNT;
    }

    double normOfExtents = vtkMath::Norm(extents);
    const double SURFACE_EXTRUSION_NORM_MULTIPLIER = 0.01; // this value is observed to produce generally acceptable results
    double surfaceExtrusionAmount = normOfExtents * SURFACE_EXTRUSION_NORM_MULTIPLIER;

    if (surfaceExtrusionAmount < MINIMUM_SURFACE_EXTRUSION_AMOUNT)
    {
        vtkGenericWarningMacro("Surface extrusion amount smaller than " << MINIMUM_SURFACE_EXTRUSION_AMOUNT << " : " << surfaceExtrusionAmount << ". "
            << "Consider checking the points for singularity. Setting surface extrusion amount to default "
            << MINIMUM_SURFACE_EXTRUSION_AMOUNT << ".");
        surfaceExtrusionAmount = MINIMUM_SURFACE_EXTRUSION_AMOUNT;
    }
    return surfaceExtrusionAmount;
}

//------------------------------------------------------------------------------
void vtkSlicerMarkupsToModelClosedSurfaceGeneration::SetNthColumnInMatrix(vtkMatrix4x4* matrix, int n, const double axis[3])
{
    if (matrix == NULL)
    {
        vtkGenericWarningMacro("No matrix provided as input. No operation performed.");
        return;
    }

    if (n < 0 || n >= 3)
    {
        vtkGenericWarningMacro("Axis n " << n << " is out of bounds. Valid values are 0, 1, and 2. No operation performed.");
        return;
    }

    if (axis == NULL)
    {
        vtkGenericWarningMacro("Axis is null. No operation performed.");
        return;
    }

    matrix->SetElement(0, n, axis[0]);
    matrix->SetElement(1, n, axis[1]);
    matrix->SetElement(2, n, axis[2]);
}

//------------------------------------------------------------------------------
void vtkSlicerMarkupsToModelClosedSurfaceGeneration::GetNthColumnInMatrix(vtkMatrix4x4* matrix, int n, double outputAxis[3])
{
    if (matrix == NULL)
    {
        vtkGenericWarningMacro("No matrix provided as input. No operation performed.");
        return;
    }

    if (n < 0 || n >= 3)
    {
        vtkGenericWarningMacro("Axis n " << n << " is out of bounds. Valid values are 0, 1, and 2. No operation performed.");
        return;
    }

    if (outputAxis == NULL)
    {
        vtkGenericWarningMacro("Axis is null. No operation performed.");
        return;
    }

    outputAxis[0] = matrix->GetElement(0, n);
    outputAxis[1] = matrix->GetElement(1, n);
    outputAxis[2] = matrix->GetElement(2, n);
}

//------------------------------------------------------------------------------
void vtkSlicerMarkupsToModelClosedSurfaceGeneration::PrintSelf(ostream& os, vtkIndent indent)
{
    Superclass::PrintSelf(os, indent);
}
