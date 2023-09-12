Slicer, or 3D Slicer, is a free, open source software package for visualization and
image analysis.

3D Slicer is natively designed to be available on multiple platforms,
including Windows, Linux and macOS.

Build instructions for all platforms are available on the Slicer wiki:
- https://slicer.readthedocs.io/en/latest/developer_guide/build_instructions/index.html

For Slicer community announcements and support, visit:
- https://discourse.slicer.org

For documentation, tutorials, and more information, please see:
- https://www.slicer.org

See License.txt for information on using and contributing.


## update log

2023/07/14
1. first commit
- 10:20:00 fork and pull Slicer.git
- Replace the images with our own images.
- Modify `CMakeLists.txt`: Add QT translations ,`./Translations/~~slicer~~medai_zh_Hans.ts`
> row 646
- Modify`./Application/SlicerApp/Main.cxx  row 49`,where the qt trans->load exist
- Modify`./Application/SlicerApp/qSlicerAppMainWindow.cxx  row 148`,change title into "MedAI"
- Modify`./Base/QTApp/Resources/UI/qSlicerMainWindow.ui` add`Usermenu`button,row318
- Modify`./Base/QTApp/qSlicerMainWindow.h` add declare`on_actionViewUserInfo_triggered();on_actionLogOut_triggered();` ,row 94
- Modify`./Base/QTApp/qSlicerMainWindow.cxx` add `include user.h ...`,and define the two `triggered()`before,row 1092
- Add `Userinfo`,`Rechargeform`,`signupform`,`userinfoform`,`deduction_dialog`,`loginform`,`post_manager`,14 files to path `base/QTGUI`
- modify `./base/QTGUI/CMakeLists.txt`,add files before into cmakefiles
