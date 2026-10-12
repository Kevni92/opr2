#pragma once

#include <filesystem>
#include <string>

namespace opr2 {

struct ExecutablePathResult {
    std::filesystem::path path;
    std::string error;

    [[nodiscard]] bool ok() const noexcept { return error.empty(); }
};

[[nodiscard]] ExecutablePathResult executable_path();

} // namespace opr2
