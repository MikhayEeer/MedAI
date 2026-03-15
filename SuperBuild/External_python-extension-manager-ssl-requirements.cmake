set(proj python-extension-manager-ssl-requirements)

# Set dependency list
set(${proj}_DEPENDENCIES
  python
  python-pip
  python-requests-requirements
  python-setuptools
  )

if(NOT DEFINED Slicer_USE_SYSTEM_${proj})
  set(Slicer_USE_SYSTEM_${proj} ${Slicer_USE_SYSTEM_python})
endif()

# Include dependent projects if any
ExternalProject_Include_Dependencies(${proj} PROJECT_VAR proj DEPENDS_VAR ${proj}_DEPENDENCIES)

if(Slicer_USE_SYSTEM_${proj})
  foreach(module_name IN ITEMS jwt wrapt deprecated pycparser cffi nacl dateutil)
    ExternalProject_FindPythonPackage(
      MODULE_NAME "${module_name}"
      REQUIRED
      )
  endforeach()
  ExternalProject_FindPythonPackage(
    MODULE_NAME github
    NO_VERSION_PROPERTY
    REQUIRED
    )
endif()

if(NOT Slicer_USE_SYSTEM_${proj})
  set(requirements_file ${CMAKE_BINARY_DIR}/${proj}-requirements.txt)
  file(WRITE ${requirements_file} [===[
  # [cryptography]
  cryptography==42.0.7
  # [/cryptography]
  # [PyJWT]
  PyJWT[crypto]==2.8.0
  # [/PyJWT]
  # [wrapt]
  wrapt==1.16.0
  # [/wrapt]
  # [Deprecated]
  Deprecated==1.2.14
  # [/Deprecated]
  # [pycparser]
  pycparser==2.22
  # [/pycparser]
  # [cffi]
  cffi==1.16.0
  # [/cffi]
  # [PyNaCl]
  PyNaCl==1.5.0
  # [/PyNaCl]
  # [python-dateutil]
  python-dateutil==2.9.0.post0
  # [/python-dateutil]
  # [six]
  six==1.16.0
  # [/six]
  # [typing_extensions]
  typing_extensions==4.12.1
  # [/typing_extensions]
  # [PyGithub]
  PyGithub==2.3.0
  # [/PyGithub]
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