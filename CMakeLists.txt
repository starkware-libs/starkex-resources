cmake_minimum_required (VERSION 3.5)

macro(copy_files_target TARGET_NAME)
set(OUTPUT_FILES)
foreach(FILENAME ${ARGN})
  add_custom_command(
    OUTPUT ${CMAKE_CURRENT_BINARY_DIR}/${FILENAME}
    COMMAND ${CMAKE_COMMAND} -E copy
    ${CMAKE_CURRENT_SOURCE_DIR}/${FILENAME}
    ${CMAKE_CURRENT_BINARY_DIR}/${FILENAME}
    DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/${FILENAME}
    COMMENT "Copying file ${FILENAME}"
  )
  set(OUTPUT_FILES ${OUTPUT_FILES} ${CMAKE_CURRENT_BINARY_DIR}/${FILENAME})
endforeach(FILENAME)

add_custom_target(${TARGET_NAME}
  ALL
  DEPENDS ${OUTPUT_FILES}
)
# Add to project virtual environment.

endmacro(copy_files_target)

# Note that PACKAGE_NAME must match the name in the package setup.py.
macro(python_package TARGET_NAME PACKAGE_NAME)
  copy_files_target(${TARGET_NAME}_copy_files ${ARGN})
  add_custom_command(
    OUTPUT ${PACKAGE_NAME}.egg-info/requires.txt
    COMMAND python3 setup.py egg_info
    DEPENDS ${CMAKE_CURRENT_BINARY_DIR}/setup.py
    COMMENT "Generating egg_info for ${TARGET_NAME}"
  )

  add_custom_command(
    OUTPUT ${CMAKE_BINARY_DIR}/python_packages/${PACKAGE_NAME}-0.1.zip
     # Delete the file so that will be able to check that it was actually created.
    COMMAND rm -f ${CMAKE_BINARY_DIR}/python_packages/${PACKAGE_NAME}-0.1.zip
    COMMAND python3.7 setup.py sdist --format=zip --dist-dir=${CMAKE_BINARY_DIR}/python_packages
    # Check that the file name passed to output is correct.
    COMMAND if test ! -f ${CMAKE_BINARY_DIR}/python_packages/${PACKAGE_NAME}-0.1.zip \; then ${CMAKE_COMMAND} -E cmake_echo_color --red "Bad package name: ${PACKAGE_NAME}." \; exit 1\; fi\;

    # If egg-info/requires.txt is missing create an empty one.
    COMMAND ${CMAKE_COMMAND} -E touch ${PACKAGE_NAME}.egg-info/requires.txt

    # Copy the egg-info/requires.txt.
    COMMAND ${CMAKE_COMMAND} -E copy
    ${CMAKE_CURRENT_BINARY_DIR}/${PACKAGE_NAME}.egg-info/requires.txt
    ${CMAKE_BINARY_DIR}/python_packages/${PACKAGE_NAME}.egg-info/requires.txt

    DEPENDS ${ARGN}
    COMMENT "Generating source distribution for ${TARGET_NAME}"
  )

  # The dependency makes sure that when this target is built, it also generates the corresponding source distribution .../python_packages/${PACKAGE_NAME}-0.1.zip, for every python package we have.
  add_custom_target(${TARGET_NAME} DEPENDS ${TARGET_NAME}_copy_files ${PACKAGE_NAME}.egg-info/requires.txt ${CMAKE_BINARY_DIR}/python_packages/${PACKAGE_NAME}-0.1.zip)
endmacro()

# This macro copies packages relevant to dockers into their respective folders on build
macro(python_dependency TARGET_NAME PACKAGE_NAME)
  add_custom_command(TARGET ${TARGET_NAME}
  COMMAND ${CMAKE_COMMAND} -E copy
  ${CMAKE_BINARY_DIR}/python_packages/${PACKAGE_NAME}-0.1.zip
  ${CMAKE_CURRENT_BINARY_DIR}/${PACKAGE_NAME}-0.1.zip
  # Copy the egg-info/requires.txt
  COMMAND ${CMAKE_COMMAND} -E copy
  ${CMAKE_BINARY_DIR}/python_packages/${PACKAGE_NAME}.egg-info/requires.txt
  ${CMAKE_CURRENT_BINARY_DIR}/${PACKAGE_NAME}.egg-info/requires.txt)
endmacro()

add_subdirectory(aerospike)
add_subdirectory(committee)
add_subdirectory(crypto)
add_subdirectory(stark_ex_objects)
add_subdirectory(storage)
