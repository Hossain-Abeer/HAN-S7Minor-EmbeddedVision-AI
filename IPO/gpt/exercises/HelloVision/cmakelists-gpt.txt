cmake_minimum_required(VERSION 4.0.0)
project(HelloVision VERSION 0.0.1)

include(CTest)
enable_testing()

find_package( OpenCV REQUIRED )
include_directories( ${OpenCV_INCLUDE_DIRS} )

add_executable(HelloVision main.cpp)

target_link_libraries( HelloVision ${OpenCV_LIBS} )

set(CPACK_PROJECT_NAME ${PROJECT_NAME})
set(CPACK_PROJECT_VERSION ${PROJECT_VERSION})
include(CPack)

