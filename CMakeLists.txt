cmake_minimum_required(VERSION 3.25)

project(opr2 VERSION 0.1.0 LANGUAGES CXX)

# The initial Windows package does not require a separately installed MSVC CRT.
set(CMAKE_MSVC_RUNTIME_LIBRARY "MultiThreaded$<$<CONFIG:Debug>:Debug>")

option(OPR2_ENABLE_SANITIZERS "Enable AddressSanitizer and UndefinedBehaviorSanitizer" OFF)

add_library(opr2_core
    src/data_validation.cpp
    src/executable_path.cpp
)
target_include_directories(opr2_core PUBLIC include)
target_compile_features(opr2_core PUBLIC cxx_std_20)
target_compile_definitions(opr2_core PUBLIC OPR2_VERSION="${PROJECT_VERSION}")

add_executable(opr2 src/main.cpp)
target_link_libraries(opr2 PRIVATE opr2_core)

if(MSVC)
    target_compile_options(opr2_core PRIVATE /W4 /permissive-)
    target_compile_options(opr2 PRIVATE /W4 /permissive-)
elseif(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
    target_compile_options(opr2_core PRIVATE -Wall -Wextra -Wpedantic)
    target_compile_options(opr2 PRIVATE -Wall -Wextra -Wpedantic)
    if(OPR2_ENABLE_SANITIZERS)
        target_compile_options(opr2_core PRIVATE -fsanitize=address,undefined -fno-omit-frame-pointer)
        target_link_options(opr2_core PRIVATE -fsanitize=address,undefined)
        target_compile_options(opr2 PRIVATE -fsanitize=address,undefined -fno-omit-frame-pointer)
        target_link_options(opr2 PRIVATE -fsanitize=address,undefined)
    endif()
endif()

include(CTest)
if(BUILD_TESTING)
    add_executable(opr2_tests tests/cpp/data_validation_tests.cpp)
    target_link_libraries(opr2_tests PRIVATE opr2_core)
    if(MSVC)
        target_compile_options(opr2_tests PRIVATE /W4 /permissive-)
    elseif(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
        target_compile_options(opr2_tests PRIVATE -Wall -Wextra -Wpedantic)
        if(OPR2_ENABLE_SANITIZERS)
            target_compile_options(opr2_tests PRIVATE -fsanitize=address,undefined -fno-omit-frame-pointer)
            target_link_options(opr2_tests PRIVATE -fsanitize=address,undefined)
        endif()
    endif()
    add_test(NAME opr2_cpp_tests COMMAND opr2_tests)
    add_test(NAME opr2_help COMMAND opr2 --help)
    add_test(NAME opr2_cli_tests
        COMMAND ${CMAKE_COMMAND}
            -DOPR2_EXECUTABLE=$<TARGET_FILE:opr2>
            -DEXPECTED_VERSION=${PROJECT_VERSION}
            -P ${CMAKE_CURRENT_SOURCE_DIR}/tests/cli/cli_test.cmake)
endif()

install(TARGETS opr2 RUNTIME DESTINATION .)
install(FILES docs/runtime-package.txt DESTINATION . RENAME README.txt)

set(CPACK_PACKAGE_NAME "opr2")
set(CPACK_PACKAGE_VERSION "${PROJECT_VERSION}")
set(CPACK_PACKAGE_FILE_NAME "opr2-${PROJECT_VERSION}-${CMAKE_SYSTEM_NAME}-${CMAKE_SYSTEM_PROCESSOR}")
set(CPACK_GENERATOR "ZIP;TGZ")
set(CPACK_SOURCE_GENERATOR "")
set(CPACK_SOURCE_IGNORE_FILES "/\\.git/;/build/;/analysis/;/pr2/;/CMakeLists\\.txt$;/CMakePresets\\.json$;/\\.gitignore$;/AGENTS\\.md$;/CLAUDE\\.md$")
include(CPack)
# A source archive made from the developer checkout could contain private
# analysis or local data. Source distribution uses Git's tracked tree instead.
file(WRITE "${CPACK_SOURCE_OUTPUT_CONFIG_FILE}"
    "message(FATAL_ERROR \"Source packaging is disabled. Use the tracked Git source tree.\")\n")
