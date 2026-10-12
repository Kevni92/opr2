#pragma once

#include <filesystem>
#include <string>
#include <vector>

namespace opr2 {

struct DataFileProblem {
    std::filesystem::path path;
    std::string message;
};

struct DataValidationResult {
    std::vector<std::filesystem::path> valid_files;
    std::vector<DataFileProblem> problems;

    [[nodiscard]] bool ok() const noexcept { return problems.empty(); }
};

// Checks that each required archive is a regular file with the known CPR header.
// No archive contents are extracted, changed, or loaded as code.
[[nodiscard]] DataValidationResult validate_data_directory(const std::filesystem::path& directory);

} // namespace opr2
