
set(APPLICATION_NAME
  MedAI
  )

set(VERSION_MAJOR
  ${Slicer_VERSION_MAJOR}
  )
set(VERSION_MINOR
  ${Slicer_VERSION_MINOR}
  )
set(VERSION_PATCH
  ${Slicer_VERSION_PATCH}
  )

set(DESCRIPTION_SUMMARY
  "Medical Visualization and Processing Environment for Research"
  )
set(DESCRIPTION_FILE
  ${Slicer_SOURCE_DIR}/README.md
  )

set(LAUNCHER_SPLASHSCREEN_FILE
  "${CMAKE_CURRENT_LIST_DIR}/Resources/Images/Slicer-SplashScreen.png"
  )
set(APPLE_ICON_FILE
  "${CMAKE_CURRENT_LIST_DIR}/Resources/Slicer.icns"
  )
set(WIN_ICON_FILE
  "${CMAKE_CURRENT_LIST_DIR}/Resources/Slicer.ico"
  )

set(LICENSE_FILE
  "${Slicer_SOURCE_DIR}/License.txt"
  )
