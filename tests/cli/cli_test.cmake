execute_process(
    COMMAND "${OPR2_EXECUTABLE}" --version
    RESULT_VARIABLE version_result
    OUTPUT_VARIABLE version_output
    ERROR_VARIABLE version_error)
if(NOT version_result EQUAL 0)
    message(FATAL_ERROR "--version failed (${version_result}): ${version_error}")
endif()
string(STRIP "${version_output}" version_output)
if(NOT version_output STREQUAL EXPECTED_VERSION)
    message(FATAL_ERROR "--version returned '${version_output}', expected '${EXPECTED_VERSION}'")
endif()

execute_process(
    COMMAND "${OPR2_EXECUTABLE}" --invalid-option
    RESULT_VARIABLE invalid_result
    OUTPUT_VARIABLE invalid_output
    ERROR_VARIABLE invalid_error)
if(invalid_result EQUAL 0)
    message(FATAL_ERROR "unknown option unexpectedly succeeded")
endif()
if(NOT "${invalid_error}" MATCHES "unknown option: --invalid-option")
    message(FATAL_ERROR "unknown option did not produce a helpful diagnostic: ${invalid_error}")
endif()
