cmake_minimum_required(VERSION 3.10)
project(Ball-Type-Identifier VERSION 0.0.1)

set(OpenCV_DIR "C:/dev/opencv-build/opencv-install/x64/mingw/lib")
find_package(OpenCV REQUIRED)
include_directories(${OpenCV_INCLUDE_DIRS})

add_executable(Ball-Type-Identifier src/main.cpp)
target_link_libraries(Ball-Type-Identifier ${OpenCV_LIBS})