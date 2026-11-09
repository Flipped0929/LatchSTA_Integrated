cmake_minimum_required(VERSION 3.16)
project(pds_howard LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# Match the root project: look in the active conda environment first.
if(DEFINED ENV{CONDA_PREFIX})
    list(APPEND CMAKE_PREFIX_PATH "$ENV{CONDA_PREFIX}")
endif()

# Boost.Graph is header-only here; no Boost libraries are linked.
find_package(Boost REQUIRED)

add_executable(pds_howard
    tools/pds_howard.cpp
    upstream/src/howard.cpp
)
target_include_directories(pds_howard PRIVATE
    upstream/include
    ${Boost_INCLUDE_DIRS}
)
