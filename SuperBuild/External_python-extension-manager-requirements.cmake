set(proj python-extension-manager-requirements)

# Set dependency list
set(${proj}_DEPENDENCIES
  python
  python-pip
  python-setuptools
  )

if(NOT DEFINED Slicer_USE_SYSTEM_${proj})
  set(Slicer_USE_SYSTEM_${proj} ${Slicer_USE_SYSTEM_python})
endif()

# Include dependent projects if any
ExternalProject_Include_Dependencies(${proj} PROJECT_VAR proj DEPENDS_VAR ${proj}_DEPENDENCIES)

if(Slicer_USE_SYSTEM_${proj})
  foreach(module_name IN ITEMS
    chardet
    couchdb
    git
    gitdb
    six
    smmap
    )
    ExternalProject_FindPythonPackage(
      MODULE_NAME "${module_name}"
      REQUIRED
      )
  endforeach()
endif()

if(NOT Slicer_USE_SYSTEM_${proj})
  set(requirements_file ${CMAKE_BINARY_DIR}/${proj}-requirements.txt)
  file(WRITE ${requirements_file} [===[
  # [chardet]
  chardet==5.2.0
  # [/chardet]
  # [CouchDB]
  couchdb==1.2
  # [/CouchDB]
  # [gitdb]
  gitdb==4.0.11
  # [/gitdb]
  # [smmap]
  smmap==5.0.1
  # [/smmap]
  # [GitPython]
  GitPython==3.1.43
  # [/GitPython]
  # [six]
  six==1.16.0
  # [/six]
  ]===])

  ExternalProject_Add(${proj}
    ${${proj}_EP_ARGS}
    DOWNLOAD_COMMAND ""
    SOURCE_DIR ${CMAKE_BINARY_DIR}/${proj}
    BUILD_IN_SOURCE 1
    CONFIGURE_COMMAND ""
    BUILD_COMMAND ""
    INSTALL_COMMAND ${CMAKE_COMMAND} -E env NO_PROXY=* ${PYTHON_EXECUTABLE} -m pip install --trusted-host pypi.tuna.tsinghua.edu.cn --index-url https://pypi.tuna.tsinghua.edu.cn/simple -r ${requirements_file}
    LOG_INSTALL 1
    DEPENDS
      ${${proj}_DEPENDENCIES}
    )

else()
  ExternalProject_Add_Empty(${proj} DEPENDS ${${proj}_DEPENDENCIES})
endif()
