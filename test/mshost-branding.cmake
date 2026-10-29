# SPDX-FileCopyrightText: 2026 MSHost contributors
# SPDX-License-Identifier: GPL-2.0-or-later
cmake_minimum_required(VERSION 3.16)
get_filename_component(CMAKE_SOURCE_DIR "${CMAKE_CURRENT_LIST_DIR}/.." ABSOLUTE)
set(WIN32 TRUE)
include("${CMAKE_SOURCE_DIR}/NEXTCLOUD.cmake")
if(NEXTCLOUD_DEV)
    set(expected_name "MSHost-CloudDev")
    set(expected_executable "mshost-cloud-dev")
else()
    set(expected_name "MSHost-Cloud")
    set(expected_executable "mshost-cloud")
endif()
if(NOT APPLICATION_NAME STREQUAL expected_name OR
   NOT APPLICATION_EXECUTABLE STREQUAL expected_executable OR
   NOT APPLICATION_CONFIG_NAME STREQUAL expected_executable)
    message(FATAL_ERROR "Application identity or configuration isolation is incorrect")
endif()
if(NOT APPLICATION_VENDOR STREQUAL "MSHost" OR BUILD_UPDATER OR APPLICATION_SERVER_URL_ENFORCE)
    message(FATAL_ERROR "Unexpected vendor, updater or server lock")
endif()
if(DEFINED EXPECTED_SERVER_URL)
    if(NOT APPLICATION_SERVER_URL STREQUAL EXPECTED_SERVER_URL)
        message(FATAL_ERROR "Custom server URL was not preserved")
    endif()
elseif(NOT APPLICATION_SERVER_URL STREQUAL "https://cloud.mshostcloud.org")
    message(FATAL_ERROR "Unexpected default server URL")
endif()
set(identifiers)
foreach(key WIN_SHELLEXT_CONTEXT_MENU_GUID WIN_SHELLEXT_OVERLAY_GUID_ERROR
        WIN_SHELLEXT_OVERLAY_GUID_OK WIN_SHELLEXT_OVERLAY_GUID_OK_SHARED
        WIN_SHELLEXT_OVERLAY_GUID_SYNC WIN_SHELLEXT_OVERLAY_GUID_WARNING WIN_MSI_UPGRADE_CODE)
    string(REGEX REPLACE "[{}]" "" identifier "${${key}}")
    string(LENGTH "${identifier}" identifier_length)
    if(NOT identifier_length EQUAL 36 OR identifier IN_LIST identifiers)
        message(FATAL_ERROR "Invalid or duplicate Windows identity: ${key}")
    endif()
    list(APPEND identifiers "${identifier}")
endforeach()
foreach(artwork "theme/colored/${APPLICATION_ICON_NAME}-icon.svg"
        "theme/colored/${APPLICATION_ICON_NAME}-w10startmenu.svg"
        "theme/colored/icons/${APPLICATION_ICON_NAME}-icon-win-folder.svg"
        "theme/colored/wizard_logo.svg")
    if(NOT EXISTS "${CMAKE_SOURCE_DIR}/${artwork}")
        message(FATAL_ERROR "Missing branding artwork: ${artwork}")
    endif()
endforeach()
message(STATUS "MSHost branding configuration passed: ${APPLICATION_NAME}")
