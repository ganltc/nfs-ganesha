# SPDX-License-Identifier: LGPL-3.0-or-later
#-------------------------------------------------------------------------------
#
# Copyright (c) SUSE, 2022
# Contributor: Vicente Cheng <vicente.cheng@suse.com>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 3 of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA
#
#-------------------------------------------------------------------------------

if(USE_ADMIN_TOOLS)
  if(Python3_FOUND)
    # Find Python 3
    find_package(Python3 REQUIRED)

    # Get the major and minor version of Python 3
    string(REPLACE "." ";" set_python_version_list ${Python3_VERSION})
    list(GET set_python_version_list 0 python_major_version)
    list(GET set_python_version_list 1 python_minor_version)

    # Check if the Python version is less than 3.12
    if(python_major_version LESS 3 OR (python_major_version EQUAL 3 AND python_minor_version LESS 12))
         set(USE_LEGACY_PYTHON_INSTALL TRUE)
    else()
        set(USE_LEGACY_PYTHON_INSTALL FALSE)
    endif()

    # Optionally, print the result for debugging
    message(STATUS "USE_LEGACY_PYTHON_INSTALL is set to: ${USE_LEGACY_PYTHON_INSTALL}")

    set(SETUP_PY_IN "${CMAKE_CURRENT_SOURCE_DIR}/setup.py.in")
    set(SETUP_PY    "${CMAKE_CURRENT_BINARY_DIR}/setup.py")
    set(OUTPUT      "${CMAKE_CURRENT_BINARY_DIR}/build/ganesha_top_timestamp")

    set(GANESHA_TOP_SRC ganesha-top.py)

    # Generate rules to copy command line scripts from src to build,
    # stripping .py along the way
    set(SCRIPTS)
    foreach(src_file ${GANESHA_TOP_SRC})
      string(REPLACE ".py" "" script_file ${src_file})
      add_custom_command(
        OUTPUT ${script_file}
        COMMAND mkdir -p build/lib
        COMMAND echo ${script_file}
        COMMAND cp "${CMAKE_CURRENT_SOURCE_DIR}/${src_file}" ${script_file}
        DEPENDS ${src_file}
        )
      list(APPEND SCRIPTS ${script_file})
    endforeach()

    # Build up the string for the configure substitution in setup.py
    set(SCRIPTS_STRING)
    foreach(script_py ${GANESHA_TOP_SRC})
      string(REPLACE ".py" "" script ${script_py})
      if("${SCRIPTS_STRING}" STREQUAL "")
        set(SCRIPTS_STRING "'${script}'")
      else()
        set(SCRIPTS_STRING "${SCRIPTS_STRING}, '${script}'")
      endif()
    endforeach()

    configure_file(${SETUP_PY_IN} ${SETUP_PY})

    if(USE_LEGACY_PYTHON_INSTALL)
      add_custom_command(
        OUTPUT ${OUTPUT}
        COMMAND ${Python3_EXECUTABLE} "${SETUP_PY}"  build
        COMMAND ${CMAKE_COMMAND} -E touch ${OUTPUT}
        DEPENDS ${GANESHA_TOP_SRCS} ${SCRIPTS}
        )
    else()
      add_custom_command(
        OUTPUT ${OUTPUT}
        COMMAND ${Python3_EXECUTABLE}  -m build --wheel --no-isolation .
        COMMAND ${CMAKE_COMMAND} -E touch ${OUTPUT}
        DEPENDS ${GANESHA_TOP_SRCS} ${SCRIPTS}
        )
    endif()

    add_custom_target(python_ganesha_top ALL DEPENDS ${OUTPUT})

    if(USE_LEGACY_PYTHON_INSTALL)
      install(
        CODE
        "execute_process(WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}
        COMMAND ${Python3_EXECUTABLE} ${SETUP_PY} install --skip-build --no-compile --prefix=\$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX})"
        )
    else()
      install(
        CODE
        "execute_process(WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}
        COMMAND ${Python3_EXECUTABLE} -m installer --destdir \$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX} dist/ganesha_top-${GANESHA_MAJOR_VERSION}${GANESHA_MINOR_VERSION}+${GANESHA_TAG}-py3-none-any.whl)"
        )
    endif()
  endif(Python3_FOUND)
endif(USE_ADMIN_TOOLS)
