cmake_minimum_required(VERSION 3.10)
project(Ex2_1 VERSION 0.0.1)

include(CTest)
enable_testing()

set(OpenCV_DIR "C:/dev/opencv-build/opencv-install/x64/mingw/lib")
find_package(OpenCV REQUIRED)
include_directories(${OpenCV_INCLUDE_DIRS})

add_executable(Ex2_1 main.cpp)

target_link_libraries(Ex2_1 ${OpenCV_LIBS})

set(CPACK_PROJECT_NAME ${PROJECT_NAME})
set(CPACK_PROJECT_VERSION ${PROJECT_VERSION})
include(CPack)