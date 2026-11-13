cmake_minimum_required(VERSION 3.10)
project(Billiard-Vision VERSION 0.0.1)

set(OpenCV_DIR "C:/dev/opencv-build/opencv-install/x64/mingw/lib")
find_package(OpenCV REQUIRED)
include_directories(${OpenCV_INCLUDE_DIRS})

add_executable(Billiard-Vision src/main.cpp src/preprocess.cpp src/segment.cpp src/features.cpp src/classify.cpp)
target_link_libraries(Billiard-Vision ${OpenCV_LIBS})