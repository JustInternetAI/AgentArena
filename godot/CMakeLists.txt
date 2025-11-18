cmake_minimum_required(VERSION 3.20)

project(agent_arena VERSION 0.1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)

# Configuration options
option(BUILD_SHARED_LIBS "Build shared library" ON)
option(AGENT_ARENA_DEBUG "Enable debug output" ON)

# Platform detection
if(WIN32)
    set(PLATFORM_NAME "windows")
    set(PLATFORM_ARCH "x86_64")
elseif(APPLE)
    set(PLATFORM_NAME "macos")
    set(PLATFORM_ARCH "universal")
elseif(UNIX)
    set(PLATFORM_NAME "linux")
    set(PLATFORM_ARCH "x86_64")
endif()

# Build type (handle both single-config and multi-config generators)
if(CMAKE_BUILD_TYPE)
    # Single-config generator (Ninja, Unix Makefiles)
    if(CMAKE_BUILD_TYPE STREQUAL "Debug")
        set(BUILD_TYPE "template_debug")
    else()
        set(BUILD_TYPE "template_release")
    endif()
else()
    # Multi-config generator (Visual Studio, Xcode)
    # Use generator expression for build type
    set(BUILD_TYPE "$<IF:$<CONFIG:Debug>,template_debug,template_release>")
endif()

# godot-cpp path (you'll need to clone godot-cpp as a submodule or dependency)
set(GODOT_CPP_DIR "${CMAKE_CURRENT_SOURCE_DIR}/../external/godot-cpp" CACHE PATH "Path to godot-cpp")

if(NOT EXISTS "${GODOT_CPP_DIR}/CMakeLists.txt")
    message(WARNING "godot-cpp not found at ${GODOT_CPP_DIR}. Please clone it:
    git clone --recursive https://github.com/godotengine/godot-cpp.git ${GODOT_CPP_DIR}")
endif()

# Add godot-cpp if available
if(EXISTS "${GODOT_CPP_DIR}/CMakeLists.txt")
    add_subdirectory(${GODOT_CPP_DIR} godot-cpp EXCLUDE_FROM_ALL)
endif()

# Source files
set(SOURCES
    src/agent_arena.cpp
    src/register_types.cpp
)

set(HEADERS
    include/agent_arena.h
    include/register_types.h
)

# Create library
add_library(${PROJECT_NAME} SHARED ${SOURCES} ${HEADERS})

# Include directories
target_include_directories(${PROJECT_NAME}
    PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}/include
        ${GODOT_CPP_DIR}/include
        ${GODOT_CPP_DIR}/gen/include
)

# Link godot-cpp
if(TARGET godot::cpp)
    target_link_libraries(${PROJECT_NAME} PRIVATE godot::cpp)
endif()

# Compiler flags
if(MSVC)
    target_compile_options(${PROJECT_NAME} PRIVATE /W4 /WX-)
    target_compile_definitions(${PROJECT_NAME} PRIVATE _CRT_SECURE_NO_WARNINGS)
else()
    target_compile_options(${PROJECT_NAME} PRIVATE -Wall -Wextra -Wpedantic)
endif()

# Debug definitions
if(AGENT_ARENA_DEBUG)
    target_compile_definitions(${PROJECT_NAME} PRIVATE AGENT_ARENA_DEBUG)
endif()

# Output directory
set(OUTPUT_NAME "libagent_arena.${PLATFORM_NAME}.${BUILD_TYPE}.${PLATFORM_ARCH}")
set_target_properties(${PROJECT_NAME} PROPERTIES
    OUTPUT_NAME_DEBUG "libagent_arena.${PLATFORM_NAME}.template_debug.${PLATFORM_ARCH}"
    OUTPUT_NAME_RELEASE "libagent_arena.${PLATFORM_NAME}.template_release.${PLATFORM_ARCH}"
    OUTPUT_NAME_RELWITHDEBINFO "libagent_arena.${PLATFORM_NAME}.template_release.${PLATFORM_ARCH}"
    OUTPUT_NAME_MINSIZEREL "libagent_arena.${PLATFORM_NAME}.template_release.${PLATFORM_ARCH}"
    LIBRARY_OUTPUT_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}/../bin/${PLATFORM_NAME}"
    RUNTIME_OUTPUT_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}/../bin/${PLATFORM_NAME}"
    LIBRARY_OUTPUT_DIRECTORY_DEBUG "${CMAKE_CURRENT_SOURCE_DIR}/../bin/${PLATFORM_NAME}"
    LIBRARY_OUTPUT_DIRECTORY_RELEASE "${CMAKE_CURRENT_SOURCE_DIR}/../bin/${PLATFORM_NAME}"
    RUNTIME_OUTPUT_DIRECTORY_DEBUG "${CMAKE_CURRENT_SOURCE_DIR}/../bin/${PLATFORM_NAME}"
    RUNTIME_OUTPUT_DIRECTORY_RELEASE "${CMAKE_CURRENT_SOURCE_DIR}/../bin/${PLATFORM_NAME}"
)

# Install rules
install(TARGETS ${PROJECT_NAME}
    LIBRARY DESTINATION lib
    RUNTIME DESTINATION bin
)

# Print configuration
message(STATUS "Agent Arena Configuration:")
message(STATUS "  Platform: ${PLATFORM_NAME}")
message(STATUS "  Architecture: ${PLATFORM_ARCH}")
message(STATUS "  Build Type: ${BUILD_TYPE}")
message(STATUS "  Output: ${OUTPUT_NAME}")
