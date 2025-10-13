import logging
import os
from typing import Annotated, Optional
import json
import vtk

import slicer
from slicer.ScriptedLoadableModule import *
from slicer.util import VTKObservationMixin
from slicer.parameterNodeWrapper import (
    parameterNodeWrapper,
    WithinRange,
)

from slicer import vtkMRMLScalarVolumeNode


#
# aaamodule
#

class aaamodule(ScriptedLoadableModule):
    """Uses ScriptedLoadableModule base class, available at:
    https://github.com/Slicer/Slicer/blob/main/Base/Python/slicer/ScriptedLoadableModule.py
    """

    def __init__(self, parent):
        ScriptedLoadableModule.__init__(self, parent)
        self.parent.title = "一键导出"  # TODO: make this more human readable by adding spaces
        self.parent.categories = ["Examples"]  # TODO: set categories (folders where the module shows up in the module selector)
        self.parent.dependencies = []  # TODO: add here list of module names that this module requires
        self.parent.contributors = ["lhf"]  # TODO: replace with "Firstname Lastname (Organization)"
        # TODO: update with short description of the module and a link to online module documentation
        self.parent.helpText = """
一键导出所有分割到指定目录
"""
        # TODO: replace with organization, grant and thanks
        self.parent.acknowledgementText = """
 developed by lhf.
"""
#
# aaamoduleParameterNode
#

@parameterNodeWrapper
class aaamoduleParameterNode:
    """
    The parameters needed by module.

    directory - 输出路径
    """
    directory: str


class FileCache:
    def __init__(self, filename):
        self.filename = filename
        self._load()

    def _load(self):
        try:
            with open(self.filename, 'r') as file:
                self._cache = json.load(file)
        except FileNotFoundError:
            self._cache = {}

    def _save(self):
        with open(self.filename, 'w') as file:
            json.dump(self._cache, file)

    def set(self, key, value):
        self._cache[key] = value
        self._save()

    def get(self, key):
        return self._cache.get(key)

#
# aaamoduleWidget
#

class aaamoduleWidget(ScriptedLoadableModuleWidget, VTKObservationMixin):
    """Uses ScriptedLoadableModuleWidget base class, available at:
    https://github.com/Slicer/Slicer/blob/main/Base/Python/slicer/ScriptedLoadableModule.py
    """

    def __init__(self, parent=None) -> None:
        """
        Called when the user opens the module the first time and the widget is initialized.
        """
        ScriptedLoadableModuleWidget.__init__(self, parent)
        VTKObservationMixin.__init__(self)  # needed for parameter node observation
        self.logic = None
        self._parameterNode = None
        self._parameterNodeGuiTag = None

    def setup(self) -> None:
        """
        Called when the user opens the module the first time and the widget is initialized.
        """
        ScriptedLoadableModuleWidget.setup(self)

        # Load widget from .ui file (created by Qt Designer).
        # Additional widgets can be instantiated manually and added to self.layout.
        uiWidget = slicer.util.loadUI(self.resourcePath('UI/aaamodule.ui'))
        self.layout.addWidget(uiWidget)
        self.ui = slicer.util.childWidgetVariables(uiWidget)

        # Set scene in MRML widgets. Make sure that in Qt designer the top-level qMRMLWidget's
        # "mrmlSceneChanged(vtkMRMLScene*)" signal in is connected to each MRML widget's.
        # "setMRMLScene(vtkMRMLScene*)" slot.
        uiWidget.setMRMLScene(slicer.mrmlScene)

        # Create logic class. Logic implements all computations that should be possible to run
        # in batch mode, without a graphical user interface.
        self.logic = aaamoduleLogic()

        # Connections

        # These connections ensure that we update parameter node when scene is closed
        self.addObserver(slicer.mrmlScene, slicer.mrmlScene.StartCloseEvent, self.onSceneStartClose)
        self.addObserver(slicer.mrmlScene, slicer.mrmlScene.EndCloseEvent, self.onSceneEndClose)

        # Buttons
        self.ui.applyButton.connect('clicked(bool)', self.onApplyButton)
        self.ui.applyButtonLuoYan.connect('clicked(bool)', self.onApplyButtonLuoYan)

        file_cache = FileCache('output_cache.json')
        last_dest=file_cache.get('dest')

        if os.path.isdir(last_dest):
            self.ui.directoryButton.directory=last_dest
        self.ui.directoryButton.connect('directoryChanged(const QString &)', self.onDirectoryChanged)

        # Make sure parameter node is initialized (needed for module reload)
        self.initializeParameterNode()

    def cleanup(self) -> None:
        """
        Called when the application closes and the module widget is destroyed.
        """
        self.removeObservers()

    def enter(self) -> None:
        """
        Called each time the user opens this module.
        """
        # Make sure parameter node exists and observed
        self.initializeParameterNode()

    def exit(self) -> None:
        """
        Called each time the user opens a different module.
        """
        # Do not react to parameter node changes (GUI will be updated when the user enters into the module)
        if self._parameterNode:
            self._parameterNode.disconnectGui(self._parameterNodeGuiTag)
            self._parameterNodeGuiTag = None
            self.removeObserver(self._parameterNode, vtk.vtkCommand.ModifiedEvent, self._checkCanApply)

    def onSceneStartClose(self, caller, event) -> None:
        """
        Called just before the scene is closed.
        """
        # Parameter node will be reset, do not use it anymore
        self.setParameterNode(None)

    def onSceneEndClose(self, caller, event) -> None:
        """
        Called just after the scene is closed.
        """
        # If this module is shown while the scene is closed then recreate a new parameter node immediately
        if self.parent.isEntered:
            self.initializeParameterNode()

    def initializeParameterNode(self) -> None:
        """
        Ensure parameter node exists and observed.
        """
        # Parameter node stores all user choices in parameter values, node selections, etc.
        # so that when the scene is saved and reloaded, these settings are restored.

        self.setParameterNode(self.logic.getParameterNode())

    def setParameterNode(self, inputParameterNode: Optional[aaamoduleParameterNode]) -> None:
        """
        Set and observe parameter node.
        Observation is needed because when the parameter node is changed then the GUI must be updated immediately.
        """

        if self._parameterNode:
            self._parameterNode.disconnectGui(self._parameterNodeGuiTag)
            self.removeObserver(self._parameterNode, vtk.vtkCommand.ModifiedEvent, self._checkCanApply)
        self._parameterNode = inputParameterNode
        if self._parameterNode:
            # Note: in the .ui file, a Qt dynamic property called "SlicerParameterName" is set on each
            # ui element that needs connection.
            self._parameterNodeGuiTag = self._parameterNode.connectGui(self.ui)
            self.addObserver(self._parameterNode, vtk.vtkCommand.ModifiedEvent, self._checkCanApply)
            self._checkCanApply()

    def _checkCanApply(self, caller=None, event=None) -> None:
        self.ui.applyButton.toolTip = "一键导出所有模型"
        self.ui.applyButton.enabled = True

    def onApplyButton(self) -> None:
        """
        Run processing when user clicks "Apply" button.
        """
        with slicer.util.tryWithErrorDisplay("Failed to compute results.", waitCursor=True):
            self.logic.process(self.ui.directoryButton.directory)

    def onApplyButtonLuoYan(self) -> None:
        """
        Run processing when user clicks "Apply" button.
        """
        with slicer.util.tryWithErrorDisplay("Failed to compute results.", waitCursor=True):
            logging.error('开始裸眼1111')
            self.logic.processLuoYan()

    def onDirectoryChanged(self, directory):
        file_cache = FileCache('output_cache.json')
        file_cache.set('dest', directory)

#
# aaamoduleLogic
#

class aaamoduleLogic(ScriptedLoadableModuleLogic):
    """This class should implement all the actual
    computation done by your module.  The interface
    should be such that other python code can import
    this class and make use of the functionality without
    requiring an instance of the Widget.
    Uses ScriptedLoadableModuleLogic base class, available at:
    https://github.com/Slicer/Slicer/blob/main/Base/Python/slicer/ScriptedLoadableModule.py
    """

    def __init__(self) -> None:
        """
        Called when the logic class is instantiated. Can be used for initializing member variables.
        """
        ScriptedLoadableModuleLogic.__init__(self)

    def getParameterNode(self):
        return aaamoduleParameterNode(super().getParameterNode())

    def process(self,
                directory: str,) -> None:
        collection=slicer.util.getNodesByClass("vtkMRMLSegmentationNode")
        shNode = slicer.vtkMRMLSubjectHierarchyNode.GetSubjectHierarchyNode(slicer.mrmlScene)
        sceneid=shNode.GetSceneItemID()
        for v in collection:
            slicer.modules.segmentations.logic().ExportAllSegmentsToModels(v,sceneid)

        models=slicer.util.getNodesByClass("vtkMRMLModelNode")
        for myNode in models:
            name=myNode.GetName()
            if 'Model' not in name and 'Volume' not in name:
                myStorageNode = myNode.CreateDefaultStorageNode()
                myStorageNode.SetFileName(directory+"//"+name+".obj")
                myStorageNode.WriteData(myNode)
                slicer.mrmlScene.RemoveNode(myNode)
        logging.error('成功导出所有模型到'+directory)


    def processLuoYan(self) -> None:
        logging.error('开始裸眼2222')
        import vtk
        import slicer
        import numpy as np
        from PIL import Image
        import cv2
        from screeninfo import get_monitors

        # 安装必要库（首次运行需取消注释）
        # slicer.util.pip_install("screeninfo")
        # slicer.util.pip_install("opencv-python")
        # slicer.util.pip_install("Pillow")

        def get_lenticular_screen():
            """获取裸眼屏分辨率（第二块显示器）"""
            monitors = get_monitors()
            if len(monitors) < 2:
                raise RuntimeError("未检测到第二块显示器，请确保裸眼屏已连接")
            return monitors[1].width, monitors[1].height, monitors[1].x, monitors[1].y

        def capture_eye_view(camera, eye_offset_px, render_width, render_height):
            """离屏渲染单眼视图（返回NumPy数组）"""
            # 获取Slicer主渲染器和场景
            main_renderer = slicer.app.layoutManager().threeDWidget(0).threeDView().renderWindow().GetRenderers().GetFirstRenderer()
            scene_actors = main_renderer.GetActors()

            # 创建离屏渲染窗口
            offscreen_window = vtk.vtkRenderWindow()
            offscreen_window.SetOffScreenRendering(1)
            offscreen_window.SetSize(render_width, render_height)
            
            # 新建渲染器并复制场景
            new_renderer = vtk.vtkRenderer()
            offscreen_window.AddRenderer(new_renderer)
            scene_actors.InitTraversal()
            for _ in range(scene_actors.GetNumberOfItems()):
                new_renderer.AddActor(scene_actors.GetNextActor())

            # 设置摄像机（平行偏移模拟视差）
            cam = vtk.vtkCamera()
            cam.DeepCopy(camera)
            cam.SetPosition(cam.GetPosition()[0] + eye_offset_px, cam.GetPosition()[1], cam.GetPosition()[2])
            new_renderer.SetActiveCamera(cam)

            # 渲染并捕获图像
            offscreen_window.Render()
            w2i = vtk.vtkWindowToImageFilter()
            w2i.SetInput(offscreen_window)
            w2i.Update()
            vtk_image = w2i.GetOutput()

            # 转换为NumPy数组并调整坐标系
            np_image = vtk.util.numpy_support.vtk_to_numpy(vtk_image.GetPointData().GetScalars())
            np_image = np_image.reshape(render_height, render_width, -1)[:, :, :3]
            return np.flip(np_image, axis=0)  # 垂直翻转以匹配OpenCV

        def generate_sbs_half(left_img, right_img):
            """生成SBS半宽图像（PIL高质量缩放）"""
            # 缩放至50%宽度
            left_half = np.array(Image.fromarray(left_img).resize((left_img.shape[1] // 2, left_img.shape[0]), Image.LANCZOS))
            right_half = np.array(Image.fromarray(right_img).resize((right_img.shape[1] // 2, right_img.shape[0]), Image.LANCZOS))
            # 水平拼接
            return np.concatenate([left_half, right_half], axis=1)

        def realtime_sbs_rendering():
            """主循环：实时渲染SBS图像到裸眼屏"""
            # 获取裸眼屏参数
            screen_w, screen_h, screen_x, screen_y = get_lenticular_screen()
            print(f"裸眼屏分辨率: {screen_w}x{screen_h} 位置({screen_x}, {screen_y})")

            # 初始化OpenCV全屏窗口
            cv2.namedWindow("Stereoscopic SBS", cv2.WND_PROP_FULLSCREEN)
            cv2.moveWindow("Stereoscopic SBS", screen_x, screen_y)
            cv2.setWindowProperty("Stereoscopic SBS", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

            # 获取Slicer主摄像机
            main_camera = slicer.app.layoutManager().threeDWidget(0).threeDView().renderWindow().GetRenderers().GetFirstRenderer().GetActiveCamera()

            # 动态渲染循环
            while True:
                # 渲染左右眼视图（10像素平行偏移）
                left_img = capture_eye_view(main_camera, eye_offset_px=-10, render_width=screen_w, render_height=screen_h)
                right_img = capture_eye_view(main_camera, eye_offset_px=10, render_width=screen_w, render_height=screen_h)

                # 生成SBS半宽图像
                sbs_image = generate_sbs_half(left_img, right_img)

                # 显示到裸眼屏（需BGR格式）
                cv2.imshow("Stereoscopic SBS", cv2.cvtColor(sbs_image, cv2.COLOR_RGB2BGR))
                
                # ESC键退出
                if cv2.waitKey(1) & 0xFF == 27:
                    break

            cv2.destroyAllWindows()

        # 执行主函数
        realtime_sbs_rendering()